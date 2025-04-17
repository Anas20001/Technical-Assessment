# Network Telemetry Data Simulator

A simulator for generating network telemetry data and sending it to Kafka for testing the streaming pipeline.

## Overview

This simulator reads sample network telemetry data from a JSON file and publishes it to a Kafka topic in batches. It's designed to help test the end-to-end network telemetry processing pipeline without requiring actual network devices.

## Features

- Loads telemetry data from a JSON file
- Sends data to Kafka in configurable batches
- Introduces random variations to simulate changing data
- Sends alerts to AWS SNS if errors occur
- Configurable simulation interval and batch size

## Setup

### Using UV Virtual Environment

We recommend using `uv` for Python environment management:

```bash
# Create a virtual environment
uv venv

# Activate the virtual environment
source .venv/bin/activate  # On Unix/macOS
.venv\Scripts\activate     # On Windows

# Install dependencies
uv pip install -r requirements.txt
```

### Requirements

Make sure your environment has the following dependencies installed:

- Python 3.8+
- confluent-kafka
- boto3
- logfire
- python-dotenv

Create a `requirements.txt` file in the simulator directory if it doesn't exist.

## Configuration

The simulator reads configuration from environment variables. You can set these in a `.env` file at the root of the project:

```
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_RAW_TOPIC=network-data

# Simulation Parameters
SAMPLE_DATA_FILE=./test_data.json
SIMULATION_INTERVAL_SECONDS=5
BATCH_SIZE=10

# AWS Configuration (optional, for alerts)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_SNS_TOPIC_ARN=

# Logging Configuration (optional)
LOGFIRE_API_KEY=
```

## Running the Simulator

After starting the infrastructure with `make run`, you can run the simulator:

```bash
# From the simulator directory with UV environment activated
python src/simulator.py
```

Or use the provided shell script:

```bash
# Make the script executable
chmod +x run_simulator.sh

# Run the simulator
./run_simulator.sh
```

The simulator will:
1. Load the sample data from the configured JSON file
2. Connect to Kafka 
3. Send batches of data at the configured interval
4. Log information about each batch sent

Press Ctrl+C to stop the simulator.

## Sample Data Format

The sample data in `test_data.json` should follow this format:

```json
[
  [
    {
      "path": ".node.srl.interface.subinterface.ipv4.address",
      "entries": [
        {
          "keys": {
            "address_ip-prefix": "12.0.0.0/31",
            "interface_name": "ethernet-1/33",
            "node_name": "srl-os",
            "subinterface_index": "0"
          },
          "fields": {
            "origin": "static",
            "status": "preferred"
          }
        }
      ]
    }
  ]
]
```

The format matches router telemetry data with paths, keys and fields. 