from pyflink.datastream import StreamExecutionEnvironment
from pyflink.common.watermark_strategy import WatermarkStrategy
from pyflink.common.time import Duration
from pyflink.common.typeinfo import Types
from dotenv import get_key, load_dotenv
from udfs.GeofenceProcessor import GeofenceProcessFunction
from utils  import setup_flink_environment,KafkaConfig,NotificationService
import os,json,logging
from utils import MessagePayload
from udfs import VehicleStateProcessor,GeofenceCoProcessFunction
load_dotenv()
import sys

def main():
 
    env = setup_flink_environment()
    hmi_source = KafkaConfig.create_hmi_source()
    bcm_source = KafkaConfig.create_bcm_source()
    bcm_range_source = KafkaConfig.create_range_source()
    
    watermark_strategy = WatermarkStrategy.for_bounded_out_of_orderness(Duration.of_millis(5000))
    
    # pipeline for HMI and BCM data
    # hmi_stream = env.from_source(source=hmi_source,watermark_strategy=watermark_strategy,source_name="HMI Source")\
    #     .map(MessagePayload, output_type=Types.PICKLED_BYTE_ARRAY())\
    #     .filter(lambda payload: 'EffectiveSOC' in payload.message_json.keys())\
    #     .key_by(lambda payload: payload.vin)
    
    # bcm_stream = env.from_source(source=bcm_source, watermark_strategy=watermark_strategy, source_name="BCM Source")\
    #             .map( MessagePayload , output_type=Types.PICKLED_BYTE_ARRAY())\
    #             .filter(lambda payload: 'BCM_ChargerDocked' in payload.message_json.keys() )\
    #             .key_by(lambda payload: payload.vin)

    # hmi_stream.connect(bcm_stream).process(VehicleStateProcessor()) 
    
    # pipeline for geofence data
    
    geo_fence_stream = env.from_source(source=KafkaConfig.create_geofence_source(), watermark_strategy=watermark_strategy, source_name="Geo Source")\
                .map(lambda x: MessagePayload(x), output_type=Types.PICKLED_BYTE_ARRAY())\
                .key_by(lambda payload: payload.vin)\
                
    
    location_stream = env.from_source(source=KafkaConfig.create_location_coordinates_source(), watermark_strategy=watermark_strategy, source_name="Location Updates")\
                .map(lambda x: MessagePayload(x), output_type=Types.PICKLED_BYTE_ARRAY())\
                .key_by(lambda payload: payload.vin)\
                    
    connected_stream = geo_fence_stream.connect(location_stream).process(GeofenceCoProcessFunction())
         
               
    connected_stream.print()
    
   
    
    env.execute("real-time-vehicle-monitoring")


if __name__ == "__main__":
    main()
