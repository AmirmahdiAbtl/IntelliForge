from datetime import datetime
from app import db

class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_input = db.Column(db.String(500))
    think_part = db.Column(db.String(1000))
    response = db.Column(db.String(1000))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)