import os
import sqlite3
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify
from langchain.prompts import PromptTemplate
from utils import get_retrieval_chain, get_llm, generate_embedding, name_generator
import requests
import numpy as np
import json
from langchain.chains import LLMChain
from database import get_rag, get_rag_documents, create_chat_session, get_chat_sessions_for_rag, get_rag_documents, get_db_connection
regular_chat_bp = Blueprint('regular_chat', __name__)

@regular_chat_bp.route("/", methods=["GET", "POST"])
def generate_story():
    if request.method == "POST":
        try:
            user_input = request.form.get('userInput', '').strip()
            chat_id = request.form.get('chat_id', None)

            # Check if chat exists and has configuration
            with sqlite3.connect('database.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''SELECT id, language_model, model_type, api_key
                       FROM regular_chat_season
                       WHERE id = ?''',
                    (chat_id,)
                )
                chat_config = cursor.fetchone()

                if not chat_config:
                    return jsonify({"error": "Chat not found"}), 404
                
                # Check if chat has required configuration
                if chat_config[1] == 'pending' or chat_config[3] == 'pending':
                    return jsonify({"error": "Please configure the chat model before sending messages. Click the gear icon to configure."}), 400

                # Attempt to retrieve existing chat
                cursor.execute(
                    '''SELECT id
                       FROM regular_chat_season
                       WHERE id = ?''',
                    (chat_id,)
                )
                existing_chat = cursor.fetchone()

                # If not found, create it
                if not existing_chat:
                    model_name = "llama-3.3-70b-versatile"
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    chat_name = user_input[:50] if len(user_input) > 50 else user_input

                    cursor.execute(
                        '''INSERT INTO regular_chat_season (name, language_model, start_chat)
                           VALUES (?, ?, ?)''',
                        (chat_name, model_name, timestamp)
                    )
                    chat_id = cursor.lastrowid
                    
                    # print(chat_id)
            with sqlite3.connect('database.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''SELECT prompt, chat_response, embedding
                    FROM regular_chat_detail
                    WHERE chat_id = ?
                    ORDER BY time ASC''',
                    (chat_id,)
                )
                # conn.commit()
            chat_history_rows = cursor.fetchall()
            print(f"Chat history rows: {len(chat_history_rows)}")
            if len(chat_history_rows) == 0:
                print("Here i am 2")
                with sqlite3.connect('database.db') as conn:
                    cursor.execute(
                        '''SELECT model_type, language_model, api_key
                        FROM regular_chat_season
                        WHERE id = ?''',
                        (chat_id,)
                    )
                configuration = cursor.fetchall()
                print(configuration[0][0])
                sug_name = name_generator(configuration[0][0], configuration[0][1], user_input, configuration[0][2])
                print(sug_name)
                with sqlite3.connect('database.db') as conn:
                    cursor = conn.cursor()
                    query = '''UPDATE regular_chat_season SET name = ? WHERE id = ?'''
                    values = (sug_name, chat_id)
                    cursor.execute(query, values)
                    conn.commit()
                print(f"Chat name updated to: {sug_name}")    
            # Format chat history (only the prompt and response are used in final chain)
            formatted_chat_history = []
            for row in chat_history_rows:
                prompt = row[0]
                # row[1] is the stored OpenAPI content (ignored when creating the final prompt text, but kept in DB)
                response = row[1]
                formatted_chat_history.append((prompt, response))

            similarities = []
            query_embedding = generate_embedding(user_input)
            for row in chat_history_rows:
                db_embedding_bytes = json.loads(row[2])
                # Compute cosine similarity
                numerator = float(np.dot(query_embedding, db_embedding_bytes))
                denominator = float(np.linalg.norm(query_embedding) * np.linalg.norm(db_embedding_bytes) + 1e-8)
                similarity = numerator / denominator
                similarities.append({
                    "prompt": row[0],
                    "response": row[1],
                    "similarity": similarity
                })
            sorted_results = sorted(similarities, key=lambda x: x["similarity"], reverse=True)
            top_3 = sorted_results[:3]

            for item in top_3:
                formatted_chat_history.append((item['prompt'], item['response']))

            print("Here")
            prompt_template = PromptTemplate(
                input_variables=["chat_history", "question"],
                template="""
                This is the summary of our chat: {chat_history}
                You are a regular Chat Bot and use the chat history as memory of the previous chat has been done.
                question : {question}
                """
            )
            with sqlite3.connect('database.db') as conn:
                    cursor.execute(
                        '''SELECT model_type, language_model, api_key
                        FROM regular_chat_season
                        WHERE id = ?''',
                        (chat_id,)
                    )
            configuration = cursor.fetchall()
            llm = get_llm(configuration[0][1], configuration[0][2], configuration[0][0])
            chat_chain = LLMChain(llm=llm, prompt=prompt_template) 

            response = chat_chain.run(chat_history=formatted_chat_history, question=user_input)
            print(response)
            embedding_vec = generate_embedding(f"{response}, {user_input}")
            embedding_json = json.dumps(embedding_vec)

            # Store changes in a single transaction
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with sqlite3.connect('database.db') as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''INSERT INTO regular_chat_detail
                    (chat_id, prompt, chat_response, time, embedding)
                    VALUES (?, ?, ?, ?, ?)''',
                    (chat_id, user_input, response, timestamp, embedding_json)
                )
                conn.commit()

            return jsonify({"response": response, "chat_id": chat_id})

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # If GET, fetch all existing chats
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM regular_chat_season ORDER BY start_chat DESC')
        chats = cursor.fetchall()
    url = "http://localhost:11434/api/tags"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
    model_list = []
    for model in data["models"]:
        model_list.append(model["model"])
    return render_template("regularchat.html", chats=chats, model_list=model_list)


@regular_chat_bp.route("/<int:chat_id>", methods=["GET"])
def get_chat(chat_id):
    """Fetch chat history by chat_id."""
    try:
        print("Here i am")
        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT name FROM regular_chat_season
                   WHERE id = ?''',
                (chat_id,)
            )
            chat_name = cursor.fetchone()

            cursor.execute(
                '''SELECT prompt, chat_response
                   FROM regular_chat_detail
                   WHERE chat_id = ?
                   ORDER BY time ASC''',
                (chat_id,)
            )
            chat_details = cursor.fetchall()

        if chat_name is None:
            return jsonify({"error": "Chat not found"}), 404

        return jsonify({"chat_name": chat_name[0], "chat_details": chat_details})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@regular_chat_bp.route("/new_chat", methods=["POST"])
def new_chat():
    """Create and return a new empty chat session."""
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        chat_name = f"New Chat"

        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO regular_chat_season 
                   (name, language_model, model_type, api_key, start_chat)
                   VALUES (?, ?, ?, ?, ?)''',
                (chat_name, 'pending', 'ChatGPT', 'pending', timestamp)
            )
            chat_id = cursor.lastrowid
            conn.commit()

        return jsonify({"chat_id": chat_id, "chat_name": chat_name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@regular_chat_bp.route('/update_model_config', methods=['POST'])
def update_model_config():
    try:
        data = request.get_json()
        chat_id = data.get('chat_id')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if not chat_id:
            # Create a new chat session
            chat_name = f"New Chat {timestamp}"
            cursor.execute('''
                INSERT INTO regular_chat_season 
                (name, language_model, model_type, api_key, temperature, start_chat)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                chat_name,
                data['language_model'],
                data['model_type'],
                data['api_key'],
                data.get('temperature', 0.7),
                timestamp
            ))
            chat_id = cursor.lastrowid
        else:
            # Update existing chat session
            cursor.execute('''
                UPDATE regular_chat_season 
                SET language_model = ?, 
                    model_type = ?, 
                    api_key = ?, 
                    temperature = ?
                WHERE id = ?
            ''', (
                data['language_model'],
                data['model_type'],
                data['api_key'],
                data.get('temperature', 0.7),
                chat_id
            ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'chat_id': chat_id,
            'chat_name': chat_name if not chat_id else None
        })
        
    except Exception as e:
        print(f"Error updating model config: {str(e)}")
        return jsonify({'error': str(e)}), 400

@regular_chat_bp.route('/get_model_config')
def get_model_config():
    try:
        chat_id = request.args.get('chat_id')
        if not chat_id:
            return jsonify({'error': 'Chat ID not provided'}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT language_model, model_type, api_key 
            FROM regular_chat_season 
            WHERE id = ?
        ''', (chat_id,))
        
        config = cursor.fetchone()
        conn.close()
        
        if config:
            return jsonify({
                'language_model': config[0],
                'model_type': config[1],
                'api_key': config[2]
            })
        else:
            return jsonify({})  # Return empty object if no config exists
            
    except Exception as e:
        print(f"Error getting model config: {str(e)}")
        return jsonify({'error': str(e)}), 400