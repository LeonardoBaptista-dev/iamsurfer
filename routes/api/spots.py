"""Picos (SurfMap) da API (`/api/v1/spots`).

Reaproveita as regras do site (`routes/spots.py`): novo pico entra como
`status='pending'` e notifica os admins; estados são padronizados
(`br_states.normalize_state`); maré e época aceitam múltiplos valores.
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from extensions import db
from br_states import normalize_state
from .deps import body, require_fields, current_api_user
from .errors import ApiError
from .serializers import spot_brief, spot_full

spots_api = Blueprint('spots_api', __name__, url_prefix='/spots')


def _str(data, key):
    v = data.get(key)
    return v.strip() if isinstance(v, str) and v.strip() else None


def _num(data, key):
    v = data.get(key)
    try:
        return float(v) if v not in (None, '') else None
    except (TypeError, ValueError):
        return None


def _multi(data, key):
    """Aceita lista (['Cheia','Seca']) ou string ('Cheia, Seca'); devolve string."""
    v = data.get(key)
    if isinstance(v, list):
        return ', '.join(str(x).strip() for x in v if str(x).strip()) or None
    return _str(data, key)


@spots_api.route('', methods=['GET'])
def list_spots():
    """Lista picos aprovados (com filtros opcionais)."""
    from models import Spot
    q = Spot.query.filter_by(status='approved', is_active=True)

    country = (request.args.get('country') or '').strip()
    state = (request.args.get('state') or '').strip()
    difficulty = (request.args.get('difficulty') or '').strip()
    wave_type = (request.args.get('wave_type') or '').strip()
    search = (request.args.get('q') or '').strip()

    if country:
        q = q.filter(Spot.country == country)
    if state:
        q = q.filter(Spot.state == normalize_state(state))
    if difficulty:
        q = q.filter(Spot.difficulty == difficulty)
    if wave_type:
        q = q.filter(Spot.wave_type == wave_type)
    if search:
        q = q.filter(Spot.name.ilike(f'%{search}%'))

    spots = q.order_by(Spot.name).all()
    return jsonify({'items': [spot_brief(s) for s in spots], 'total': len(spots)})


@spots_api.route('/<int:spot_id>', methods=['GET'])
def get_spot(spot_id):
    """Detalhe de um pico aprovado."""
    from models import Spot
    spot = Spot.query.get(spot_id)
    if spot is None or spot.status != 'approved' or not spot.is_active:
        raise ApiError('not_found', 'Pico não encontrado.', 404)
    viewer = current_api_user(optional=True)
    return jsonify(spot_full(spot, viewer))


@spots_api.route('', methods=['POST'])
@jwt_required()
def create_spot():
    """Cadastra um pico (entra como pendente e notifica os admins)."""
    from models import Spot, Notification
    user = current_api_user(verify=False)
    data = body()
    require_fields(data, 'name', 'latitude', 'longitude')

    try:
        lat = float(data['latitude'])
        lng = float(data['longitude'])
    except (TypeError, ValueError):
        raise ApiError('validation_error', 'Coordenadas inválidas.', 422,
                       {'latitude': 'Inválida', 'longitude': 'Inválida'})

    spot = Spot(
        name=data['name'].strip()[:100],
        description=_str(data, 'description'),
        latitude=lat,
        longitude=lng,
        address=_str(data, 'address'),
        city=_str(data, 'city'),
        state=normalize_state(_str(data, 'state')),
        country=_str(data, 'country') or 'Brasil',
        bottom_type=_str(data, 'bottom_type'),
        wave_type=_str(data, 'wave_type') or 'Beach Break',
        difficulty=_str(data, 'difficulty') or 'Intermediário',
        crowd_level=_str(data, 'crowd_level'),
        best_wind_direction=_str(data, 'best_wind_direction'),
        best_swell_direction=_str(data, 'best_swell_direction'),
        best_tide=_multi(data, 'best_tide'),
        best_season=_multi(data, 'best_season'),
        water_temp=_str(data, 'water_temp'),
        min_swell_size=_num(data, 'min_swell_size'),
        max_swell_size=_num(data, 'max_swell_size'),
        created_by=user.id,
        status='pending',
        is_active=True,
    )
    db.session.add(spot)
    db.session.commit()

    Notification.notify_admins(
        'spot_pending',
        f'{user.username} sugeriu um novo pico: {spot.name}',
        related_user_id=user.id, related_spot_id=spot.id)

    return jsonify(spot_full(spot, user)), 201


@spots_api.route('/<int:spot_id>/follow', methods=['POST'])
@jwt_required()
def follow_spot(spot_id):
    """Segue/deixa de seguir um pico (toggle)."""
    from models import Spot, SpotFollow
    user = current_api_user(verify=False)
    spot = Spot.query.get(spot_id)
    if spot is None:
        raise ApiError('not_found', 'Pico não encontrado.', 404)

    existing = SpotFollow.query.filter_by(user_id=user.id, spot_id=spot.id).first()
    if existing:
        db.session.delete(existing)
        following = False
    else:
        db.session.add(SpotFollow(user_id=user.id, spot_id=spot.id))
        following = True
    db.session.commit()

    count = SpotFollow.query.filter_by(spot_id=spot.id).count()
    return jsonify({'following': following, 'followers_count': count})
