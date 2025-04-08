from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from models import User, Post, Comment, Message
from app import db
from functools import wraps
from sqlalchemy import func

admin = Blueprint('admin', __name__, url_prefix='/admin')

# Decorator para verificar se o usuário é um administrador
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@admin.route('/')
@login_required
@admin_required
def index():
    # Estatísticas gerais
    users_count = User.query.count()
    posts_count = Post.query.count()
    comments_count = Comment.query.count()
    
    # Usuários mais recentes
    recent_users = User.query.order_by(User.joined_at.desc()).limit(5).all()
    
    # Posts mais recentes
    recent_posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()
    
    return render_template('admin/index.html', 
                          users_count=users_count,
                          posts_count=posts_count,
                          comments_count=comments_count,
                          recent_users=recent_users,
                          recent_posts=recent_posts)

@admin.route('/users')
@login_required
@admin_required
def users():
    # Lista todos os usuários
    page = request.args.get('page', 1, type=int)
    users = User.query.paginate(page=page, per_page=20)
    return render_template('admin/users.html', users=users)

@admin.route('/toggle_admin/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    
    # Impede que o administrador remova seu próprio status de admin
    if user.id == current_user.id:
        flash('Você não pode remover seu próprio status de administrador.', 'danger')
        return redirect(url_for('admin.users'))
    
    user.is_admin = not user.is_admin
    db.session.commit()
    
    status = 'concedido' if user.is_admin else 'removido'
    flash(f'Status de administrador {status} para {user.username}.', 'success')
    return redirect(url_for('admin.users'))

@admin.route('/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Impede que o administrador exclua sua própria conta
    if user.id == current_user.id:
        flash('Você não pode excluir sua própria conta.', 'danger')
        return redirect(url_for('admin.users'))
    
    db.session.delete(user)
    db.session.commit()
    
    flash(f'Usuário {user.username} excluído com sucesso.', 'success')
    return redirect(url_for('admin.users'))

@admin.route('/posts')
@login_required
@admin_required
def posts():
    # Lista todos os posts
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('admin/posts.html', posts=posts)

@admin.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    db.session.delete(post)
    db.session.commit()
    
    flash('Post excluído com sucesso.', 'success')
    return redirect(url_for('admin.posts'))

@admin.route('/comments')
@login_required
@admin_required
def comments():
    # Lista todos os comentários
    page = request.args.get('page', 1, type=int)
    comments = Comment.query.order_by(Comment.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('admin/comments.html', comments=comments)

@admin.route('/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    
    db.session.delete(comment)
    db.session.commit()
    
    flash('Comentário excluído com sucesso.', 'success')
    return redirect(url_for('admin.comments'))

@admin.route('/reports')
@login_required
@admin_required
def reports():
    # Estatísticas de usuários por dia
    user_stats = db.session.query(
        func.date(User.joined_at).label('date'),
        func.count(User.id).label('count')
    ).group_by(func.date(User.joined_at)).order_by(func.date(User.joined_at).desc()).limit(30).all()
    
    # Estatísticas de posts por dia
    post_stats = db.session.query(
        func.date(Post.created_at).label('date'),
        func.count(Post.id).label('count')
    ).group_by(func.date(Post.created_at)).order_by(func.date(Post.created_at).desc()).limit(30).all()
    
    # Top usuários com mais posts
    top_posters = db.session.query(
        User.username,
        func.count(Post.id).label('post_count')
    ).join(Post, User.id == Post.user_id).group_by(User.id).order_by(func.count(Post.id).desc()).limit(10).all()
    
    return render_template('admin/reports.html', 
                          user_stats=user_stats,
                          post_stats=post_stats,
                          top_posters=top_posters) 