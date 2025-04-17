import os
import logfire
from dotenv import load_dotenv
from clickhouse_driver import Client

# Load environment variables
load_dotenv()

# Configure Logfire
logfire.configure(
    api_key=os.getenv("LOGFIRE_API_KEY", ""),
    service_name="network-telemetry",
    service_version=os.getenv("SERVICE_VERSION", "0.1.0"),
)
logger = logfire.getLogger(__name__)

# ClickHouse connection settings
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "9000"))
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")
CLICKHOUSE_DATABASE = os.getenv("CLICKHOUSE_DATABASE", "telemetry")

# Kafka settings
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_PROCESSED_TOPICS = os.getenv("KAFKA_PROCESSED_TOPICS", "node-data,interface-data,address-data").split(",")

def init_clickhouse_tables() -> bool:
    """
    Initialize ClickHouse tables with optimized schema
    Returns True if successful, False otherwise
    """
    try:
        # Connect to ClickHouse
        client = Client(
            host=CLICKHOUSE_HOST,
            port=CLICKHOUSE_PORT,
            user=CLICKHOUSE_USER,
            password=CLICKHOUSE_PASSWORD,
            database=CLICKHOUSE_DATABASE,
        )
        logger.info(f"Connected to ClickHouse at {CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}")

        # Create database if not exists
        client.execute(f"CREATE DATABASE IF NOT EXISTS {CLICKHOUSE_DATABASE}")
        logger.info(f"Created database {CLICKHOUSE_DATABASE} if it didn't exist")

        # 1. Nodes table - Using ReplacingMergeTree for deduplication
        client.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                node_id UUID,
                node_name String,
                system_ip String,
                mgmt_ip String,
                first_seen DateTime,
                last_updated DateTime,
                
                PRIMARY KEY (node_id)
            ) ENGINE = ReplacingMergeTree(last_updated)
            ORDER BY (node_id)
            SETTINGS index_granularity = 8192
        """)
        logger.info("Created nodes table")
        
        # 2. Interfaces table - Using ReplacingMergeTree for deduplication
        client.execute("""
            CREATE TABLE IF NOT EXISTS interfaces (
                interface_id UUID,
                node_id UUID,
                interface_name String,
                interface_type Enum8('unknown' = 0, 'ethernet' = 1, 'loopback' = 2, 'virtual' = 3, 'port_channel' = 4, 'tunnel' = 5, 'vlan' = 6, 'other' = 7),
                admin_status Enum8('unknown' = 0, 'up' = 1, 'down' = 2, 'testing' = 3),
                oper_status Enum8('unknown' = 0, 'up' = 1, 'down' = 2, 'testing' = 3, 'dormant' = 4, 'not_present' = 5, 'lower_layer_down' = 6),
                speed UInt64,
                mtu UInt32,
                description String,
                first_seen DateTime,
                last_updated DateTime,
                
                PRIMARY KEY (node_id, interface_id)
            ) ENGINE = ReplacingMergeTree(last_updated)
            ORDER BY (node_id, interface_id)
            SETTINGS index_granularity = 8192
        """)
        logger.info("Created interfaces table")
        
        # 3. IP Assignments table - Using MergeTree with date partitioning for time-series queries
        client.execute("""
            CREATE TABLE IF NOT EXISTS ip_assignments (
                assignment_id UUID,
                node_id UUID,
                interface_id UUID,
                subinterface_index String,
                address_ip_prefix String,
                origin String,
                status String,
                source_path String,
                batch_id String,
                timestamp DateTime,
                event_date Date DEFAULT toDate(timestamp),
                
                PRIMARY KEY (node_id, interface_id, address_ip_prefix, timestamp)
            ) ENGINE = MergeTree()
            PARTITION BY toYYYYMM(event_date)
            ORDER BY (node_id, interface_id, address_ip_prefix, timestamp)
            TTL event_date + INTERVAL 6 MONTH
            SETTINGS index_granularity = 8192
        """)
        logger.info("Created ip_assignments table")
        
        # 4. IP Assignment History table for tracking changes
        client.execute("""
            CREATE TABLE IF NOT EXISTS ip_assignment_history (
                assignment_id UUID,
                node_id UUID,
                interface_id UUID,
                subinterface_index String,
                address_ip_prefix String,
                origin String,
                status String,
                source_path String,
                batch_id String,
                timestamp DateTime,
                event_date Date DEFAULT toDate(timestamp),
                event_type Enum8('add' = 1, 'remove' = 2, 'change' = 3),
                
                PRIMARY KEY (node_id, interface_id, timestamp)
            ) ENGINE = MergeTree()
            PARTITION BY toYYYYMM(event_date)
            ORDER BY (node_id, interface_id, timestamp)
            TTL event_date + INTERVAL 12 MONTH
            SETTINGS index_granularity = 8192
        """)
        logger.info("Created ip_assignment_history table")
        
        # 5. Kafka Engine Tables for ingestion from Kafka
        # 5.1 Node data from Kafka
        client.execute(f"""
            CREATE TABLE IF NOT EXISTS node_data_queue (
                node_name String,
                system_ip String,
                mgmt_ip String,
                timestamp DateTime,
                batch_id String
            ) ENGINE = Kafka()
            SETTINGS kafka_broker_list = '{KAFKA_BOOTSTRAP_SERVERS}',
                     kafka_topic_list = '{KAFKA_PROCESSED_TOPICS[0]}',
                     kafka_group_name = 'clickhouse_node_data_consumer',
                     kafka_format = 'JSONEachRow',
                     kafka_max_block_size = 1048576
        """)
        logger.info(f"Created Kafka engine table for {KAFKA_PROCESSED_TOPICS[0]}")
        
        # 5.2 Interface data from Kafka
        client.execute(f"""
            CREATE TABLE IF NOT EXISTS interface_data_queue (
                node_name String,
                interface_name String,
                interface_type String,
                subinterface_index String,
                timestamp DateTime,
                batch_id String
            ) ENGINE = Kafka()
            SETTINGS kafka_broker_list = '{KAFKA_BOOTSTRAP_SERVERS}',
                     kafka_topic_list = '{KAFKA_PROCESSED_TOPICS[1]}',
                     kafka_group_name = 'clickhouse_interface_data_consumer',
                     kafka_format = 'JSONEachRow',
                     kafka_max_block_size = 1048576
        """)
        logger.info(f"Created Kafka engine table for {KAFKA_PROCESSED_TOPICS[1]}")
        
        # 5.3 Address data from Kafka
        client.execute(f"""
            CREATE TABLE IF NOT EXISTS address_data_queue (
                node_name String,
                interface_name String,
                subinterface_index String,
                address_ip_prefix String,
                origin String,
                status String,
                timestamp DateTime,
                batch_id String
            ) ENGINE = Kafka()
            SETTINGS kafka_broker_list = '{KAFKA_BOOTSTRAP_SERVERS}',
                     kafka_topic_list = '{KAFKA_PROCESSED_TOPICS[2]}',
                     kafka_group_name = 'clickhouse_address_data_consumer',
                     kafka_format = 'JSONEachRow',
                     kafka_max_block_size = 1048576
        """)
        logger.info(f"Created Kafka engine table for {KAFKA_PROCESSED_TOPICS[2]}")
        
        # 6. Materialized views to transfer data from Kafka tables to storage tables
        client.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS node_data_mv TO node_data AS
            SELECT * FROM node_data_queue
        """)
        logger.info("Created node_data_mv materialized view")
        
        client.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS interface_data_mv TO interface_data AS
            SELECT * FROM interface_data_queue
        """)
        logger.info("Created interface_data_mv materialized view")
        
        client.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS address_data_mv TO address_data AS
            SELECT * FROM address_data_queue
        """)
        logger.info("Created address_data_mv materialized view")
        
        # 7. Create destination tables for the materialized views
        client.execute("""
            CREATE TABLE IF NOT EXISTS node_data (
                node_name String,
                system_ip String,
                mgmt_ip String,
                timestamp DateTime,
                batch_id String
            ) ENGINE = MergeTree()
            ORDER BY (node_name, timestamp)
            TTL timestamp + INTERVAL 6 MONTH
        """)
        logger.info("Created node_data table")
        
        client.execute("""
            CREATE TABLE IF NOT EXISTS interface_data (
                node_name String,
                interface_name String,
                interface_type String,
                subinterface_index String,
                timestamp DateTime,
                batch_id String
            ) ENGINE = MergeTree()
            ORDER BY (node_name, interface_name, timestamp)
            TTL timestamp + INTERVAL 6 MONTH
        """)
        logger.info("Created interface_data table")
        
        client.execute("""
            CREATE TABLE IF NOT EXISTS address_data (
                node_name String,
                interface_name String,
                subinterface_index String,
                address_ip_prefix String,
                origin String,
                status String,
                timestamp DateTime,
                batch_id String
            ) ENGINE = MergeTree()
            ORDER BY (node_name, interface_name, address_ip_prefix, timestamp)
            TTL timestamp + INTERVAL 6 MONTH
        """)
        logger.info("Created address_data table")

        # 8. Materialized view for IP address changes
        client.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS ip_changes_mv TO ip_assignment_history AS
            SELECT
                assignment_id,
                node_id,
                interface_id,
                subinterface_index,
                address_ip_prefix,
                origin,
                status,
                source_path,
                batch_id,
                timestamp,
                event_date,
                'add' as event_type
            FROM ip_assignments
            WHERE 1=1
        """)
        logger.info("Created ip_changes_mv materialized view")
        
        # 9. Materialized view for the latest network state - flattened for faster querying
        client.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS network_state_mv
            ENGINE = ReplacingMergeTree
            ORDER BY (node_id, interface_id, address_ip_prefix)
            POPULATE AS
            SELECT
                n.node_id,
                n.node_name,
                n.system_ip,
                n.mgmt_ip,
                i.interface_id,
                i.interface_name,
                i.interface_type,
                i.admin_status,
                i.oper_status,
                i.speed,
                i.mtu,
                i.description,
                ip.subinterface_index,
                ip.address_ip_prefix,
                ip.origin,
                ip.status,
                ip.timestamp,
                max(ip.timestamp) as max_timestamp
            FROM nodes n
            JOIN interfaces i ON n.node_id = i.node_id
            JOIN ip_assignments ip ON i.interface_id = ip.interface_id
            GROUP BY
                n.node_id,
                n.node_name,
                n.system_ip,
                n.mgmt_ip,
                i.interface_id,
                i.interface_name,
                i.interface_type,
                i.admin_status,
                i.oper_status,
                i.speed,
                i.mtu,
                i.description,
                ip.subinterface_index,
                ip.address_ip_prefix,
                ip.origin,
                ip.status,
                ip.timestamp
        """)
        logger.info("Created network_state_mv materialized view")
        
        # 10. Create aggregated statistics view for nodes
        client.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS node_stats_mv
            ENGINE = SummingMergeTree
            ORDER BY (node_id, day)
            POPULATE AS
            SELECT 
                n.node_id,
                n.node_name,
                toDate(ip.timestamp) as day,
                count(DISTINCT ip.address_ip_prefix) as ip_count,
                count(DISTINCT i.interface_id) as interface_count,
                max(ip.timestamp) as last_seen_time,
                max(ip.timestamp) as last_processed_time
            FROM nodes n
            JOIN interfaces i ON n.node_id = i.node_id
            JOIN ip_assignments ip ON i.interface_id = ip.interface_id
            GROUP BY n.node_id, n.node_name, toDate(ip.timestamp)
        """)
        logger.info("Created node_stats_mv materialized view")
        
        # 11. Create dictionary for fast node lookups
        client.execute("""
            CREATE DICTIONARY IF NOT EXISTS node_dict (
                node_id UUID,
                node_name String,
                system_ip String,
                mgmt_ip String
            )
            PRIMARY KEY node_id
            SOURCE(CLICKHOUSE(TABLE 'nodes'))
            LIFETIME(MIN 300 MAX 360)
            LAYOUT(FLAT())
        """)
        logger.info("Created node_dict dictionary")
        
        logger.info("Successfully initialized all ClickHouse tables")
        return True
    except Exception as e:
        logger.error(f"Error initializing ClickHouse tables: {str(e)}")
        return False

if __name__ == "__main__":
    success = init_clickhouse_tables()
    logger.info(f"ClickHouse tables initialization: {'Success' if success else 'Failed'}") 