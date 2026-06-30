from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from models import (User, Post, Comment, Message, Spot, UserBadge, SpotContribution,
                    Like, Follow, SpotFollow, SurfTrip, TripParticipant, Photographer,
                    SpotPhotoNew, PhotoSession, SessionPhoto, PhotoPurchase, SpotReport,
                    Notification, Business, Coupon, Story, StoryView, SurfSession,
                    TokenBlocklist, DeviceToken)
from extensions import db
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

def _purge_user(user, admin_user):
    """Remove um usuário e todo o seu conteúdo pessoal. Os picos que ele criou
    são PRESERVADOS e realocados para o admin que fez a exclusão."""
    uid = user.id

    # 1) Todos os picos criados pelo usuário passam a ser do admin (preservados)
    Spot.query.filter_by(created_by=uid).update({'created_by': admin_user.id}, synchronize_session=False)

    # FKs de moderação (nullable) que apontam para o usuário
    Spot.query.filter_by(approved_by=uid).update({'approved_by': None}, synchronize_session=False)
    Spot.query.filter_by(rejected_by=uid).update({'rejected_by': None}, synchronize_session=False)
    SpotContribution.query.filter_by(reviewed_by=uid).update({'reviewed_by': None}, synchronize_session=False)
    UserBadge.query.filter_by(granted_by=uid).update({'granted_by': None}, synchronize_session=False)

    # 2) Conteúdo do usuário referenciado por outras tabelas
    post_ids = [p.id for p in Post.query.filter_by(user_id=uid).all()]
    if post_ids:
        Comment.query.filter(Comment.post_id.in_(post_ids)).delete(synchronize_session=False)
        Like.query.filter(Like.post_id.in_(post_ids)).delete(synchronize_session=False)
        Notification.query.filter(Notification.related_post_id.in_(post_ids)).delete(synchronize_session=False)
    msg_ids = [m.id for m in Message.query.filter((Message.sender_id == uid) | (Message.recipient_id == uid)).all()]
    if msg_ids:
        Notification.query.filter(Notification.related_message_id.in_(msg_ids)).delete(synchronize_session=False)
    story_ids = [s.id for s in Story.query.filter_by(user_id=uid).all()]
    if story_ids:
        StoryView.query.filter(StoryView.story_id.in_(story_ids)).delete(synchronize_session=False)
    sess_ids = [s.id for s in PhotoSession.query.filter_by(photographer_id=uid).all()]
    if sess_ids:
        photo_ids = [p.id for p in SessionPhoto.query.filter(SessionPhoto.session_id.in_(sess_ids)).all()]
        if photo_ids:
            PhotoPurchase.query.filter(PhotoPurchase.photo_id.in_(photo_ids)).delete(synchronize_session=False)
            SessionPhoto.query.filter(SessionPhoto.session_id.in_(sess_ids)).delete(synchronize_session=False)
        PhotoSession.query.filter(PhotoSession.id.in_(sess_ids)).delete(synchronize_session=False)
    trip_ids = [t.id for t in SurfTrip.query.filter_by(creator_id=uid).all()]
    if trip_ids:
        TripParticipant.query.filter(TripParticipant.trip_id.in_(trip_ids)).delete(synchronize_session=False)
        SurfTrip.query.filter(SurfTrip.id.in_(trip_ids)).delete(synchronize_session=False)
    for biz in Business.query.filter_by(owner_id=uid).all():
        Coupon.query.filter_by(business_id=biz.id).delete(synchronize_session=False)

    # 3) Linhas que pertencem diretamente ao usuário
    Comment.query.filter_by(user_id=uid).delete(synchronize_session=False)
    Like.query.filter_by(user_id=uid).delete(synchronize_session=False)
    Follow.query.filter((Follow.follower_id == uid) | (Follow.followed_id == uid)).delete(synchronize_session=False)
    SpotFollow.query.filter_by(user_id=uid).delete(synchronize_session=False)
    TripParticipant.query.filter_by(user_id=uid).delete(synchronize_session=False)
    PhotoPurchase.query.filter_by(user_id=uid).delete(synchronize_session=False)
    SpotReport.query.filter_by(user_id=uid).delete(synchronize_session=False)
    SpotContribution.query.filter_by(user_id=uid).delete(synchronize_session=False)
    SpotPhotoNew.query.filter_by(uploaded_by=uid).delete(synchronize_session=False)
    Photographer.query.filter_by(user_id=uid).delete(synchronize_session=False)
    StoryView.query.filter_by(user_id=uid).delete(synchronize_session=False)
    Story.query.filter_by(user_id=uid).delete(synchronize_session=False)
    SurfSession.query.filter_by(user_id=uid).delete(synchronize_session=False)
    UserBadge.query.filter_by(user_id=uid).delete(synchronize_session=False)
    Business.query.filter_by(owner_id=uid).delete(synchronize_session=False)
    Notification.query.filter((Notification.user_id == uid) | (Notification.related_user_id == uid)).delete(synchronize_session=False)
    Message.query.filter((Message.sender_id == uid) | (Message.recipient_id == uid)).delete(synchronize_session=False)
    Post.query.filter_by(user_id=uid).delete(synchronize_session=False)
    TokenBlocklist.query.filter_by(user_id=uid).delete(synchronize_session=False)
    DeviceToken.query.filter_by(user_id=uid).delete(synchronize_session=False)

    # 4) Finalmente o usuário
    db.session.delete(user)
    db.session.commit()


@admin.route('/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    # Impede que o administrador exclua sua própria conta
    if user.id == current_user.id:
        flash('Você não pode excluir sua própria conta.', 'danger')
        return redirect(url_for('admin.users'))

    username = user.username
    try:
        _purge_user(user, current_user)
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir o usuário {username}: {e}', 'danger')
        return redirect(url_for('admin.users'))

    flash(f'Usuário {username} e todo o conteúdo dele foram excluídos. '
          f'Os picos que ele criou foram mantidos e estão sob sua conta.', 'success')
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


# Campos que uma contribuição pode alterar no pico (whitelist de segurança)
ALLOWED_CONTRIB_FIELDS = {'wave_type', 'bottom_type', 'difficulty', 'crowd_level',
                          'best_wind_direction', 'best_swell_direction', 'best_tide', 'description'}


@admin.route('/contributions')
@login_required
@admin_required
def contributions():
    """Fila de moderação das sugestões de informação enviadas pelos usuários."""
    pending = (SpotContribution.query.filter_by(status='pending')
               .order_by(SpotContribution.created_at.desc()).all())
    recent = (SpotContribution.query.filter(SpotContribution.status != 'pending')
              .order_by(SpotContribution.reviewed_at.desc()).limit(20).all())
    return render_template('admin/contributions.html', pending=pending, recent=recent)


@admin.route('/contributions/<int:contrib_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_contribution(contrib_id):
    """Aprova: aplica os campos sugeridos ao pico e marca como aprovada."""
    c = SpotContribution.query.get_or_404(contrib_id)
    if c.status != 'pending':
        flash('Esta contribuição já foi avaliada.', 'warning')
        return redirect(url_for('admin.contributions'))
    applied = 0
    for field, value in c.fields().items():
        if field in ALLOWED_CONTRIB_FIELDS and value:
            setattr(c.spot, field, value)
            applied += 1
    c.status = 'approved'
    c.reviewed_by = current_user.id
    c.reviewed_at = datetime.utcnow()
    db.session.commit()
    flash(f'Contribuição aplicada ao pico "{c.spot.name}" ({applied} campo(s)).', 'success')
    return redirect(url_for('admin.contributions'))


@admin.route('/contributions/<int:contrib_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_contribution(contrib_id):
    """Rejeita a sugestão (não altera o pico)."""
    c = SpotContribution.query.get_or_404(contrib_id)
    if c.status != 'pending':
        flash('Esta contribuição já foi avaliada.', 'warning')
        return redirect(url_for('admin.contributions'))
    c.status = 'rejected'
    c.reviewed_by = current_user.id
    c.reviewed_at = datetime.utcnow()
    db.session.commit()
    flash('Contribuição rejeitada.', 'info')
    return redirect(url_for('admin.contributions'))


@admin.route('/badges')
@login_required
@admin_required
def badges():
    """Painel de selos de papel: conceder/remover por usuário."""
    from badges import BADGES, ORDER
    users = User.query.order_by(User.username).all()
    user_badges = {}
    for ub in UserBadge.query.filter_by(status='active').all():
        user_badges.setdefault(ub.user_id, []).append(ub)
    return render_template('admin/badges.html', users=users,
                           user_badges=user_badges, BADGES=BADGES, ORDER=ORDER)


@admin.route('/badges/grant', methods=['POST'])
@login_required
@admin_required
def grant_badge():
    from badges import BADGES
    uid = request.form.get('user_id', type=int)
    btype = request.form.get('type')
    if btype not in BADGES or not uid:
        flash('Dados inválidos para conceder o selo.', 'danger')
        return redirect(url_for('admin.badges'))
    existing = UserBadge.query.filter_by(user_id=uid, type=btype).first()
    if existing:
        existing.status = 'active'
        existing.granted_by = current_user.id
        existing.granted_at = datetime.utcnow()
    else:
        db.session.add(UserBadge(user_id=uid, type=btype, status='active',
                                 granted_by=current_user.id))
    db.session.commit()
    flash('Selo concedido com sucesso!', 'success')
    return redirect(url_for('admin.badges'))


@admin.route('/badges/<int:badge_id>/revoke', methods=['POST'])
@login_required
@admin_required
def revoke_badge(badge_id):
    ub = UserBadge.query.get_or_404(badge_id)
    db.session.delete(ub)
    db.session.commit()
    flash('Selo removido.', 'info')
    return redirect(url_for('admin.badges'))


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

    # Gamificação: XP para quem criou o pico, ao ser aprovado
    from gamification import award
    if spot.creator:
        award(spot.creator, 'spot')

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