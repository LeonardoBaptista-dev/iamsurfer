from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, send_file, send_from_directory
from flask_login import login_required, current_user
from models import Post, Comment, Like
from app import db, app
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid
import io
from io import BytesIO
# Importa o módulo de armazenamento em nuvem
from cloud_storage import upload_file as cloud_upload, delete_file as cloud_delete

posts = Blueprint('posts', __name__)

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@posts.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'POST':
        content = request.form.get('content')
        
        # Cria post inicialmente sem mídia
        post = Post(content=content, user_id=current_user.id)
        
        # Processamento de imagem ou vídeo
        if 'media' in request.files and request.files['media'].filename:
            file = request.files['media']
            
            if file and allowed_file(file.filename):
                # Determina o tipo de mídia
                file_ext = file.filename.rsplit('.', 1)[1].lower()
                is_image = file_ext in ['jpg', 'jpeg', 'png', 'gif']
                is_video = file_ext in ['mp4', 'mov']
                
                # Define a pasta no Cloudinary
                folder = 'posts'
                
                # Upload para Cloudinary
                file_url = cloud_upload(file, folder=folder)
                
                if file_url:
                    # Atribui a URL ao campo apropriado
                    if is_image:
                        post.image_url = file_url
                    elif is_video:
                        post.video_url = file_url
                else:
                    flash('Erro ao fazer upload do arquivo. Tente novamente.', 'danger')
                    return redirect(url_for('posts.new_post'))
            else:
                flash('Formato de arquivo não permitido.', 'danger')
                return redirect(url_for('posts.new_post'))
        
        # Verifica se há conteúdo para postar
        if not content and not post.image_url and not post.video_url:
            flash('O post deve ter texto, imagem ou vídeo.', 'danger')
            return redirect(url_for('posts.new_post'))
        
        db.session.add(post)
        db.session.commit()
        
        flash('Post criado com sucesso!', 'success')
        return redirect(url_for('main.index'))
    
    return render_template('posts/create_post.html')

# Rota adicional para compatibilidade com os testes
@posts.route('/posts/new', methods=['GET', 'POST'])
@login_required
def new_post_alt():
    return new_post()

@posts.route('/post/<int:post_id>')
def view_post(post_id):
    post = Post.query.get_or_404(post_id)
    comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.created_at.desc()).all()
    
    # Verifica se o usuário atual já curtiu o post
    liked = False
    if current_user.is_authenticated:
        like = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()
        liked = like is not None
    
    return render_template('posts/view_post.html', post=post, comments=comments, liked=liked)

@posts.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    # Verifica se o usuário atual é o autor do post ou admin
    if post.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    # Remove arquivo de imagem ou vídeo caso exista
    if post.image_url:
        try:
            # Excluir do Cloudinary
            cloud_delete(post.image_url)
        except Exception as e:
            # Log do erro, mas continua com a exclusão do post
            print(f"Erro ao excluir arquivo de imagem: {str(e)}")
    
    if post.video_url:
        try:
            # Excluir do Cloudinary
            cloud_delete(post.video_url)
        except Exception as e:
            # Log do erro, mas continua com a exclusão do post
            print(f"Erro ao excluir arquivo de vídeo: {str(e)}")
    
    db.session.delete(post)
    db.session.commit()
    
    flash('Post excluído com sucesso!', 'success')
    return redirect(url_for('main.index'))

@posts.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    post = Post.query.get_or_404(post_id)
    content = request.form.get('content')
    
    if not content:
        flash('O comentário não pode estar vazio.', 'danger')
        return redirect(url_for('posts.view_post', post_id=post_id))
    
    comment = Comment(content=content, user_id=current_user.id, post_id=post_id)
    db.session.add(comment)
    db.session.commit()
    
    flash('Comentário adicionado com sucesso!', 'success')
    return redirect(url_for('posts.view_post', post_id=post_id))

# Rota adicional para compatibilidade com os testes
@posts.route('/posts/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment_alt(post_id):
    return add_comment(post_id)

@posts.route('/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    post_id = comment.post_id
    
    # Verifica se o usuário atual é o autor do comentário, autor do post ou admin
    if comment.user_id != current_user.id and comment.post.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    db.session.delete(comment)
    db.session.commit()
    
    flash('Comentário excluído com sucesso!', 'success')
    return redirect(url_for('posts.view_post', post_id=post_id))

@posts.route('/post/<int:post_id>/like', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    # Verifica se o usuário já curtiu o post
    like = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    
    if like:
        # Se já curtiu, remove a curtida
        db.session.delete(like)
        db.session.commit()
        flash('Curtida removida!', 'info')
    else:
        # Se não, adiciona uma curtida
        like = Like(user_id=current_user.id, post_id=post_id)
        db.session.add(like)
        db.session.commit()
        flash('Post curtido!', 'success')
    
    # Redireciona de volta para a página anterior
    next_page = request.referrer
    if not next_page:
        next_page = url_for('posts.view_post', post_id=post_id)
    
    return redirect(next_page)

# Rota adicional para compatibilidade com os testes
@posts.route('/posts/<int:post_id>/like', methods=['POST'])
@login_required
def like_post_alt(post_id):
    return like_post(post_id)

@posts.route('/create', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        content = request.form.get('content')
        
        # Cria post inicialmente sem mídia
        post = Post(content=content, user_id=current_user.id)
        
        if 'media' in request.files and request.files['media'].filename:
            file = request.files['media']
            
            if file and file.filename:
                # Gera um nome de arquivo seguro e único
                file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                filename = secure_filename(f"post_{str(uuid.uuid4())}.{file_ext}")
                
                # Diretório para posts
                posts_upload_folder = os.path.join(app.root_path, 'static', 'uploads', 'posts')
                os.makedirs(posts_upload_folder, exist_ok=True)
                
                # Salva o arquivo
                file_path = os.path.join(posts_upload_folder, filename)
                file.save(file_path)
                
                # URL relativa para o arquivo salvo - apenas o caminho relativo ao diretório static
                file_url = os.path.join('uploads', 'posts', filename)
                
                # Verifica se é uma imagem ou vídeo
                import mimetypes
                mimetype = file.content_type
                
                if mimetype.startswith('image/'):
                    post.image_url = file_url
                elif mimetype.startswith('video/'):
                    post.video_url = file_url
        
        db.session.add(post)
        db.session.commit()
        
        flash('Post criado com sucesso!', 'success')
        return redirect(url_for('main.index'))
        
    return render_template('posts/create.html') 