import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
import logging
from datetime import datetime
import uuid
from decimal import Decimal

# Set up logging
logger = logging.getLogger(__name__)

class DynamoDBHelper:
    def __init__(self):
        try:
            self.dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-2')
            self.table_name = 'ImageMetadata'
            self.table = self.dynamodb.Table(self.table_name)
            
            # Create table if it doesn't exist
            self._create_table_if_not_exists()
            
            logger.info("DynamoDB helper initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DynamoDB helper: {e}")
            raise
    
    def _create_table_if_not_exists(self):
        """Create DynamoDB table if it doesn't exist"""
        try:
            # Try to describe the table to check if it exists
            self.table.load()
            logger.info(f"Table {self.table_name} already exists")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                # Table doesn't exist, create it
                try:
                    logger.info(f"Creating table {self.table_name}...")
                    
                    table = self.dynamodb.create_table(
                        TableName=self.table_name,
                        KeySchema=[
                            {
                                'AttributeName': 'image_id',
                                'KeyType': 'HASH'
                            }
                        ],
                        AttributeDefinitions=[
                            {
                                'AttributeName': 'image_id',
                                'AttributeType': 'S'
                            },
                            {
                                'AttributeName': 'user_id',
                                'AttributeType': 'S'
                            }
                        ],
                        GlobalSecondaryIndexes=[
                            {
                                'IndexName': 'UserIndex',
                                'KeySchema': [
                                    {
                                        'AttributeName': 'user_id',
                                        'KeyType': 'HASH'
                                    }
                                ],
                                'Projection': {
                                    'ProjectionType': 'ALL'
                                },
                                'ProvisionedThroughput': {
                                    'ReadCapacityUnits': 5,
                                    'WriteCapacityUnits': 5
                                }
                            }
                        ],
                        BillingMode='PAY_PER_REQUEST',
                        Tags=[
                            {
                                'Key': 'qut-username',
                                'Value': 'n11957948@qut.edu.au'
                            },
                            {
                                'Key': 'purpose',
                                'Value': 'assessment-2'
                            }
                        ]
                    )
                    
                    # Wait for table to be created
                    table.meta.client.get_waiter('table_exists').wait(TableName=self.table_name)
                    logger.info(f"Table {self.table_name} created successfully")
                    
                    # Update the table reference
                    self.table = self.dynamodb.Table(self.table_name)
                    
                except ClientError as create_error:
                    logger.error(f"Error creating table {self.table_name}: {create_error}")
                    raise
            else:
                logger.error(f"Error checking table {self.table_name}: {e}")
                raise
    
    def _convert_floats_to_decimals(self, obj):
        """Recursively convert float values to Decimal for DynamoDB compatibility"""
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {k: self._convert_floats_to_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_floats_to_decimals(v) for v in obj]
        else:
            return obj
    
    def put_image_metadata(self, image_id, user_id, metadata):
        """Store image metadata in DynamoDB"""
        try:
            # Convert float values to Decimal
            metadata = self._convert_floats_to_decimals(metadata)
            
            item = {
                'image_id': image_id,
                'user_id': user_id,
                'filename': metadata.get('filename', ''),
                'filter': metadata.get('filter', ''),
                'strength': Decimal(str(metadata.get('strength', 0))),  # Convert to Decimal
                'size_multiplier': Decimal(str(metadata.get('size_multiplier', 1.0))),  # Convert to Decimal
                'format': metadata.get('format', 'jpeg'),
                'created_at': datetime.utcnow().isoformat(),
                'original_key': f"original_{image_id}",
                'processed_key': image_id
            }
            self.table.put_item(Item=item)
            logger.info(f"Successfully stored metadata for image {image_id}")
            return True
        except ClientError as e:
            logger.error(f"Error putting item in DynamoDB: {e}")
            return False
    
    def get_image_metadata(self, image_id):
        """Retrieve image metadata from DynamoDB"""
        try:
            response = self.table.get_item(Key={'image_id': image_id})
            item = response.get('Item', None)
            if item:
                logger.info(f"Successfully retrieved metadata for image {image_id}")
            else:
                logger.warning(f"Metadata not found for image {image_id}")
            return item
        except ClientError as e:
            logger.error(f"Error getting item from DynamoDB: {e}")
            return None
    
    def get_user_images(self, user_id):
        """Get all images for a specific user"""
        try:
            response = self.table.query(
                IndexName='UserIndex',
                KeyConditionExpression=Key('user_id').eq(user_id)
            )
            items = response.get('Items', [])
            logger.info(f"Retrieved {len(items)} images for user {user_id}")
            return items
        except ClientError as e:
            logger.error(f"Error querying DynamoDB: {e}")
            return []
    
    def delete_image_metadata(self, image_id):
        """Delete image metadata from DynamoDB"""
        try:
            self.table.delete_item(Key={'image_id': image_id})
            logger.info(f"Successfully deleted metadata for image {image_id}")
            return True
        except ClientError as e:
            logger.error(f"Error deleting item from DynamoDB: {e}")
            return False
    
    def update_image_metadata(self, image_id, update_expression, expression_values):
        """Update specific fields in image metadata"""
        try:
            # Convert float values in expression_values to Decimal
            expression_values = self._convert_floats_to_decimals(expression_values)
            
            response = self.table.update_item(
                Key={'image_id': image_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ReturnValues="UPDATED_NEW"
            )
            logger.info(f"Successfully updated metadata for image {image_id}")
            return response.get('Attributes', {})
        except ClientError as e:
            logger.error(f"Error updating item in DynamoDB: {e}")
            return None