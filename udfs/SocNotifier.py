
from pyflink.datastream.functions import CoProcessFunction
from pyflink.datastream.state import ValueStateDescriptor
from pyflink.common.typeinfo import Types

from utils import MessagePayload

class helper(CoProcessFunction):

    def open(self, runtime_context):
        pass

    def process_element1(self, hmi_event:MessagePayload, ctx):
       
        print(f"[HMI STREAM] VIN: {hmi_event.vin}, Data: {hmi_event.message_json}")
        yield hmi_event  

    def process_element2(self, bcm_event:MessagePayload, ctx):
        
        print(f"[BCM STREAM] VIN: {bcm_event.vin}, Data: {bcm_event.message_json}")
        yield bcm_event 