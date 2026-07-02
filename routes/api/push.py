"""Envio de push notifications via Expo (`exp.host`) — Prompt A12.

O app registra o Expo push token de cada device (model `DeviceToken`). Aqui
buscamos os tokens dos destinatários e disparamos em lote para o serviço da
Expo. É um serviço de melhor-esforço: **nunca** levanta exceção pro caller —
uma falha de push jamais deve derrubar o envio de uma mensagem/notificação.

Se a Expo responder que um token está morto (`DeviceNotRegistered`), apagamos
aquele `DeviceToken` para não insistir num aparelho que desinstalou o app.

Uso:
    from .push import notify, send_push
    notify(user.id, 'Nova mensagem', 'Oi!', data={'type': 'message'})
"""
import requests
from flask import current_app

from extensions import db

EXPO_PUSH_URL = 'https://exp.host/--/api/v2/push/send'
# A Expo aceita até 100 mensagens por requisição.
_BATCH_SIZE = 100


def _log():
    """Logger seguro tanto dentro quanto fora de um app context."""
    try:
        return current_app.logger
    except Exception:  # pragma: no cover - fora de contexto
        import logging
        return logging.getLogger(__name__)


def send_push(user_ids, title, body, data=None):
    """Envia um push para todos os devices dos usuários em `user_ids`.

    - `user_ids`: int ou iterável de ints (destinatários).
    - `title`/`body`: texto da notificação.
    - `data`: dict opcional com payload extra (ex.: {'type': 'message'}).

    Robusto por design: captura toda exceção e loga. Remove tokens que a Expo
    reportar como `DeviceNotRegistered`. Retorna a lista de tickets da Expo
    (ou [] em falha), útil para testes.
    """
    from models import DeviceToken

    try:
        if isinstance(user_ids, int):
            user_ids = [user_ids]
        user_ids = [uid for uid in (user_ids or []) if uid is not None]
        if not user_ids:
            return []

        tokens = DeviceToken.query.filter(DeviceToken.user_id.in_(user_ids)).all()
        if not tokens:
            return []

        # Mapeia token -> registro para poder apagar os mortos depois.
        token_rows = {t.token: t for t in tokens}
        messages = []
        for tok in token_rows:
            msg = {'to': tok, 'title': title, 'body': body, 'sound': 'default'}
            if data is not None:
                msg['data'] = data
            messages.append(msg)

        tickets = []
        for start in range(0, len(messages), _BATCH_SIZE):
            batch = messages[start:start + _BATCH_SIZE]
            try:
                resp = requests.post(
                    EXPO_PUSH_URL,
                    json=batch,
                    headers={
                        'Accept': 'application/json',
                        'Content-Type': 'application/json',
                    },
                    timeout=10,
                )
                payload = resp.json() if resp is not None else {}
            except Exception as exc:  # falha de rede / parse: loga e segue
                _log().warning('Falha ao enviar push para a Expo: %s', exc)
                continue

            batch_tickets = payload.get('data') if isinstance(payload, dict) else None
            if not isinstance(batch_tickets, list):
                continue
            tickets.extend(batch_tickets)

            # Casa cada ticket com a mensagem enviada (mesma ordem) para saber
            # qual token remover em caso de DeviceNotRegistered.
            for msg, ticket in zip(batch, batch_tickets):
                if not isinstance(ticket, dict):
                    continue
                if ticket.get('status') == 'error':
                    details = ticket.get('details') or {}
                    if details.get('error') == 'DeviceNotRegistered':
                        dead = token_rows.get(msg['to'])
                        if dead is not None:
                            db.session.delete(dead)

        db.session.commit()
        return tickets
    except Exception as exc:  # blindagem total: push nunca quebra o caller
        _log().warning('send_push falhou silenciosamente: %s', exc)
        try:
            db.session.rollback()
        except Exception:
            pass
        return []


def notify(user_id, title, body, data=None):
    """Atalho para enviar um push a um único usuário."""
    return send_push([user_id], title, body, data=data)
