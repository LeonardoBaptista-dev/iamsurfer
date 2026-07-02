"""Mensagens diretas e notificações da API (`/api/v1`) — Prompt A6.

Reaproveita a lógica do site (`routes/messages.py`): conversas por interlocutor
(`User.get_conversations()`), marcação de lidas e criação de notificação a cada
mensagem. Ao enviar uma mensagem, dispara um push Expo pro destinatário (A12).

Endpoints (montados sob `/api/v1` pelo blueprint pai):
- GET  /conversations                       → inbox (última msg por interlocutor)
- GET  /conversations/<username>            → histórico (cursor; marca lidas)
- POST /conversations/<username>/messages   → envia mensagem (+notif +push)
- GET  /notifications                       → lista (cursor)
- POST /notifications/read                  → marca todas (ou {ids:[...]}) lidas
- GET  /notifications/count                 → {unread: N}

Serializers de mensagem/conversa/notificação ficam aqui de propósito (o módulo
compartilhado `serializers.py` não é editado); reusamos `user_brief`/`iso` dele.
"""
from flask import Blueprint, jsonify, request
from sqlalchemy import and_, or_

from extensions import db
from .deps import body, current_api_user, require_fields
from .errors import ApiError
from .pagination import clamp_limit, paginate_query
from .push import notify
from .serializers import iso, user_brief

messages_api = Blueprint('messages_api', __name__)


# ── Serializers locais ─────────────────────────────────────────────────────────

def message_item(message, viewer):
    """Item de mensagem numa conversa. `from_me` = o viewer é o remetente."""
    return {
        'id': message.id,
        'content': message.content,
        'created_at': iso(message.timestamp),
        'from_me': message.sender_id == viewer.id,
    }


def conversation_item(message, viewer):
    """Item de inbox: o interlocutor + a última mensagem trocada com ele."""
    other = message.recipient if message.sender_id == viewer.id else message.sender
    from_me = message.sender_id == viewer.id
    return {
        'user': user_brief(other),
        'last_message': {
            'content': message.content,
            'created_at': iso(message.timestamp),
            'from_me': from_me,
        },
        # Não lida: mensagem recebida (não minha) e ainda não marcada como lida.
        'unread': (not from_me) and (not message.read),
    }


def notification_item(notification):
    """Item de notificação para o app."""
    return {
        'id': notification.id,
        'type': notification.type,
        'content': notification.content,
        'created_at': iso(notification.created_at),
        'read': bool(notification.read),
        'actor': user_brief(notification.related_user) if notification.related_user else None,
    }


# ── Conversas ───────────────────────────────────────────────────────────────

def _get_user_or_404(username):
    from models import User
    user = User.query.filter_by(username=username).first()
    if user is None:
        raise ApiError('not_found', 'Usuário não encontrado.', 404)
    return user


@messages_api.route('/conversations', methods=['GET'])
def conversations():
    viewer = current_api_user()
    convos = viewer.get_conversations()  # última msg por interlocutor (desc)
    return jsonify({
        'items': [conversation_item(m, viewer) for m in convos],
    })


@messages_api.route('/conversations/<username>', methods=['GET'])
def conversation(username):
    from models import Message

    viewer = current_api_user()
    other = _get_user_or_404(username)

    query = Message.query.filter(
        or_(
            and_(Message.sender_id == viewer.id, Message.recipient_id == other.id),
            and_(Message.sender_id == other.id, Message.recipient_id == viewer.id),
        )
    )
    # Cursor por id de Message (mais novas primeiro, como os demais feeds).
    items, next_cursor = paginate_query(
        query, Message, cursor=request.args.get('cursor'),
        limit=clamp_limit(request.args.get('limit')),
    )

    # Marca como lidas as recebidas (nesta página) ainda não lidas.
    unread = [m for m in items if m.recipient_id == viewer.id and not m.read]
    if unread:
        for m in unread:
            m.read = True
        db.session.commit()

    return jsonify({
        'items': [message_item(m, viewer) for m in items],
        'next_cursor': next_cursor,
    })


@messages_api.route('/conversations/<username>/messages', methods=['POST'])
def send_message(username):
    from models import Message, Notification

    viewer = current_api_user()
    other = _get_user_or_404(username)

    if other.id == viewer.id:
        raise ApiError('validation_error', 'Você não pode enviar mensagens para si mesmo.',
                       422, {'content': 'Destinatário inválido.'})

    data = body()
    require_fields(data, 'content')
    content = data['content'].strip()
    if not content:
        raise ApiError('validation_error', 'A mensagem não pode ser vazia.', 422,
                       {'content': 'Escreva algo.'})

    message = Message(sender_id=viewer.id, recipient_id=other.id, content=content)
    db.session.add(message)
    db.session.commit()

    # Notificação in-app + push Expo (best-effort; push nunca quebra o envio).
    Notification.create_message_notification(viewer, other, message)
    notify(
        other.id,
        f'Nova mensagem de {viewer.username}',
        content[:140],
        data={'type': 'message', 'from': viewer.username},
    )

    return jsonify({'message': message_item(message, viewer)}), 201


# ── Notificações ──────────────────────────────────────────────────────────────

@messages_api.route('/notifications', methods=['GET'])
def notifications():
    from models import Notification

    viewer = current_api_user()
    query = Notification.query.filter_by(user_id=viewer.id)
    items, next_cursor = paginate_query(
        query, Notification, cursor=request.args.get('cursor'),
        limit=clamp_limit(request.args.get('limit')),
    )
    return jsonify({
        'items': [notification_item(n) for n in items],
        'next_cursor': next_cursor,
    })


@messages_api.route('/notifications/read', methods=['POST'])
def mark_notifications_read():
    from models import Notification

    viewer = current_api_user()
    data = body()
    ids = data.get('ids')

    query = Notification.query.filter_by(user_id=viewer.id, read=False)
    if isinstance(ids, list) and ids:
        clean_ids = [int(i) for i in ids if isinstance(i, (int, str)) and str(i).isdigit()]
        query = query.filter(Notification.id.in_(clean_ids))

    updated = query.update({Notification.read: True}, synchronize_session=False)
    db.session.commit()
    return jsonify({'ok': True, 'updated': updated})


@messages_api.route('/notifications/count', methods=['GET'])
def notifications_count():
    viewer = current_api_user()
    return jsonify({'unread': viewer.unread_notifications_count})
