from typing import Dict, List, Literal, Optional, Union, Any
from uuid import UUID, uuid4
from datetime import datetime
import ipaddress

from pydantic import BaseModel, Field, validator


class NetworkAddressKeys(BaseModel):
    """Keys for a network address entry."""
    address_ip_prefix: str = Field(..., alias="address_ip-prefix")
    interface_name: str
    node_name: str
    subinterface_index: str


class NetworkAddressFields(BaseModel):
    """Fields for a network address entry."""
    origin: Literal["static", "dhcp"]
    status: Literal["preferred"]


class NetworkAddressEntry(BaseModel):
    """A network address entry."""
    keys: NetworkAddressKeys
    fields: NetworkAddressFields


class NetworkDataPath(BaseModel):
    """A network data path with its entries."""
    path: str
    entries: List[NetworkAddressEntry]


class NetworkDataBatch(BaseModel):
    """A batch of network data paths."""
    batch_id: str
    timestamp: str
    data: List[List[NetworkDataPath]]


# New normalized models

class Node(BaseModel):
    """
    Represents a network device node
    
    Attributes:
        node_id: Unique identifier for the node
        node_name: Name of the node
        system_ip: System IP address
        mgmt_ip: Management IP address
        first_seen: When this node was first discovered
        last_updated: When this node's information was last updated
    """
    node_id: UUID = Field(default_factory=uuid4)
    node_name: str
    system_ip: Optional[str] = None
    mgmt_ip: Optional[str] = None
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('system_ip', 'mgmt_ip')
    def validate_ip_address(cls, v):
        if v is not None:
            try:
                ipaddress.ip_address(v)
            except ValueError:
                raise ValueError(f"Invalid IP address: {v}")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "node_id": "123e4567-e89b-12d3-a456-426614174000",
                "node_name": "router1.example.com",
                "system_ip": "10.0.0.1",
                "mgmt_ip": "192.168.1.1",
                "first_seen": "2023-01-01T00:00:00Z",
                "last_updated": "2023-01-01T12:00:00Z"
            }
        }


class Interface(BaseModel):
    """
    Represents a network interface on a node
    
    Attributes:
        interface_id: Unique identifier for the interface
        node_id: ID of the node this interface belongs to
        interface_name: Name of the interface
        interface_type: Type of interface (ethernet, loopback, etc.)
        admin_status: Administrative status (up, down, testing)
        oper_status: Operational status (up, down, testing, dormant, etc.)
        speed: Speed of the interface in bits per second
        mtu: Maximum Transmission Unit size
        description: User-defined description of the interface
        first_seen: When this interface was first discovered
        last_updated: When this interface's information was last updated
    """
    interface_id: UUID = Field(default_factory=uuid4)
    node_id: UUID
    interface_name: str
    interface_type: str = "unknown"  # Can be: unknown, ethernet, loopback, virtual, port_channel, tunnel, vlan, other
    admin_status: str = "unknown"    # Can be: unknown, up, down, testing
    oper_status: str = "unknown"     # Can be: unknown, up, down, testing, dormant, not_present, lower_layer_down
    speed: Optional[int] = None
    mtu: Optional[int] = None
    description: Optional[str] = None
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "interface_id": "123e4567-e89b-12d3-a456-426614174001",
                "node_id": "123e4567-e89b-12d3-a456-426614174000",
                "interface_name": "GigabitEthernet0/0/0",
                "interface_type": "ethernet",
                "admin_status": "up",
                "oper_status": "up",
                "speed": 1000000000,
                "mtu": 1500,
                "description": "Connection to Core Switch",
                "first_seen": "2023-01-01T00:00:00Z",
                "last_updated": "2023-01-01T12:00:00Z"
            }
        }


class IPAssignment(BaseModel):
    """
    Represents an IP address assignment to an interface
    
    Attributes:
        assignment_id: Unique identifier for this IP assignment
        node_id: ID of the node 
        interface_id: ID of the interface this IP is assigned to
        subinterface_index: Index of the subinterface (if applicable)
        address_ip_prefix: IP address with prefix length (CIDR notation)
        origin: How this IP was configured (static, dhcp, etc.)
        status: Status of the IP address
        source_path: Path in the configuration where this IP was found
        batch_id: ID of the processing batch that identified this IP
        timestamp: When this IP assignment was recorded
    """
    assignment_id: UUID = Field(default_factory=uuid4)
    node_id: UUID
    interface_id: UUID
    subinterface_index: Optional[str] = None
    address_ip_prefix: str
    origin: Optional[str] = None
    status: Optional[str] = None
    source_path: Optional[str] = None
    batch_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('address_ip_prefix')
    def validate_ip_prefix(cls, v):
        try:
            ipaddress.ip_network(v, strict=False)
        except ValueError:
            raise ValueError(f"Invalid IP prefix: {v}")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "assignment_id": "123e4567-e89b-12d3-a456-426614174002",
                "node_id": "123e4567-e89b-12d3-a456-426614174000",
                "interface_id": "123e4567-e89b-12d3-a456-426614174001",
                "subinterface_index": "0",
                "address_ip_prefix": "192.168.1.1/24",
                "origin": "static",
                "status": "active",
                "source_path": "config/interfaces/GigabitEthernet0/0/0",
                "batch_id": "batch-2023-01-01-001",
                "timestamp": "2023-01-01T12:00:00Z"
            }
        }


class IPAddressChange(BaseModel):
    """
    Represents a change to an IP address assignment
    
    Attributes:
        assignment_id: ID of the assignment that changed
        node_id: ID of the node
        interface_id: ID of the interface
        address_ip_prefix: IP address with prefix length (CIDR notation)
        event_type: Type of change event (add, remove, change)
        timestamp: When this change was recorded
    """
    assignment_id: UUID
    node_id: UUID
    interface_id: UUID
    address_ip_prefix: str
    event_type: str  # add, remove, change
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class NodeStats(BaseModel):
    """
    Aggregated statistics for a node
    
    Attributes:
        node_id: ID of the node
        node_name: Name of the node
        ip_count: Number of IP addresses assigned to this node
        interface_count: Number of interfaces on this node
        last_seen_time: When this node was last seen in the network
        last_processed_time: When this node was last processed by the system
    """
    node_id: UUID
    node_name: str
    ip_count: int
    interface_count: int
    day: datetime
    last_seen_time: datetime
    last_processed_time: datetime


class NetworkState(BaseModel):
    """
    Flattened view of the network state for a specific point in time
    
    Attributes:
        node_id: ID of the node
        node_name: Name of the node
        system_ip: System IP of the node
        mgmt_ip: Management IP of the node
        interface_id: ID of the interface
        interface_name: Name of the interface
        interface_type: Type of interface
        admin_status: Administrative status of the interface
        oper_status: Operational status of the interface
        address_ip_prefix: IP address with prefix
        timestamp: When this state was recorded
    """
    node_id: UUID
    node_name: str
    system_ip: Optional[str] = None
    mgmt_ip: Optional[str] = None
    interface_id: UUID
    interface_name: str
    interface_type: str
    admin_status: str
    oper_status: str
    speed: Optional[int] = None
    mtu: Optional[int] = None
    description: Optional[str] = None
    subinterface_index: Optional[str] = None
    address_ip_prefix: str
    origin: Optional[str] = None
    status: Optional[str] = None
    timestamp: datetime


class RawTelemetryData(BaseModel):
    """
    Raw telemetry data received from network devices
    
    Attributes:
        node_id: ID of the node that sent the data
        node_name: Name of the node that sent the data
        data_type: Type of telemetry data
        data: The raw telemetry data
        timestamp: When this data was received
    """
    node_id: Optional[UUID] = None
    node_name: str
    data_type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    def extract_normalized_data(self) -> Dict[str, Any]:
        """
        Extract and normalize the telemetry data into structured format
        
        Returns:
            Dictionary containing normalized data with node, interfaces, and IP assignments
        """
        # This is a placeholder implementation
        # To be implemented based on specific data format and normalization logic
        return {
            "node": self.extract_node_data(),
            "interfaces": self.extract_interfaces_data(),
            "ip_assignments": self.extract_ip_assignments_data()
        }
    
    def extract_node_data(self) -> Dict[str, Any]:
        """Extract node data from telemetry"""
        # Implementation depends on actual data structure
        return {}
    
    def extract_interfaces_data(self) -> List[Dict[str, Any]]:
        """Extract interfaces data from telemetry"""
        # Implementation depends on actual data structure
        return []
    
    def extract_ip_assignments_data(self) -> List[Dict[str, Any]]:
        """Extract IP assignment data from telemetry"""
        # Implementation depends on actual data structure
        return []


class ProcessedData(BaseModel):
    """
    Processed and normalized telemetry data
    
    Attributes:
        node: Node information
        interfaces: List of interfaces
        ip_assignments: List of IP assignments
        batch_id: ID of the processing batch
        timestamp: When this data was processed
    """
    node: Node
    interfaces: List[Interface]
    ip_assignments: List[IPAssignment]
    batch_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Models for backward compatibility (for existing code)

class NodeData(BaseModel):
    """Node data for ClickHouse (backward compatibility)."""
    node_name: str
    system_ip: Optional[str] = None
    mgmt_ip: Optional[str] = None
    timestamp: str
    batch_id: str


class InterfaceData(BaseModel):
    """Interface data for ClickHouse (backward compatibility)."""
    node_name: str
    interface_name: str
    interface_type: Optional[str] = None
    subinterface_index: str
    timestamp: str
    batch_id: str


class AddressData(BaseModel):
    """Address data for ClickHouse (backward compatibility)."""
    node_name: str
    interface_name: str
    subinterface_index: str
    address_ip_prefix: str
    origin: str
    status: str
    timestamp: str
    batch_id: str


# Aggregated view models for querying

class NodeWithInterfaces(Node):
    """Node with its interfaces."""
    interfaces: List[Interface] = []


class InterfaceWithIPs(Interface):
    """Interface with its IP assignments."""
    node_name: str
    ip_assignments: List[IPAssignment] = []


class TelemetryEvent(BaseModel):
    """Model for telemetry events view."""
    assignment_id: UUID
    event_type: str  # e.g., 'ip_assignment'
    node_name: str
    interface_name: str
    address_ip_prefix: str
    status: str
    origin: str
    timestamp: datetime 