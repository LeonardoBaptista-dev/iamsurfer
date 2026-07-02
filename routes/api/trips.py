"""Caronas / viagens de surf da API (`/api/v1`) — Prompt A8.

Reaproveita as regras do site (`routes/trips.py`): gamificação em criar/participar
e o cálculo de vagas (`SurfTrip.get_available_seats`). Diferente do fluxo web
(que tem aprovação do organizador), no app a participação é confirmada na hora —
assim `viewer_state.joined` e a lotação ficam consistentes e idempotentes.

Endpoints:
- GET  /trips                → lista de caronas (cursor por id desc; filtros opcionais)
- POST /trips                → cria carona
- GET  /trips/:id            → detalhe (participantes, vagas, viewer_state)
- POST /trips/:id/join       → participa (idempotente, respeita lotação)
- POST /trips/:id/leave      → sai (idempotente; organizador não sai)
- GET  /me/trips             → caronas que criei + que participo
"""
from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import or_

from extensions import db
from .deps import body, current_api_user, require_fields
from .errors import ApiError
from .pagination import clamp_limit, paginate_query
from .serializers import user_brief, iso

trips_api = Blueprint('trips_api', __name__)


# ── Serializer (definido aqui; usa user_brief/iso de .serializers) ─────────────

def _confirmed(trip):
    """Participantes confirmados da carona (lista de TripParticipant)."""
    return [p for p in trip.participants if p.status == 'Confirmed']


def _viewer_state(trip, viewer):
    if viewer is None:
        return {'joined': False, 'is_owner': False}
    is_owner = viewer.id == trip.creator_id
    joined = any(p.user_id == viewer.id for p in _confirmed(trip))
    return {'joined': joined, 'is_owner': is_owner}


def trip_card(trip, viewer=None):
    """Serializer de carona para listas (sem a lista de participantes)."""
    confirmed = _confirmed(trip)
    total = trip.available_seats or 0
    return {
        'id': trip.id,
        'title': trip.title,
        'departure_location': trip.departure_location,
        'destination': trip.destination_text or trip.get_destination_display(),
        'departure_time': iso(trip.departure_time),
        'return_time': iso(trip.return_time),
        'description': trip.description or '',
        'contribution': trip.contribution,
        'vehicle_info': trip.vehicle_info or '',
        'status': trip.status,
        'author': user_brief(trip.creator),
        'counts': {
            'participants': len(confirmed),
            'seats_total': total,
            'seats_available': trip.get_available_seats(),
        },
        'viewer_state': _viewer_state(trip, viewer),
        'created_at': iso(trip.created_at),
    }


def trip_detail(trip, viewer=None):
    """Serializer de detalhe: inclui a lista de participantes (user_brief)."""
    data = trip_card(trip, viewer=viewer)
    data['participants'] = [user_brief(p.user) for p in _confirmed(trip)]
    return data


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_trip_or_404(trip_id):
    from models import SurfTrip
    trip = SurfTrip.query.get(trip_id)
    if trip is None:
        raise ApiError('not_found', 'Carona não encontrada.', 404)
    return trip


def _parse_dt(value, field):
    """Parseia um datetime ISO-8601 do cliente. Erro → ApiError 422."""
    if isinstance(value, datetime):
        return value
    text = (value or '').strip() if isinstance(value, str) else ''
    if not text:
        return None
    if text.endswith('Z'):
        text = text[:-1]
    try:
        return datetime.fromisoformat(text)
    except (ValueError, TypeError):
        raise ApiError('validation_error', 'Data/hora inválida.', 422,
                       {field: 'Use o formato ISO-8601 (ex.: 2026-07-10T08:00).'})


# ── Lista / criação ─────────────────────────────────────────────────────────────

@trips_api.route('/trips', methods=['GET'])
def list_trips():
    from models import SurfTrip

    viewer = current_api_user(optional=True)

    query = SurfTrip.query.filter(SurfTrip.status != 'Cancelled')

    # Por padrão só mostra caronas futuras; ?past=1 inclui as passadas.
    if request.args.get('past') not in ('1', 'true', 'yes'):
        query = query.filter(SurfTrip.departure_time > datetime.utcnow())

    # Filtro por destino (rótulo do destino ou local de partida).
    destination = (request.args.get('destination') or request.args.get('q') or '').strip()
    if destination:
        like = f'%{destination}%'
        query = query.filter(or_(
            SurfTrip.destination_text.ilike(like),
            SurfTrip.departure_location.ilike(like),
            SurfTrip.title.ilike(like),
        ))

    # Filtro por data (YYYY-MM-DD) → caronas que partem naquele dia.
    date_raw = (request.args.get('date') or '').strip()
    if date_raw:
        try:
            day = datetime.strptime(date_raw, '%Y-%m-%d').date()
        except ValueError:
            raise ApiError('validation_error', 'Data inválida.', 422,
                           {'date': 'Use o formato AAAA-MM-DD.'})
        start = datetime(day.year, day.month, day.day)
        end = datetime(day.year, day.month, day.day, 23, 59, 59)
        query = query.filter(SurfTrip.departure_time >= start,
                             SurfTrip.departure_time <= end)

    items, next_cursor = paginate_query(
        query, SurfTrip, cursor=request.args.get('cursor'),
        limit=clamp_limit(request.args.get('limit')),
    )
    return jsonify({
        'items': [trip_card(t, viewer=viewer) for t in items],
        'next_cursor': next_cursor,
    })


@trips_api.route('/trips', methods=['POST'])
@jwt_required()
def create_trip():
    from gamification import award
    from models import SurfTrip

    viewer = current_api_user(verify=False)
    data = body()
    require_fields(data, 'title', 'departure_location', 'destination_text', 'departure_time')

    departure_time = _parse_dt(data.get('departure_time'), 'departure_time')
    return_time = _parse_dt(data.get('return_time'), 'return_time')

    # Vagas: default do model é 3; valida faixa se informado.
    seats = data.get('available_seats', 3)
    try:
        seats = int(seats)
    except (TypeError, ValueError):
        raise ApiError('validation_error', 'Número de vagas inválido.', 422,
                       {'available_seats': 'Informe um número inteiro.'})
    if seats < 1 or seats > 10:
        raise ApiError('validation_error', 'Número de vagas inválido.', 422,
                       {'available_seats': 'Entre 1 e 10.'})

    contribution = data.get('contribution')
    if contribution in ('', None):
        contribution = None
    else:
        try:
            contribution = float(contribution)
        except (TypeError, ValueError):
            raise ApiError('validation_error', 'Contribuição inválida.', 422,
                           {'contribution': 'Informe um valor numérico.'})

    def _float(v):
        try:
            return float(v) if v not in ('', None) else None
        except (TypeError, ValueError):
            return None

    trip = SurfTrip(
        title=data['title'].strip(),
        creator_id=viewer.id,
        departure_location=data['departure_location'].strip(),
        departure_lat=_float(data.get('departure_lat')),
        departure_lng=_float(data.get('departure_lng')),
        destination_lat=_float(data.get('destination_lat')),
        destination_lng=_float(data.get('destination_lng')),
        destination_text=data['destination_text'].strip(),
        departure_time=departure_time,
        return_time=return_time,
        description=(data.get('description') or '').strip() or None,
        available_seats=seats,
        contribution=contribution,
        vehicle_info=(data.get('vehicle_info') or '').strip() or None,
        intermediate_stops=(data.get('intermediate_stops') or '').strip() or None,
    )
    db.session.add(trip)
    award(viewer, 'trip_create')
    db.session.commit()

    return jsonify({'trip': trip_detail(trip, viewer=viewer)}), 201


# ── Detalhe ─────────────────────────────────────────────────────────────────────

@trips_api.route('/trips/<int:trip_id>', methods=['GET'])
def get_trip(trip_id):
    viewer = current_api_user(optional=True)
    trip = _get_trip_or_404(trip_id)
    return jsonify({'trip': trip_detail(trip, viewer=viewer)})


# ── Participação ─────────────────────────────────────────────────────────────────

@trips_api.route('/trips/<int:trip_id>/join', methods=['POST'])
@jwt_required()
def join_trip(trip_id):
    from gamification import award
    from models import TripParticipant

    viewer = current_api_user(verify=False)
    trip = _get_trip_or_404(trip_id)

    if trip.creator_id == viewer.id:
        raise ApiError('already_owner', 'Você é o organizador desta carona.', 422)
    if trip.status == 'Cancelled':
        raise ApiError('trip_cancelled', 'Esta carona foi cancelada.', 409)

    existing = TripParticipant.query.filter_by(trip_id=trip.id, user_id=viewer.id).first()

    if existing is not None and existing.status == 'Confirmed':
        # Idempotente: já está dentro.
        return jsonify({'trip': trip_detail(trip, viewer=viewer)})

    if trip.get_available_seats() <= 0:
        raise ApiError('trip_full', 'Esta carona não tem mais vagas.', 409)

    if existing is not None:
        existing.status = 'Confirmed'
        existing.confirmation_time = datetime.utcnow()
    else:
        db.session.add(TripParticipant(
            trip_id=trip.id, user_id=viewer.id,
            status='Confirmed', confirmation_time=datetime.utcnow(),
        ))
    award(viewer, 'trip_join')
    db.session.commit()

    return jsonify({'trip': trip_detail(trip, viewer=viewer)})


@trips_api.route('/trips/<int:trip_id>/leave', methods=['POST'])
@jwt_required()
def leave_trip(trip_id):
    from models import TripParticipant

    viewer = current_api_user(verify=False)
    trip = _get_trip_or_404(trip_id)

    if trip.creator_id == viewer.id:
        raise ApiError('owner_cannot_leave',
                       'O organizador não pode sair da própria carona. Cancele-a.', 422)

    existing = TripParticipant.query.filter_by(trip_id=trip.id, user_id=viewer.id).first()
    if existing is not None:  # idempotente
        db.session.delete(existing)
        db.session.commit()

    return jsonify({'trip': trip_detail(trip, viewer=viewer)})


# ── Minhas caronas ──────────────────────────────────────────────────────────────

@trips_api.route('/me/trips', methods=['GET'])
@jwt_required()
def my_trips():
    from models import SurfTrip, TripParticipant

    viewer = current_api_user(verify=False)

    created_ids = [t.id for t in SurfTrip.query.filter_by(creator_id=viewer.id).all()]
    joined_ids = [
        p.trip_id for p in TripParticipant.query.filter_by(
            user_id=viewer.id, status='Confirmed').all()
    ]
    trip_ids = set(created_ids) | set(joined_ids)

    query = SurfTrip.query.filter(SurfTrip.id.in_(trip_ids))

    items, next_cursor = paginate_query(
        query, SurfTrip, cursor=request.args.get('cursor'),
        limit=clamp_limit(request.args.get('limit')),
    )
    return jsonify({
        'items': [trip_card(t, viewer=viewer) for t in items],
        'next_cursor': next_cursor,
    })
