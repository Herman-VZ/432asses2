import boto3
import io
from botocore.exceptions import NoCredentialsError, ClientError
import logging

# Set up logging
logger = logging.getLogger(__name__)

class S3Helper:
    def __init__(self):
        try:
            self.s3_client = boto3.client('s3')
            self.original_bucket = 'n11957948-original-images'
            self.processed_bucket = 'n11957948-processed-images'
            logger.info("S3 helper initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize S3 helper: {e}")
            raise
    
    def upload_image(self, image_data, image_id, is_processed=False):
        """Upload image to S3"""
        bucket = self.processed_bucket if is_processed else self.original_bucket
        try:
            self.s3_client.put_object(
                Bucket=bucket,
                Key=image_id,
                Body=image_data,
                ContentType='image/jpeg'
            )
            logger.info(f"Successfully uploaded image {image_id} to {bucket}")
            return True
        except (NoCredentialsError, ClientError) as e:
            logger.error(f"Error uploading to S3: {e}")
            return False
    
    def download_image(self, image_id, is_processed=False):
        """Download image from S3"""
        bucket = self.processed_bucket if is_processed else self.original_bucket
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=image_id)
            image_data = response['Body'].read()
            logger.info(f"Successfully downloaded image {image_id} from {bucket}")
            return image_data
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"Image {image_id} not found in {bucket}")
            else:
                logger.error(f"Error downloading from S3: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading from S3: {e}")
            return None
    
    def generate_presigned_url(self, image_id, expiration=3600, is_processed=False):
        """Generate presigned URL for direct access"""
        bucket = self.processed_bucket if is_processed else self.original_bucket
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': image_id},
                ExpiresIn=expiration
            )
            logger.info(f"Generated presigned URL for image {image_id}")
            return url
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            return None
    
    def delete_image(self, image_id, is_processed=False):
        """Delete image from S3"""
        bucket = self.processed_bucket if is_processed else self.original_bucket
        try:
            self.s3_client.delete_object(Bucket=bucket, Key=image_id)
            logger.info(f"Successfully deleted image {image_id} from {bucket}")
            return True
        except ClientError as e:
            logger.error(f"Error deleting from S3: {e}")
            return False
    
    def image_exists(self, image_id, is_processed=False):
        """Check if image exists in S3"""
        bucket = self.processed_bucket if is_processed else self.original_bucket
        try:
            self.s3_client.head_object(Bucket=bucket, Key=image_id)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error(f"Error checking image existence: {e}")
            return False