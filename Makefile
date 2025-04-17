.PHONY: check-env run stop logs clean setup

# Default target
all: run

# Set up directories
setup:
	@echo "Setting up directories..."
	@mkdir -p data/kafka data/clickhouse logs

# Clean data directories
clean-data:
	@echo "Cleaning data directories to avoid conflicts..."
	@rm -rf data/kafka/* data/clickhouse/* logs/*

# Check for required environment variables
check-env:
	@echo "Checking environment variables..."
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found. Copy .env.example to .env and configure it."; \
		exit 1; \
	fi
	@echo "Environment variables check passed."

# Run the containerized pipeline
run: setup clean-data check-env
	@echo "Starting all services with Docker Compose..."
	@docker-compose up -d --build
	@echo "Creating Kafka topics and ClickHouse schemas..."
	@sleep 10  # Wait for services to be available
	@echo "Pipeline is now running."
	@echo "Kafka UI: http://localhost:8080"
	@echo "ClickHouse Tabix: http://localhost:8081"
	@echo "To view logs, run 'make logs'"
	@echo "To stop the pipeline, run 'make stop'"
	@echo ""
	@echo "To run the simulator:"
	@echo "cd simulator && ./run_simulator.sh"

# View logs for all or specific services
logs:
	@echo "Viewing logs for all services. Press Ctrl+C to exit."
	@docker-compose logs -f

# View logs for a specific service (usage: make service-logs SERVICE=kafka)
service-logs:
	@if [ -z "$(SERVICE)" ]; then \
		echo "Error: SERVICE parameter is required. Usage: make service-logs SERVICE=kafka"; \
		exit 1; \
	fi
	@echo "Viewing logs for $(SERVICE). Press Ctrl+C to exit."
	@docker-compose logs -f $(SERVICE)

# Stop all services
stop:
	@echo "Stopping Docker services..."
	@docker-compose down
	@echo "Pipeline stopped successfully."

# Clean up all data
clean: stop
	@echo "Cleaning up data directories..."
	@rm -rf data/kafka/* data/clickhouse/* logs/*
	@echo "Cleanup completed successfully." 