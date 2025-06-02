from pyflink.datastream.functions import KeyedCoProcessFunction
from pyflink.datastream.state import ValueStateDescriptor
from pyflink.common.typeinfo import Types
from utils import MessagePayload, NotificationService

class RangeJoinProcessor(KeyedCoProcessFunction):
    def __init__(self):
        self.notification_service = NotificationService()

    def open(self, runtime_context):
        # Store range as (value, timestamp) tuple
        self.range_state = runtime_context.get_state(
            ValueStateDescriptor("range_state", Types.TUPLE([Types.FLOAT(), Types.LONG()]))
        )
        # Store last charging event
        self.event_state = runtime_context.get_state(
            ValueStateDescriptor("event_state", Types.PICKLED_BYTE_ARRAY())
        )

    def process_element1(self, event_data: dict, ctx):
        """Process charging events from enriched_stream"""
        if event_data.get("event") != "chargingStarted":
            return

        # Store event data
        self.event_state.update(event_data)
        
        # Get current range data
        range_data = self.range_state.value()
        self._process_and_notify(event_data, range_data)

    def process_element2(self, range_msg: MessagePayload, ctx):
        """Process range updates from range_stream"""
        # Extract range value and timestamp
        range_value = float(range_msg.message_json.get("BCM_RangeDisplay"))
        range_time = range_msg.event_time
        
        # Update state with tuple (value, timestamp)
        self.range_state.update((range_value, range_time))
        
        # Get last charging event
        event_data = self.event_state.value()
        self._process_and_notify(event_data, (range_value, range_time))

    def _process_and_notify(self, event_data, range_data):
        """Common processing logic"""
        if not event_data or not range_data:
            return

        event_time = event_data["event_time"]
        range_value, range_time = range_data
        
        if abs(event_time - range_time) > 60000:
            return

        payload = {
            "vin": event_data["vin"],
            "soc": event_data["soc"],
            "range": range_value,
            "timestamp": max(event_time, range_time)
        }

        print(f"Generated payload: {payload}") 
        yield payload
        # Send notification
        # self.notification_service.send_notification_payload2(
        #     vin=payload["vin"],
        #     soc=payload["soc"],
        #     range=payload["range"],
        #     time=payload["timestamp"]
        # )
