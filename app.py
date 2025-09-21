from flask import Flask, request, jsonify, render_template, session, redirect, url_for, send_file, g
from functools import wraps
import datetime
import os
from PIL import Image, ImageFilter, ImageEnhance
import io
import base64
import uuid
import concurrent.futures
import logging
from s3_helper import S3Helper
from dynamodb_helper import DynamoDBHelper
from cognito_helper import CognitoHelper
import sys

# Set up logging to output to stdout (Docker captures this)
logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET', 'flask-super-secret-key')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize AWS helpers
s3_helper = S3Helper()
db_helper = DynamoDBHelper()
cognito_helper = CognitoHelper()

# Custom decorator for Cognito JWT verification
def cognito_jwt_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({"msg": "Missing or invalid Authorization header"}), 401
        
        token = auth_header[7:]
        try:
            # Verify using Cognito helper
            claims = cognito_helper.verify_token(token)
            # Store user info in flask.g for access in routes
            g.cognito_user = claims
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return jsonify({"msg": f"Token verification failed: {str(e)}"}), 401
    return decorated_function

# Helper function to process a single image
def process_single_image(file, filter_type, strength, size_multiplier, current_user):
    try:
        img = Image.open(file.stream)
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
        
        # Generate a unique ID
        image_id = str(uuid.uuid4())
        
        # Save original image to S3
        file.stream.seek(0)  # Reset stream to beginning
        original_image_data = file.stream.read()
        s3_helper.upload_image(original_image_data, f"original_{image_id}")
        
        # Save processed image to buffer and then to S3
        img_io = io.BytesIO()
        filtered_img.save(img_io, format=original_format)
        img_io.seek(0)
        processed_image_data = img_io.getvalue()
        s3_helper.upload_image(processed_image_data, image_id, is_processed=True)
        
        # Store metadata in DynamoDB
        metadata = {
            'filename': file.filename,
            'filter': filter_type,
            'strength': strength,
            'size_multiplier': size_multiplier,
            'format': original_format.lower()
        }
        db_helper.put_image_metadata(image_id, current_user, metadata)
        
        # Generate presigned URL for the frontend
        image_url = s3_helper.generate_presigned_url(image_id, is_processed=True)
        
        return {
            "filename": file.filename,
            "message": "Image processed successfully",
            "filter": filter_type,
            "strength": strength,
            "size_multiplier": size_multiplier,
            "image_id": image_id,
            "image_url": image_url
        }
        
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        return {
            "filename": file.filename,
            "error": f"Error processing image: {str(e)}"
        }

# Web interface routes
@app.route('/')
def index():
    return render_template('index.html', token=session.get('token'), current_user=session.get('username'))

@app.route('/web/login', methods=['POST'])
def web_login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        return render_template('index.html', error="Username and password required")
    
    result = cognito_helper.authenticate(username, password)
    
    if result['success']:
        try:
            # Verify the token and get user claims
            claims = cognito_helper.verify_token(result['id_token'])
            
            # Use Cognito token directly (no Flask-JWT)
            session['token'] = result['id_token']
            session['cognito_token'] = result['id_token']
            session['username'] = claims.get('cognito:username', username)
            
            return redirect(url_for('index'))
            
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return render_template('index.html', error="Authentication failed")
    else:
        return render_template('index.html', error="Invalid credentials")

@app.route('/web/logout')
def web_logout():
    session.pop('token', None)
    session.pop('cognito_token', None)
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/web/test-endpoints')
@cognito_jwt_required
def web_test_endpoints():
    current_user = g.cognito_user.get('cognito:username', g.cognito_user.get('username'))
    return render_template('index.html', 
                         token=session.get('token'),
                         current_user=current_user,
                         test_results={"message": "Ready to test endpoints"})

# API routes
@app.route('/api/')
def api_root():
    return jsonify({"message": "Welcome to the CAB432 API Server"})

# New Cognito authentication endpoints
@app.route('/api/auth/signup', methods=['POST'])
def api_signup():
    if not request.is_json:
        return jsonify({"msg": "Missing JSON in request"}), 400
        
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    email = request.json.get('email', None)
    
    if not username or not password or not email:
        return jsonify({"msg": "Missing required fields"}), 400
        
    # Validate password strength (Cognito has requirements)
    if len(password) < 8:
        return jsonify({"msg": "Password must be at least 8 characters"}), 400
        
    result = cognito_helper.sign_up(username, password, email)
    
    if result['success']:
        return jsonify({
            "message": "User registered successfully. Please check your email for confirmation code.",
            "user_sub": result['user_sub']
        }), 200
    else:
        return jsonify({
            "msg": f"Sign up failed: {result.get('error_message', 'Unknown error')}"
        }), 400

@app.route('/api/auth/confirm', methods=['POST'])
def api_confirm_signup():
    if not request.is_json:
        return jsonify({"msg": "Missing JSON in request"}), 400
        
    username = request.json.get('username', None)
    confirmation_code = request.json.get('confirmation_code', None)
    
    if not username or not confirmation_code:
        return jsonify({"msg": "Missing username or confirmation code"}), 400
        
    result = cognito_helper.confirm_sign_up(username, confirmation_code)
    
    if result['success']:
        return jsonify({"msg": "User confirmed successfully"}), 200
    else:
        return jsonify({
            "msg": f"Confirmation failed: {result.get('error_message', 'Unknown error')}"
        }), 400

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    if not request.is_json:
        return jsonify({"msg": "Missing JSON in request"}), 400
        
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    
    if not username or not password:
        return jsonify({"msg": "Missing username or password"}), 400
        
    result = cognito_helper.authenticate(username, password)
    
    if result['success']:
        # Verify the token to ensure it's valid
        try:
            claims = cognito_helper.verify_token(result['id_token'])
            
            return jsonify({
                "access_token": result['access_token'],
                "id_token": result['id_token'],
                "token_type": "Bearer",
                "expires_in": result['expires_in']
            }), 200
            
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return jsonify({"msg": "Authentication failed: token verification error"}), 401
    else:
        return jsonify({
            "msg": f"Authentication failed: {result.get('error_message', 'Unknown error')}"
        }), 401

@app.route('/api/auth/userinfo', methods=['GET'])
@cognito_jwt_required
def api_user_info():
    try:
        # Get user info from Cognito
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            cognito_token = auth_header[7:]
            user_info = cognito_helper.get_user_info(cognito_token)
            return jsonify(user_info), 200
        else:
            return jsonify({"msg": "Authorization header missing or invalid"}), 401
    except Exception as e:
        logger.error(f"Failed to get user info: {e}")
        return jsonify({"msg": "Failed to retrieve user information"}), 500

@app.route('/api/protected', methods=['GET'])
@cognito_jwt_required
def api_protected():
    current_user = g.cognito_user.get('cognito:username', g.cognito_user.get('username'))
    
    # Try to get additional info from Cognito if available
    cognito_info = {}
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        try:
            cognito_token = auth_header[7:]
            cognito_info = cognito_helper.get_user_info(cognito_token)
        except:
            pass  # Fall back to basic info
    
    return jsonify({
        "logged_in_as": current_user,
        "cognito_info": cognito_info,
        "message": "This is a protected endpoint"
    }), 200

@app.route('/api/process', methods=['POST'])
@cognito_jwt_required
def api_process():
    current_user = g.cognito_user.get('cognito:username', g.cognito_user.get('username'))
    # Simulate CPU-intensive work
    import time
    time.sleep(2)  # Simulate processing time
    return jsonify({
        "message": "Processing complete", 
        "user": current_user,
        "result": "Sample processed data"
    }), 200

@app.route('/api/filter-image', methods=['POST'])
@cognito_jwt_required
def api_filter_image():
    current_user = g.cognito_user.get('cognito:username', g.cognito_user.get('username'))
    
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    
    file = request.files['image']
    filter_type = request.form.get('filter', 'BLUR')
    strength = int(request.form.get('strength', 5))
    size_multiplier = float(request.form.get('size_multiplier', 1.0))
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        result = process_single_image(file, filter_type, strength, size_multiplier, current_user)
        
        if 'error' in result:
            return jsonify({"error": result['error']}), 500
        else:
            return jsonify({
                "message": "Image processed successfully",
                "user": current_user,
                "filter": result['filter'],
                "strength": result['strength'],
                "size_multiplier": result['size_multiplier'],
                "image_id": result['image_id'],
                "image_url": result['image_url']
            }), 200

@app.route('/api/batch-filter-images', methods=['POST'])
@cognito_jwt_required
def api_batch_filter_images():
    current_user = g.cognito_user.get('cognito:username', g.cognito_user.get('username'))
    
    if 'images' not in request.files:
        return jsonify({"error": "No image files provided"}), 400
    
    uploaded_files = request.files.getlist('images')
    filter_type = request.form.get('filter', 'BLUR')
    strength = int(request.form.get('strength', 5))
    size_multiplier = float(request.form.get('size_multiplier', 1.0))
    
    if not uploaded_files or uploaded_files[0].filename == '':
        return jsonify({"error": "No selected files"}), 400
    
    results = []
    
    # Process images in parallel using ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Create a list of futures
        futures = []
        for file in uploaded_files:
            if file and file.filename != '':
                # Reset file stream position to ensure each thread gets a fresh copy
                file.stream.seek(0)
                futures.append(
                    executor.submit(
                        process_single_image, 
                        file, 
                        filter_type, 
                        strength, 
                        size_multiplier, 
                        current_user
                    )
                )
        
        # Wait for all futures to complete and collect results
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append({
                    "filename": "Unknown",
                    "error": f"Error processing image: {str(e)}"
                })
    
    return jsonify({
        "user": current_user,
        "processed_count": len([r for r in results if 'error' not in r]),
        "error_count": len([r for r in results if 'error' in r]),
        "results": results
    }), 200

@app.route('/api/my-images', methods=['GET'])
@cognito_jwt_required
def api_my_images():
    current_user = g.cognito_user.get('cognito:username', g.cognito_user.get('username'))

    # Get user's images from DynamoDB
    user_images = db_helper.get_user_images(current_user)

    # Generate presigned URLs for each image
    images_with_urls = []
    for img in user_images:
        image_url = s3_helper.generate_presigned_url(img['ImageID'], is_processed=True)
        images_with_urls.append({
            "image_id": img['ImageID'],
            "filter": img['Filter'],
            "strength": img['Strength'],
            "size_multiplier": img['SizeMultiplier'],
            "image_url": image_url
        })

    return jsonify(images_with_urls), 200

@app.route('/api/download-image/<image_id>', methods=['GET'])
def api_download_image(image_id):
    token = request.args.get('token')
    if not token:
        return jsonify({"error": "Missing token"}), 401
    
    try:
        claims = cognito_helper.verify_token(token)
    except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return jsonify({"error": "Invalid token"}), 401
        
    # Get image directly from S3
    image_data = s3_helper.download_image(image_id, is_processed=True)
    
    if not image_data:
        return jsonify({"error": "Image not found"}), 404
    
    # Get metadata from DynamoDB for filename
    metadata = db_helper.get_image_metadata(image_id)
    
    if metadata:
        filter_name = metadata['filter']
        format = metadata['format']
        filename = f"filtered_image_{filter_name.lower()}.{format}"
    else:
        filename = f"filtered_image.{image_id.split('.')[-1] if '.' in image_id else 'jpg'}"
    
    # Create in-memory file and send
    img_io = io.BytesIO(image_data)
    img_io.seek(0)
    
    return send_file(
        img_io,
        mimetype=f"image/{format if metadata else 'jpeg'}",
        as_attachment=True,
        download_name=filename
    )

@app.route('/api/health', methods=['GET'])
def api_health():
    """Health check endpoint to verify all services including Cognito"""
    try:
        # Test S3 connectivity
        s3_test = s3_helper.image_exists("test", is_processed=False)
        
        # Test DynamoDB connectivity
        db_test = db_helper.get_image_metadata("test")
        
        # Test Cognito connectivity by trying to get JWKS
        try:
            cognito_helper._get_jwks()
            cognito_connected = True
        except:
            cognito_connected = False
        
        return jsonify({
            "status": "healthy",
            "s3_connected": True,
            "dynamodb_connected": True,
            "cognito_connected": cognito_connected,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.datetime.utcnow().isoformat()
        }), 500

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
        
    app.run(debug=True, host='0.0.0.0', port=8080)