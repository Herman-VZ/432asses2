import boto3
import json
import time
import logging
import io
import uuid
from PIL import Image, ImageFilter, ImageEnhance
from sqs_helper import SQSHelper
from s3_helper import S3Helper
from dynamodb_helper import DynamoDBHelper

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageProcessorWorker:
    def __init__(self):
        self.sqs_helper = SQSHelper()
        self.s3_helper = S3Helper()
        self.db_helper = DynamoDBHelper()
        self.running = True
    
    def process_image(self, image_data, filter_type, strength, size_multiplier):
        """Your image processing logic from app.py"""
        try:
            img = Image.open(io.BytesIO(image_data))
            original_format = img.format if img.format else 'JPEG'
            
            # Apply size multiplier if needed
            if size_multiplier != 1.0:
                new_width = int(img.width * size_multiplier)
                new_height = int(img.height * size_multiplier)
                img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Apply filter with strength modifier
            if filter_type == 'BLUR':
                filtered_img = img.filter(ImageFilter.GaussianBlur(radius=strength/2))
            elif filter_type == 'CONTOUR':
                filtered_img = img
                for _ in range(strength):
                    filtered_img = filtered_img.filter(ImageFilter.CONTOUR)
            elif filter_type == 'DETAIL':
                filtered_img = img
                for _ in range(strength):
                    filtered_img = filtered_img.filter(ImageFilter.DETAIL)
            elif filter_type == 'EDGE_ENHANCE':
                filtered_img = img
                for _ in range(strength):
                    filtered_img = filtered_img.filter(ImageFilter.EDGE_ENHANCE_MORE)
            elif filter_type == 'EMBOSS':
                filtered_img = img
                for _ in range(strength):
                    filtered_img = filtered_img.filter(ImageFilter.EMBOSS)
            elif filter_type == 'SHARPEN':
                radius = max(1, strength / 3)
                percent = min(500, strength * 50)
                filtered_img = img.filter(ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=3))
            elif filter_type == 'SMOOTH':
                filtered_img = img
                for _ in range(strength):
                    filtered_img = filtered_img.filter(ImageFilter.SMOOTH_MORE)
            elif filter_type == 'EDGES':
                filtered_img = img.filter(ImageFilter.FIND_EDGES)
                enhancer = ImageEnhance.Contrast(filtered_img)
                filtered_img = enhancer.enhance(strength/2)
            else:
                filtered_img = img
            
            # Save processed image to buffer
            img_io = io.BytesIO()
            filtered_img.save(img_io, format=original_format)
            img_io.seek(0)
            processed_image_data = img_io.getvalue()
            
            return processed_image_data, original_format.lower()
            
        except Exception as e:
            logger.error(f"Error in image processing: {e}")
            raise
    
    def update_metadata_status(self, image_id, status):
        """Update image status in DynamoDB"""
        try:
            # You'll need to add this method to your DynamoDBHelper
            update_expression = "SET #status = :status"
            expression_values = {":status": status}
            expression_names = {"#status": "status"}
            
            self.db_helper.update_image_metadata(
                image_id, 
                update_expression, 
                expression_values,
                expression_names
            )
        except Exception as e:
            logger.error(f"Failed to update metadata for {image_id}: {e}")
    
    def process_message(self, message):
        try:
            body = json.loads(message['Body'])
            image_id = body['image_id']
            filter_type = body['filter_type']
            strength = body['strength']
            size_multiplier = body['size_multiplier']
            
            logger.info(f"Processing image {image_id} with filter {filter_type}")
            
            # Update status to processing
            self.update_metadata_status(image_id, 'processing')
            
            # Download original from S3
            original_data = self.s3_helper.download_image(f"original_{image_id}", is_processed=False)
            if not original_data:
                raise Exception(f"Failed to download original image {image_id}")
            
            # Process image using your logic
            processed_data, image_format = self.process_image(original_data, filter_type, strength, size_multiplier)
            
            # Upload processed image to S3
            success = self.s3_helper.upload_image(processed_data, image_id, is_processed=True)
            if not success:
                raise Exception(f"Failed to upload processed image {image_id}")
            
            # Update metadata to completed
            self.update_metadata_status(image_id, 'completed')
            
            # Update format in metadata if needed
            try:
                update_expression = "SET #format = :format"
                expression_values = {":format": image_format}
                expression_names = {"#format": "format"}
                self.db_helper.update_image_metadata(
                    image_id, 
                    update_expression, 
                    expression_values,
                    expression_names
                )
            except Exception as e:
                logger.warning(f"Could not update format for {image_id}: {e}")
            
            # Delete message from queue (successfully processed)
            self.sqs_helper.delete_message(message['ReceiptHandle'])
            
            logger.info(f"Successfully processed image {image_id}")
            
        except Exception as e:
            logger.error(f"Failed to process image {image_id}: {e}")
            # Update status to failed
            try:
                self.update_metadata_status(image_id, 'failed')
            except:
                pass
            # Don't delete message - it will return to queue after visibility timeout
            # This allows other workers to retry
    
    def start_worker(self):
        logger.info("Image processor worker started - waiting for messages...")
        while self.running:
            try:
                messages = self.sqs_helper.receive_messages()
                if messages:
                    logger.info(f"Received {len(messages)} messages to process")
                
                for message in messages:
                    self.process_message(message)
                
                # Short sleep if no messages to avoid tight loop
                if not messages:
                    time.sleep(5)
                else:
                    time.sleep(1)  # Small sleep between message processing
                    
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                time.sleep(10)  # Longer sleep on error
    
    def stop_worker(self):
        self.running = False
        logger.info("Image processor worker stopping...")

if __name__ == '__main__':
    worker = ImageProcessorWorker()
    try:
        worker.start_worker()
    except KeyboardInterrupt:
        worker.stop_worker()
    except Exception as e:
        logger.error(f"Worker crashed: {e}")