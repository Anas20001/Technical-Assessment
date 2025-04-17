import boto3
from typing import Dict, Any, Optional
from common import logger, AWS_REGION, AWS_SNS_TOPIC_ARN, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

class AlertManager:
    """Handles alerts to AWS SNS when issues occur in processing"""
    
    def __init__(self):
        """Initialize the SNS client"""
        self.sns_client = None
        self.topic_arn = AWS_SNS_TOPIC_ARN
        
        # Only initialize SNS client if credentials and topic ARN are provided
        if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and AWS_SNS_TOPIC_ARN:
            try:
                self.sns_client = boto3.client(
                    'sns',
                    region_name=AWS_REGION,
                    aws_access_key_id=AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
                )
                logger.info("SNS client initialized for alerting")
            except Exception as e:
                logger.error(f"Failed to initialize SNS client: {str(e)}")
                self.sns_client = None
        else:
            logger.warning("SNS alerting disabled: missing AWS credentials or SNS topic ARN")
    
    def send_alert(self, subject: str, message: str, attributes: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send an alert to SNS
        
        Args:
            subject: Alert subject line
            message: Alert message body
            attributes: Optional message attributes
            
        Returns:
            bool: True if alert was sent successfully, False otherwise
        """
        if not self.sns_client or not self.topic_arn:
            logger.warning(f"Alert not sent - SNS client not configured: {subject}")
            return False
            
        try:
            message_attrs = {}
            if attributes:
                # Convert attributes to SNS message attribute format
                for key, value in attributes.items():
                    if isinstance(value, str):
                        message_attrs[key] = {
                            'DataType': 'String',
                            'StringValue': value
                        }
                    elif isinstance(value, (int, float)):
                        message_attrs[key] = {
                            'DataType': 'Number',
                            'StringValue': str(value)
                        }
            
            response = self.sns_client.publish(
                TopicArn=self.topic_arn,
                Subject=subject,
                Message=message,
                MessageAttributes=message_attrs
            )
            
            logger.info(f"Alert sent: {subject}", message_id=response.get('MessageId', ''))
            return True
            
        except Exception as e:
            logger.error(f"Failed to send alert: {str(e)}", subject=subject)
            return False
            
    def alert_processing_error(self, component: str, error: Exception, batch_id: str = "") -> bool:
        """
        Send an alert for a processing error
        
        Args:
            component: Component where the error occurred
            error: The exception that was raised
            batch_id: Optional batch ID for context
            
        Returns:
            bool: True if alert was sent successfully, False otherwise
        """
        subject = f"Stream Processing Error in {component}"
        message = f"""
        A processing error occurred in the network telemetry pipeline.
        
        Component: {component}
        Error: {str(error)}
        Batch ID: {batch_id}
        
        Please check the logs for more details.
        """
        
        attributes = {
            "component": component,
            "error_type": error.__class__.__name__,
            "batch_id": batch_id
        }
        
        return self.send_alert(subject, message, attributes) 