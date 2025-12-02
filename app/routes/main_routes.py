"""Main application routes"""
from flask import Blueprint, render_template
from app.services.rag_service import rag_service

main_bp = Blueprint('main', __name__)


@main_bp.route("/")
def index():
    """Home page"""
    return render_template("index.html")


@main_bp.route("/panel")
def panel():
    """RAG management panel"""
    rags = rag_service.get_all_rags()
    # Add next step URL for each RAG
    for rag in rags:
        if rag['status'] != 'ready':
            rag['next_step_url'] = rag_service.get_next_step_url(rag['id'])
    return render_template("panel.html", rags=rags)
