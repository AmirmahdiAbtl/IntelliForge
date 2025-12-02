"""IntelliForge Application Package"""
from flask import Flask
from app.repositories.database import init_db


def create_app():
    """Application factory pattern"""
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    
    # Initialize database
    with app.app_context():
        init_db()
    
    # Register blueprints
    from app.routes.main_routes import main_bp
    from app.routes.rag_routes import rag_bp
    from app.routes.chat_routes import chat_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(rag_bp, url_prefix='/rag')
    app.register_blueprint(chat_bp, url_prefix='/regularchat')
    
    return app
