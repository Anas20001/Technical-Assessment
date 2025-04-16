# Network Telemetry Data Pipeline

A real-time data streaming and processing pipeline for network telemetry data. This project simulates ingesting network telemetry data into Kafka, processing it with QuixStreams, and storing it in ClickHouse for analysis.

## Architecture

The pipeline consists of the following components:

1. **Data Simulator**: Generates simulated network telemetry data and sends it to Kafka.
2. **Stream Processor**: Processes raw data using QuixStreams and sends it to multiple Kafka topics.
3. **ClickHouse Ingestion**: Consumes processed data from Kafka and inserts it into ClickHouse tables.
4. **AWS S3 Storage**: Stores processed data as Parquet files for long-term storage.
5. **AWS SNS Alerting**: Sends alerts for errors and failures in the pipeline.

## Technology Stack

- **Apache Kafka (KRaft mode)**: Used for message streaming without requiring Zookeeper
- **Kafka UI**: Web-based UI for monitoring Kafka
- **ClickHouse**: Column-oriented database for analytics
- **Tabix**: Web-based UI for ClickHouse
- **QuixStreams**: Python library for stream processing
- **Logfire**: Structured logging solution

## Project Structure

```
.
├── .env                        # Environment variables
├── .github/                    # GitHub workflows and templates
├── Makefile                    # For automating setup and execution
├── README.md                   # This file
├── docker-compose.yml          # Docker Compose file for infrastructure
├── pyproject.toml              # Python project configuration for UV
├── scripts/                    # Shell scripts for running the pipeline
├── src/                        # Source code
│   ├── processor/              # Stream processor code
│   │   ├── clickhouse_ingestion.py # Ingestion of data to ClickHouse
│   │   └── processor.py        # QuixStreams processor
│   ├── schema/                 # Schema definitions
│   │   ├── clickhouse_tables.py # ClickHouse table creation
│   │   └── models.py           # Pydantic models for data validation
│   └── simulator/              # Data simulator
│       └── simulator.py        # Kafka producer for simulated data
└── topic_1.json                # Sample telemetry data
```

## Prerequisites

- Docker and Docker Compose
- Python 3.9+
- UV package manager

## Setup

1. **Install UV**:

   Follow the [official UV installation guide](https://github.com/astral-sh/uv).

2. **Configure environment variables**:

   Copy the `.env.example` file to `.env` and update the values as needed:

   ```bash
   cp .env.example .env
   ```

3. **AWS Configuration (optional)**:

   If you want to use AWS S3 for storage and SNS for alerting, update the following environment variables in the `.env` file:

   ```
   AWS_REGION=us-east-1
   AWS_ACCESS_KEY_ID=your-access-key
   AWS_SECRET_ACCESS_KEY=your-secret-key
   AWS_S3_BUCKET=network-telemetry-data
   AWS_SNS_TOPIC_ARN=arn:aws:sns:us-east-1:123456789012:network-telemetry-alerts
   ```

## Usage

### Running with Make (Recommended)

The easiest way to run the entire pipeline is using the provided Makefile:

```bash
# Start the entire pipeline
make run

# Stop the pipeline
make stop

# Clean up all data
make clean
```

The Makefile automates:
- Environment variable checks
- Dependency validation
- Directory setup
- Service startup
- Schema creation
- Pipeline process management
- Logging (logs stored in the `logs` directory)

Additional make targets:
```bash
# Only check environment variables and dependencies
make check-env check-deps

# Only set up directories and install dependencies
make setup

# Only start the Docker services
make start-services

# Only create Kafka topics and ClickHouse tables
make create-schemas

# Only start the pipeline components
make start-pipeline
```

### Running Manually

Use the provided shell script to start the complete pipeline:

```bash
./scripts/run_pipeline.sh
```

This script will:

1. Install dependencies using UV
2. Start Kafka (in KRaft mode) and ClickHouse using Docker Compose
3. Create necessary Kafka topics and ClickHouse tables
4. Start the data simulator, stream processor, and ClickHouse ingestion components

### Monitoring the Pipeline

- **Kafka UI**: Open http://localhost:8080 in your browser to access the Kafka UI dashboard.
- **ClickHouse Tabix**: Open http://localhost:8081 in your browser to access the ClickHouse Tabix UI.
- **Container Logs**: Use `docker-compose logs -f` to view logs from all containers.
- **Component Logs**: When using the Makefile, component logs are available in the `logs` directory.

### Stopping the Pipeline

When running with `make run`, press Ctrl+C in the terminal or run `make stop` from another terminal.

When running with the shell script, press Ctrl+C in the terminal where the pipeline is running. The cleanup function will stop all components gracefully.

## Running Individual Components

### Data Simulator

```bash
python -m src.simulator.simulator
```

### Stream Processor

```bash
python -m src.processor.processor
```

### ClickHouse Ingestion

```bash
python -m src.processor.clickhouse_ingestion
```

### ClickHouse Table Setup

```bash
python -m src.schema.clickhouse_tables
```

## Data Model

The pipeline processes network telemetry data into three main entities:

1. **Node Data**: Information about network nodes.
2. **Interface Data**: Information about network interfaces associated with nodes.
3. **Address Data**: IP address information associated with interfaces.

### ClickHouse Tables

- `node_data`: Stores information about network nodes
- `interface_data`: Stores information about network interfaces
- `address_data`: Stores IP address information

## Logging

This project uses Logfire for logging. To configure Logfire:

1. Create a Logfire account and obtain a token.
2. Set the `LOGFIRE_TOKEN` environment variable in the `.env` file.

## AWS Integration

### S3 Storage

Processed data is stored in S3 as Parquet files. The files are organized by timestamp:

```
s3://network-telemetry-data/processed/YYYY/MM/DD/HH/batch-id.parquet
```

### SNS Alerting

Alerts are sent to SNS when errors occur in the pipeline. Configure the `AWS_SNS_TOPIC_ARN` environment variable to enable alerting.

## Development

### Adding New Data Sources

To add a new data source:

1. Create a new simulator in the `src/simulator` directory
2. Update the processor to handle the new data format
3. Create new ClickHouse tables if needed

### Adding New Processing Logic

To add new processing logic:

1. Update the QuixStreams processor in `src/processor/processor.py`
2. Create new output topics in Kafka
3. Add new ingestion logic for the new topics

## Troubleshooting

### Common Issues

- **Kafka Connection Errors**: Make sure Kafka is running and the `KAFKA_BOOTSTRAP_SERVERS` environment variable is set correctly.
- **ClickHouse Connection Errors**: Check that ClickHouse is running and the connection parameters are correct.
- **AWS Permission Errors**: Verify your AWS credentials and make sure the IAM user has the necessary permissions.

### Checking Service Status

```bash
docker-compose ps
```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 