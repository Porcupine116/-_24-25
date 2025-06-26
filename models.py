from flask_login import UserMixin
from datetime import datetime
from app import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    role = db.Column(db.String(50))  # 'student' or 'teacher'

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    topic = db.Column(db.String(100))
    max_score = db.Column(db.Integer)
    deadline = db.Column(db.DateTime)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'))
    score = db.Column(db.Integer)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)