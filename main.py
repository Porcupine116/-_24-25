from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user, logout_user
from app import db
from models import User, Assignment, Score
from datetime import datetime
from werkzeug.security import generate_password_hash

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return redirect(url_for('main.dashboard'))

@main.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'teacher':
        students = User.query.filter_by(role='student').all()
        assignments = Assignment.query.all()
        return render_template('teacher_dashboard.html', 
                             students=students, 
                             assignments=assignments,
                             current_user=current_user)
    else:
        assignments = Assignment.query.all()
        scores = Score.query.filter_by(student_id=current_user.id).all()
        return render_template('student_dashboard.html', 
                             assignments=assignments, 
                             scores=scores,
                             current_user=current_user)

@main.route('/add_student', methods=['POST'])
@login_required
def add_student():
    if current_user.role != 'teacher':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('main.dashboard'))
    
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    
    if User.query.filter_by(email=email).first():
        flash('Пользователь с таким email уже существует', 'error')
        return redirect(url_for('main.dashboard'))
    
    new_student = User(name=name, email=email, role='student',
                      password=generate_password_hash(password))
    db.session.add(new_student)
    db.session.commit()
    flash('Студент успешно добавлен', 'success')
    return redirect(url_for('main.dashboard'))

@main.route('/delete_student/<int:student_id>')
@login_required
def delete_student(student_id):
    if current_user.role != 'teacher':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('main.dashboard'))
    
    student = User.query.get_or_404(student_id)
    db.session.delete(student)
    db.session.commit()
    flash('Студент удален', 'success')
    return redirect(url_for('main.dashboard'))

@main.route('/create_assignment', methods=['POST'])
@login_required
def create_assignment():
    if current_user.role != 'teacher':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('main.dashboard'))
    
    title = request.form.get('title')
    topic = request.form.get('topic')
    max_score = int(request.form.get('max_score'))
    deadline = datetime.strptime(request.form.get('deadline'), '%Y-%m-%d')
    
    assignment = Assignment(title=title, topic=topic, max_score=max_score,
                          deadline=deadline, created_by=current_user.id)
    db.session.add(assignment)
    db.session.commit()
    flash('Задание создано', 'success')
    return redirect(url_for('main.dashboard'))

@main.route('/submit_score/<int:assignment_id>', methods=['POST'])
@login_required
def submit_score(assignment_id):
    if current_user.role != 'student':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('main.dashboard'))
    
    score_val = int(request.form.get('score'))
    score = Score(student_id=current_user.id, assignment_id=assignment_id, score=score_val)
    db.session.add(score)
    db.session.commit()
    flash('Оценка сохранена', 'success')
    return redirect(url_for('main.dashboard'))

@main.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.name = request.form.get('name')
        current_user.email = request.form.get('email')
        if request.form.get('password'):
            current_user.password = generate_password_hash(request.form.get('password'))
        db.session.commit()
        flash('Профиль обновлен', 'success')
        return redirect(url_for('main.profile'))
    return render_template('profile.html', user=current_user)

@main.route('/statistics')
@login_required
def statistics():
    if current_user.role == 'student':
        scores = Score.query.filter_by(student_id=current_user.id).all()
        assignments = Assignment.query.all()
        return render_template('statistics_student.html', 
                             scores=scores, 
                             assignments=assignments,
                             current_user=current_user)
    else:
        students = User.query.filter_by(role='student').all()
        scores = Score.query.all()
        assignments = Assignment.query.all()
        return render_template('statistics_teacher.html', 
                             students=students, 
                             scores=scores,
                             assignments=assignments,
                             current_user=current_user)

@main.route('/students', methods=['GET', 'POST'])
@login_required
def students():
    if current_user.role != 'teacher':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash('Студент уже существует', 'error')
        else:
            new_user = User(email=email, name=name, 
                          password=generate_password_hash(password), 
                          role='student')
            db.session.add(new_user)
            db.session.commit()
            flash('Студент добавлен', 'success')
    
    students = User.query.filter_by(role='student').all()
    return render_template('students.html', students=students)

@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из системы', 'success')
    return redirect(url_for('auth.login'))
