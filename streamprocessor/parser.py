import json
import uuid
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

from common import logger

class TelemetryParser:
    """
    Parser for network telemetry data.
    Extracts structured data from raw telemetry messages.
    """
    
    def __init__(self):
        """Initialize the telemetry parser."""
        pass
    
    def parse(self, raw_data: Any) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Parse raw telemetry data into structured node, interface, and address data.
        
        Args:
            raw_data: Raw telemetry data from Kafka
            
        Returns:
            tuple: (node_data, interface_data, address_data)
        """
        try:
            # Initialize result lists
            nodes_data = []
            interfaces_data = []
            addresses_data = []
            
            # Generate a batch ID for correlation
            batch_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()
            
            # Process each item in the raw data
            if isinstance(raw_data, list):
                for item in raw_data:
                    self._extract_data_from_item(item, batch_id, timestamp,
                                              nodes_data, interfaces_data, addresses_data)
            else:
                # Handle case where raw_data might be a single item
                self._extract_data_from_item(raw_data, batch_id, timestamp,
                                          nodes_data, interfaces_data, addresses_data)
            
            return nodes_data, interfaces_data, addresses_data
            
        except Exception as e:
            logger.error(f"Error parsing telemetry data: {e}")
            # Return empty lists on error
            return [], [], []
    
    def _extract_data_from_item(self, item: Dict, batch_id: str, timestamp: str,
                              nodes_data: List, interfaces_data: List, addresses_data: List):
        """
        Extract data from a single telemetry item.
        
        Args:
            item: A single telemetry data item
            batch_id: Batch ID for correlation
            timestamp: Processing timestamp
            nodes_data: List to append node data to
            interfaces_data: List to append interface data to
            addresses_data: List to append address data to
        """
        if isinstance(item, list):
            # Some payloads might be nested lists
            for nested_item in item:
                self._extract_data_from_item(nested_item, batch_id, timestamp,
                                          nodes_data, interfaces_data, addresses_data)
            return
        
        # Skip if not a dictionary
        if not isinstance(item, dict):
            return
        
        # Check path to determine data type
        path = item.get('path', '')
        
        if 'entries' not in item:
            return
        
        # Process based on data type
        if '.node.' in path:
            self._extract_node_data(item['entries'], batch_id, timestamp, nodes_data)
        
        if '.interface.status' in path:
            self._extract_interface_data(item['entries'], batch_id, timestamp, interfaces_data)
        
        if '.interface.statistics' in path:
            self._extract_interface_stats(item['entries'], batch_id, timestamp, interfaces_data)
        
        if '.subinterface.ipv4.address' in path or '.subinterface.ipv6.address' in path:
            self._extract_address_data(item['entries'], batch_id, timestamp, addresses_data)
    
    def _extract_node_data(self, entries: List[Dict], batch_id: str, timestamp: str, nodes_data: List):
        """Extract node data from entries."""
        for entry in entries:
            if not isinstance(entry, dict) or 'keys' not in entry:
                continue
                
            keys = entry.get('keys', {})
            fields = entry.get('fields', {})
            
            node_name = keys.get('node_name', '')
            if not node_name:
                continue
                
            # Create node data record
            node_data = {
                'node_name': node_name,
                'batch_id': batch_id,
                'timestamp': timestamp,
                **fields  # Include all fields from the entry
            }
            
            nodes_data.append(node_data)
    
    def _extract_interface_data(self, entries: List[Dict], batch_id: str, timestamp: str, interfaces_data: List):
        """Extract interface status data from entries."""
        for entry in entries:
            if not isinstance(entry, dict) or 'keys' not in entry:
                continue
                
            keys = entry.get('keys', {})
            fields = entry.get('fields', {})
            
            node_name = keys.get('node_name', '')
            interface_name = keys.get('interface_name', '')
            
            if not node_name or not interface_name:
                continue
                
            # Create interface data record
            interface_data = {
                'node_name': node_name,
                'interface_name': interface_name,
                'batch_id': batch_id,
                'timestamp': timestamp,
                'admin_status': fields.get('admin_status', ''),
                'oper_status': fields.get('oper_status', '')
            }
            
            interfaces_data.append(interface_data)
    
    def _extract_interface_stats(self, entries: List[Dict], batch_id: str, timestamp: str, interfaces_data: List):
        """Extract interface statistics data from entries."""
        for entry in entries:
            if not isinstance(entry, dict) or 'keys' not in entry:
                continue
                
            keys = entry.get('keys', {})
            fields = entry.get('fields', {})
            
            node_name = keys.get('node_name', '')
            interface_name = keys.get('interface_name', '')
            
            if not node_name or not interface_name:
                continue
                
            # Create interface stats record
            interface_stats = {
                'node_name': node_name,
                'interface_name': interface_name,
                'batch_id': batch_id,
                'timestamp': timestamp,
                'in_octets': fields.get('in_octets', 0),
                'out_octets': fields.get('out_octets', 0),
                'in_packets': fields.get('in_packets', 0),
                'out_packets': fields.get('out_packets', 0),
                'in_errors': fields.get('in_errors', 0),
                'out_errors': fields.get('out_errors', 0)
            }
            
            interfaces_data.append(interface_stats)
    
    def _extract_address_data(self, entries: List[Dict], batch_id: str, timestamp: str, addresses_data: List):
        """Extract IP address data from entries."""
        for entry in entries:
            if not isinstance(entry, dict) or 'keys' not in entry:
                continue
                
            keys = entry.get('keys', {})
            fields = entry.get('fields', {})
            
            node_name = keys.get('node_name', '')
            interface_name = keys.get('interface_name', '')
            subinterface_index = keys.get('subinterface_index', '')
            address_ip_prefix = keys.get('address_ip-prefix', '')
            
            if not node_name or not interface_name or not address_ip_prefix:
                continue
                
            # Create address data record
            address_data = {
                'node_name': node_name,
                'interface_name': interface_name,
                'subinterface_index': subinterface_index,
                'address_ip_prefix': address_ip_prefix,
                'batch_id': batch_id,
                'timestamp': timestamp,
                'origin': fields.get('origin', ''),
                'status': fields.get('status', '')
            }
            
            addresses_data.append(address_data)


def extract_network_data(data) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    Legacy function to extract network data from raw telemetry.
    This is maintained for backward compatibility.
    
    Args:
        data: Raw network telemetry data
        
    Returns:
        tuple: (nodes, interfaces, addresses)
    """
    parser = TelemetryParser()
    return parser.parse(data)