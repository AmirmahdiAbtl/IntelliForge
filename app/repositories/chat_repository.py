"""Repository for regular chat operations"""
from typing import List, Dict, Optional
from datetime import datetime
from app.repositories.database import get_db_connection


class ChatRepository:
    """Handle regular chat database operations"""
    
    @staticmethod
    def create_chat_session(name: str, language_model: str = 'pending', 
                          model_type: str = 'ChatGPT', api_key: str = 'pending') -> int:
        """Create a new chat session"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO regular_chat_season 
            (name, language_model, model_type, api_key, start_chat)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, language_model, model_type, api_key, timestamp))
        chat_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return chat_id
    
    @staticmethod
    def get_chat_session(chat_id: int) -> Optional[Dict]:
        """Get chat session by ID"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, language_model, model_type, api_key, name
            FROM regular_chat_season
            WHERE id = ?
        ''', (chat_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    @staticmethod
    def get_all_chat_sessions() -> List[Dict]:
        """Get all chat sessions"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM regular_chat_season ORDER BY start_chat DESC')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def update_chat_name(chat_id: int, name: str):
        """Update chat session name"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE regular_chat_season SET name = ? WHERE id = ?', (name, chat_id))
        conn.commit()
        conn.close()
    
    @staticmethod
    def update_chat_config(chat_id: int, language_model: str, model_type: str, 
                          api_key: str, temperature: float = 0.7):
        """Update chat configuration"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE regular_chat_season 
            SET language_model = ?, model_type = ?, api_key = ?, temperature = ?
            WHERE id = ?
        ''', (language_model, model_type, api_key, temperature, chat_id))
        conn.commit()
        conn.close()
    
    @staticmethod
    def add_chat_message(chat_id: int, prompt: str, response: str, embedding: str,
                        model_type: str, language_model: str, response_length: int,
                        execution_time: int, generated_at: str):
        """Add a chat message"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO regular_chat_detail
            (chat_id, prompt, chat_response, time, embedding, model_type, language_model, 
             response_length, execution_time, generated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (chat_id, prompt, response, timestamp, embedding, model_type, 
              language_model, response_length, execution_time, generated_at))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_chat_history(chat_id: int) -> List[Dict]:
        """Get chat history"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT prompt, chat_response, embedding, language_model, model_type,
                   response_length, execution_time, generated_at
            FROM regular_chat_detail
            WHERE chat_id = ?
            ORDER BY time ASC
        ''', (chat_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def get_chat_config(chat_id: int) -> Optional[Dict]:
        """Get chat configuration"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT language_model, model_type, api_key 
            FROM regular_chat_season 
            WHERE id = ?
        ''', (chat_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
