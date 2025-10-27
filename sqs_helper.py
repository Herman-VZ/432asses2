import boto3
import json
import logging

logger = logging.getLogger(__name__)

class SQSHelper:
    def __init__(self):
        self.sqs = boto3.client('sqs', region_name='ap-southeast-2')
        self.queue_url = None
        self._get_or_create_queue()
    
    def _get_or_create_queue(self):
        try:
            # Try to get existing queue
            response = self.sqs.get_queue_url(QueueName='image-processing-queue')
            self.queue_url = response['QueueUrl']
        except:
            # Create new queue
            response = self.sqs.create_queue(
                QueueName='image-processing-queue',
                Attributes={
                    'VisibilityTimeout': '300',  # 5 minutes
                    'MessageRetentionPeriod': '86400'  # 1 day
                }
            )
            self.queue_url = response['QueueUrl']
    
    def send_processing_task(self, image_id, filter_type, strength, size_multiplier):
        message = {
            'image_id': image_id,
            'filter_type': filter_type,
            'strength': strength,
            'size_multiplier': size_multiplier
        }
        
        response = self.sqs.send_message(
            QueueUrl=self.queue_url,
            MessageBody=json.dumps(message)
        )
        return response
    
    def receive_messages(self, max_messages=10):
        response = self.sqs.receive_message(
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=20
        )
        return response.get('Messages', [])
    
    def delete_message(self, receipt_handle):
        self.sqs.delete_message(
            QueueUrl=self.queue_url,
            ReceiptHandle=receipt_handle
        )