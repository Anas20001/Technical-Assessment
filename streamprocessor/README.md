# Network Telemetry Stream Processor

This component processes network telemetry data from Kafka and:
1. Sends processed data to Kafka topics for ClickHouse ingestion
2. Exports processed data to S3 as Parquet files
3. Sends alerts to SNS when processing errors occur

## Architecture

The processor consists of the following components:

- **common.py**: Shared configuration and utilities
- **parser.py**: Data extraction and normalization
- **processor.py**: Main streaming application using QuixStreams
- **s3_exporter.py**: Parquet file creation and S3 upload
- **alerts.py**: AWS SNS alerting for error conditions

## Data Flow

1. Raw telemetry data is consumed from the `network-data` Kafka topic
2. Data is parsed into node, interface, and address data
3. Processed data is sent to dedicated Kafka topics:
   - `node-data`
   - `interface-data`
   - `address-data`
4. The same processed data is stored in S3 as Parquet files
5. If any errors occur during processing, alerts are sent to SNS

## Running Locally

To run the processor locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp ../.env.example .env
# Edit .env with your configuration

# Run the processor
python processor.py
```

## Docker Deployment

To build and run using Docker:

```bash
# Build the image
docker build -t network-telemetry-processor .

# Run the container
docker run -d --name processor \
  --env-file .env \
  --network=host \
  network-telemetry-processor
```

## Environment Variables

See `.env.example` for the required environment variables.

Key variables:
- `KAFKA_RAW_TOPIC`: Topic for raw telemetry data
- `KAFKA_NODE_TOPIC`, `KAFKA_INTERFACE_TOPIC`, `KAFKA_ADDRESS_TOPIC`: Output topics
- `AWS_S3_BUCKET`: S3 bucket for Parquet files
- `AWS_SNS_TOPIC_ARN`: SNS topic ARN for alerting
- `LOGFIRE_API_KEY`: API key for Logfire logging

## Dependencies

- QuixStreams: Stream processing framework for Kafka
- Pandas/PyArrow: For DataFrame handling and Parquet creation
- Boto3: For AWS S3 integration and SNS alerting
- Logfire: Structured logging with enhanced observability 