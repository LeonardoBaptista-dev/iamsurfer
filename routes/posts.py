from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, send_file, send_from_directory
from flask_login import login_required, current_user
from models import Post, Comment, Like, Notification
from extensions import db
from flask import current_app as app
import os
import uuid
from werkzeug.utils import secure_filename

# Função para determinar qual processador usar
def get_image_processor():
    """Retorna o processador de imagem apropriado"""
    use_local = not (os.environ.get('RENDER', False) or os.environ.get('FLASK_ENV') == 'production')
    
    if use_local:
        from local_image_processor import LocalImageProcessor
        return LocalImageProcessor
    else:
        from image_processor import ImageProcessor
        return ImageProcessor

posts = Blueprint('posts', __name__)

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@posts.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'POST':
        content = request.form.get('content')
        spot_id = request.form.get('spot_id')
        post_type = request.form.get('post_type', 'regular')
        is_reel = post_type == 'reel'

        if spot_id == "": spot_id = None

        # Cria post inicialmente sem mídia
        post = Post(content=content, user_id=current_user.id, spot_id=spot_id, post_type=post_type)

        # Salva o post para ter um ID
        db.session.add(post)
        db.session.flush()  # Flush para ter o ID sem commit completo
        
        # Processamento de imagem ou vídeo
        if 'media' in request.files and request.files['media'].filename:
            file = request.files['media']
            
            if file and allowed_file(file.filename):
                # Determina o tipo de mídia
                file_ext = file.filename.rsplit('.', 1)[1].lower()
                is_image = file_ext in ['jpg', 'jpeg', 'png', 'gif']
                is_video = file_ext in ['mp4', 'mov']
                
                if is_image:
                    # Usa o sistema apropriado de processamento de imagens
                    processor = get_image_processor()
                    
                    if hasattr(processor, 'process_and_save'):
                        # Processador local
                        success, message, urls = processor.process_and_save(file)
                        
                        if success:
                            # Gera hash para deduplicação
                            file.seek(0)
                            import hashlib
                            file_hash = hashlib.md5(file.read()).hexdigest()
                            file.seek(0)
                            
                            # Armazena as URLs múltiplas e hash
                            post.image_urls = urls
                            post.image_hash = file_hash
                            # Mantém compatibilidade com campo antigo
                            post.image_url = urls.get('medium', urls.get('small', ''))
                            print(f"✅ Imagem processada com sucesso: {len(urls)} tamanhos")
                        else:
                            flash(f"Erro no processamento da imagem: {message}", 'error')
                            db.session.rollback()
                            return redirect(url_for('posts.new_post'))
                    
                    else:
                        # Processador do Cloudinary (produção)
                        result = processor.process_and_upload_image(file, post.id)
                        
                        if result.get('success'):
                            # Armazena as URLs múltiplas e hash
                            post.image_urls = result['urls']
                            post.image_hash = result['hash']
                            # Mantém compatibilidade com campo antigo
                            post.image_url = result['urls'].get('medium', result['urls'].get('small', ''))
                            print(f"✅ Imagem processada com sucesso: {len(result['urls'])} tamanhos")
                        else:
                            flash(f"Erro no processamento da imagem: {result.get('error')}", 'error')
                            db.session.rollback()
                            return redirect(url_for('posts.new_post'))
                
                elif is_video:
                    # Guarda de tamanho no servidor (a validação do navegador é burlável).
                    # Aceitamos vídeos grandes do celular; eles são comprimidos antes do upload.
                    max_video = app.config.get('MAX_VIDEO_UPLOAD_SIZE', 100 * 1024 * 1024)
                    file.seek(0, os.SEEK_END)
                    video_size = file.tell()
                    file.seek(0)
                    if video_size > max_video:
                        flash(f"Vídeo muito grande (máx {max_video // (1024*1024)}MB). Reduza antes de enviar.", 'danger')
                        db.session.rollback()
                        return redirect(url_for('posts.new_post'))

                    # Usa o sistema de processamento que abstrai Nuvem/Local
                    processor = get_image_processor()

                    if hasattr(processor, 'process_and_save_video'):
                        # Ambiente de Dev Local
                        success, message, url_path = processor.process_and_save_video(file, is_reel=is_reel)
                        if success:
                            post.video_url = url_for('static', filename=url_path)
                            print(message)  # Ex: Aviso dizendo se usou FFmpeg
                        else:
                            flash(f"Erro local: {message}", 'danger')
                            db.session.rollback()
                            return redirect(url_for('posts.new_post'))

                    elif hasattr(processor, 'process_and_upload_video'):
                        # Ambiente Produtivo Cloudinary
                        result = processor.process_and_upload_video(file, post.id, is_reel=is_reel)
                        if result.get('success'):
                            post.video_url = result['url']
                        else:
                            flash(result.get('error', 'Erro desconhecido'), 'danger')
                            db.session.rollback()
                            return redirect(url_for('posts.new_post'))
                    else:
                        flash('Processador de vídeo não configurado', 'danger')
                        return redirect(url_for('posts.new_post'))
                else:
                    flash('Erro ao fazer upload do arquivo. Tente novamente.', 'danger')
                    return redirect(url_for('posts.new_post'))
            else:
                flash('Formato de arquivo não permitido.', 'danger')
                return redirect(url_for('posts.new_post'))
        
        # Um Reel precisa obrigatoriamente de vídeo
        if is_reel and not post.video_url:
            flash('Um Reel precisa de um vídeo.', 'danger')
            db.session.rollback()
            return redirect(url_for('posts.new_post'))

        # Verifica se há conteúdo para postar
        if not content and not post.image_url and not post.video_url:
            flash('O post deve ter texto, imagem ou vídeo.', 'danger')
            return redirect(url_for('posts.new_post'))
        
        db.session.add(post)
        # Gamificação: relato (post com pico) vale mais que post comum
        from gamification import award
        award(current_user, 'report' if post.spot_id else 'post')
        db.session.commit()

        flash('Post criado com sucesso!', 'success')
        return redirect(url_for('main.index'))

    from models import Spot
    spots = Spot.query.filter_by(status='approved', is_active=True).order_by(Spot.name).all()
    return render_template('posts/create_post.html', spots=spots)

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
    
    # Remove arquivo de imagem ou vídeo localmente, se existir
    if post.image_url and post.image_url.startswith('/static/uploads/'):
        try:
            image_path = os.path.join(app.root_path, post.image_url.lstrip('/'))
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception as e:
            print(f"Erro ao excluir arquivo de imagem local: {str(e)}")

    if post.video_url and post.video_url.startswith('/static/uploads/videos/'):
        try:
            video_path = os.path.join(app.root_path, post.video_url.lstrip('/'))
            if os.path.exists(video_path):
                os.remove(video_path)
        except Exception as e:
            print(f"Erro ao excluir arquivo de vídeo local: {str(e)}")
    
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

    # Gamificação: XP para quem comenta e para o autor do post
    from gamification import award
    award(current_user, 'comment')
    if current_user.id != post.user_id:
        award(post.author, 'comment_received')
    db.session.commit()

    # Cria notificação de comentário (se não for próprio post)
    if current_user.id != post.user_id:
        Notification.create_comment_notification(current_user, post, content)
    
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

        # Gamificação: XP para o autor do post curtido (se não for o próprio)
        if current_user.id != post.user_id:
            from gamification import award
            award(post.author, 'like_received')
        db.session.commit()

        # Cria notificação de like (se não for próprio post)
        if current_user.id != post.user_id:
            Notification.create_like_notification(current_user, post)
            
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
        spot_id = request.form.get('spot_id')
        post_type = request.form.get('post_type', 'regular')
        
        if spot_id == "": spot_id = None

        # Cria post inicialmente sem mídia
        post = Post(content=content, user_id=current_user.id, spot_id=spot_id, post_type=post_type)
        
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

    # Rota legada: o formulário oficial de criação é posts.new_post
    return redirect(url_for('posts.new_post'))