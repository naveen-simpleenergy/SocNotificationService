from pyflink.datastream.functions import CoProcessFunction
from pyflink.datastream.state import ValueStateDescriptor
from pyflink.common.typeinfo import Types
from utils import MessagePayload, NotificationService
from datetime import datetime, timezone

class VehicleStateProcessor(CoProcessFunction):
    def __init__(self):
        self.hmi_time_state = None
        self.bcm_time_state = None
        self.current_soc_state = None
        self.current_charging_state = None
        self.prev_charging_state = None
        self.notification_service = None

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
        self.notification_service = NotificationService()

    def process_element1(self, hmi_msg: MessagePayload, ctx):
        vin = hmi_msg.vin
        soc = float(hmi_msg.message_json.get('EffectiveSOC'))
        hmi_time = hmi_msg.event_time

        # Always keep the latest HMI event
        prev_hmi_time = self.hmi_time_state.value()
        if prev_hmi_time is None or hmi_time >= prev_hmi_time:
            self.hmi_time_state.update(hmi_time)
            self.current_soc_state.update(soc)

        bcm_time = self.bcm_time_state.value()
        if bcm_time is not None:
            self._maybe_notify(vin)

    def process_element2(self, bcm_msg: MessagePayload, ctx):
        vin = bcm_msg.vin
        charging_status = int(bcm_msg.message_json.get('BCM_ChargingOnProgress', 0))
        bcm_time = bcm_msg.event_time

        # Always keep the latest BCM event
        prev_bcm_time = self.bcm_time_state.value()
        if prev_bcm_time is None or bcm_time >= prev_bcm_time:
            self.bcm_time_state.update(bcm_time)
            prev_charging = self.current_charging_state.value()
            self.prev_charging_state.update(prev_charging if prev_charging is not None else charging_status)
            self.current_charging_state.update(charging_status)

        hmi_time = self.hmi_time_state.value()
        if hmi_time is not None:
            self._maybe_notify(vin)

    def _maybe_notify(self, vin):
        hmi_time = self.hmi_time_state.value()
        bcm_time = self.bcm_time_state.value()
        soc = self.current_soc_state.value()
        charging = self.current_charging_state.value()
        prev_charging = self.prev_charging_state.value()

        # Only proceed if both events are present and within 1 minute
        if hmi_time is not None and bcm_time is not None:
            time_diff = abs(hmi_time - bcm_time)
            if time_diff <= 60000:
                event_time = max(hmi_time, bcm_time)
                # event_dt = datetime.fromtimestamp(event_time // 1000, tz=timezone.utc)
                event_dt=event_time
                
                if soc is not None and soc <= 20 and charging == 0:
                    self._send_alert(vin, event_dt, "Critical battery level! Please plug in charger immediately.")
                
                if soc is not None and soc >= 100 and charging == 1:
                    self._send_alert(vin, event_dt, "Battery fully charged! Please disconnect charger.")
                
                if prev_charging is not None and charging != prev_charging:
                    status = "connected" if charging == 1 else "disconnected"
                    self._send_alert(vin, event_dt, f"Charger {status}. Current SOC: {soc}%")
                # Clear state after notification window
                self._clear_states()

    def _send_alert(self, vin, timestamp, message):
        try:
            print(f"Sending notification to {vin}: {message} at {timestamp}")
            
            self.notification_service.send_notification(
                recipient="naveen@simpleenergy.in",
                vin=vin,
                timestamp=timestamp,
                message=message
            )
            
            print(f"Notification successfully sent to {vin}")
        except Exception as e:
            print(f"Notification failed for {vin}: {str(e)}")


    def _clear_states(self):
        self.hmi_time_state.clear()
        self.bcm_time_state.clear()
        self.current_soc_state.clear()
        self.current_charging_state.clear()
        self.prev_charging_state.clear()
