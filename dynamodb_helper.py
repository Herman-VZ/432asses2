import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
import logging
from datetime import datetime
import uuid

# Set up logging
logger = logging.getLogger(__name__)

class DynamoDBHelper:
    def __init__(self):
        try:
            self.dynamodb = boto3.resource('dynamodb')
            self.table = self.dynamodb.Table('ImageMetadata')
            logger.info("DynamoDB helper initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DynamoDB helper: {e}")
            raise
    
    def put_image_metadata(self, image_id, user_id, metadata):
        """Store image metadata in DynamoDB"""
        try:
            item = {
                'image_id': image_id,
                'user_id': user_id,
                'filename': metadata.get('filename', ''),
                'filter': metadata.get('filter', ''),
                'strength': metadata.get('strength', 0),
                'size_multiplier': metadata.get('size_multiplier', 1.0),
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