from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user, logout_user
from app import db
from models import User, Assignment, Score, Submission, Question, AnswerOption
from datetime import datetime
from werkzeug.security import generate_password_hash
from datetime import datetime
from flask import jsonify
import json

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

        # ——— ВЫЧИСЛЯЕМ avg_scores:
        avg_scores = {}
        for student in students:
            submissions = Submission.query.filter_by(student_id=student.id).all()
            scores = [s.score for s in submissions if s.score is not None]
            avg_scores[student.id] = round(sum(scores) / len(scores), 2) if scores else None

        # ——— Передаем avg_scores в шаблон!
        return render_template(
            'teacher_dashboard.html',
            students=students,
            assignments=assignments,
            avg_scores=avg_scores,  # <——— вот оно!
            current_user=current_user,
            all_groups=[],           # если используешь фильтрацию по группам, передай актуально
            group_filter='',
            score_filter=''
        )
    else:
        assignments = Assignment.query.all()
        my_submissions = Submission.query.filter_by(student_id=current_user.id).all()
        submissions_by_assignment = {s.assignment_id: s for s in my_submissions}
        for a in assignments:
            a.submissions = [submissions_by_assignment[a.id]] if a.id in submissions_by_assignment else []
        return render_template('student_dashboard.html',
                               assignments=assignments,
                               submissions=my_submissions,
                               current_user=current_user)


@main.route('/students')
@login_required
def students():
    if current_user.role != 'teacher':
        abort(403)

    # Фильтры из GET-параметров
    group_filter = request.args.get('group', '').strip()
    score_filter = request.args.get('score', '')

    students_query = current_user.students.order_by(User.name.asc())

    # Применяем фильтр по группе, если выбран
    if group_filter:
        students_query = students_query.filter_by(group=group_filter)

    students = students_query.all()

    # Для выпадающего списка групп:
    all_groups = [g[0] for g in db.session.query(User.group).distinct() if g[0]]

    # Для фильтра по среднему баллу (готовим словарь student_id: avg_score)
    avg_scores = {}
    for student in students:
        submissions = Submission.query.filter_by(student_id=student.id).all()
        scores = [s.score for s in submissions if s.score is not None]
        avg_scores[student.id] = round(sum(scores) / len(scores), 2) if scores else 0

    # Фильтрация по среднему баллу (например: ">=80", "<50")
    if score_filter:
        op = score_filter[0]
        try:
            value = float(score_filter[1:])
            if op == '>':
                students = [s for s in students if avg_scores.get(s.id, 0) > value]
            elif op == '<':
                students = [s for s in students if avg_scores.get(s.id, 0) < value]
            elif op == '=':
                students = [s for s in students if avg_scores.get(s.id, 0) == value]
        except Exception:
            pass

    return render_template('students.html', students=students, all_groups=all_groups, avg_scores=avg_scores,
                           group_filter=group_filter, score_filter=score_filter)


@main.route('/students/add', methods=['POST'])
@login_required
def add_student():
    if current_user.role != 'teacher':
        abort(403)
    try:
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        if not all([name, email]):
            flash('Имя и email обязательны', 'error')
            return redirect(url_for('main.students'))
        student = User.query.filter_by(email=email, role='student').first()
        if not student:
            flash('Пользователь с таким email не найден или он не является студентом', 'error')
            return redirect(url_for('main.students'))
        if student in current_user.students:
            flash('Студент уже добавлен к вам', 'warning')
        else:
            current_user.students.append(student)
            db.session.commit()
            flash('Студент успешно добавлен!', 'success')
        # Обновим имя, если что
        if student.name != name:
            student.name = name
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при добавлении студента: {str(e)}', 'error')
    return redirect(url_for('main.students'))

@main.route('/students/<int:student_id>/delete', methods=['POST'])
@login_required
def delete_student(student_id):
    if current_user.role != 'teacher':
        abort(403)
    try:
        student = User.query.get_or_404(student_id)
        if student.role != 'student':
            flash('Нельзя удалить пользователя с другой ролью', 'error')
            return redirect(url_for('main.students'))
        if student in current_user.students:
            current_user.students.remove(student)
            db.session.commit()
            flash('Студент удалён из вашей группы', 'success')
        else:
            flash('Этот студент не прикреплён к вам', 'warning')
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


@main.route('/submit_assignment/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
def submit_assignment(assignment_id):
    if current_user.role != 'student':
        abort(403)

    assignment = Assignment.query.get_or_404(assignment_id)

    if request.method == 'POST':
        # Получаем ответы студента
        student_answers = {}
        for question in assignment.questions:
            answer = request.form.get(f'question_{question.id}')
            if answer:
                student_answers[question.id] = int(answer)

        # Автоматическая проверка
        correct_count = 0
        for question in assignment.questions:
            correct_option = next((opt for opt in question.options if opt.is_correct), None)
            if correct_option and student_answers.get(question.id) == correct_option.id:
                correct_count += 1

        # Баллы за задание (целое число)
        if assignment.questions:
            points_per_question = assignment.max_score // len(assignment.questions)
        else:
            points_per_question = assignment.max_score

        score = correct_count * points_per_question

        try:
            submission = Submission(
                student_id=current_user.id,
                assignment_id=assignment.id,
                solution_text=str(student_answers),
                submitted_at=datetime.utcnow(),
                score=score    # <--- вот тут автоматом ставим!
            )
            db.session.add(submission)
            db.session.commit()
            flash(f'Решение отправлено! Вы набрали {score} баллов.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при отправке решения: {str(e)}', 'error')
        return redirect(url_for('main.dashboard'))

    # Для GET — показываем форму сдачи
    return render_template('submit_assignment.html', assignment=assignment)


@main.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Редактирование профиля пользователя"""
    if request.method == 'POST':
        try:
            current_user.name = request.form.get('name', current_user.name)
            current_user.last_name = request.form.get('last_name', current_user.last_name)
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
    if current_user.role != 'teacher':
        abort(403)

    students = User.query.filter_by(role='student').all()
    assignments = Assignment.query.all()
    submissions = Submission.query.all()

    # Список для таблицы
    student_stats = []
    for student in students:
        student_subs = [s for s in submissions if s.student_id == student.id]
        scores = [s.score for s in student_subs if s.score is not None]
        avg_score = round(sum(scores) / len(scores), 2) if scores else 0

        total_assignments = len(assignments)
        completed = len([s for s in student_subs if s.solution_text and s.score is not None])
        not_completed = total_assignments - completed
        late = len([s for s in student_subs if s.submitted_at and any(a.id == s.assignment_id and a.deadline and s.submitted_at > a.deadline for a in assignments)])

        last_submission = max(student_subs, key=lambda x: x.submitted_at, default=None)
        last_score = last_submission.score if last_submission and last_submission.score is not None else '—'

        # Сдано с первого раза (если submission у студента по заданию только один)
        first_try = 0
        for a in assignments:
            subs_for_a = [s for s in student_subs if s.assignment_id == a.id]
            if len(subs_for_a) == 1 and subs_for_a[0].score is not None:
                first_try += 1

        student_stats.append({
            'student': student,
            'avg_score': avg_score,
            'completed': completed,
            'not_completed': not_completed,
            'late': late,
            'last_score': last_score,
            'first_try': first_try,
        })

    # Для диаграмм
    avg_scores = [s['avg_score'] for s in student_stats]
    student_names = [s['student'].name for s in student_stats]
    scores_distribution = [s['last_score'] if isinstance(s['last_score'], (int, float)) else 0 for s in student_stats]

    # Активность по дням (тепловая карта)
    from collections import Counter
    import datetime
    day_counts = Counter(
        s.submitted_at.date() for s in submissions if s.submitted_at is not None
    )
    heatmap_data = []
    if day_counts:
        date_from = min(day_counts)
        date_to = max(day_counts)
        curr = date_from
        while curr <= date_to:
            heatmap_data.append({
                'date': curr.strftime('%Y-%m-%d'),
                'count': day_counts.get(curr, 0)
            })
            curr += datetime.timedelta(days=1)

    return render_template(
        'statistics_teacher.html',
        student_stats=student_stats,
        student_names=student_names,
        avg_scores=avg_scores,
        scores_distribution=scores_distribution,
        heatmap_data=heatmap_data,
        assignments=assignments,
        submissions=submissions
    )


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
    if current_user.role == 'teacher':
        assignments = Assignment.query.filter_by(teacher_id=current_user.id).order_by(Assignment.created_at.desc()).all()
        return render_template('assignments.html', assignments=assignments)
    elif current_user.role == 'student':
        assignments = Assignment.query.all()
        my_submissions = Submission.query.filter_by(student_id=current_user.id).all()
        submissions_by_assignment = {s.assignment_id: s for s in my_submissions}
        for a in assignments:
            a.submissions = [submissions_by_assignment[a.id]] if a.id in submissions_by_assignment else []
        return render_template('student_assignments.html', assignments=assignments, current_user=current_user)
    else:
        abort(403)
