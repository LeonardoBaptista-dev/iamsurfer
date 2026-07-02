"""Fotos à venda + pagamento da API (`/api/v1`) — Prompt A9.

Fluxo de "fotos de sessão" à venda por fotógrafos (models PhotoSession /
SessionPhoto / PhotoPurchase). O app lista as sessões e fotos (com preview /
marca d'água), o usuário compra uma foto (o preço vem SEMPRE do servidor) e o
provedor de pagamento (Mercado Pago em produção; modo teste em dev) processa a
cobrança. A URL de download em alta resolução só é liberada após o pagamento
confirmado, via webhook idempotente.

Endpoints:
- GET  /photo-sessions            → lista sessões ativas (cursor)
- GET  /photo-sessions/<id>       → detalhe da sessão + fotos (preview; alta só se comprada)
- POST /photos/<id>/purchase      → cria a compra (pending) + cobrança no provedor
- POST /webhooks/payments         → confirma pagamento (idempotente) — MP ou modo teste
- GET  /me/purchases              → minhas compras (download liberado só p/ pagas)

Preço/segurança: o valor cobrado vem de SessionPhoto.price (fallback
PhotoSession.price_per_photo) — nunca do cliente. O webhook nunca libera duas
vezes a mesma compra.
"""
from datetime import date

from flask import Blueprint, jsonify, request

from extensions import db
from .deps import body, current_api_user
from .errors import ApiError
from .pagination import clamp_limit, paginate_query
from .serializers import iso, media_url, user_brief
from . import payments

photos_api = Blueprint('photos_api', __name__)

# A foto de sessão fica em /static/uploads/sessions/<filename> (ver routes/spots.py).
SESSION_MEDIA_PREFIX = 'uploads/sessions/'

# Status de compra considerados "pagos" (o site legado usa 'completed'; a API
# usa 'paid'). Ambos liberam o download.
PAID_STATUSES = ('paid', 'completed')
PENDING_STATUS = 'pending'


# ── Helpers de preço / cupom ───────────────────────────────────────────────────

def _photo_price_cents(photo):
    """Preço da foto em centavos, do servidor (nunca do cliente).

    Usa SessionPhoto.price; se não houver, cai para PhotoSession.price_per_photo.
    """
    price = photo.price
    if not price and photo.session is not None:
        price = photo.session.price_per_photo
    return int(round((price or 0) * 100))


def _apply_coupon(price_cents, code):
    """Aplica um cupom válido ao preço (em centavos). Devolve (preço_final, coupon).

    Cupom inválido/expirado é silenciosamente ignorado (coupon=None). O desconto
    é interpretado do campo textual `Coupon.discount` ("10%" ou "R$ 20 OFF").
    """
    if not code:
        return price_cents, None
    from models import Coupon

    coupon = Coupon.query.filter_by(code=code.strip()).first()
    if coupon is None:
        return price_cents, None
    if coupon.valid_until is not None and coupon.valid_until < date.today():
        return price_cents, None

    discount = (coupon.discount or '').strip()
    final = price_cents
    if '%' in discount:
        try:
            pct = float(discount.replace('%', '').strip())
            final = int(round(price_cents * (1 - pct / 100.0)))
        except ValueError:
            final = price_cents
    else:
        # Formatos "R$ 20 OFF", "20", "R$20" → desconto fixo em reais.
        digits = ''.join(ch for ch in discount if ch.isdigit() or ch in '.,')
        digits = digits.replace(',', '.')
        try:
            off_cents = int(round(float(digits) * 100)) if digits else 0
            final = price_cents - off_cents
        except ValueError:
            final = price_cents
    return max(final, 0), coupon


# ── Serializers locais ──────────────────────────────────────────────────────────

def _session_brief(session):
    return {
        'id': session.id,
        'title': session.title,
        'description': session.description or '',
        'spot_id': session.spot_id,
        'session_date': session.session_date.isoformat() if session.session_date else None,
        'price_per_photo_cents': int(round((session.price_per_photo or 0) * 100)),
        'photographer': user_brief(session.photographer),
        'photos_count': session.session_photos.filter_by(is_available=True).count(),
        'created_at': iso(session.created_at),
    }


def _photo_card(photo, purchased=False):
    """Serializa uma foto de sessão.

    `preview_url` é sempre exposta (baixa resolução / marca d'água — o app mostra
    para vender). `download_url` (alta) só vem quando `purchased` é True.
    """
    full = media_url(SESSION_MEDIA_PREFIX + photo.filename)
    return {
        'id': photo.id,
        'session_id': photo.session_id,
        'title': photo.title or '',
        'price_cents': _photo_price_cents(photo),
        'is_available': bool(photo.is_available),
        'preview_url': full,          # placeholder de preview/marca d'água
        'download_url': full if purchased else None,
        'is_purchased': bool(purchased),
        'created_at': iso(photo.created_at),
    }


def _purchase_card(purchase):
    photo = purchase.photo
    paid = purchase.status in PAID_STATUSES
    return {
        'id': purchase.id,
        'photo_id': purchase.photo_id,
        'status': purchase.status,
        'amount_cents': int(round((purchase.amount_paid or 0) * 100)),
        'coupon_code': purchase.coupon_code,
        'provider': purchase.provider,
        'purchased_at': iso(purchase.purchase_date),
        'photo': _photo_card(photo, purchased=paid) if photo is not None else None,
        'download_url': (media_url(SESSION_MEDIA_PREFIX + photo.filename)
                         if (paid and photo is not None) else None),
    }


def _payment_public(provider_result, purchase):
    """Parte 'payment' da resposta de compra (o que o app precisa p/ pagar)."""
    return {
        'provider': provider_result['provider'],
        'provider_ref': provider_result.get('provider_ref'),
        'init_point': provider_result.get('init_point'),
        'qr': provider_result.get('qr'),
        'test_mode': provider_result.get('test_mode', False),
        'amount_cents': int(round((purchase.amount_paid or 0) * 100)),
    }


# ── Endpoints ───────────────────────────────────────────────────────────────────

@photos_api.route('/photo-sessions', methods=['GET'])
def list_sessions():
    from models import PhotoSession

    current_api_user(optional=True)
    query = PhotoSession.query.filter_by(is_active=True)
    items, next_cursor = paginate_query(
        query, PhotoSession, cursor=request.args.get('cursor'),
        limit=clamp_limit(request.args.get('limit')),
    )
    return jsonify({
        'items': [_session_brief(s) for s in items],
        'next_cursor': next_cursor,
    })


@photos_api.route('/photo-sessions/<int:session_id>', methods=['GET'])
def get_session(session_id):
    from models import PhotoSession, PhotoPurchase

    viewer = current_api_user(optional=True)
    session = PhotoSession.query.get(session_id)
    if session is None or not session.is_active:
        raise ApiError('not_found', 'Sessão de fotos não encontrada.', 404)

    # Quais fotos desta sessão o viewer já comprou (para liberar download)?
    purchased_ids = set()
    if viewer is not None:
        photo_ids = [p.id for p in session.session_photos]
        if photo_ids:
            rows = PhotoPurchase.query.filter(
                PhotoPurchase.user_id == viewer.id,
                PhotoPurchase.photo_id.in_(photo_ids),
                PhotoPurchase.status.in_(PAID_STATUSES),
            ).all()
            purchased_ids = {r.photo_id for r in rows}

    photos = [
        _photo_card(p, purchased=p.id in purchased_ids)
        for p in session.session_photos.filter_by(is_available=True)
    ]
    data = _session_brief(session)
    data['photos'] = photos
    return jsonify({'session': data})


@photos_api.route('/photos/<int:photo_id>/purchase', methods=['POST'])
def purchase_photo(photo_id):
    from models import SessionPhoto, PhotoPurchase

    viewer = current_api_user()
    photo = SessionPhoto.query.get(photo_id)
    if photo is None:
        raise ApiError('not_found', 'Foto não encontrada.', 404)
    if not photo.is_available:
        raise ApiError('unavailable', 'Esta foto não está disponível para compra.', 409)

    # Já comprou (pago)? Não cobra de novo.
    already = PhotoPurchase.query.filter(
        PhotoPurchase.photo_id == photo_id,
        PhotoPurchase.user_id == viewer.id,
        PhotoPurchase.status.in_(PAID_STATUSES),
    ).first()
    if already is not None:
        return jsonify({
            'purchase_id': already.id,
            'already_purchased': True,
            'purchase': _purchase_card(already),
        }), 200

    # Preço do SERVIDOR (o cliente não pode informar valor). Aplica cupom opcional.
    data = body()
    coupon_code = (data.get('coupon_code') or data.get('coupon') or '').strip() or None
    base_cents = _photo_price_cents(photo)
    final_cents, coupon = _apply_coupon(base_cents, coupon_code)

    # Reaproveita uma compra pendente do mesmo par (evita pendências duplicadas).
    purchase = PhotoPurchase.query.filter_by(
        photo_id=photo_id, user_id=viewer.id, status=PENDING_STATUS,
    ).first()
    if purchase is None:
        purchase = PhotoPurchase(
            photo_id=photo_id, user_id=viewer.id,
            amount_paid=final_cents / 100.0, status=PENDING_STATUS,
        )
        db.session.add(purchase)
    else:
        purchase.amount_paid = final_cents / 100.0
    purchase.coupon_code = coupon.code if coupon is not None else None
    db.session.flush()  # garante purchase.id para o external_reference

    title = photo.title or (photo.session.title if photo.session else 'Foto')
    provider_result = payments.create_payment(
        purchase_id=purchase.id,
        amount_cents=final_cents,
        title=title,
        payer_email=viewer.email,
    )
    purchase.provider = provider_result['provider']
    purchase.provider_ref = provider_result.get('provider_ref')
    db.session.commit()

    return jsonify({
        'purchase_id': purchase.id,
        'already_purchased': False,
        'purchase': _purchase_card(purchase),
        'payment': _payment_public(provider_result, purchase),
    }), 201


@photos_api.route('/webhooks/payments', methods=['POST'])
def payments_webhook():
    """Confirma pagamentos. Público (não usa JWT) e IDEMPOTENTE.

    Aceita dois formatos:
    - Modo teste:  {"purchase_id": <id>, "status": "paid"}
    - Mercado Pago: {"type": "payment", "data": {"id": <payment_id>}} (ou via
      query ?topic=payment&id=...). Nesse caso consultamos o pagamento no MP e
      só liberamos se estiver 'approved'.
    """
    from models import PhotoPurchase

    data = body()

    purchase = None
    should_confirm = False

    # 1) Modo teste / confirmação direta por purchase_id.
    purchase_id = data.get('purchase_id')
    if purchase_id is not None:
        try:
            purchase = PhotoPurchase.query.get(int(purchase_id))
        except (TypeError, ValueError):
            purchase = None
        status = (data.get('status') or 'paid').lower()
        should_confirm = status in ('paid', 'approved', 'completed')

    # 2) Formato Mercado Pago (consulta o pagamento real para confirmar).
    if purchase is None:
        payment_id = (
            (data.get('data') or {}).get('id')
            or data.get('id')
            or request.args.get('id')
            or request.args.get('data.id')
        )
        topic = data.get('type') or data.get('topic') or request.args.get('topic') or request.args.get('type')
        if payment_id is not None and (topic in (None, 'payment', 'merchant_order')):
            mp_status, external_ref = payments.fetch_payment_status(payment_id)
            if external_ref is not None:
                try:
                    purchase = PhotoPurchase.query.get(int(external_ref))
                except (TypeError, ValueError):
                    purchase = None
            should_confirm = mp_status == 'approved'

    if purchase is None:
        # 200 para o provedor não reenviar infinitamente por algo que não achamos.
        return jsonify({'ok': True, 'ignored': True}), 200

    # Idempotência: se já está pago, não libera de novo.
    if purchase.status in PAID_STATUSES:
        return jsonify({'ok': True, 'purchase_id': purchase.id,
                        'status': purchase.status, 'already': True}), 200

    if should_confirm:
        purchase.status = 'paid'
        db.session.commit()
        return jsonify({'ok': True, 'purchase_id': purchase.id, 'status': 'paid'}), 200

    return jsonify({'ok': True, 'purchase_id': purchase.id, 'status': purchase.status}), 200


@photos_api.route('/me/purchases', methods=['GET'])
def my_purchases():
    from models import PhotoPurchase

    viewer = current_api_user()
    query = PhotoPurchase.query.filter_by(user_id=viewer.id)
    items, next_cursor = paginate_query(
        query, PhotoPurchase, cursor=request.args.get('cursor'),
        limit=clamp_limit(request.args.get('limit')),
    )
    return jsonify({
        'items': [_purchase_card(p) for p in items],
        'next_cursor': next_cursor,
    })
