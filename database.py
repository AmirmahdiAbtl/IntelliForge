import sqlite3

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        # Regular Chat Database
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS regular_chat_season (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                language_model TEXT NOT NULL,
                model_type VARCHAR(50) CHECK (model_type IN ('ChatGPT', 'Ollama', 'GROQ')),
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
                time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES chat_season(id) ON DELETE CASCADE
            )
        ''')

        # Main RAG project table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rag (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) NOT NULL,

                -- Model selection (Step 1)
                model_type VARCHAR(50) CHECK (model_type IN ('ChatGPT', 'Ollama', 'GROQ')),
                model_name VARCHAR(255),
                api_key VARCHAR(255),

                -- Embedding setup (Step 2)
                embedding_model VARCHAR(255),
                vector_db VARCHAR(50),
                chunk_size INT,
                project_purpose TEXT,

                -- Prompt template (Step 4)
                prompt_template TEXT,

                -- Progress tracking
                status VARCHAR(50) DEFAULT 'created' CHECK (status IN ('init', 'created', 'configured', 'uploaded_docs', 'ready')),

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Uploaded documents
        cursor.execute(''' 
            CREATE TABLE IF NOT EXISTS rag_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rag_id INTEGER NOT NULL,
                doc_name VARCHAR(255) NOT NULL,
                doc_type VARCHAR(50) CHECK (doc_type IN ('pdf', 'link', 'text')),
                doc_link TEXT,
                file_path TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (rag_id) REFERENCES rag(id) ON DELETE CASCADE
            )
        ''')

        # Chat session (RAG usage)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_season (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rag_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                language_model TEXT NOT NULL,
                start_chat TEXT NOT NULL,
                FOREIGN KEY (rag_id) REFERENCES rag(id) ON DELETE CASCADE
            )
        ''')

        # Chat detail logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_detail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                prompt TEXT NOT NULL,
                chat_response TEXT NOT NULL,
                embedding BLOB NOT NULL,
                time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES chat_season(id) ON DELETE CASCADE
            )
        ''')
        

        conn.commit()

def get_all_rags():
    """Get all RAG applications from the database"""
    with sqlite3.connect('database.db') as conn:
        conn.row_factory = sqlite3.Row  # This enables column access by name
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM rag ORDER BY created_at DESC')
        return [dict(row) for row in cursor.fetchall()]

def create_rag(name, model_type=None, model_name=None, api_key=None):
    """Create a new RAG application with initial details"""
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO rag (name, model_type, model_name, api_key, status)
               VALUES (?, ?, ?, ?, ?)''',
            (name, model_type, model_name, api_key, 'init')
        )
        rag_id = cursor.lastrowid
        conn.commit()
        return rag_id

def update_rag(rag_id, data, status=None):
    """Update RAG application details"""
    allowed_fields = [
        'name', 'model_type', 'model_name', 'api_key','embedding_model', 
        'vector_db', 'chunk_size', 'project_purpose', 'prompt_template'
    ]
    
    update_fields = []
    values = []
    
    for field in allowed_fields:
        if field in data and data[field] is not None:
            update_fields.append(f"{field} = ?")
            values.append(data[field])
    
    if status:
        update_fields.append("status = ?")
        values.append(status)
    
    if not update_fields:
        return False
    
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        query = f'''UPDATE rag SET {", ".join(update_fields)} WHERE id = ?'''
        values.append(rag_id)
        cursor.execute(query, values)
        conn.commit()
        return cursor.rowcount > 0

def get_rag(rag_id):
    """Get a RAG application by ID"""
    with sqlite3.connect('database.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM rag WHERE id = ?', (rag_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def add_document_to_rag(rag_id, doc_name, doc_type, doc_link=None, file_path=None, description=None):
    """Add a document to a RAG application"""
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO rag_documents (rag_id, doc_name, doc_type, doc_link, file_path, description)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (rag_id, doc_name, doc_type, doc_link, file_path, description)
        )
        conn.commit()
        return cursor.lastrowid

def get_rag_documents(rag_id):
    """Get all documents for a RAG application"""
    with sqlite3.connect('database.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM rag_documents WHERE rag_id = ?', (rag_id,))
        return [dict(row) for row in cursor.fetchall()]

def create_chat_session(rag_id, name, language_model, start_chat):
    """Create a new chat session for a RAG application"""
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO chat_season (rag_id, name, language_model, start_chat)
               VALUES (?, ?, ?, ?)''',
            (rag_id, name, language_model, start_chat)
        )
        chat_id = cursor.lastrowid
        conn.commit()
        return chat_id

def get_chat_sessions_for_rag(rag_id):
    """Get all chat sessions for a RAG application"""
    with sqlite3.connect('database.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM chat_season WHERE rag_id = ? ORDER BY start_chat DESC', (rag_id,))
        return [dict(row) for row in cursor.fetchall()]
