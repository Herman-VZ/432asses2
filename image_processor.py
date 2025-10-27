from flask import Flask, request, jsonify
from PIL import Image, ImageFilter, ImageEnhance
import io
import boto3
import os
import logging
import time

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# S3 setup
s3 = boto3.client('s3')
ORIGINAL_BUCKET = 'n11957948-original-images'
PROCESSED_BUCKET = 'n11957948-processed-images'

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy", 
        "service": "image-processor",
        "timestamp": time.time()
    })

@app.route('/process', methods=['POST'])
def process_image():
    start_time = time.time()
    try:
        # Get parameters
        image_id = request.form.get('image_id')
        filter_type = request.form.get('filter', 'BLUR')
        strength = int(request.form.get('strength', 5))
        size_multiplier = float(request.form.get('size_multiplier', 1.0))
        
        logger.info(f"Processing image {image_id} with filter {filter_type}, strength {strength}")
        
        # Download from S3
        original_key = f"original_{image_id}"
        try:
            response = s3.get_object(Bucket=ORIGINAL_BUCKET, Key=original_key)
            image_data = response['Body'].read()
        except Exception as e:
            logger.error(f"Failed to download image from S3: {e}")
            return jsonify({
                "success": False,
                "error": f"Failed to download image: {str(e)}"
            }), 400
        
        # Process image
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
            
            # Upload processed image to S3
            s3.put_object(
                Bucket=PROCESSED_BUCKET,
                Key=image_id,
                Body=processed_image_data,
                ContentType=f'image/{original_format.lower()}'
            )
            
            processing_time = time.time() - start_time
            logger.info(f"Successfully processed image {image_id} in {processing_time:.2f}s")
            
            return jsonify({
                "success": True,
                "image_id": image_id,
                "format": original_format.lower(),
                "processing_time": processing_time,
                "service": "image-processor"
            })
            
        except Exception as processing_error:
            logger.error(f"Image processing error: {processing_error}")
            return jsonify({
                "success": False,
                "error": f"Image processing failed: {str(processing_error)}"
            }), 500
        
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/stats', methods=['GET'])
def stats():
    """Endpoint to get microservice statistics"""
    return jsonify({
        "service": "image-processor",
        "status": "running",
        "buckets": {
            "original": ORIGINAL_BUCKET,
            "processed": PROCESSED_BUCKET
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081, debug=False)