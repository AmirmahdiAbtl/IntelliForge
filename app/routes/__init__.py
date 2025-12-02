"""Initialize routes package"""
from app.routes.main_routes import main_bp
from app.routes.rag_routes import rag_bp
from app.routes.chat_routes import chat_bp

__all__ = ['main_bp', 'rag_bp', 'chat_bp']
