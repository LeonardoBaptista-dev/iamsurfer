from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from models import User, Post, Comment, Message, Spot
from app import db
from functools import wraps
from sqlalchemy import func
from datetime import datetime

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
    messages_count = Message.query.count()
    
    # Usuários mais recentes
    recent_users = User.query.order_by(User.joined_at.desc()).limit(5).all()
    
    # Posts mais recentes
    recent_posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()
    
    return render_template('admin/index.html', 
                          users_count=users_count,
                          posts_count=posts_count,
                          comments_count=comments_count,
                          messages_count=messages_count,
                          recent_users=recent_users,
                          recent_posts=recent_posts)

@admin.route('/panel')
@login_required
@admin_required
def admin_panel():
    """Painel principal de administração"""
    return redirect(url_for('admin.index'))

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

@admin.route('/spots')
@login_required
@admin_required
def spots():
    """Página principal de gerenciamento de spots"""
    # Filtros por status
    status_filter = request.args.get('status', 'all')
    page = request.args.get('page', 1, type=int)
    
    # Base query
    query = Spot.query
    
    # Aplica filtros
    if status_filter == 'pending':
        query = query.filter_by(status='pending')
    elif status_filter == 'approved':
        query = query.filter_by(status='approved')
    elif status_filter == 'rejected':
        query = query.filter_by(status='rejected')
    
    # Ordena por data de criação
    spots = query.order_by(Spot.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Estatísticas
    stats = {
        'total': Spot.query.count(),
        'pending': Spot.query.filter_by(status='pending').count(),
        'approved': Spot.query.filter_by(status='approved').count(),
        'rejected': Spot.query.filter_by(status='rejected').count()
    }
    
    return render_template('admin/spots.html', spots=spots, stats=stats, status_filter=status_filter)

@admin.route('/spots/<int:spot_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_spot(spot_id):
    """Aprova um spot pendente"""
    spot = Spot.query.get_or_404(spot_id)
    
    if spot.status != 'pending':
        flash('Este spot não está pendente de aprovação.', 'warning')
        return redirect(url_for('admin.spots'))
    
    spot.status = 'approved'
    spot.approved_by = current_user.id
    spot.approved_at = datetime.utcnow()
    
    db.session.commit()
    
    flash(f'Spot "{spot.name}" foi aprovado com sucesso!', 'success')
    return redirect(url_for('admin.spots'))

@admin.route('/spots/<int:spot_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_spot(spot_id):
    """Rejeita um spot pendente"""
    spot = Spot.query.get_or_404(spot_id)
    
    if spot.status != 'pending':
        flash('Este spot não está pendente de aprovação.', 'warning')
        return redirect(url_for('admin.spots'))
    
    spot.status = 'rejected'
    spot.rejected_by = current_user.id
    spot.rejected_at = datetime.utcnow()
    
    db.session.commit()
    
    flash(f'Spot "{spot.name}" foi rejeitado.', 'info')
    return redirect(url_for('admin.spots'))

@admin.route('/spots/<int:spot_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_spot(spot_id):
    """Exclui um spot permanentemente"""
    spot = Spot.query.get_or_404(spot_id)
    
    # Confirma se o admin realmente quer excluir
    confirm = request.form.get('confirm')
    if confirm != 'DELETE':
        flash('Para excluir permanentemente, digite "DELETE" no campo de confirmação.', 'danger')
        return redirect(url_for('admin.spots'))
    
    spot_name = spot.name
    db.session.delete(spot)
    db.session.commit()
    
    flash(f'Spot "{spot_name}" foi excluído permanentemente.', 'success')
    return redirect(url_for('admin.spots'))

@admin.route('/spots/<int:spot_id>/reactivate', methods=['POST'])
@login_required
@admin_required
def reactivate_spot(spot_id):
    """Reativa um spot rejeitado"""
    spot = Spot.query.get_or_404(spot_id)
    
    if spot.status != 'rejected':
        flash('Este spot não está rejeitado.', 'warning')
        return redirect(url_for('admin.spots'))
    
    spot.status = 'pending'
    spot.rejected_by = None
    spot.rejected_at = None
    
    db.session.commit()
    
    flash(f'Spot "{spot.name}" foi reativado e está pendente novamente.', 'success')
    return redirect(url_for('admin.spots'))

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
        User.profile_image,
        func.count(Post.id).label('post_count')
    ).join(Post, User.id == Post.user_id).group_by(User.id).order_by(func.count(Post.id).desc()).limit(10).all()
    
    return render_template('admin/reports.html', 
                          user_stats=user_stats,
                          post_stats=post_stats,
                          top_posters=top_posters)

@admin.route('/messages')
@login_required
@admin_required
def messages():
    """Gerenciar todas as mensagens do sistema"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    
    # Query base para mensagens
    query = Message.query
    
    # Filtro de busca
    if search:
        query = query.join(User, Message.sender_id == User.id).filter(
            User.username.contains(search)
        )
    
    # Paginação
    messages_pagination = query.order_by(Message.timestamp.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Estatísticas
    total_messages = Message.query.count()
    unread_messages = Message.query.filter_by(read=False).count()
    messages_today = Message.query.filter(
        func.date(Message.timestamp) == datetime.utcnow().date()
    ).count()
    
    return render_template('admin/messages.html',
                          messages=messages_pagination.items,
                          pagination=messages_pagination,
                          search=search,
                          total_messages=total_messages,
                          unread_messages=unread_messages,
                          messages_today=messages_today)

@admin.route('/messages/<int:message_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_message(message_id):
    """Deletar uma mensagem específica"""
    message = Message.query.get_or_404(message_id)
    
    try:
        db.session.delete(message)
        db.session.commit()
        flash('Mensagem deletada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao deletar mensagem: {str(e)}', 'error')
    
    return redirect(url_for('admin.messages'))

@admin.route('/messages/bulk-delete', methods=['POST'])
@login_required
@admin_required
def bulk_delete_messages():
    """Deletar múltiplas mensagens selecionadas"""
    message_ids = request.form.getlist('message_ids')
    
    if not message_ids:
        flash('Nenhuma mensagem selecionada.', 'warning')
        return redirect(url_for('admin.messages'))
    
    try:
        Message.query.filter(Message.id.in_(message_ids)).delete(synchronize_session=False)
        db.session.commit()
        flash(f'{len(message_ids)} mensagens deletadas com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao deletar mensagens: {str(e)}', 'error')
    
    return redirect(url_for('admin.messages'))