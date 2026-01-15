from flask import Blueprint, request, jsonify, send_from_directory, current_app
from werkzeug.utils import secure_filename
import os
import uuid

upload_bp = Blueprint('upload', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@upload_bp.route('/upload', methods=['POST'])
def upload_file():

    if 'image' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['image']
    product_name = request.form.get('product_name', '')
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):

        filename = secure_filename(file.filename)
        
        name_part = secure_filename(product_name.lower().replace(' ', '-'))
        unique_id = uuid.uuid4().hex[:8]
        ext = filename.rsplit('.', 1)[1].lower()
        new_filename = f"{name_part}_{unique_id}.{ext}"
        
        uploads_dir = os.path.join(current_app.root_path, 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        
        file_path = os.path.join(uploads_dir, new_filename)
        file.save(file_path)
        
        image_url = f"http://localhost:5000/uploads/{new_filename}"
        
        return jsonify({
            'success': True,
            'message': 'File uploaded successfully',
            'product_name': product_name,
            'image_url': image_url,
            'filename': new_filename
        }), 201
    
    return jsonify({'error': 'File type not allowed'}), 400

@upload_bp.route('/uploads/<filename>')
def uploaded_file(filename):
    uploads_dir = os.path.join(current_app.root_path, 'uploads')
    return send_from_directory(uploads_dir, filename)
