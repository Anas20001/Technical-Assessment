import os
import time
import json
import logging
from datetime import datetime

from common import logger
from parser import TelemetryParser
from alerts import AlertManager
from s3_exporter import S3Exporter

# Import required libraries
try:
    from quixstreams import Application
    from quixstreams.dataframe import StreamDataFrame
    QUIX_AVAILABLE = True
except ImportError:
    QUIX_AVAILABLE = False
    from kafka import KafkaConsumer, KafkaProducer


class TelemetryProcessor:
    """
    Processor for network telemetry data.
    Consumes raw telemetry data from Kafka, processes it, and outputs
    structured data to different Kafka topics.
    """
    
    def __init__(self):
        """Initialize the telemetry processor."""
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
        self.raw_topic = os.getenv("KAFKA_RAW_TOPIC", "network-data")
        self.node_topic = os.getenv("KAFKA_NODE_TOPIC", "node-data")
        self.interface_topic = os.getenv("KAFKA_INTERFACE_TOPIC", "interface-data")
        self.address_topic = os.getenv("KAFKA_ADDRESS_TOPIC", "address-data")
        
        # Initialize the parser
        self.parser = TelemetryParser()
        
        # Initialize the alert manager
        self.alert_manager = AlertManager()
        
        # Initialize S3 exporter if enabled
        s3_export_enabled = os.getenv("S3_EXPORT_ENABLED", "false").lower() == "true"
        self.s3_exporter = S3Exporter() if s3_export_enabled else None
        
        logger.info(f"Telemetry processor initialized with bootstrap servers: {self.bootstrap_servers}")
        
    def process_raw_data(self, raw_data):
        """
        Process raw telemetry data and extract structured information.
        
        Args:
            raw_data: Raw telemetry data from Kafka
            
        Returns:
            tuple: (node_data, interface_data, address_data)
        """
        try:
            # Parse raw data into structured format
            node_data, interface_data, address_data = self.parser.parse(raw_data)
            
            # Check for alerts (e.g., interface down)
            self.alert_manager.check_alerts(interface_data)
            
            # Export data to S3 if enabled
            if self.s3_exporter:
                self.s3_exporter.export_batch(raw_data)
            
            return node_data, interface_data, address_data
        
        except Exception as e:
            logger.error(f"Error processing data: {e}")
            self.alert_manager.send_alert("ALERT: Data Processing Error", 
                                        f"Failed to process telemetry data: {e}")
            return [], [], []
    
    def run_with_quix(self):
        """Run processor using QuixStreams."""
        try:
            logger.info("Starting telemetry processor with QuixStreams")
            
            # Initialize SNS for alerting
            self.alert_manager.init_sns_client()
            logger.info("SNS client initialized for alerting")
            
            # Create Kafka application
            logger.info(f"Creating Kafka application with bootstrap servers: {self.bootstrap_servers}")
            app = Application(
                broker_address=self.bootstrap_servers,
                consumer_group="telemetry-processor"
            )
            
            # Configure input/output topics
            input_topic = app.topic(self.raw_topic, value_deserializer='json')
            node_output = app.topic(self.node_topic, value_serializer='json')
            interface_output = app.topic(self.interface_topic, value_serializer='json')
            address_output = app.topic(self.address_topic, value_serializer='json')
            
            # Create dataframe from input topic
            sdf = app.dataframe(input_topic)
            
            # Process and produce to output topics
            def process_and_produce(raw_data, timestamp):
                node_data, interface_data, address_data = self.process_raw_data(raw_data)
                
                # Produce to output topics if data exists
                with app.get_producer() as producer:
                    if node_data:
                        producer.produce(node_output, node_data, timestamp)
                    if interface_data:
                        producer.produce(interface_output, interface_data, timestamp)
                    if address_data:
                        producer.produce(address_output, address_data, timestamp)
                
                return raw_data  # Return data for status logging
            
            # Apply processing and log status
            sdf = sdf.update(process_and_produce)
            sdf = sdf.update(lambda data, ts: logger.info(f"Processed batch with timestamp: {ts}"))
            
            # Run the application
            app.run()
            
        except Exception as e:
            logger.critical(f"Fatal error in telemetry processor: {e}")
            self.alert_manager.send_alert("ALERT: Telemetry Processing Error", 
                                        f"Telemetry processor failed: {e}")
            raise
    
    def run_with_kafka_python(self):
        """Run processor using kafka-python library (fallback)."""
        try:
            logger.info("Starting telemetry processor with kafka-python")
            
            # Initialize consumer
            consumer = KafkaConsumer(
                self.raw_topic,
                bootstrap_servers=self.bootstrap_servers,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                group_id='telemetry-processor'
            )
            
            # Initialize producers
            producers = {
                self.node_topic: KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda m: json.dumps(m).encode('utf-8')
                ),
                self.interface_topic: KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda m: json.dumps(m).encode('utf-8')
                ),
                self.address_topic: KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda m: json.dumps(m).encode('utf-8')
                )
            }
            
            # Process messages
            for message in consumer:
                raw_data = message.value
                node_data, interface_data, address_data = self.process_raw_data(raw_data)
                
                # Produce to output topics if data exists
                if node_data:
                    producers[self.node_topic].send(self.node_topic, node_data)
                if interface_data:
                    producers[self.interface_topic].send(self.interface_topic, interface_data)
                if address_data:
                    producers[self.address_topic].send(self.address_topic, address_data)
                
                # Flush producers
                for producer in producers.values():
                    producer.flush()
                
                logger.info(f"Processed message at offset: {message.offset}")
                
        except Exception as e:
            logger.critical(f"Fatal error in telemetry processor: {e}")
            self.alert_manager.send_alert("ALERT: Telemetry Processing Error", 
                                        f"Telemetry processor failed: {e}")
            raise
    
    def run(self):
        """Run the processor with available library."""
        if QUIX_AVAILABLE:
            self.run_with_quix()
        else:
            self.run_with_kafka_python()


if __name__ == "__main__":
    processor = TelemetryProcessor()
    processor.run() 