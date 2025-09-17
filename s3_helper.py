import boto3
import io
from botocore.exceptions import NoCredentialsError, ClientError
import logging
import sys

# Set up logging to output to stdout (Docker captures this)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class S3Helper:
    def __init__(self):
        try:
            logger.info("Initializing S3 helper...")
            self.s3_client = boto3.client('s3', region_name='ap-southeast-2')
            self.original_bucket = 'n11957948-original-images'
            self.processed_bucket = 'n11957948-processed-images'
            
            # Create buckets if they don't exist
            self._create_bucket_if_not_exists(self.original_bucket)
            self._create_bucket_if_not_exists(self.processed_bucket)
            
            # Tag the buckets
            self._tag_bucket(self.original_bucket)
            self._tag_bucket(self.processed_bucket)
            
            logger.info("S3 helper initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize S3 helper: {e}")
            raise
    
    def _create_bucket_if_not_exists(self, bucket_name):
        """Create S3 bucket if it doesn't exist"""
        try:
            # Check if bucket exists
            self.s3_client.head_bucket(Bucket=bucket_name)
            logger.info(f"Bucket {bucket_name} already exists")
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                # Bucket doesn't exist, create it
                try:
                    logger.info(f"Creating bucket {bucket_name}...")
                    response = self.s3_client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': 'ap-southeast-2'}
                    )
                    logger.info(f"Bucket {bucket_name} created successfully: {response.get('Location')}")
                except ClientError as create_error:
                    logger.error(f"Error creating bucket {bucket_name}: {create_error}")
                    raise
            else:
                logger.error(f"Error checking bucket {bucket_name}: {e}")
                raise
    
    def _tag_bucket(self, bucket_name):
        """Tag S3 bucket with required tags"""
        try:
            qut_username = 'n11957948@qut.edu.au'
            purpose = 'assessment-2'
            
            response = self.s3_client.put_bucket_tagging(
                Bucket=bucket_name,
                Tagging={
                    'TagSet': [
                        {'Key': 'qut-username', 'Value': qut_username},
                        {'Key': 'purpose', 'Value': purpose}
                    ]
                }
            )
            logger.info(f"Bucket {bucket_name} tagged successfully")
        except ClientError as e:
            logger.error(f"Error tagging bucket {bucket_name}: {e}")
    

    
    def upload_image(self, image_data, image_id, is_processed=False):
        """Upload image to S3"""
        bucket = self.processed_bucket if is_processed else self.original_bucket
        try:
            logger.info(f"Attempting to upload image {image_id} to bucket {bucket}")
            
            response = self.s3_client.put_object(
                Bucket=bucket,
                Key=image_id,
                Body=image_data,
                ContentType='image/jpeg'
            )
            
            logger.info(f"Successfully uploaded image {image_id} to {bucket}")
            logger.debug(f"Upload response: {response}")
            
            # Verify the upload worked
            try:
                self.s3_client.head_object(Bucket=bucket, Key=image_id)
                logger.info(f"Successfully verified upload of {image_id}")
            except Exception as e:
                logger.error(f"Failed to verify upload: {e}")
                
            return True
        except Exception as e:
            logger.error(f"Error uploading to S3: {e}")
            return False
    
    def download_image(self, image_id, is_processed=False):
        """Download image from S3"""
        bucket = self.processed_bucket if is_processed else self.original_bucket
        try:
            logger.info(f"Attempting to download image {image_id} from bucket {bucket}")
            
            response = self.s3_client.get_object(Bucket=bucket, Key=image_id)
            image_data = response['Body'].read()
            
            logger.info(f"Successfully downloaded image {image_id} from {bucket}")
            logger.debug(f"Download response headers: {response['ResponseMetadata']['HTTPHeaders']}")
            
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
            logger.info(f"Generating presigned URL for image {image_id} in bucket {bucket}")
            logger.info(f"URL will expire in {expiration} seconds")
            
            # First check if the object exists
            try:
                self.s3_client.head_object(Bucket=bucket, Key=image_id)
                logger.info(f"Image {image_id} exists in bucket {bucket}")
            except ClientError as e:
                logger.error(f"Image {image_id} does not exist in bucket {bucket}: {e}")
                return None
            
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': bucket,
                    'Key': image_id
                },
                ExpiresIn=expiration
            )
            
            logger.info(f"Successfully generated presigned URL for image {image_id}")
            logger.debug(f"Generated URL: {url}")
            
            # Test the URL
            import requests
            test_response = requests.head(url)
            logger.info(f"URL test response: {test_response.status_code}")
            if test_response.status_code == 200:
                logger.info("URL test successful - URL is accessible")
            else:
                logger.warning(f"URL test failed with status: {test_response.status_code}")
            
            return url
        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}")
            return None
    
    def image_exists(self, image_id, is_processed=False):
        """Check if image exists in S3"""
        bucket = self.processed_bucket if is_processed else self.original_bucket
        try:
            logger.info(f"Checking if image {image_id} exists in bucket {bucket}")
            
            self.s3_client.head_object(Bucket=bucket, Key=image_id)
            logger.info(f"Image {image_id} exists in bucket {bucket}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.warning(f"Image {image_id} not found in {bucket}")
                return False
            logger.error(f"Error checking image existence: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking image existence: {e}")
            return False