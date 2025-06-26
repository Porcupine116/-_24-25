from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from app import db
from models import User, Assignment, Score
from datetime import datetime
from werkzeug.security import generate_password_hash

main = Blueprint('main', __name__)

@main.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'teacher':
        students = User.query.filter_by(role='student').all()
        assignments = Assignment.query.all()
        return render_template('teacher_dashboard.html', students=students, assignments=assignments)
    else:
        assignments = Assignment.query.all()
        scores = Score.query.filter_by(student_id=current_user.id).all()
        return render_template('student_dashboard.html', assignments=assignments, scores=scores)

@main.route('/add_student', methods=['POST'])
@login_required
def add_student():
    if current_user.role != 'teacher':
        return "Access denied"
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    new_student = User(name=name, email=email, role='student',
                       password=generate_password_hash(password))
    db.session.add(new_student)
    db.session.commit()
    return redirect(url_for('main.dashboard'))

@main.route('/delete_student/<int:student_id>')
@login_required
def delete_student(student_id):
    if current_user.role != 'teacher':
        return "Access denied"
    student = User.query.get_or_404(student_id)
    db.session.delete(student)
    db.session.commit()
    return redirect(url_for('main.dashboard'))

@main.route('/create_assignment', methods=['POST'])
@login_required
def create_assignment():
    if current_user.role != 'teacher':
        return "Access denied"
    title = request.form.get('title')
    topic = request.form.get('topic')
    max_score = int(request.form.get('max_score'))
    deadline = datetime.strptime(request.form.get('deadline'), '%Y-%m-%d')
    assignment = Assignment(title=title, topic=topic, max_score=max_score,
                            deadline=deadline, created_by=current_user.id)
    db.session.add(assignment)
    db.session.commit()
    return redirect(url_for('main.dashboard'))

@main.route('/submit_score/<int:assignment_id>', methods=['POST'])
@login_required
def submit_score(assignment_id):
    if current_user.role != 'student':
        return "Access denied"
    score_val = int(request.form.get('score'))
    score = Score(student_id=current_user.id, assignment_id=assignment_id, score=score_val)
    db.session.add(score)
    db.session.commit()
    return redirect(url_for('main.dashboard'))