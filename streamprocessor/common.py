import os
import logging
from datetime import datetime
try:
    import logfire
    LOGFIRE_AVAILABLE = True
except ImportError:
    LOGFIRE_AVAILABLE = False

from dotenv import load_dotenv
import uuid

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.getenv("LOG_FILE", "logs/processor.log")),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("stream_processor")

# Setup logfire if available
if LOGFIRE_AVAILABLE and os.getenv("LOGFIRE_API_KEY"):
    logfire.configure(
        api_key=os.getenv("LOGFIRE_API_KEY"),
        service_name="network-telemetry-processor",
        service_version=os.getenv("SERVICE_VERSION", "0.1.0"),
    )

# Kafka parameters
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_RAW_TOPIC = os.getenv("KAFKA_RAW_TOPIC", "network-data")
KAFKA_NODE_TOPIC = os.getenv("KAFKA_NODE_TOPIC", "node-data")
KAFKA_INTERFACE_TOPIC = os.getenv("KAFKA_INTERFACE_TOPIC", "interface-data")
KAFKA_ADDRESS_TOPIC = os.getenv("KAFKA_ADDRESS_TOPIC", "address-data")
CONSUMER_GROUP = os.getenv("KAFKA_CONSUMER_GROUP", f"telemetry-processor-{uuid.uuid4()}")

# S3 parameters
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET", "network-telemetry-data")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")

# SNS parameters
AWS_SNS_TOPIC_ARN = os.getenv("AWS_SNS_TOPIC_ARN", "") 