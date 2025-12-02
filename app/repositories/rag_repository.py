"""Repository for RAG operations"""
from typing import List, Dict, Optional, Tuple
from app.repositories.database import get_db_connection


class RAGRepository:
    """Handle RAG database operations"""
    
    @staticmethod
    def create_rag(name: str) -> int:
        """Create a new RAG project"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO rag (name) VALUES (?)', (name,))
        rag_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return rag_id
    
    @staticmethod
    def get_rag(rag_id: int) -> Optional[Dict]:
        """Get RAG by ID"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM rag WHERE id = ?', (rag_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    @staticmethod
    def get_all_rags() -> List[Dict]:
        """Get all RAG projects"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM rag ORDER BY created_at DESC')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def update_rag_model(rag_id: int, model_type: str, model_name: str, api_key: str):
        """Update RAG model configuration"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE rag 
            SET model_type = ?, model_name = ?, api_key = ?
            WHERE id = ?
        ''', (model_type, model_name, api_key, rag_id))
        conn.commit()
        conn.close()
    
    @staticmethod
    def update_rag_vector_db(rag_id: int, embedding_model: str, vector_db: str, chunk_size: int):
        """Update RAG vector database configuration"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE rag 
            SET embedding_model = ?, vector_db = ?, chunk_size = ?
            WHERE id = ?
        ''', (embedding_model, vector_db, chunk_size, rag_id))
        conn.commit()
        conn.close()
    
    @staticmethod
    def update_rag_prompt_template(rag_id: int, prompt_template: str):
        """Update RAG prompt template"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE rag 
            SET prompt_template = ?
            WHERE id = ?
        ''', (prompt_template, rag_id))
        conn.commit()
        conn.close()
    
    @staticmethod
    def update_rag_project_purpose(rag_id: int, project_purpose: str):
        """Update RAG project purpose"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE rag 
            SET project_purpose = ?
            WHERE id = ?
        ''', (project_purpose, rag_id))
        conn.commit()
        conn.close()
    
    @staticmethod
    def add_document(rag_id: int, doc_type: str, doc_path: str, description: str = ""):
        """Add a document to RAG"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if doc_type == 'link':
            # For URLs, store in doc_link column
            doc_name = doc_path[:50]  # Use first part of URL as name
            cursor.execute('''
                INSERT INTO rag_documents (rag_id, doc_name, doc_type, doc_link, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (rag_id, doc_name, doc_type, doc_path, description))
        else:
            # For files, store in file_path column
            import os
            doc_name = os.path.basename(doc_path)  # Extract filename
            cursor.execute('''
                INSERT INTO rag_documents (rag_id, doc_name, doc_type, file_path, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (rag_id, doc_name, doc_type, doc_path, description))
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_documents(rag_id: int) -> List[Tuple[str, str]]:
        """Get all documents for a RAG"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT doc_type, 
                   CASE 
                       WHEN doc_type = 'link' THEN doc_link 
                       ELSE file_path 
                   END as doc_path
            FROM rag_documents 
            WHERE rag_id = ?
        ''', (rag_id,))
        rows = cursor.fetchall()
        conn.close()
        return [(row['doc_type'], row['doc_path']) for row in rows]
    
    @staticmethod
    def get_documents_with_descriptions(rag_id: int) -> List[Dict]:
        """Get all documents with descriptions for a RAG"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT doc_name, doc_type, description,
                   CASE 
                       WHEN doc_type = 'link' THEN doc_link 
                       ELSE file_path 
                   END as doc_path
            FROM rag_documents 
            WHERE rag_id = ?
            ORDER BY created_at
        ''', (rag_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def delete_document(rag_id: int, doc_path: str):
        """Delete a document from RAG"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM rag_documents 
            WHERE rag_id = ? AND (file_path = ? OR doc_link = ?)
        ''', (rag_id, doc_path, doc_path))
        conn.commit()
        conn.close()
    
    @staticmethod
    def create_chat_session(rag_id: int, session_name: str) -> int:
        """Create a new chat session"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO rag_chat_sessions (rag_id, session_name)
            VALUES (?, ?)
        ''', (rag_id, session_name))
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return session_id
    
    @staticmethod
    def get_chat_sessions(rag_id: int) -> List[Dict]:
        """Get all chat sessions for a RAG"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM rag_chat_sessions 
            WHERE rag_id = ?
            ORDER BY created_at DESC
        ''', (rag_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def add_chat_message(session_id: int, user_message: str, bot_response: str):
        """Add a chat message"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO rag_chat_messages (session_id, user_message, bot_response)
            VALUES (?, ?, ?)
        ''', (session_id, user_message, bot_response))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_chat_history(session_id: int) -> List[Dict]:
        """Get chat history for a session"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM rag_chat_messages 
            WHERE session_id = ?
            ORDER BY created_at ASC
        ''', (session_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def update_chat_session_name(session_id: int, name: str):
        """Update chat session name"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE rag_chat_sessions SET session_name = ? WHERE id = ?
        ''', (name, session_id))
        conn.commit()
        conn.close()
