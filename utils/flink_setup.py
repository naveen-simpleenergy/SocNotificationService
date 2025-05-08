from pyflink.datastream import StreamExecutionEnvironment
from pyflink.common import Configuration
from pathlib import Path
from .kafka_setup import KafkaConfig

def setup_flink_environment():
    # parallelism = KafkaConfig.get_kafka_partition_count()
    config = Configuration()
    env = StreamExecutionEnvironment.get_execution_environment(configuration=config)
    env.set_parallelism(2)

 
    checkpoint_config = env.get_checkpoint_config()
    checkpoint_config.set_checkpoint_interval(5 * 60 * 1000)  
    checkpoint_config.set_checkpoint_timeout(25 * 60 * 1000)  
    checkpoint_config.set_tolerable_checkpoint_failure_number(5)
    checkpoint_config.set_max_concurrent_checkpoints(1)
    checkpoint_config.set_min_pause_between_checkpoints(60 * 1000) 
    checkpoint_config.enable_unaligned_checkpoints(True)

    print("Flink environment setup complete")
    return env

