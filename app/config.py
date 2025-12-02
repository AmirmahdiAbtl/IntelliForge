"""Application configuration"""
from dotenv import load_dotenv
import os
from dataclasses import dataclass
from typing import Optional

# Load environment variables
load_dotenv()


@dataclass
class Config:
    """Application configuration"""
    
    # API Keys
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    GITHUB_TOKEN: Optional[str] = os.getenv("GITHUB_TOKEN")
    
    # Model Settings
    EMBEDDING_MODEL_NAME: str = os.getenv(
        "EMBEDDING_MODEL_NAME", 
        "sentence-transformers/all-MiniLM-L6-v2"
    )
    LLM_MODEL_NAME: Optional[str] = os.getenv("LLM_MODEL_NAME")
    
    # Database
    DATABASE_PATH: str = "database.db"
    
    # Vector Database
    VECTOR_DB_PATH: str = "vectorDB"
    
    # File Upload
    UPLOAD_FOLDER: str = "uploads"
    MAX_FILE_SIZE: int = 16 * 1024 * 1024  # 16MB
    
    # Chunk Settings
    DEFAULT_CHUNK_SIZE: int = 1000
    DEFAULT_CHUNK_OVERLAP: int = 50
    
    # Model Types
    SUPPORTED_MODEL_TYPES = ['ChatGPT', 'Ollama', 'GROQ', 'GitHub']
    SUPPORTED_VECTOR_STORES = ['faiss', 'chroma']
    
    # Token Management
    MAX_CONTEXT_TOKENS = 6000  # Safe limit for most models
    MAX_RECENT_MESSAGES = 8    # Keep last N messages for context
    MAX_SIMILAR_MESSAGES = 2   # Add N most similar older messages
    MAX_MESSAGE_LENGTH = 500   # Truncate long messages
    SIMILARITY_THRESHOLD = 0.3 # Minimum similarity for including old messages
    
    # Reranking Settings
    DEFAULT_RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    DEFAULT_TOP_K_RETRIEVAL: int = 20  # Retrieve more docs initially
    DEFAULT_TOP_K_RERANKED: int = 5    # Return fewer after reranking
    ENABLE_RERANKING: bool = True


# Create a singleton instance
config = Config()
