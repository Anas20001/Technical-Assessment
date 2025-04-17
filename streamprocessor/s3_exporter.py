import os
import boto3
import pandas as pd
import json
from datetime import datetime
from typing import Dict, Any, List
import io

from common import logger, AWS_REGION, AWS_S3_BUCKET, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

class S3Exporter:
    def __init__(self):
        """Initialize S3 client and resources."""
        self.s3_client = boto3.client(
            's3',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        ) if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY else None
        
        if not self.s3_client:
            logger.warning("AWS credentials not provided. S3 export will be skipped.")
    
    def export_to_parquet(self, nodes: List[Dict[str, Any]], interfaces: List[Dict[str, Any]], 
                         addresses: List[Dict[str, Any]], batch_id: str) -> bool:
        """
        Export processed data to a parquet file and upload to S3
        Returns True if successful, False otherwise
        """
        if not self.s3_client:
            logger.warning("S3 client not initialized. Skipping export.")
            return False
        
        try:
            # Create dataframes from the processed data
            node_df = pd.DataFrame(nodes)
            interface_df = pd.DataFrame(interfaces)
            address_df = pd.DataFrame(addresses)
            
            # Create a dictionary of dataframes to save in a single parquet file
            data_dict = {
                'nodes': node_df,
                'interfaces': interface_df,
                'addresses': address_df
            }
            
            # Create a buffer to store the parquet file
            buffer = io.BytesIO()
            
            # Combine all dataframes into a single parquet file with separate tables
            for key, df in data_dict.items():
                if not df.empty:
                    # Convert timestamp strings to datetime objects
                    if 'timestamp' in df.columns:
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df.to_parquet(buffer, engine='pyarrow', index=False)
            
            # Set the buffer position to the beginning
            buffer.seek(0)
            
            # Generate S3 key with timestamp organization
            now = datetime.utcnow()
            s3_key = f"processed/{now.year}/{now.month:02d}/{now.day:02d}/{now.hour:02d}/{batch_id}.parquet"
            
            # Upload to S3
            self.s3_client.upload_fileobj(buffer, AWS_S3_BUCKET, s3_key)
            
            logger.info(f"Successfully uploaded parquet file to s3://{AWS_S3_BUCKET}/{s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export data to S3: {str(e)}")
            return False
            
    def export_batch(self, batch_data: Dict[str, Any]) -> bool:
        """
        Export a batch of data to S3
        The batch_data should contain 'nodes', 'interfaces', and 'addresses' keys
        Returns True if successful, False otherwise
        """
        if not batch_data:
            logger.warning("No data provided for export")
            return False
            
        # Extract data
        nodes = batch_data.get('nodes', [])
        interfaces = batch_data.get('interfaces', [])
        addresses = batch_data.get('addresses', [])
        batch_id = batch_data.get('batch_id', datetime.utcnow().strftime('%Y%m%d%H%M%S'))
        
        return self.export_to_parquet(nodes, interfaces, addresses, batch_id) 