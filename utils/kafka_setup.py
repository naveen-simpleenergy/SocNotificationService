from pyflink.datastream.connectors.kafka import KafkaSource, KafkaOffsetsInitializer
from kafka.admin import KafkaAdminClient
from pyflink.common.serialization import SimpleStringSchema
from pyflink.common.typeinfo import Types
import os 
from dotenv import load_dotenv
load_dotenv()


class KafkaConfig:
    CONSUMER_BROKER = os.getenv("PROD_KAFKA_BROKER")
    CONSUMER_USERNAME = os.getenv("PROD_KAFKA_USERNAME")
    CONSUMER_PASSWORD = os.getenv("PROD_KAFKA_PASSWORD")
    INPUT_TOPIC_1 = os.getenv("INPUT_TOPIC_1")
    INPUT_TOPIC_2 = os.getenv("INPUT_TOPIC_2")
    INPUT_TOPIC_3 = os.getenv("INPUT_TOPIC_3")
    CONSUMER_GROUP_ID = os.getenv("CONSUMER_GROUP_ID")
    
    
    PRODUCER_BROKERS = os.getenv("PROD_KAFKA_BROKER", "").split(',')
    PRODUCER_USERNAME = os.getenv("PROD_KAFKA_USERNAME")
    PRODUCER_PASSWORD = os.getenv("PROD_KAFKA_PASSWORD")

    SASL_MECHANISMS = os.getenv("SASL_MECHANISMS", "SCRAM-SHA-256")
    SECURITY_PROTOCOL = os.getenv("SECURITY_PROTOCOL", "SASL_PLAINTEXT")


    @staticmethod
    def get_kafka_partition_count():
        """Fetch the number of partitions for the Kafka topic with SASL authentication."""
        print("hello")
        admin_client = KafkaAdminClient(
            bootstrap_servers=KafkaConfig.CONSUMER_BROKER,
            security_protocol=KafkaConfig.SECURITY_PROTOCOL,
            sasl_mechanism=KafkaConfig.SASL_MECHANISMS,
            sasl_plain_username=KafkaConfig.CONSUMER_USERNAME,
            sasl_plain_password=KafkaConfig.CONSUMER_PASSWORD
        )

        try:
            topic_metadata = admin_client.describe_topics([KafkaConfig.INPUT_TOPIC_3])

            topic_info = next((topic for topic in topic_metadata if topic['topic'] == KafkaConfig.INPUT_TOPIC_3), None)

            if topic_info is None:
                raise ValueError(f"Topic {KafkaConfig.INPUT_TOPIC_3} not found")

            if topic_info['error_code'] != 0:
                raise ValueError(f"Error fetching topic metadata: {topic_info['error_code']}")

            num_partitions = len(topic_info['partitions'])

            return num_partitions
        except Exception as e:
            print(f"Error getting partition count: {str(e)}")
            return None
        finally:
            admin_client.close()
        
    def create_hmi_source():

        return KafkaSource.builder() \
            .set_bootstrap_servers(KafkaConfig.CONSUMER_BROKER) \
            .set_topics(KafkaConfig.INPUT_TOPIC_1) \
            .set_group_id(KafkaConfig.CONSUMER_GROUP_ID) \
            .set_starting_offsets(KafkaOffsetsInitializer.latest()) \
            .set_value_only_deserializer(SimpleStringSchema()) \
            .set_property("security.protocol", KafkaConfig.SECURITY_PROTOCOL) \
            .set_property("sasl.mechanism", KafkaConfig.SASL_MECHANISMS) \
            .set_property("sasl.jaas.config",
                          f"org.apache.kafka.common.security.scram.ScramLoginModule required "
                          f"username='{KafkaConfig.CONSUMER_USERNAME}' password='{KafkaConfig.CONSUMER_PASSWORD}';") \
            .set_property("enable.auto.commit", "true") \
            .build()

    def create_bcm_source():
        return KafkaSource.builder() \
            .set_bootstrap_servers(KafkaConfig.CONSUMER_BROKER) \
            .set_topics(KafkaConfig.INPUT_TOPIC_2) \
            .set_group_id(KafkaConfig.CONSUMER_GROUP_ID) \
            .set_starting_offsets(KafkaOffsetsInitializer.latest()) \
            .set_value_only_deserializer(SimpleStringSchema()) \
            .set_property("security.protocol", KafkaConfig.SECURITY_PROTOCOL) \
            .set_property("sasl.mechanism", KafkaConfig.SASL_MECHANISMS) \
            .set_property("sasl.jaas.config",
                          f"org.apache.kafka.common.security.scram.ScramLoginModule required "
                          f"username='{KafkaConfig.CONSUMER_USERNAME}' password='{KafkaConfig.CONSUMER_PASSWORD}';") \
            .set_property("enable.auto.commit", "true") \
            .build()
            
    def create_geofence_source():
        print("Creating geofence source with topic:", KafkaConfig.INPUT_TOPIC_3)
        return KafkaSource.builder() \
            .set_bootstrap_servers(KafkaConfig.CONSUMER_BROKER) \
            .set_topics(KafkaConfig.INPUT_TOPIC_3) \
            .set_group_id(KafkaConfig.CONSUMER_GROUP_ID) \
            .set_starting_offsets(KafkaOffsetsInitializer.latest()) \
            .set_value_only_deserializer(SimpleStringSchema()) \
            .set_property("security.protocol", KafkaConfig.SECURITY_PROTOCOL) \
            .set_property("sasl.mechanism", KafkaConfig.SASL_MECHANISMS) \
            .set_property("sasl.jaas.config",
                          f"org.apache.kafka.common.security.scram.ScramLoginModule required "
                          f"username='{KafkaConfig.CONSUMER_USERNAME}' password='{KafkaConfig.CONSUMER_PASSWORD}';") \
            .set_property("enable.auto.commit", "true") \
            .build()
