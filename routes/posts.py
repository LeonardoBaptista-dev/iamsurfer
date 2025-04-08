from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from models import Post, Comment, Like
from app import db, app
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid

posts = Blueprint('posts', __name__)

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@posts.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'POST':
        content = request.form.get('content')
        image_url = None
        video_url = None
        
        # Salva imagem ou vídeo
        if 'media' in request.files and request.files['media'].filename:
            file = request.files['media']
            
            if file and allowed_file(file.filename):
                # Cria nome de arquivo único
                original_filename = secure_filename(file.filename)
                file_ext = original_filename.rsplit('.', 1)[1].lower()
                filename = f"{uuid.uuid4().hex}.{file_ext}"
                
                # Define o caminho onde salvar
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'posts', filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
                # Salva o arquivo
                file.save(filepath)
                
                # Determina se é imagem ou vídeo
                if file_ext in ['jpg', 'jpeg', 'png', 'gif']:
                    image_url = f"uploads/posts/{filename}"
                elif file_ext in ['mp4', 'mov']:
                    video_url = f"uploads/posts/{filename}"
            else:
                flash('Formato de arquivo não permitido.', 'danger')
                return redirect(url_for('posts.new_post'))
        
        # Verifica se há conteúdo ou mídia para postar
        if not content and not image_url and not video_url:
            flash('O post deve ter texto, imagem ou vídeo.', 'danger')
            return redirect(url_for('posts.new_post'))
        
        post = Post(content=content, image_url=image_url, video_url=video_url, user_id=current_user.id)
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
    
    # Remove arquivos de mídia se existirem
    if post.image_url:
        try:
            os.remove(os.path.join(app.root_path, 'static', post.image_url))
        except:
            pass
    
    if post.video_url:
        try:
            os.remove(os.path.join(app.root_path, 'static', post.video_url))
        except:
            pass
    
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