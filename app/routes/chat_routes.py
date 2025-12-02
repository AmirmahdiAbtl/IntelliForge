"""Regular chat routes"""
from flask import Blueprint, render_template, request, jsonify
import requests
from app.services.chat_service import chat_service

chat_bp = Blueprint('regular_chat', __name__)


@chat_bp.route("/", methods=["GET", "POST"])
def chat_interface():
    """Main chat interface"""
    if request.method == "POST":
        try:
            user_input = request.form.get('userInput', '').strip()
            chat_id = request.form.get('chat_id', None)
            web_search_enabled = request.form.get('web_search_enabled', 'false').lower() == 'true'
            
            # Debug output
            print(f"DEBUG: user_input={user_input}")
            print(f"DEBUG: chat_id={chat_id}")
            print(f"DEBUG: web_search_enabled={web_search_enabled}")
            print(f"DEBUG: form data={dict(request.form)}")
            
            if not user_input:
                return jsonify({"error": "Input cannot be empty"}), 400
            
            if not chat_id:
                return jsonify({"error": "Chat ID is required"}), 400
            
            # Process message through service with web search option
            result = chat_service.process_message(int(chat_id), user_input, web_search_enabled)
            return jsonify(result)
            
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    # GET: Display chat list
    chats = chat_service.get_all_chat_sessions()
    
    # Try to fetch Ollama models
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
    
    return render_template("regularchat.html", chats=chats, model_list=model_list)


@chat_bp.route("/<int:chat_id>", methods=["GET"])
def get_chat(chat_id):
    """Fetch chat history by chat_id"""
    try:
        session = chat_service.get_chat_session(chat_id)
        if not session:
            return jsonify({"error": "Chat not found"}), 404
        
        history = chat_service.repo.get_chat_history(chat_id)
        
        # Format chat details
        formatted_details = []
        for msg in history:
            response_metadata = {
                'response_length': msg['response_length'],
                'execution_time': msg['execution_time'],
                'generated_at': msg['generated_at']
            }
            formatted_details.append([
                msg['prompt'], 
                msg['chat_response'], 
                msg['model_type'], 
                msg['language_model'], 
                response_metadata
            ])
        
        return jsonify({
            "chat_name": session['name'],
            "chat_details": formatted_details
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/new_chat", methods=["POST"])
def new_chat():
    """Create a new chat session"""
    try:
        chat_id = chat_service.create_chat_session()
        return jsonify({"chat_id": chat_id, "chat_name": "New Chat"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@chat_bp.route('/update_model_config', methods=['POST'])
def update_model_config():
    """Update chat model configuration"""
    try:
        data = request.get_json()
        chat_id = data.get('chat_id')
        
        if not chat_id:
            # Create new chat if no ID provided
            chat_id = chat_service.create_chat_session()
        
        chat_service.update_chat_config(
            int(chat_id),
            data['language_model'],
            data['model_type'],
            data['api_key'],
            data.get('temperature', 0.7)
        )
        
        return jsonify({
            'success': True,
            'chat_id': chat_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@chat_bp.route('/get_model_config')
def get_model_config():
    """Get chat model configuration"""
    try:
        chat_id = request.args.get('chat_id')
        if not chat_id:
            return jsonify({'error': 'Chat ID not provided'}), 400
        
        config = chat_service.repo.get_chat_config(int(chat_id))
        
        if config:
            return jsonify({
                'language_model': config['language_model'],
                'model_type': config['model_type'],
                'api_key': config['api_key']
            })
        else:
            return jsonify({})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@chat_bp.route('/get_chat_config')
def get_chat_config():
    """Get chat configuration from latest message"""
    try:
        chat_id = request.args.get('chat_id')
        if not chat_id:
            return jsonify({'error': 'Chat ID not provided'}), 400
        
        # Get latest message or session config
        history = chat_service.repo.get_chat_history(int(chat_id))
        
        if history:
            latest = history[-1]
            return jsonify({
                'language_model': latest['language_model'],
                'model_type': latest['model_type']
            })
        else:
            config = chat_service.repo.get_chat_config(int(chat_id))
            if config:
                return jsonify({
                    'language_model': config['language_model'],
                    'model_type': config['model_type'],
                    'api_key': config.get('api_key')
                })
        
        return jsonify({})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400
