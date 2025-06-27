from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from models import User
from app import db
from sqlalchemy.exc import SQLAlchemyError

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', 'student')  # По умолчанию student
        
        # Валидация данных
        if not all([email, name, password]):
            flash('Все поля обязательны для заполнения', 'error')
            return redirect(url_for('auth.register'))
            
        if len(password) < 6:
            flash('Пароль должен содержать минимум 6 символов', 'error')
            return redirect(url_for('auth.register'))
            
        try:
            # Проверка существующего пользователя
            if User.query.filter_by(email=email).first():
                flash('Пользователь с таким email уже существует', 'error')
                return redirect(url_for('auth.register'))
                
            # Создание нового пользователя
            new_user = User(
                email=email,
                name=name,
                role=role,
                password=generate_password_hash(password, method='pbkdf2:sha256')
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            flash('Регистрация прошла успешно! Пожалуйста, войдите в систему.', 'success')
            return redirect(url_for('auth.login'))
            
        except SQLAlchemyError as e:
            db.session.rollback()
            flash('Произошла ошибка при регистрации. Пожалуйста, попробуйте позже.', 'error')
            return redirect(url_for('auth.register'))
            
    return render_template('register.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        if not email or not password:
            flash('Пожалуйста, заполните все поля', 'error')
            return redirect(url_for('auth.login'))
            
        user = User.query.filter_by(email=email).first()
        
        if not user or not check_password_hash(user.password, password):
            flash('Неверный email или пароль', 'error')
            return redirect(url_for('auth.login'))
            
        login_user(user)
        flash(f'Добро пожаловать, {user.name}!', 'success')
        return redirect(url_for('main.dashboard'))
        
    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из системы', 'success')
    return redirect(url_for('auth.login'))
