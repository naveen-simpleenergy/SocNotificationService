from pyflink.datastream.functions import CoProcessFunction, KeyedCoProcessFunction
from pyflink.datastream.state import ValueStateDescriptor
from pyflink.common.typeinfo import Types
from datetime import datetime, timezone
from utils import MessagePayload, NotificationService

class VehicleStateProcessor(CoProcessFunction):
    def __init__(self):
        self.hmi_time_state = None
        self.bcm_time_state = None
        self.current_soc_state = None
        self.current_charging_state = None
        self.prev_charging_state = None
        self.last_event_type = None
        self.has_seen_charger_connected_state = None
        self.range_state = None
        self.notification_service = NotificationService()

    def open(self, runtime_context):
        self.hmi_time_state = runtime_context.get_state(
            ValueStateDescriptor("hmi_event_time", Types.LONG()))
        self.bcm_time_state = runtime_context.get_state(
            ValueStateDescriptor("bcm_event_time", Types.LONG()))
        self.current_soc_state = runtime_context.get_state(
            ValueStateDescriptor("current_soc", Types.FLOAT()))
        self.current_charging_state = runtime_context.get_state(
            ValueStateDescriptor("current_charging", Types.INT()))
        self.prev_charging_state = runtime_context.get_state(
            ValueStateDescriptor("prev_charging", Types.INT()))
        self.last_event_type = runtime_context.get_state(
            ValueStateDescriptor("last_event_type", Types.STRING()))
        self.has_seen_charger_connected_state = runtime_context.get_state(
            ValueStateDescriptor("has_seen_charger_connected_state", Types.BOOLEAN()))
        self.range_state = runtime_context.get_state(
            ValueStateDescriptor("range_state", Types.FLOAT()))

    def process_element1(self, hmi_msg: MessagePayload, ctx):
        soc = float(hmi_msg.message_json.get('EffectiveSOC'))
        vin = hmi_msg.vin
        hmi_time = hmi_msg.event_time

        prev_hmi_time = self.hmi_time_state.value()
        if prev_hmi_time is None or hmi_time >= prev_hmi_time:
            self.hmi_time_state.update(hmi_time)
            self.current_soc_state.update(soc)

        if self.bcm_time_state.value() is not None :
            self._maybe_notify(vin)

    def process_element2(self, bcm_msg: MessagePayload, ctx):
        charging_status = int(bcm_msg.message_json.get('BCM_ChargerDocked'))
        vin = bcm_msg.vin
        bcm_time = bcm_msg.event_time

        prev_bcm_time = self.bcm_time_state.value()
        if prev_bcm_time is None or bcm_time >= prev_bcm_time:
            self.bcm_time_state.update(bcm_time)

            prev_charging = self.current_charging_state.value()
            if prev_charging is None:
                self.prev_charging_state.update(charging_status)
                self.current_charging_state.update(charging_status)
                return

            self.prev_charging_state.update(prev_charging)
            self.current_charging_state.update(charging_status)

        if self.hmi_time_state.value() is not None:
            self._maybe_notify(vin)

    def process_element3(self, range_msg: MessagePayload, ctx):
        range_value = float(range_msg.message_json.get('BCM_RangeDisplay', None))
        vin = range_msg.vin
        
        
    def _maybe_notify(self, vin):
        hmi_time = self.hmi_time_state.value()
        bcm_time = self.bcm_time_state.value()
        
        if hmi_time is None or bcm_time is None:
            return

        if abs(hmi_time - bcm_time) > 60000:
            return
        
        print(f"Processing notification for VIN={vin} with HMI time {hmi_time} and BCM time {bcm_time} and soc: {self.current_soc_state.value()} ")
        print(f"Current SOC: {self.current_soc_state.value()}, Current Charging State: {self.current_charging_state.value()}, Previous Charging State: {self.prev_charging_state.value()}")
        print(f"Last Event Type: {self.last_event_type.value()}, Has Seen Charger Connected State: {self.has_seen_charger_connected_state.value()}")
        
        soc = self.current_soc_state.value()
        charging = self.current_charging_state.value()
        prev_charging = self.prev_charging_state.value()
        last_event = self.last_event_type.value()
        event_time = max(hmi_time, bcm_time)

        if soc == 100:
            new_event = "batteryfull" if charging == 1 else None
            if new_event and new_event != last_event:
                self._send_alert(vin, event_time, soc, new_event)
                self.has_seen_charger_connected_state.update(False)
            return

        if soc == 20:
            new_event = "lowbattery" if charging == 0 else None
            if new_event and new_event != last_event:
                self._send_alert(vin, event_time, soc, new_event)
            return

        if charging != prev_charging:
            if charging == 1:
                new_event = "chargingStarted"
                if new_event != last_event:
                    self._send_alert(vin, event_time, soc, new_event)
                    self.has_seen_charger_connected_state.update(True)
            elif charging == 0:
                if self.has_seen_charger_connected_state.value():
                    new_event = "chargerRemoved"
                    if new_event != last_event:
                        self._send_alert(vin, event_time, soc, new_event)
                        self.has_seen_charger_connected_state.update(False)
    
    def on_timer(self, timestamp: int, ctx: 'KeyedCoProcessFunction.OnTimerContext'):
        hmi_data = self.hmi_state.value()
        bcm_data = self.bcm_state.value()

        if hmi_data is None or bcm_data is None:
            return

        vin = hmi_data.get("vin") or bcm_data.get("vin")
        soc = hmi_data.get("soc", -1)
        vehicle_range = hmi_data.get("range", -1)
        charging_status = hmi_data.get("charging_status", "").lower()
        charger_connected = bcm_data.get("charger_connected", False)
        event_time = hmi_data.get("timestamp") or bcm_data.get("timestamp")  # in ms

        # Send SOC-based alerts
        self.maybe_notify(vin=vin, soc=soc, charger_connected=charger_connected, timestamp=event_time)

        # Send SOC + range when charging
        is_charging = charging_status == "charging"
        self.maybe_notify_range_soc(
            vin=vin,
            soc=soc,
            range_value=vehicle_range,
            timestamp=event_time,
            charging=is_charging
        )
 

    def send_range_soc_update(self, vin: str, soc: float, range_value: float, timestamp: int, charging: bool):
        """
        Sends SOC + range notification only when charging and data is fresh.
        """
        # Convert timestamp (ms) to datetime
        last_time = timestamp
        event_dt = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)

        if (last_time - event_dt).total_seconds() > 60:
            return

        if charging and soc >= 0 and range_value >= 0:
            self.notifier.send_range_soc_update(
                vin=vin,
                soc=soc,
                range_value=range_value,
                timestamp=event_dt
            )

        

    def _send_alert(self, vin, event_time, soc, event):
        try:
            print(f"Sending '{event}' notification for VIN={vin}: {soc} at {event_time}")
            self.last_event_type.update(event)
            self.notification_service.send_notification(
                vin=vin,
                soc=soc,
                event=event,
            )
        except Exception as e:
            print(f"Notification failed for VIN={vin}: {str(e)}")
