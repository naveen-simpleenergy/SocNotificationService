from pyflink.datastream.functions import KeyedCoProcessFunction
from pyflink.datastream.state import ValueStateDescriptor
from pyflink.common.typeinfo import Types
from utils import MessagePayload, NotificationService

class RangeJoinProcessor(KeyedCoProcessFunction):
    def __init__(self):
        self.notification_service = NotificationService()

    def open(self, runtime_context):
        self.range_state = runtime_context.get_state(
            ValueStateDescriptor("range_state", Types.TUPLE([Types.INT(), Types.LONG()]))
        )
        self.event_state = runtime_context.get_state(
            ValueStateDescriptor("event_state", Types.PICKLED_BYTE_ARRAY())
        )
        self.last_emitted_state = runtime_context.get_state(
            ValueStateDescriptor("last_emitted_state", Types.PICKLED_BYTE_ARRAY())
        )
        
    def process_element1(self, event_data: dict, ctx):
        """Process charging events from enriched_stream"""
        if event_data.get("event") not in ["chargingStarted", "socUpdate"]:
            return

        
        self.event_state.update(event_data)
        range_data = self.range_state.value()
        
        if range_data: 
            for payload in self._process_and_notify(event_data, range_data):
                yield payload

    def process_element2(self, range_msg: MessagePayload, ctx):
        """Process range updates from range_stream"""
        range_value = int(range_msg.message_json.get("BCM_RangeDisplay"))        
        self.range_state.update((range_value, range_msg.event_time))
        
        event_data = self.event_state.value()
        if event_data:
            for payload in self._process_and_notify(event_data, (range_value, range_msg.event_time)):
                yield payload

    def _process_and_notify(self, event_data, range_data):
        """Common processing logic"""
        
        
        event_time = event_data["event_time"]
        range_value, range_time = range_data
        
        if abs(event_time - range_time) > 60000:
            return

        payload= {
            **event_data,
            "range": range_value,
            "timestamp": max(event_time, range_time)
        }
        
        current_soc = payload["soc"]
        current_range = payload["range"]
        last_emitted = self.last_emitted_state.value()
        
        if last_emitted:
            last_soc, last_range = last_emitted
            if current_soc == last_soc and abs(current_range - last_range) <= 1:
                return
        
        self.last_emitted_state.update((current_soc, current_range))
        
        print(f"Generated payload: {payload}") 
        yield payload
        
        if event_data["event"] in ["chargingStarted", "socUpdate"]:
            print(f"Dynamic island notification sent for {payload['vin']} at {payload['timestamp']}")
            self.notification_service.send_notification_payload2(
                vin=payload["vin"],
                soc=payload["soc"],
                range=payload["range"],
                time=payload["timestamp"]
            )
        
     