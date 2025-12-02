"""Database connection and initialization"""
import sqlite3
from app.config import config


def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables"""
    with sqlite3.connect(config.DATABASE_PATH) as conn:
        cursor = conn.cursor()
        
        # Regular Chat Tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS regular_chat_season (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                language_model TEXT NOT NULL,
                model_type VARCHAR(50) CHECK (model_type IN ('ChatGPT', 'Ollama', 'GROQ', 'GitHub')),
                api_key VARCHAR(255),
                temperature FLOAT DEFAULT 0.7,
                start_chat TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS regular_chat_detail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                prompt TEXT NOT NULL,
                chat_response TEXT NOT NULL,
                embedding BLOB NOT NULL,
                model_type VARCHAR(50),
                language_model TEXT,
                time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                response_length INTEGER,
                execution_time INTEGER,
                generated_at TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES regular_chat_season(id) ON DELETE CASCADE
            )
        ''')

        # RAG Tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rag (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) NOT NULL,
                model_type VARCHAR(50) CHECK (model_type IN ('ChatGPT', 'Ollama', 'GROQ', 'GitHub')),
                model_name VARCHAR(255),
                api_key VARCHAR(255),
                embedding_model VARCHAR(255),
                vector_db VARCHAR(50),
                chunk_size INTEGER,
                prompt_template TEXT,
                project_purpose TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rag_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rag_id INTEGER NOT NULL,
                doc_name VARCHAR(255),
                doc_type VARCHAR(50),
                doc_path TEXT,
                file_path TEXT,
                doc_link TEXT,
                description TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (rag_id) REFERENCES rag(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rag_chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rag_id INTEGER NOT NULL,
                session_name VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (rag_id) REFERENCES rag(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rag_chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                user_message TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES rag_chat_sessions(id) ON DELETE CASCADE
            )
        ''')

        conn.commit()
        
        # Run migrations to add missing columns
        _run_migrations(cursor)


def _run_migrations(cursor):
    """Run database migrations to add missing columns"""
    try:
        # Check if prompt_template column exists in rag table
        cursor.execute("PRAGMA table_info(rag)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'prompt_template' not in columns:
            cursor.execute('ALTER TABLE rag ADD COLUMN prompt_template TEXT')
        
        if 'project_purpose' not in columns:
            cursor.execute('ALTER TABLE rag ADD COLUMN project_purpose TEXT')
        
        # Check rag_documents table columns
        cursor.execute("PRAGMA table_info(rag_documents)")
        doc_columns = [column[1] for column in cursor.fetchall()]
        
        if 'doc_name' not in doc_columns:
            cursor.execute('ALTER TABLE rag_documents ADD COLUMN doc_name VARCHAR(255)')
        
        if 'file_path' not in doc_columns:
            cursor.execute('ALTER TABLE rag_documents ADD COLUMN file_path TEXT')
        
        if 'doc_link' not in doc_columns:
            cursor.execute('ALTER TABLE rag_documents ADD COLUMN doc_link TEXT')
        
        if 'description' not in doc_columns:
            cursor.execute('ALTER TABLE rag_documents ADD COLUMN description TEXT')
        
        if 'created_at' not in doc_columns:
            cursor.execute('ALTER TABLE rag_documents ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        
    except sqlite3.Error as e:
        print(f"Migration error: {e}")
        # Continue with app startup even if migration fails
