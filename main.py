from pyflink.datastream import StreamExecutionEnvironment
from pyflink.common.watermark_strategy import WatermarkStrategy
from pyflink.common.time import Duration
from pyflink.common.typeinfo import Types
from dotenv import get_key, load_dotenv
from utils  import setup_flink_environment,KafkaConfig,NotificationService
import os,json,logging
from utils import MessagePayload
from udfs import VehicleStateProcessor,RangeJoinProcessor
load_dotenv()
import sys

def main():
 
    env = setup_flink_environment()
    hmi_source = KafkaConfig.create_hmi_source()
    bcm_source = KafkaConfig.create_bcm_source()
    range_source = KafkaConfig.create_range_source()
    
    watermark_strategy = WatermarkStrategy.for_bounded_out_of_orderness(Duration.of_millis(5000))
    
    hmi_stream = env.from_source(source=hmi_source,watermark_strategy=watermark_strategy,source_name="HMI Source")\
                    .map(MessagePayload, output_type=Types.PICKLED_BYTE_ARRAY())\
                    .filter(lambda payload: 'EffectiveSOC' in payload.message_json.keys())\
                    .key_by(lambda payload: payload.vin)
    
    bcm_stream = env.from_source(source=bcm_source, watermark_strategy=watermark_strategy, source_name="BCM Source")\
                    .map( MessagePayload , output_type=Types.PICKLED_BYTE_ARRAY())\
                    .filter(lambda payload: 'BCM_ChargingOnProgress' in payload.message_json.keys() )\
                    .key_by(lambda payload: payload.vin)
    
    range_stream = env.from_source(source=range_source, watermark_strategy=watermark_strategy, source_name="Range Source")\
                      .map(MessagePayload, output_type=Types.PICKLED_BYTE_ARRAY())\
                      .filter(lambda payload: 'BCM_RangeDisplay' in payload.message_json.keys())\
                      .key_by(lambda payload: payload.vin)


    

    enriched_stream = hmi_stream.connect(bcm_stream)\
        .key_by(lambda hmi_payload : hmi_payload.vin,lambda bcm_payload : bcm_payload.vin) \
        .process(VehicleStateProcessor())\
    
    
    final_stream = enriched_stream.connect(range_stream)\
        .key_by(lambda event_dict : event_dict["vin"], lambda range_payload : range_payload.vin)\
        .process(RangeJoinProcessor())\
        .map(lambda x: json.dumps(x), output_type=Types.STRING())
        
    final_stream.print()

    env.execute("SOC Notification Service")


if __name__ == "__main__":
    main()
