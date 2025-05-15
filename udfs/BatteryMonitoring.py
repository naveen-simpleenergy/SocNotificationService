from doctest import debug
import time
from pyflink.datastream.functions import CoProcessFunction
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


    def process_element1(self, hmi_msg: MessagePayload, ctx):
        soc = float(hmi_msg.message_json.get('EffectiveSOC', 0.0))
        vin = hmi_msg.vin
        hmi_time = hmi_msg.event_time

        prev_hmi_time = self.hmi_time_state.value()
        if prev_hmi_time is None or hmi_time >= prev_hmi_time:
            self.hmi_time_state.update(hmi_time)
            self.current_soc_state.update(soc)

        if self.bcm_time_state.value() is not None:
            self._maybe_notify(vin)

    def process_element2(self, bcm_msg: MessagePayload, ctx):
        charging_status = int(bcm_msg.message_json.get('BCM_ChargerDocked', 0))
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

    def _maybe_notify(self, vin):
    
        hmi_time = self.hmi_time_state.value()
        bcm_time = self.bcm_time_state.value()
        
        if hmi_time is None or bcm_time is None:
            return

        if abs(hmi_time - bcm_time) > 60000:
            return
        
        soc = self.current_soc_state.value()
        charging = self.current_charging_state.value()
        prev_charging = self.prev_charging_state.value()
        last_event = self.last_event_type.value()
        event_time = max(hmi_time, bcm_time)
        debug_time =event_time
        event_dt = datetime.fromtimestamp(event_time // 1000, tz=timezone.utc)

        if soc == 100:
            if charging == 1 and last_event != "battery-full":
                self._send_alert(vin, debug_time, event_dt, soc, "battery-full")
            return

        if soc == 20 and charging == 0:
            if last_event != "low-battery":
                self._send_alert(vin, debug_time, event_dt, soc, "low-battery")
            return
        elif soc == 20 and charging == 1 :
            return

        if prev_charging is not None and charging != prev_charging:
            if charging == 1 and last_event != "charger-connected":
                self._send_alert(vin,debug_time, event_dt,soc,"charger-connected")
            elif charging == 0 and last_event != "charger-disconnected":
                self._send_alert(vin, debug_time,event_dt,soc,"charger-disconnected")

    def _send_alert(self, vin, debug_time, timestamp,soc, event):
        try:
            print(f"Sending '{event}' notification for VIN={vin}: {soc} at {debug_time}")
            self.last_event_type.update(event)
            self.notification_service.send_notification(
                vin=vin,
                timestamp=timestamp,
                soc=soc,
                event=event,
            )
        except Exception as e:
            print(f"Notification failed for VIN={vin}: {str(e)}")
