from pyflink.datastream import StreamExecutionEnvironment
from pyflink.common.watermark_strategy import WatermarkStrategy
from pyflink.common.time import Duration
from pyflink.common.typeinfo import Types
from dotenv import load_dotenv
from utils  import setup_flink_environment,KafkaConfig,NotificationService
import os,json,logging
from utils import MessagePayload
from udfs import VehicleStateProcessor
load_dotenv()
import sys

def main():
 
    env = setup_flink_environment()
    hmi_source = KafkaConfig.create_hmi_source()
    bcm_source = KafkaConfig.create_bcm_source()
    
    watermark_strategy = WatermarkStrategy.for_bounded_out_of_orderness(Duration.of_millis(5000))
    
    hmi_stream = env.from_source(source=hmi_source,watermark_strategy=watermark_strategy,source_name="HCM Source")\
        .map(MessagePayload, output_type=Types.PICKLED_BYTE_ARRAY()).key_by(lambda payload: payload.vin)
    
    bcm_stream = env.from_source( source=bcm_source, watermark_strategy=watermark_strategy, source_name="BCM Source")\
    .map( MessagePayload , output_type=Types.PICKLED_BYTE_ARRAY()).key_by(lambda payload: payload.vin)
    

    processed_stream= hmi_stream.connect(bcm_stream).process(VehicleStateProcessor())\
        .map(lambda payload : json.dumps(payload.message_json), output_type=Types.STRING())  
        
    processed_stream.print()

    env.execute("SOC Notification Service")


if __name__ == "__main__":
    main()
