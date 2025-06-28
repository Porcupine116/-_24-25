from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user, logout_user
from app import db
from models import User, Assignment, Score, Submission, Question, AnswerOption
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
        assignments = Assignment.query.filter_by(teacher_id=current_user.id).all()
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

@main.route('/students')
@login_required
def students():
    """Страница управления студентами (только для учителей)"""
    if current_user.role != 'teacher':
        abort(403)
    
    students = User.query.filter_by(role='student').order_by(User.name.asc()).all()
    return render_template('students.html', students=students)

@main.route('/students/add', methods=['POST'])
@login_required
def add_student():
    """Добавление нового студента"""
    if current_user.role != 'teacher':
        abort(403)
    
    try:
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        # Валидация данных
        if not all([name, email, password]):
            flash('Все поля обязательны для заполнения', 'error')
            return redirect(url_for('main.students'))
            
        if len(password) < 6:
            flash('Пароль должен содержать минимум 6 символов', 'error')
            return redirect(url_for('main.students'))
            
        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует', 'error')
            return redirect(url_for('main.students'))
            
        new_student = User(
            name=name,
            email=email,
            role='student',
            password=generate_password_hash(password)
        )
        
        db.session.add(new_student)
        db.session.commit()
        flash('Студент успешно добавлен', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при добавлении студента: {str(e)}', 'error')
    
    return redirect(url_for('main.students'))

@main.route('/students/<int:student_id>/delete', methods=['POST'])
@login_required
def delete_student(student_id):
    """Удаление студента"""
    if current_user.role != 'teacher':
        abort(403)
    
    try:
        student = User.query.get_or_404(student_id)
        if student.role != 'student':
            flash('Нельзя удалить пользователя с другой ролью', 'error')
            return redirect(url_for('main.students'))
            
        # Удаляем все связанные данные студента
        Score.query.filter_by(student_id=student_id).delete()
        Submission.query.filter_by(student_id=student_id).delete()
        
        db.session.delete(student)
        db.session.commit()
        flash('Студент успешно удален', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении студента: {str(e)}', 'error')
    
    return redirect(url_for('main.students'))

@main.route('/assignments/create', methods=['GET', 'POST'])
@login_required
def create_assignment():
    if current_user.role != 'teacher':
        abort(403)

    if request.method == 'POST':
        try:
            title = request.form['title']
            description = request.form['description']
            deadline_str = request.form.get('deadline')
            deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M') if deadline_str else None
            max_score = int(request.form['max_score'])

            assignment = Assignment(
                title=title,
                description=description,
                deadline=deadline,
                max_score=max_score,
                teacher_id=current_user.id
            )

            db.session.add(assignment)
            db.session.flush()  # сохраняем, чтобы получить assignment.id

            questions = request.form.getlist('question_text[]')
            for idx, q_text in enumerate(questions):
                question = Question(text=q_text, assignment_id=assignment.id)
                db.session.add(question)
                db.session.flush()

                options = request.form.getlist(f'answer_option_{idx+1}[]')
                correct_option = request.form.get(f'correct_option_{idx+1}')

                for opt_idx, opt_text in enumerate(options):
                    answer_option = AnswerOption(
                        text=opt_text,
                        is_correct=(str(opt_idx) == correct_option),
                        question_id=question.id
                    )
                    db.session.add(answer_option)

            db.session.commit()
            flash('Задание успешно создано', 'success')
            return redirect(url_for('main.dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при создании задания: {str(e)}', 'error')

    return render_template('create_assignment.html')

@main.route('/assignments/<int:assignment_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_assignment(assignment_id):
    """Редактирование задания"""
    assignment = Assignment.query.get_or_404(assignment_id)
    if current_user.role != 'teacher' or assignment.teacher_id != current_user.id:
        abort(403)
    
    if request.method == 'POST':
        try:
            assignment.title = request.form['title']
            assignment.description = request.form['description']
            assignment.deadline = datetime.strptime(request.form['deadline'], '%Y-%m-%dT%H:%M') if request.form['deadline'] else None
            assignment.max_score = int(request.form['max_score'])
            db.session.commit()
            flash('Задание успешно обновлено', 'success')
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении задания: {str(e)}', 'error')
    
    return render_template('edit_assignment.html', assignment=assignment)

@main.route('/assignments/<int:assignment_id>/delete', methods=['POST'])
@login_required
def delete_assignment(assignment_id):
    """Удаление задания"""
    assignment = Assignment.query.get_or_404(assignment_id)
    if current_user.role != 'teacher' or assignment.teacher_id != current_user.id:
        abort(403)
    
    try:
        db.session.delete(assignment)
        db.session.commit()
        flash('Задание успешно удалено', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении задания: {str(e)}', 'error')
    
    return redirect(url_for('main.dashboard'))

@main.route('/assignments/<int:assignment_id>/submissions')
@login_required
def view_submissions(assignment_id):
    """Просмотр работ студентов по заданию"""
    assignment = Assignment.query.get_or_404(assignment_id)
    if current_user.role != 'teacher' or assignment.teacher_id != current_user.id:
        abort(403)
    
    submissions = Submission.query.filter_by(assignment_id=assignment_id).all()
    return render_template('view_submissions.html',
                         assignment=assignment,
                         submissions=submissions)

@main.route('/submissions/<int:submission_id>/grade', methods=['POST'])
@login_required
def grade_submission(submission_id):
    """Оценка работы студента"""
    submission = Submission.query.get_or_404(submission_id)
    assignment = submission.assignment
    
    if current_user.role != 'teacher' or assignment.teacher_id != current_user.id:
        abort(403)
    
    try:
        submission.score = int(request.form['score']) if request.form['score'] else None
        submission.feedback = request.form['feedback']
        db.session.commit()
        flash('Оценка сохранена', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при сохранении оценки: {str(e)}', 'error')
    
    return redirect(url_for('main.view_submissions', assignment_id=assignment.id))

@main.route('/submit_assignment/<int:assignment_id>', methods=['POST'])
@login_required
def submit_assignment(assignment_id):
    """Сдача задания студентом"""
    if current_user.role != 'student':
        abort(403)
    
    assignment = Assignment.query.get_or_404(assignment_id)
    solution_text = request.form.get('solution_text', '')
    
    if not solution_text:
        flash('Решение не может быть пустым', 'error')
        return redirect(url_for('main.dashboard'))
    
    try:
        submission = Submission(
            student_id=current_user.id,
            assignment_id=assignment.id,
            solution_text=solution_text,
            submitted_at=datetime.utcnow()
        )
        db.session.add(submission)
        db.session.commit()
        flash('Решение успешно отправлено', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при отправке решения: {str(e)}', 'error')
    
    return redirect(url_for('main.dashboard'))

@main.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Редактирование профиля пользователя"""
    if request.method == 'POST':
        try:
            current_user.name = request.form.get('name', current_user.name)
            current_user.email = request.form.get('email', current_user.email)
            
            if request.form.get('password'):
                if len(request.form.get('password')) < 6:
                    flash('Пароль должен содержать минимум 6 символов', 'error')
                else:
                    current_user.password = generate_password_hash(request.form.get('password'))
            
            db.session.commit()
            flash('Профиль успешно обновлен', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении профиля: {str(e)}', 'error')
        
        return redirect(url_for('main.profile'))
    
    return render_template('profile.html', user=current_user)

@main.route('/statistics')
@login_required
def statistics():
    """Просмотр статистики"""
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

@main.route('/logout')
@login_required
def logout():
    """Выход из системы"""
    logout_user()
    flash('Вы успешно вышли из системы', 'success')
    return redirect(url_for('auth.login'))

@main.route('/assignments')
@login_required
def assignments_list():
    if current_user.role != 'teacher':
        abort(403)
    assignments = Assignment.query.filter_by(teacher_id=current_user.id).order_by(Assignment.created_at.desc()).all()
    return render_template('assignments.html', assignments=assignments)