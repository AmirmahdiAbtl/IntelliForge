"""RAG routes"""
import os
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
import requests
from app.services.rag_service import rag_service
from app.config import config

rag_bp = Blueprint('rag_creator', __name__)


@rag_bp.route("/new", methods=["GET", "POST"])
def new_rag():
    """Create a new RAG project"""
    if request.method == "POST":
        rag_name = request.form.get("rag_name")
        if not rag_name:
            return jsonify({"error": "RAG name is required"}), 400
        
        rag_id = rag_service.create_rag(rag_name)
        return redirect(url_for('rag_creator.model_selection', rag_id=rag_id))
    
    return render_template("new_rag.html")


@rag_bp.route("/<int:rag_id>/model-selection", methods=["GET", "POST"])
def model_selection(rag_id):
    """Configure model for RAG"""
    if request.method == "POST":
        model_type = request.form.get("model_type")
        model_name = request.form.get("model_name")
        api_key = request.form.get("api_key", "")
        
        rag_service.update_model_config(rag_id, model_type, model_name, api_key)
        return redirect(url_for('rag_creator.db_embedding_selection', rag_id=rag_id))
    
    # GET: Show model selection form
    rag = rag_service.get_rag(rag_id)
    
    # Fetch Ollama models
    model_list = []
    try:
        url = "http://localhost:11434/api/tags"
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            data = response.json()
            for model in data.get("models", []):
                model_list.append(model["model"])
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        print(f"Warning: Could not connect to Ollama. Error: {e}")
    
    return render_template('model_selection.html', rag=rag, ollama_name=model_list)


@rag_bp.route("/<int:rag_id>/db-embedding", methods=["GET", "POST"])
def db_embedding_selection(rag_id):
    """Configure vector database for RAG"""
    if request.method == "POST":
        embedding_model = request.form.get("embedding_model")
        vector_db = request.form.get("vector_db")
        chunk_size = int(request.form.get("chunk_size", config.DEFAULT_CHUNK_SIZE))
        project_purpose = request.form.get("project_purpose", "")
        
        rag_service.update_vector_db_config(rag_id, embedding_model, vector_db, chunk_size)
        if project_purpose:
            rag_service.repo.update_rag_project_purpose(rag_id, project_purpose)
        
        return redirect(url_for('rag_creator.documentation_upload', rag_id=rag_id))
    
    rag = rag_service.get_rag(rag_id)
    return render_template('db_embedding_selection.html', rag=rag)


@rag_bp.route("/<int:rag_id>/documentation", methods=["GET", "POST"])
def documentation_upload(rag_id):
    """Upload documents to RAG"""
    if request.method == "POST":
        try:
            doc_type = request.form.get('doc_type')
            description = request.form.get('description', '')
            
            if doc_type == 'pdf':
                # Handle file upload
                if 'file' in request.files:
                    files = request.files.getlist('file')
                    for file in files:
                        if file and file.filename:
                            filename = secure_filename(file.filename)
                            upload_dir = os.path.join(config.UPLOAD_FOLDER, str(rag_id))
                            os.makedirs(upload_dir, exist_ok=True)
                            file_path = os.path.join(upload_dir, filename)
                            file.save(file_path)
                            
                            rag_service.add_document(rag_id, 'pdf', file_path, description)
            
            elif doc_type == 'link':
                # Handle URL
                doc_link = request.form.get('doc_link')
                if doc_link and doc_link.strip():
                    rag_service.add_document(rag_id, 'link', doc_link.strip(), description)
            
            elif doc_type == 'text':
                # Handle text content
                text_content = request.form.get('text_content')
                if text_content and text_content.strip():
                    # Create text file
                    upload_dir = os.path.join(config.UPLOAD_FOLDER, str(rag_id))
                    os.makedirs(upload_dir, exist_ok=True)
                    from datetime import datetime
                    filename = f"text_doc_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
                    file_path = os.path.join(upload_dir, filename)
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(text_content)
                    
                    rag_service.add_document(rag_id, 'text', file_path, description)
            
            # Check if this is continue button (finish adding documents)
            if request.form.get('finish'):
                return redirect(url_for('rag_creator.prompt_template', rag_id=rag_id))
            
            # Return success for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"success": True})
            
            # Otherwise return to same page to add more documents
            return redirect(url_for('rag_creator.documentation_upload', rag_id=rag_id))
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    # GET request - show form with existing documents
    rag = rag_service.get_rag(rag_id)
    documents = rag_service.repo.get_documents_with_descriptions(rag_id)
    return render_template('documentations.html', rag=rag, documents=documents)
    return render_template('documentations.html', rag=rag)


@rag_bp.route("/<int:rag_id>/details", methods=["GET"])
def rag_details(rag_id):
    """Show RAG details and chat interface"""
    rag = rag_service.get_rag(rag_id)
    if not rag:
        return "RAG not found", 404
    
    sessions = rag_service.get_chat_sessions(rag_id)
    documents = rag_service.get_documents_with_descriptions(rag_id)
    print(rag)
    return render_template('rag_details.html', rag=rag, sessions=sessions, documents=documents)


@rag_bp.route("/<int:rag_id>/chat", methods=["POST"])
def chat_with_rag(rag_id):
    """Chat with RAG"""
    try:
        data = request.get_json()
        query = data.get('query')
        session_id = data.get('session_id')
        
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        # Create session if one doesn't exist
        if not session_id:
            session_id = rag_service.create_chat_session(rag_id, "Chat Session")
        
        # Get chat history if session exists
        chat_history = []
        if session_id:
            history = rag_service.get_chat_history(session_id)
            chat_history = [
                (msg['user_message'], msg['bot_response']) 
                for msg in history
            ]
        
        # Query RAG
        result = rag_service.query_rag(rag_id, query, chat_history)
        
        # Save message to session (pass rag_id for name generation)
        if session_id:
            rag_service.add_chat_message(
                session_id, 
                query, 
                result['answer'],
                rag_id
            )
        
        return jsonify({
            "answer": result['answer'],
            "sources": [doc.page_content for doc in result.get('source_documents', [])],
            "session_id": session_id
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@rag_bp.route("/<int:rag_id>/new-session", methods=["POST"])
def new_session(rag_id):
    """Create a new chat session for RAG"""
    try:
        data = request.get_json()
        session_name = data.get('session_name', 'New Session')
        
        session_id = rag_service.create_chat_session(rag_id, session_name)
        
        return jsonify({
            "session_id": session_id,
            "session_name": session_name
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@rag_bp.route("/<int:rag_id>/prompt-template", methods=["GET", "POST"])
def prompt_template(rag_id):
    """Configure prompt template for RAG"""
    if request.method == "POST":
        try:
            prompt_template = request.form.get("prompt_template")
            if not prompt_template:
                return jsonify({"error": "Prompt template is required"}), 400
            
            # Save prompt template
            rag_service.update_prompt_template(rag_id, prompt_template)
            
            # Create vector database after prompt is confirmed
            rag_service.create_vector_database(rag_id)
            
            # Mark RAG as complete and redirect to details
            return redirect(url_for('rag_creator.rag_details', rag_id=rag_id))
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    # GET request - show prompt template form with auto-generated prompt
    rag = rag_service.get_rag(rag_id)
    
    # Get document descriptions for prompt generation
    documents = rag_service.repo.get_documents_with_descriptions(rag_id)
    doc_descriptions = ", ".join([doc['description'] for doc in documents if doc['description']])
    
    # Auto-generate prompt
    generated_prompt = ""
    project_purpose = rag.get('project_purpose', '') or "A general purpose AI assistant"
    
    # Always try to generate a prompt, even if some data is missing
    if rag.get('model_type') and rag.get('model_name'):
        from app.services.prompt_generation_service import prompt_generation_service
        try:
            print(f"DEBUG: Generating prompt with model_type={rag['model_type']}, project_purpose={project_purpose}, doc_descriptions={doc_descriptions}")
            generated_prompt = prompt_generation_service.generate_prompt(
                rag['model_type'], 
                rag['model_name'], 
                project_purpose, 
                doc_descriptions or "General documentation and knowledge base",
                rag.get('api_key', '')
            )
            print(f"DEBUG: Generated prompt: {generated_prompt[:200]}...")
        except Exception as e:
            print(f"Error generating prompt: {e}")
            # Fallback to default prompt with context
            generated_prompt = prompt_generation_service._get_default_prompt(project_purpose, doc_descriptions)
            print(f"DEBUG: Using fallback prompt: {generated_prompt[:200]}...")
    
    return render_template("prompt_template.html", rag=rag, prompt=generated_prompt)


@rag_bp.route("/<int:rag_id>/create-vectordb", methods=["POST"])
def create_vectordb(rag_id):
    """Create vector database for RAG"""
    try:
        rag_service.create_vector_database(rag_id)
        return jsonify({"message": "Vector database created successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@rag_bp.route("/<int:rag_id>/chat-interface", methods=["GET"])
def rag_chat(rag_id):
    """RAG chat interface"""
    rag = rag_service.get_rag(rag_id)
    if not rag:
        return "RAG not found", 404
    
    sessions = rag_service.get_chat_sessions(rag_id)
    return render_template('developerassistant.html', rag=rag, sessions=sessions)


@rag_bp.route("/<int:rag_id>/session/<int:session_id>/history", methods=["GET"])
def get_session_history(rag_id, session_id):
    """Get chat history for a session"""
    try:
        history = rag_service.get_chat_history(session_id)
        return jsonify(history)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@rag_bp.route("/<int:rag_id>/delete-document", methods=["POST"])
def delete_document(rag_id):
    """Delete a document from RAG"""
    try:
        data = request.get_json()
        doc_path = data.get('doc_path')
        
        if not doc_path:
            return jsonify({"error": "Document path is required"}), 400
            
        rag_service.delete_document(rag_id, doc_path)
        return jsonify({"message": "Document deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Legacy developer assistant routes - consolidated from old developer_routes.py
@rag_bp.route("/developerassistant", methods=["GET", "POST"])
@rag_bp.route("/developerassistant/<int:rag_id>", methods=["GET", "POST"])
def developer_assistant(rag_id=None):
    """Legacy developer assistant interface"""
    if request.method == "POST":
        try:
            query = request.form.get('userInput')
            rag_id = request.form.get('rag_id') or rag_id
            session_id = request.form.get('session_id')
            
            if not query:
                return jsonify({"error": "Query is required"}), 400
            
            if not rag_id:
                return jsonify({"error": "RAG ID is required"}), 400
            
            # Convert rag_id to int
            rag_id = int(rag_id)
            
            # Get or create session
            if not session_id:
                session_id = rag_service.create_chat_session(rag_id, "New Session")
            
            # Get chat history if session exists
            chat_history = []
            if session_id:
                history = rag_service.get_chat_history(int(session_id))
                chat_history = [
                    (msg['user_message'], msg['bot_response']) 
                    for msg in history
                ]
            
            # Query RAG
            result = rag_service.query_rag(rag_id, query, chat_history)
            
            # Save message to session
            if session_id:
                rag_service.add_chat_message(
                    int(session_id),
                    query,
                    result['answer'],
                    rag_id
                )
            
            return jsonify({
                "response": result['answer'],
                "session_id": session_id,
                "sources": [doc.page_content[:200] for doc in result.get('source_documents', [])]
            })
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    # GET request - if rag_id is provided, redirect to proper chat interface
    if rag_id:
        return redirect(url_for('rag_creator.rag_chat', rag_id=rag_id))
    
    # Otherwise show generic assistant page
    return render_template("developerassistant.html")


@rag_bp.route("/developerassistant/new_chat", methods=["POST"])
def developer_new_chat():
    """Create a new chat session for RAG"""
    try:
        rag_id = request.form.get('rag_id')
        if not rag_id:
            return jsonify({"error": "RAG ID is required"}), 400
        
        session_id = rag_service.create_chat_session(int(rag_id), "New Chat")
        
        return jsonify({
            "chat_id": session_id,
            "chat_name": "New Chat"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@rag_bp.route("/developerassistant/chat_history/<int:session_id>")
def developer_chat_history(session_id):
    """Get chat history for a session"""
    try:
        history = rag_service.get_chat_history(session_id)
        
        # Format for the expected response
        formatted_details = []
        for msg in history:
            formatted_details.append([
                msg['user_message'], 
                msg['bot_response']
            ])
        
        return jsonify({
            "chat_details": formatted_details
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
