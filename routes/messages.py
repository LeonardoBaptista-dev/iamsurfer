from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from models import User, Message
from app import db
from datetime import datetime

messages = Blueprint('messages', __name__)

@messages.route('/messages')
@login_required
def inbox():
    # Obtém todas as mensagens recebidas pelo usuário atual
    received_messages = current_user.messages_received.order_by(Message.timestamp.desc()).all()
    
    # Marca as mensagens como lidas
    for message in received_messages:
        if not message.read:
            message.read = True
    
    db.session.commit()
    
    return render_template('messages/inbox.html', messages=received_messages)

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
        
        flash('Mensagem enviada com sucesso!', 'success')
        return redirect(url_for('messages.sent'))
    
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
        
        flash(f'Mensagem enviada para {recipient.username}!', 'success')
        return redirect(url_for('main.user_profile', username=username))
    
    return render_template('messages/send.html', recipient=recipient) 