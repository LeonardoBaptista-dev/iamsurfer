from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, current_app
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from werkzeug.urls import url_parse
import os
import uuid
from werkzeug.utils import secure_filename
# Importa o módulo de armazenamento em nuvem


auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    from models import User  # Import aqui para evitar import circular
    
    if current_user.is_authenticated:
        # Se já estiver autenticado e for admin, redireciona para o painel admin
        if current_user.is_admin:
            return redirect(url_for('admin.index'))
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        # Aceita login por username OU email, sem diferenciar maiúsculas e
        # ignorando espaços nas pontas. (Usernames podem ter espaços/maiúsculas,
        # ex.: "Leonardo Baptista" — match exato confundia os usuários.)
        identifier = (request.form.get('username') or '').strip()
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        ident_lower = identifier.lower()
        user = User.query.filter(
            db.or_(
                db.func.lower(User.username) == ident_lower,
                db.func.lower(User.email) == ident_lower,
            )
        ).first()

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
    from models import User  # Import aqui para evitar import circular
    
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
    # O perfil próprio usa a mesma página (estilo Instagram) do perfil público
    username = request.args.get('username') or current_user.username
    return redirect(url_for('main.user_profile', username=username))

@auth.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        # Atualiza as informações básicas primeiro
        current_user.bio = request.form.get('bio')
        current_user.location = request.form.get('location')
        
        # Flag para indicar se a foto de perfil foi alterada
        profile_image_updated = False
        
        # Processa o upload da imagem, se fornecida
        if 'profile_image' in request.files and request.files['profile_image'].filename:
            file = request.files['profile_image']
            
            if file and file.filename:
                try:
                    from local_image_processor import LocalImageProcessor
                    
                    # Remove imagens antigas se existirem
                    if current_user.profile_image_urls:
                        LocalImageProcessor.delete_image_files(current_user.profile_image_urls)
                    
                    # Processa e salva a nova imagem de perfil
                    success, message, urls = LocalImageProcessor.process_and_save_profile(file)
                    
                    if success and urls:
                        # Gera hash da nova imagem para deduplicação
                        file.seek(0)
                        import hashlib
                        file_content = file.read()
                        file_hash = hashlib.md5(file_content).hexdigest()
                        file.seek(0)
                        
                        # Atualiza o perfil com as novas URLs e hash
                        current_user.profile_image_urls = urls
                        current_user.profile_image_hash = file_hash
                        
                        # Mantém compatibilidade com sistema antigo
                        current_user.profile_image = urls.get('small', 'uploads/default_profile.jpg')
                        
                        profile_image_updated = True
                        flash('Imagem de perfil atualizada com sucesso!', 'success')
                    else:
                        flash(f'Erro ao processar imagem: {message}', 'danger')
                        
                except Exception as e:
                    current_app.logger.error(f"Erro ao processar imagem de perfil: {str(e)}")
                    flash(f'Erro ao processar imagem: {str(e)}', 'danger')
        
        # Salva todas as alterações no banco de dados
        try:
            db.session.commit()
            if profile_image_updated:
                flash('Perfil e foto atualizados com sucesso!', 'success')
            else:
                flash('Perfil atualizado com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao atualizar perfil no banco de dados: {str(e)}")
            flash(f'Erro ao atualizar perfil: {str(e)}', 'danger')
        
        # Redireciona após processar tudo
        return redirect(url_for('auth.profile'))
    
    # Método GET - Exibe o formulário
    return render_template('auth/edit_profile.html') 