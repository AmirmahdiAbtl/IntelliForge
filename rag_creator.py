import os
import sqlite3
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from werkzeug.utils import secure_filename
from database import create_rag, update_rag, get_rag, add_document_to_rag, get_rag_documents
from utils import create_vectordb, prompt_generator_groq
import requests
rag_creator_bp = Blueprint('rag_creator', __name__)

# Constants
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'docx'}

# Utility functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@rag_creator_bp.route('/new', methods=['GET', 'POST'])
def create_new_rag():
    """Create a new RAG application and redirect to the first phase"""
    if request.method == 'POST':
        rag_name = request.form.get('rag_name', f"New RAG Project - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        rag_id = create_rag(rag_name)
        return redirect(url_for('rag_creator.model_selection', rag_id=rag_id))
    
    # If GET, show new RAG creation form
    return render_template('new_rag.html')

@rag_creator_bp.route('/<int:rag_id>/model-selection', methods=['GET', 'POST'])
def model_selection(rag_id):
    """Phase 1: Model selection"""
    if request.method == 'POST':
        model_type = request.form.get('model_type')
        model_name = request.form.get('model_name')
        api_key = request.form.get('api_key')  # We might not store this in the DB but use it in the session

        # Store API key in session if provided
        # try:
        #     if api_key:
        #         session[f'api_key_{rag_id}'] = api_key
        # except Exception as e:
        #     # Continue without setting session if there's an error
        #     print(f"Warning: Could not store API key in session: {str(e)}")
        
        # Update the RAG entry
        update_data = {
            'model_type': model_type,
            'model_name': model_name,
            'api_key': api_key,
        }
        update_rag(rag_id, update_data, 'created')
        
        # Move to the next phase
        return redirect(url_for('rag_creator.db_embedding_selection', rag_id=rag_id))
    
    # If GET, show the model selection form
    rag = get_rag(rag_id)
    url = "http://localhost:11434/api/tags"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
    model_list = []
    for model in data["models"]:
        model_list.append(model["model"])
    return render_template('model_selection.html', rag=rag, ollama_name = model_list)

@rag_creator_bp.route('/<int:rag_id>/db-embedding', methods=['GET', 'POST'])
def db_embedding_selection(rag_id):
    """Phase 2: Database and embedding selection"""
    if request.method == 'POST':
        embedding_model = request.form.get('embedding_model')
        vector_db = request.form.get('vector_db')
        chunk_size = request.form.get('chunk_size')
        project_purpose = request.form.get('project_purpose')
        
        # Update the RAG entry
        update_data = {
            'embedding_model': embedding_model,
            'vector_db': vector_db,
            'chunk_size': int(chunk_size) if chunk_size else None,
            'project_purpose': project_purpose
        }
        update_rag(rag_id, update_data, 'configured')
        
        # Move to the next phase
        return redirect(url_for('rag_creator.documentation_upload', rag_id=rag_id))
    
    # If GET, show the embedding form
    rag = get_rag(rag_id)
    return render_template('db_embedding_selection.html', rag=rag)

@rag_creator_bp.route('/<int:rag_id>/documentation', methods=['GET', 'POST'])
def documentation_upload(rag_id):
    """Phase 3: Documentation upload"""
    if request.method == 'POST':
        doc_type = request.form.get('doc_type')
        
        if doc_type == 'pdf':
            # Handle file upload
            if 'file' not in request.files:
                return jsonify({"error": "No file part"}), 400
            
            files = request.files.getlist('file')  # Get list of files
            if not files or files[0].filename == '':
                return jsonify({"error": "No selected file"}), 400
            
            # Process each file
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    os.makedirs(f'{UPLOAD_FOLDER}\{rag_id}', exist_ok=True)
                    file_path = os.path.join(f'{UPLOAD_FOLDER}\{rag_id}', filename)
                    file.save(file_path)
                    
                    # Store document info in the database
                    add_document_to_rag(
                        rag_id=rag_id,
                        doc_name=filename,
                        doc_type='pdf',
                        file_path=file_path,
                        description=request.form.get('description', '')
                    )
                
        elif doc_type == 'link':
            # Handle URL documentation
            doc_link = request.form.get('doc_link')
            if not doc_link:
                return jsonify({"error": "No URL provided"}), 400
            # Store document info in the database
            add_document_to_rag(
                rag_id=rag_id,
                doc_name=doc_link[:50],  # Use first part of URL as name
                doc_type='link',
                doc_link=doc_link,
                description=request.form.get('description', '')
            )
            
        elif doc_type == 'text':
            # Handle direct text input
            text_content = request.form.get('text_content')
            if not text_content:
                return jsonify({"error": "No text content provided"}), 400
            
            # Create a text file to store the content
            os.makedirs(f"{UPLOAD_FOLDER}\{rag_id}", exist_ok=True)
            filename = f"text_doc_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
            file_path = os.path.join(f"{UPLOAD_FOLDER}\{rag_id}", filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            with open(file_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
            print(text_content)
            # Store document info in the database
            add_document_to_rag(
                rag_id=rag_id,
                doc_name=filename,
                doc_type='text',
                file_path=file_path,
                description=request.form.get('description', '')
            )
        
        # If this is an AJAX request, return success
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": True})
        
        # Otherwise, redirect to continue adding documents or move to the next phase
        if request.form.get('finish', False):
            update_rag(rag_id, {}, 'uploaded_docs')
            documentations = []
            docs = get_rag_documents(rag_id)
            rag_inf = get_rag(rag_id)
            for doc in docs:
                if doc['doc_type'] == 'link':
                    documentations.append((doc['doc_type'], doc['doc_link']))
                elif doc['doc_type'] == 'pdf':
                    documentations.append((doc['doc_type'], doc['file_path']))
                elif doc['doc_type'] == 'text':
                    documentations.append((doc['doc_type'], doc['file_path']))
            print(documentations)
            vectorcreating = create_vectordb(documentations, rag_inf["vector_db"], rag_inf["chunk_size"], f"rag_{rag_id}")
            
            return redirect(url_for('rag_creator.prompt_template', rag_id=rag_id))
        else:
            return redirect(url_for('rag_creator.documentation_upload', rag_id=rag_id))
    
    # If GET, show the documentation upload form
    rag = get_rag(rag_id)
    documents = get_rag_documents(rag_id)
    return render_template('documentations.html', rag=rag, documents=documents)

@rag_creator_bp.route('/<int:rag_id>/prompt-template', methods=['GET', 'POST'])
def prompt_template(rag_id):
    """Phase 4: Prompt template"""
    if request.method == 'POST':
        prompt_template = request.form.get('prompt_template')
        
        # Update the RAG entry
        update_data = {
            'prompt_template': prompt_template
        }
        update_rag(rag_id, update_data, 'ready')
        
        # Move to the chat interface
        return redirect(url_for('developerassistant.chat_with_rag', rag_id=rag_id))
    
    # If GET, show the prompt template form
    rag = get_rag(rag_id)
    rag_docs = get_rag_documents(rag_id)
    doc_descriptions = ""
    for doc in rag_docs:
        doc_descriptions = doc_descriptions + doc['description'] + ", "
    prompt = prompt_generator_groq(rag["model_type"], rag["model_name"], rag["project_purpose"], doc_descriptions, rag["api_key"])
    return render_template('prompt_template.html', rag=rag, prompt=prompt)

@rag_creator_bp.route('/<int:rag_id>/details')
def rag_details(rag_id):
    """View RAG application details"""
    rag = get_rag(rag_id)
    documents = get_rag_documents(rag_id)
    return render_template('rag_details.html', rag=rag, documents=documents)

@rag_creator_bp.route('/<int:rag_id>/delete_document/<int:doc_id>', methods=['POST'])
def delete_document(rag_id, doc_id):
    """Delete a document from the RAG application"""
    try:
        # Get document info before deletion
        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT file_path FROM rag_documents WHERE id = ? AND rag_id = ?', (doc_id, rag_id))
            doc = cursor.fetchone()
            
            if not doc:
                return jsonify({"error": "Document not found"}), 404
            
            # Delete the file if it exists
            if doc[0] and os.path.exists(doc[0]):
                try:
                    os.remove(doc[0])
                except Exception as e:
                    print(f"Error deleting file: {str(e)}")
            
            # Delete from database
            cursor.execute('DELETE FROM rag_documents WHERE id = ? AND rag_id = ?', (doc_id, rag_id))
            conn.commit()
            
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500 