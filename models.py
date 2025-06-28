from flask_login import UserMixin
from datetime import datetime
from app import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    role = db.Column(db.String(50))  # 'student' or 'teacher'
    
    # Новые поля профиля
    first_name = db.Column(db.String(150))
    last_name = db.Column(db.String(150))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))  # 'male', 'female', 'other'

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    deadline = db.Column(db.DateTime)
    max_score = db.Column(db.Integer, default=10)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'))
    solution_text = db.Column(db.Text)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    score = db.Column(db.Integer)
    feedback = db.Column(db.Text)

class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'))
    score = db.Column(db.Integer)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)

    assignment = db.relationship('Assignment', backref=db.backref('questions', cascade='all, delete-orphan', lazy=True))

class AnswerOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    text = db.Column(db.String(255), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)

    question = db.relationship('Question', backref=db.backref('options', cascade='all, delete-orphan', lazy=True))
