"""File handling utilities"""
import os
from werkzeug.utils import secure_filename
from typing import Tuple


ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx', 'md'}


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file, upload_dir: str) -> Tuple[str, str]:
    """
    Save uploaded file
    
    Args:
        file: File object from request.files
        upload_dir: Directory to save file
        
    Returns:
        Tuple of (file_path, file_type)
    """
    if not file or not file.filename:
        raise ValueError("No file provided")
    
    filename = secure_filename(file.filename)
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)
    
    # Determine file type
    if filename.endswith('.pdf'):
        file_type = 'pdf'
    else:
        file_type = 'text'
    
    return file_path, file_type
