#!/usr/bin/env python3
import json
import os
import time
import uuid
import signal
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from quixstreams import Application

# Set up paths - stay within simulator directory
SCRIPT_DIR = Path(__file__).parent.absolute()
SIM_DIR = Path(__file__).parent.parent.absolute()
ENV_FILE = SIM_DIR / ".env"

# Create minimal .env if not exists
if not ENV_FILE.exists():
    print(f"Creating .env file in {SIM_DIR}")
    with open(ENV_FILE, "w") as f:
        f.write("KAFKA_RAW_TOPIC=network-data\n")
        f.write("SIMULATION_INTERVAL_SECONDS=5\n")
        f.write("SIMULATOR_KAFKA_BOOTSTRAP_SERVERS=localhost:9092\n")

# Load environment variables
load_dotenv(ENV_FILE)

# Configuration
INTERVAL = int(os.getenv("SIMULATION_INTERVAL_SECONDS", "5"))
KAFKA_SERVERS = os.getenv("SIMULATOR_KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_RAW_TOPIC", "network-data")
DATA_FILE = os.getenv("SAMPLE_DATA_FILE", str(SIM_DIR / "test_data.json"))

# Graceful shutdown handling
running = True
def signal_handler(sig, frame):
    global running
    running = False
    print("\nShutting down...")
signal.signal(signal.SIGINT, signal_handler)

def main():
    """Main simulator function"""
    print(f"Network Telemetry Simulator")
    
    # Load test data
    try:
        with open(DATA_FILE, 'r') as f:
            test_data = json.load(f)
            print(f"Loaded test data: {len(test_data)} batches")
    except Exception as e:
        print(f"Error loading test data: {e}")
        return
    
    # Setup Kafka
    print(f"Connecting to Kafka: {KAFKA_SERVERS}")
    print(f"Topic: {KAFKA_TOPIC}")
    
    try:
        # Initialize application with producer configs
        app = Application(
            broker_address=KAFKA_SERVERS,
            consumer_group=f"simulator-{uuid.uuid4()}",
            producer_extra_config={'enable.idempotence': False}
        )
        
        # Get producer from the application
        producer = app.get_producer()
        
        print(f"Connected to Kafka. Sending data every {INTERVAL}s. Press Ctrl+C to stop.")
        
        # Main loop
        while running:
            timestamp = datetime.now().isoformat()
            
            try:
                # Send each item in test_data as an individual message
                for i, item in enumerate(test_data):
                    # Manually serialize the dictionary to JSON bytes
                    serialized_value = json.dumps(item).encode('utf-8')
                    serialized_key = f"sim-{timestamp}-{i}".encode('utf-8')
                    
                    # Send using serialized values
                    producer.produce(
                        KAFKA_TOPIC,
                        value=serialized_value,
                        key=serialized_key
                    )
                
                # Ensure delivery
                producer.flush()
                
                print(f"[{timestamp}] Sent {len(test_data)} data items successfully")
            except Exception as e:
                print(f"Error sending data: {e}")
                import traceback
                traceback.print_exc()
            
            # Wait for next interval
            for _ in range(INTERVAL):
                if not running:
                    break
                time.sleep(1)
                
        # Clean shutdown
        producer.flush()
        producer.close()
        print("Simulator shutdown complete")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 