from flask import Flask, render_template
from developerassistant import developerassistant_bp
# from test import test_bp
from rag_creator import rag_creator_bp
from regularchat import regular_chat_bp
from database import get_db_connection

def create_app():
    app = Flask(__name__)

    # Register blueprints
    app.register_blueprint(developerassistant_bp, url_prefix='/developerassistant')
    app.register_blueprint(rag_creator_bp, url_prefix='/rag')
    app.register_blueprint(regular_chat_bp, url_prefix='/regularchat')
    # app.register_blueprint(test_bp, url_prefix = "/test")
    # Initialize the database
    with app.app_context():
        from database import init_db
        init_db()

    return app

# Define routes after creating the app
app = create_app()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/panel")
def panel():
    from database import get_all_rags
    rags = get_all_rags()
    return render_template("panel.html", rags=rags)

if __name__ == "__main__":
    app.run(debug=True)
