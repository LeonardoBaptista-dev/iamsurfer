from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from models import User, Message, Notification
from app import db
from datetime import datetime
from sqlalchemy import or_, and_, func

messages = Blueprint('messages', __name__)

@messages.route('/messages')
@login_required
def inbox():
    """Página principal de mensagens - mostra conversas"""
    conversations = current_user.get_conversations()
    
    return render_template('messages/inbox.html', conversations=conversations)

@messages.route('/messages/conversation/<username>')
@login_required
def conversation(username):
    """Visualiza conversa específica com um usuário"""
    other_user = User.query.filter_by(username=username).first_or_404()
    
    # Busca todas as mensagens entre os dois usuários
    messages_query = Message.query.filter(
        or_(
            and_(Message.sender_id == current_user.id, Message.recipient_id == other_user.id),
            and_(Message.sender_id == other_user.id, Message.recipient_id == current_user.id)
        )
    ).order_by(Message.timestamp.asc())
    
    conversation_messages = messages_query.all()
    
    # Marca como lidas as mensagens recebidas
    unread_messages = [msg for msg in conversation_messages 
                      if msg.recipient_id == current_user.id and not msg.read]
    for msg in unread_messages:
        msg.read = True
    
    if unread_messages:
        db.session.commit()
    
    return render_template('messages/conversation.html', 
                         messages=conversation_messages, 
                         other_user=other_user)

@messages.route('/messages/sent')
@login_required
def sent():
    # Obtém todas as mensagens enviadas pelo usuário atual
    sent_messages = current_user.messages_sent.order_by(Message.timestamp.desc()).all()
    return render_template('messages/sent.html', messages=sent_messages)

@messages.route('/messages/new', methods=['GET', 'POST'])
@login_required
def new_message():
    if request.method == 'POST':
        recipient_username = request.form.get('recipient')
        content = request.form.get('content')
        
        if not recipient_username or not content:
            flash('Por favor, preencha todos os campos.', 'danger')
            return redirect(url_for('messages.new_message'))
        
        recipient = User.query.filter_by(username=recipient_username).first()
        
        if not recipient:
            flash('Usuário não encontrado.', 'danger')
            return redirect(url_for('messages.new_message'))
        
        if recipient == current_user:
            flash('Você não pode enviar mensagens para si mesmo.', 'danger')
            return redirect(url_for('messages.new_message'))
        
        message = Message(sender_id=current_user.id, recipient_id=recipient.id, content=content)
        db.session.add(message)
        db.session.commit()
        
        # Cria notificação para o destinatário
        Notification.create_message_notification(current_user, recipient, message)
        
        flash('Mensagem enviada com sucesso!', 'success')
        return redirect(url_for('messages.conversation', username=recipient.username))
    
    return render_template('messages/new.html')

@messages.route('/messages/view/<int:message_id>')
@login_required
def view_message(message_id):
    message = Message.query.get_or_404(message_id)
    
    # Verifica se o usuário atual é o destinatário ou o remetente
    if message.recipient_id != current_user.id and message.sender_id != current_user.id:
        abort(403)
    
    # Marca como lida se o usuário atual é o destinatário
    if message.recipient_id == current_user.id and not message.read:
        message.read = True
        db.session.commit()
    
    return render_template('messages/view.html', message=message)

@messages.route('/messages/delete/<int:message_id>', methods=['POST'])
@login_required
def delete_message(message_id):
    message = Message.query.get_or_404(message_id)
    
    # Verifica se o usuário atual é o destinatário ou o remetente
    if message.recipient_id != current_user.id and message.sender_id != current_user.id:
        abort(403)
    
    db.session.delete(message)
    db.session.commit()
    
    flash('Mensagem excluída com sucesso!', 'success')
    return redirect(url_for('messages.inbox'))

@messages.route('/messages/send/<username>', methods=['GET', 'POST'])
@login_required
def send_message(username):
    recipient = User.query.filter_by(username=username).first_or_404()
    
    if recipient == current_user:
        flash('Você não pode enviar mensagens para si mesmo.', 'danger')
        return redirect(url_for('main.user_profile', username=username))
    
    if request.method == 'POST':
        content = request.form.get('content')
        
        if not content:
            flash('O conteúdo da mensagem não pode estar vazio.', 'danger')
            return redirect(url_for('messages.send_message', username=username))
        
        message = Message(sender_id=current_user.id, recipient_id=recipient.id, content=content)
        db.session.add(message)
        db.session.commit()
        
        # Cria notificação para o destinatário
        Notification.create_message_notification(current_user, recipient, message)
        
        flash(f'Mensagem enviada para {recipient.username}!', 'success')
        return redirect(url_for('messages.conversation', username=recipient.username))
    
    return render_template('messages/send.html', recipient=recipient)

# Rotas para sistema de notificações
@messages.route('/notifications')
@login_required
def notifications():
    """Página de notificações"""
    all_notifications = current_user.get_recent_notifications(50)
    
    # Marca todas como lidas
    unread_notifications = [n for n in all_notifications if not n.read]
    for notification in unread_notifications:
        notification.read = True
    
    if unread_notifications:
        db.session.commit()
    
    return render_template('messages/notifications.html', notifications=all_notifications)

@messages.route('/api/notifications/count')
@login_required
def notifications_count():
    """API para obter número de notificações não lidas"""
    unread_count = current_user.unread_notifications_count
    unread_messages = current_user.unread_messages_count
    
    return jsonify({
        'notifications': unread_count,
        'messages': unread_messages,
        'total': unread_count + unread_messages
    })

@messages.route('/api/notifications/mark-read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Marca uma notificação específica como lida"""
    notification = Notification.query.get_or_404(notification_id)
    
    if notification.user_id != current_user.id:
        abort(403)
    
    notification.mark_as_read()
    
    return jsonify({'success': True})

@messages.route('/messages/send-quick', methods=['POST'])
@login_required  
def send_quick_message():
    """API para enviar mensagem rápida via AJAX"""
    recipient_id = request.json.get('recipient_id')
    content = request.json.get('content')
    
    if not recipient_id or not content:
        return jsonify({'success': False, 'error': 'Dados incompletos'}), 400
    
    recipient = User.query.get_or_404(recipient_id)
    
    if recipient == current_user:
        return jsonify({'success': False, 'error': 'Não é possível enviar mensagem para si mesmo'}), 400
    
    message = Message(sender_id=current_user.id, recipient_id=recipient.id, content=content)
    db.session.add(message)
    db.session.commit()
    
    # Cria notificação
    Notification.create_message_notification(current_user, recipient, message)
    
    return jsonify({
        'success': True, 
        'message': 'Mensagem enviada com sucesso!',
        'message_id': message.id
    })