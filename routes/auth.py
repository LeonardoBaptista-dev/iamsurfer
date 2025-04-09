from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from models import User
from app import db, app
from werkzeug.urls import url_parse
import os
import uuid
from werkzeug.utils import secure_filename

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # Se já estiver autenticado e for admin, redireciona para o painel admin
        if current_user.is_admin:
            return redirect(url_for('admin.index'))
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            flash('Por favor, verifique suas credenciais e tente novamente.', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=remember)
        
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            # Se o usuário for administrador, redireciona para o painel admin
            if user.is_admin:
                next_page = url_for('admin.index')
            else:
                next_page = url_for('main.index')
        
        flash('Login realizado com sucesso!', 'success')
        return redirect(next_page)
    
    return render_template('auth/login.html')

@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Verifica se o usuário já existe
        user_check = User.query.filter_by(username=username).first()
        email_check = User.query.filter_by(email=email).first()
        
        if user_check:
            flash('Usuário já existe. Por favor, escolha outro nome de usuário.', 'danger')
            return redirect(url_for('auth.signup'))
        
        if email_check:
            flash('Email já cadastrado. Faça login ou utilize outro email.', 'danger')
            return redirect(url_for('auth.signup'))
        
        # Cria um novo usuário
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        # O primeiro usuário registrado será admin
        if User.query.count() == 0:
            new_user.is_admin = True
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Conta criada com sucesso! Agora você pode fazer login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/signup.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você saiu do sistema.', 'info')
    return redirect(url_for('auth.login'))

@auth.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html', user=current_user)

@auth.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        current_user.bio = request.form.get('bio')
        current_user.location = request.form.get('location')
        
        if 'profile_image' in request.files and request.files['profile_image'].filename:
            file = request.files['profile_image']
            
            if file and file.filename:
                # Verifica extensões permitidas
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
                file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                
                if file_ext in allowed_extensions:
                    # Gera um nome de arquivo seguro e único
                    filename = secure_filename(f"profile_{current_user.id}_{str(uuid.uuid4())}.{file_ext}")
                    
                    # Diretório para imagens de perfil
                    profile_upload_folder = os.path.join(app.root_path, 'static', 'uploads', 'profile_pics')
                    os.makedirs(profile_upload_folder, exist_ok=True)
                    
                    # Salva o arquivo
                    file_path = os.path.join(profile_upload_folder, filename)
                    file.save(file_path)
                    
                    # Atualiza o caminho da imagem no perfil do usuário
                    # O caminho é relativo ao diretório static
                    current_user.profile_image = os.path.join('uploads', 'profile_pics', filename)
                else:
                    flash('Formato de arquivo não permitido. Use PNG, JPG, JPEG ou GIF.', 'danger')
        
        db.session.commit()
        flash('Perfil atualizado com sucesso!', 'success')
        return redirect(url_for('auth.profile', username=current_user.username))
    
    return render_template('auth/edit_profile.html') 