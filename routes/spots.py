from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from models import State, City, SurfSpot, Photographer, SpotPhoto, Spot, SpotPhotoNew, PhotoSession, SessionPhoto, PhotoPurchase, SpotReport, Business, Coupon, SpotFollow, Notification, SpotContribution
from extensions import db
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime
from functools import wraps

spots = Blueprint('spots', __name__)

# === ROTAS ANTIGAS DOS "PICOS DE SURF" - REMOVIDAS ===
# As rotas abaixo foram comentadas para remover o sistema antigo de navegação por estados/cidades
# Mantemos apenas o sistema novo do "Mapa Colaborativo"

# @spots.route('/states')
# def states_list():
#     states = State.query.order_by(State.name).all()
#     return render_template('spots/states_list.html', states=states)

# @spots.route('/state/<uf>')
# def state_detail(uf):
#     state = State.query.filter_by(uf=uf).first_or_404()
#     cities = City.query.filter_by(state_id=state.id).order_by(City.name).all()
#     return render_template('spots/state_detail.html', state=state, cities=cities)

# @spots.route('/city/<int:city_id>')
# def city_detail(city_id):
#     city = City.query.get_or_404(city_id)
#     spots = SurfSpot.query.filter_by(city_id=city_id).order_by(SurfSpot.name).all()
#     return render_template('spots/city_detail.html', city=city, spots=spots)

# @spots.route('/spot/<int:spot_id>')
# def spot_detail(spot_id):
#     spot = SurfSpot.query.get_or_404(spot_id)
#     photographers = Photographer.query.filter_by(spot_id=spot_id).all()
#     photos = SpotPhoto.query.filter_by(spot_id=spot_id).order_by(SpotPhoto.created_at.desc()).all()
#     return render_template('spots/spot_detail.html', spot=spot, photographers=photographers, photos=photos)

# @spots.route('/spot/<int:spot_id>/photographers')
# def spot_photographers(spot_id):
#     spot = SurfSpot.query.get_or_404(spot_id)
#     photographers = Photographer.query.filter_by(spot_id=spot_id).all()
#     return render_template('spots/spot_photographers.html', spot=spot, photographers=photographers)

# @spots.route('/spot/<int:spot_id>/services')
# def spot_services(spot_id):
#     spot = SurfSpot.query.get_or_404(spot_id)
#     # Aqui você pode adicionar filtros para diferentes tipos de serviços
#     return render_template('spots/spot_services.html', spot=spot)

# === NOVAS ROTAS PARA SPOTS COLABORATIVOS ===

@spots.route('/spots/map')
def spots_map():
    """Exibe o mapa interativo GRATUITO com todos os spots aprovados"""
    from models import Post
    approved_spots = Spot.query.filter_by(status='approved', is_active=True).all()
    spots_data = []

    # Previsão atual de todos os picos (cacheada por 1h)
    from surf_forecast import get_forecast
    forecasts = get_forecast(approved_spots)

    for spot in approved_spots:
        cover_photo = SpotPhotoNew.query.filter_by(spot_id=spot.id, is_cover=True).first()

        # Buscar a última interação (relato/post mais recente desse pico)
        last_post = Post.query.filter_by(spot_id=spot.id).order_by(Post.created_at.desc()).first()
        last_interaction = last_post.created_at.isoformat() if last_post else "2000-01-01T00:00:00"

        fc = (forecasts.get(spot.id) or {}).get('current') if forecasts else None

        spots_data.append({
            'id': spot.id,
            'name': spot.name,
            'city': spot.city or '',
            'state': spot.state or '',
            'country': spot.country or 'Brasil',
            'last_interaction': last_interaction,
            'lat': spot.latitude,
            'lng': spot.longitude,
            'description': spot.description[:100] + '...' if spot.description and len(spot.description) > 100 else spot.description,
            'cover_photo': cover_photo.filename if cover_photo else None,
            'difficulty': spot.difficulty,
            'wave_type': spot.wave_type,
            'wave': fc.get('wave_height') if fc else None,
            'wind': fc.get('wind_speed') if fc else None,
            'wave_dir': fc.get('wave_dir') if fc else None,
            'quality': fc.get('quality') if fc else None,
        })
    
    # Usa mapa GRATUITO (OpenStreetMap + Leaflet) por padrão
    return render_template('spots/map_free.html', spots=json.dumps(spots_data))

# UF -> região (Brasil). Usado para filtrar a previsão por região/estado.
UF_REGION = {
    'AC': 'Norte', 'AP': 'Norte', 'AM': 'Norte', 'PA': 'Norte', 'RO': 'Norte', 'RR': 'Norte', 'TO': 'Norte',
    'AL': 'Nordeste', 'BA': 'Nordeste', 'CE': 'Nordeste', 'MA': 'Nordeste', 'PB': 'Nordeste',
    'PE': 'Nordeste', 'PI': 'Nordeste', 'RN': 'Nordeste', 'SE': 'Nordeste',
    'DF': 'Centro-Oeste', 'GO': 'Centro-Oeste', 'MT': 'Centro-Oeste', 'MS': 'Centro-Oeste',
    'ES': 'Sudeste', 'MG': 'Sudeste', 'RJ': 'Sudeste', 'SP': 'Sudeste',
    'PR': 'Sul', 'RS': 'Sul', 'SC': 'Sul',
}
REGION_ORDER = ['Norte', 'Nordeste', 'Centro-Oeste', 'Sudeste', 'Sul']

# Nome do estado (BR) -> UF. Normaliza picos que gravaram "Paraná" em vez de "PR",
# pra não duplicar opções no filtro. Estados de fora do Brasil ficam como estão.
BR_STATE_UF = {
    'acre': 'AC', 'alagoas': 'AL', 'amapa': 'AP', 'amazonas': 'AM', 'bahia': 'BA',
    'ceara': 'CE', 'distrito federal': 'DF', 'espirito santo': 'ES', 'goias': 'GO',
    'maranhao': 'MA', 'mato grosso': 'MT', 'mato grosso do sul': 'MS', 'minas gerais': 'MG',
    'para': 'PA', 'paraiba': 'PB', 'parana': 'PR', 'pernambuco': 'PE', 'piaui': 'PI',
    'rio de janeiro': 'RJ', 'rio grande do norte': 'RN', 'rio grande do sul': 'RS',
    'rondonia': 'RO', 'roraima': 'RR', 'santa catarina': 'SC', 'sao paulo': 'SP',
    'sergipe': 'SE', 'tocantins': 'TO',
}


def _strip_accents(txt):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', txt)
                   if unicodedata.category(c) != 'Mn')


def fc_country(spot):
    """País do pico, normalizado (default Brasil)."""
    return (spot.country or 'Brasil').strip() or 'Brasil'


def fc_state(spot):
    """Estado do pico, normalizado: nome de estado BR vira UF; resto fica como está."""
    raw = (spot.state or '').strip()
    if not raw:
        return ''
    return BR_STATE_UF.get(_strip_accents(raw).lower(), raw)


SORT_OPTIONS = {'quality': 'Melhor qualidade', 'wave': 'Maior onda', 'name': 'Nome (A-Z)'}


def _fc_best_quality(fc):
    """Melhor qualidade prevista do pico (max entre os dias e a atual)."""
    if not fc:
        return -1
    days = fc.get('days') or []
    dq = max((d.get('quality') or 0 for d in days), default=0)
    cq = (fc.get('current') or {}).get('quality') or 0
    return max(dq, cq)


def _fc_best_wave(fc):
    if not fc:
        return -1
    days = fc.get('days') or []
    dw = max((d.get('wave_height') or 0 for d in days), default=0)
    cw = (fc.get('current') or {}).get('wave_height') or 0
    return max(dw, cw)


@spots.route('/forecast')
def forecast():
    """Previsão de surf (ondas + vento) dos picos aprovados, com filtro por
    região/estado/nome, ordenação e memória do último filtro (cookie). Filtra
    ANTES de buscar a previsão para não consultar a API de todos os picos."""
    from surf_forecast import get_forecast

    # Os filtros vêm SÓ da URL. Sem "memória" por cookie: abrir a Previsão sem
    # parâmetros sempre mostra TODOS os picos (evita um filtro antigo esconder picos).
    args = request.args
    country = (args.get('country') or '').strip()
    state = (args.get('state') or '').strip()
    q = (args.get('q') or '').strip()
    sort = (args.get('sort') or 'quality').strip()
    if sort not in SORT_OPTIONS:
        sort = 'quality'

    all_spots = Spot.query.filter_by(status='approved', is_active=True).order_by(Spot.name).all()
    total_count = len(all_spots)

    # Opções de filtro orientadas a dados: só aparece país/estado que TEM pico.
    countries = sorted({fc_country(s) for s in all_spots},
                       key=lambda c: (c != 'Brasil', c.lower()))  # Brasil primeiro
    pairs = sorted({(fc_state(s), fc_country(s)) for s in all_spots if fc_state(s)},
                   key=lambda t: t[0].lower())
    states_meta = [{'uf': st, 'country': co} for (st, co) in pairs]

    # Aplica os filtros em Python (estado normalizado, ignora maiúsc./acento no país)
    filtered = list(all_spots)
    if country:
        filtered = [s for s in filtered if fc_country(s).lower() == country.lower()]
    if state:
        filtered = [s for s in filtered if fc_state(s).lower() == state.lower()]
    if q:
        ql = q.lower()
        filtered = [s for s in filtered if ql in (s.name or '').lower()]

    forecasts = get_forecast(filtered)

    # Ordenação (a query já vem por nome; reordena por qualidade/onda quando pedido)
    if sort == 'wave':
        filtered.sort(key=lambda s: (-_fc_best_wave(forecasts.get(s.id)),
                                     -_fc_best_quality(forecasts.get(s.id)), s.name.lower()))
    elif sort == 'quality':
        filtered.sort(key=lambda s: (-_fc_best_quality(forecasts.get(s.id)),
                                     -_fc_best_wave(forecasts.get(s.id)), s.name.lower()))

    return render_template(
        'spots/forecast.html', spots=filtered, forecasts=forecasts,
        countries=countries, states_meta=states_meta, sort_options=SORT_OPTIONS,
        sel_country=country, sel_state=state, sel_q=q, sel_sort=sort,
        total_count=total_count)

@spots.route('/spots/add', methods=['GET', 'POST'])
@login_required
def add_spot():
    """Adiciona um novo spot (pendente de aprovação) - suporta HTML e JSON"""
    if request.method == 'POST':
        try:
            # Verifica se é requisição JSON (modo rápido) ou HTML form (formulário completo)
            if request.is_json:
                data = request.get_json()

                def _num(key):
                    v = data.get(key)
                    try:
                        return float(v) if v not in (None, '') else None
                    except (TypeError, ValueError):
                        return None

                spot = Spot(
                    name=data['name'],
                    description=data.get('description') or None,
                    latitude=float(data['latitude']),
                    longitude=float(data['longitude']),
                    address=data.get('address') or None,
                    city=data.get('city') or None,
                    state=data.get('state') or None,
                    country=data.get('country') or 'Brasil',
                    bottom_type=data.get('bottom_type') or None,
                    wave_type=data.get('wave_type') or 'Beach Break',
                    difficulty=data.get('difficulty') or 'Intermediário',
                    crowd_level=data.get('crowd_level') or None,
                    best_wind_direction=data.get('best_wind_direction') or None,
                    best_swell_direction=data.get('best_swell_direction') or None,
                    best_tide=data.get('best_tide') or None,
                    min_swell_size=_num('min_swell_size'),
                    max_swell_size=_num('max_swell_size'),
                    created_by=current_user.id,
                    status='pending',
                    is_active=True
                )

                db.session.add(spot)
                db.session.commit()

                Notification.notify_admins(
                    'spot_pending',
                    f'{current_user.username} sugeriu um novo pico: {spot.name}',
                    related_user_id=current_user.id, related_spot_id=spot.id)

                return jsonify({
                    'success': True,
                    'message': 'Spot adicionado com sucesso! Aguardando aprovação.',
                    'spot_id': spot.id
                })
            else:
                # Formulário HTML tradicional
                spot = Spot(
                    name=request.form['name'],
                    description=request.form.get('description'),
                    latitude=float(request.form['latitude']),
                    longitude=float(request.form['longitude']),
                    address=request.form.get('address'),
                    city=request.form.get('city'),
                    state=request.form.get('state'),
                    country=request.form.get('country', 'Brasil'),
                    bottom_type=request.form.get('bottom_type'),
                    wave_type=request.form.get('wave_type'),
                    difficulty=request.form.get('difficulty'),
                    crowd_level=request.form.get('crowd_level'),
                    best_wind_direction=request.form.get('best_wind_direction'),
                    best_swell_direction=request.form.get('best_swell_direction'),
                    best_tide=request.form.get('best_tide'),
                    min_swell_size=float(request.form['min_swell_size']) if request.form.get('min_swell_size') else None,
                    max_swell_size=float(request.form['max_swell_size']) if request.form.get('max_swell_size') else None,
                    created_by=current_user.id,
                    status='pending',
                    is_active=True
                )
                
                db.session.add(spot)
                db.session.commit()

                Notification.notify_admins(
                    'spot_pending',
                    f'{current_user.username} sugeriu um novo pico: {spot.name}',
                    related_user_id=current_user.id, related_spot_id=spot.id)

                flash('Spot adicionado com sucesso! Aguarde a aprovação do administrador.', 'success')
                return redirect(url_for('spots.spots_map'))
            
        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': f'Erro ao adicionar spot: {str(e)}'
                })
            else:
                flash(f'Erro ao adicionar spot: {str(e)}', 'error')
            
    return render_template('spots/add_spot.html')

@spots.route('/spots/<int:spot_id>/detail')
def new_spot_detail(spot_id):
    """Exibe detalhes de um spot específico (novo sistema)"""
    spot = Spot.query.get_or_404(spot_id)
    
    if spot.status != 'approved' and not (current_user.is_authenticated and current_user.is_admin):
        flash('Spot não encontrado ou ainda não aprovado.', 'error')
        return redirect(url_for('spots.spots_map'))
    
    photos = SpotPhotoNew.query.filter_by(spot_id=spot_id).all()
    sessions = PhotoSession.query.filter_by(spot_id=spot_id, is_active=True).all()
    businesses = Business.query.filter_by(spot_id=spot_id).all()

    # Fetch posts related to this spot instead of structured spot reports
    from models import Post
    recent_reports = Post.query.filter_by(spot_id=spot_id).order_by(Post.created_at.desc()).limit(15).all()

    # Mini-previsão do pico (cacheada por 1h)
    from surf_forecast import get_forecast
    forecast = get_forecast([spot]).get(spot.id)

    is_following = current_user.is_authenticated and current_user.is_following_spot(spot)
    followers_count = SpotFollow.query.filter_by(spot_id=spot_id).count()

    return render_template('spots/new_detail.html', spot=spot, photos=photos,
                           sessions=sessions, businesses=businesses, reports=recent_reports,
                           forecast=forecast, is_following=is_following,
                           followers_count=followers_count)


# Campos que um usuário comum pode sugerir para um pico (whitelist)
CONTRIB_FIELDS = ['wave_type', 'bottom_type', 'difficulty', 'crowd_level',
                  'best_wind_direction', 'best_swell_direction', 'best_tide', 'description']


@spots.route('/spots/<int:spot_id>/contribute', methods=['POST'])
@login_required
def contribute_spot(spot_id):
    """Usuário sugere informações para um pico. Entra na fila de moderação
    (status pending) e só é aplicado ao pico quando um admin aprovar."""
    spot = Spot.query.get_or_404(spot_id)
    data = {}
    for f in CONTRIB_FIELDS:
        v = (request.form.get(f) or '').strip()
        if v:
            data[f] = v[:600] if f == 'description' else v[:60]
    if not data:
        flash('Selecione ou preencha ao menos um campo para sugerir.', 'danger')
        return redirect(url_for('spots.new_spot_detail', spot_id=spot.id))
    note = (request.form.get('note') or '').strip()[:200]
    db.session.add(SpotContribution(
        spot_id=spot.id, user_id=current_user.id,
        data=json.dumps(data, ensure_ascii=False), note=note, status='pending'))
    db.session.commit()

    Notification.notify_admins(
        'spot_contribution',
        f'{current_user.username} sugeriu informações para o pico {spot.name}',
        related_user_id=current_user.id, related_spot_id=spot.id)

    return redirect(url_for('spots.new_spot_detail', spot_id=spot.id, contributed=1))


@spots.route('/spots/<int:spot_id>/follow', methods=['POST'])
@login_required
def follow_spot(spot_id):
    """Seguir um pico para receber alertas de swell (toggle via AJAX ou form)."""
    spot = Spot.query.get_or_404(spot_id)
    existing = SpotFollow.query.filter_by(user_id=current_user.id, spot_id=spot.id).first()
    if existing:
        db.session.delete(existing)
        following = False
    else:
        db.session.add(SpotFollow(user_id=current_user.id, spot_id=spot.id))
        following = True
    db.session.commit()
    count = SpotFollow.query.filter_by(spot_id=spot.id).count()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({'following': following, 'followers': count})
    flash('Você está seguindo este pico! Vai receber alertas de swell.' if following
          else 'Deixou de seguir o pico.', 'success' if following else 'info')
    return redirect(request.referrer or url_for('spots.new_spot_detail', spot_id=spot.id))


@spots.route('/meus-picos')
@login_required
def my_spots():
    """Picos seguidos com a previsão + alerta: destaca quais vão bombar nos
    próximos dias e ordena os 'bombando' primeiro."""
    from surf_forecast import get_forecast
    from swell_alerts import _best_upcoming, GOOD_QUALITY, HORIZON_DAYS

    follows = SpotFollow.query.filter_by(user_id=current_user.id).order_by(SpotFollow.created_at.desc()).all()
    spots_list = [f.spot for f in follows if f.spot and f.spot.is_active]
    forecast = get_forecast(spots_list) if spots_list else {}

    alerts = {}
    for sp in spots_list:
        best = _best_upcoming(forecast.get(sp.id), HORIZON_DAYS)
        if best:
            day, q = best
            alerts[sp.id] = {'label': day.get('label'), 'quality': q,
                             'wave': day.get('wave_height'), 'cond': day.get('cond'),
                             'firing': q >= GOOD_QUALITY}

    # Ordena: vão bombar primeiro, depois por melhor qualidade prevista, depois nome
    spots_list.sort(key=lambda s: (
        0 if alerts.get(s.id, {}).get('firing') else 1,
        -(alerts.get(s.id, {}).get('quality') or 0),
        s.name.lower(),
    ))
    firing_count = sum(1 for a in alerts.values() if a['firing'])

    return render_template('spots/my_spots.html', spots=spots_list, forecast=forecast,
                           alerts=alerts, firing_count=firing_count, good_quality=GOOD_QUALITY)


@spots.route('/cron/swell-alerts')
def cron_swell_alerts():
    """Dispara os alertas de swell. Protegido por ?key=CRON_KEY (env).

    Pensado para um cron externo (cron-job.org, GitHub Actions, Coolify
    scheduled task) bater 1-2x ao dia.
    """
    key = os.environ.get('CRON_KEY')
    if not key or request.args.get('key') != key:
        return jsonify({'error': 'forbidden'}), 403
    from swell_alerts import run_swell_alerts
    return jsonify(run_swell_alerts())


@spots.route('/spots/<int:spot_id>/sessions/new', methods=['POST'])
@login_required
def new_photo_session(spot_id):
    """Fotógrafo cria uma sessão de fotos à venda num pico."""
    if not current_user.has_role('fotografo'):
        flash('Apenas fotógrafos podem criar sessões de fotos.', 'danger')
        return redirect(url_for('spots.new_spot_detail', spot_id=spot_id))
    Spot.query.get_or_404(spot_id)
    title = request.form.get('title') or 'Sessão de fotos'
    date_str = request.form.get('session_date')
    try:
        session_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.utcnow().date()
    except ValueError:
        session_date = datetime.utcnow().date()
    try:
        price = float(request.form.get('price_per_photo') or 0)
    except ValueError:
        price = 0.0

    sess = PhotoSession(spot_id=spot_id, title=title, description=request.form.get('description'),
                        session_date=session_date, photographer_id=current_user.id, price_per_photo=price)
    db.session.add(sess)
    db.session.flush()

    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'sessions')
    os.makedirs(upload_path, exist_ok=True)
    count = 0
    for f in request.files.getlist('photos'):
        if f and f.filename:
            fn = f"sess_{sess.id}_{count}_{secure_filename(f.filename)}"
            f.save(os.path.join(upload_path, fn))
            db.session.add(SessionPhoto(session_id=sess.id, filename=fn, price=price))
            count += 1
    db.session.commit()
    flash(f'Sessão "{title}" criada com {count} foto(s)!', 'success')
    return redirect(url_for('spots.new_spot_detail', spot_id=spot_id))


@spots.route('/photos/<int:photo_id>/buy', methods=['POST'])
@login_required
def buy_photo(photo_id):
    """Reserva de foto (pagamento real será habilitado depois)."""
    photo = SessionPhoto.query.get_or_404(photo_id)
    existing = PhotoPurchase.query.filter_by(photo_id=photo_id, user_id=current_user.id).first()
    if not existing:
        db.session.add(PhotoPurchase(photo_id=photo_id, user_id=current_user.id,
                                     amount_paid=photo.price or 0, status='reserved'))
        db.session.commit()
    flash('Foto reservada! O pagamento online será habilitado em breve.', 'success')
    return redirect(request.referrer or url_for('spots.spots_map'))


@spots.route('/spots/<int:spot_id>/business/new', methods=['POST'])
@login_required
def new_business(spot_id):
    """Empresário cadastra um negócio dentro do pico."""
    if not current_user.has_role('empresario'):
        flash('Apenas o selo Negócio permite cadastrar empresas.', 'danger')
        return redirect(url_for('spots.new_spot_detail', spot_id=spot_id))
    Spot.query.get_or_404(spot_id)
    b = Business(owner_id=current_user.id, spot_id=spot_id,
                 name=request.form.get('name'), category=request.form.get('category'),
                 description=request.form.get('description'), phone=request.form.get('phone'),
                 instagram=request.form.get('instagram'), address=request.form.get('address'))
    db.session.add(b)
    db.session.commit()
    flash('Negócio cadastrado no pico!', 'success')
    return redirect(url_for('spots.new_spot_detail', spot_id=spot_id))


@spots.route('/business/<int:business_id>/coupon/new', methods=['POST'])
@login_required
def new_coupon(business_id):
    """Dono do negócio cria um cupom de desconto."""
    b = Business.query.get_or_404(business_id)
    if b.owner_id != current_user.id:
        flash('Você só pode adicionar cupons ao seu próprio negócio.', 'danger')
        return redirect(url_for('spots.new_spot_detail', spot_id=b.spot_id))
    vu = request.form.get('valid_until')
    try:
        valid = datetime.strptime(vu, '%Y-%m-%d').date() if vu else None
    except ValueError:
        valid = None
    db.session.add(Coupon(business_id=business_id, code=request.form.get('code'),
                          description=request.form.get('description'),
                          discount=request.form.get('discount'), valid_until=valid))
    db.session.commit()
    flash('Cupom criado!', 'success')
    return redirect(url_for('spots.new_spot_detail', spot_id=b.spot_id))

@spots.route('/spots/<int:spot_id>/report', methods=['GET', 'POST'])
@login_required
def add_report(spot_id):
    """Adiciona relatório de condições do spot"""
    spot = Spot.query.get_or_404(spot_id)
    
    if request.method == 'POST':
        try:
            report = SpotReport(
                spot_id=spot_id,
                user_id=current_user.id,
                wave_height=float(request.form['wave_height']) if request.form.get('wave_height') else None,
                wind_direction=request.form.get('wind_direction'),
                wind_speed=float(request.form['wind_speed']) if request.form.get('wind_speed') else None,
                conditions=request.form['conditions'],
                crowd_level=request.form.get('crowd_level'),
                water_temp=float(request.form['water_temp']) if request.form.get('water_temp') else None,
                notes=request.form.get('notes')
            )
            
            db.session.add(report)
            db.session.commit()
            
            flash('Relatório adicionado com sucesso!', 'success')
            return redirect(url_for('spots.new_spot_detail', spot_id=spot_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao adicionar relatório: {str(e)}', 'error')
    
    return render_template('spots/add_report.html', spot=spot)

@spots.route('/spots/<int:spot_id>/photos', methods=['GET', 'POST'])
@login_required
def spot_photos(spot_id):
    """Gerencia fotos do spot"""
    spot = Spot.query.get_or_404(spot_id)
    
    if request.method == 'POST':
        if 'photo' not in request.files:
            flash('Nenhuma foto selecionada', 'error')
            return redirect(request.url)
        
        file = request.files['photo']
        if file.filename == '':
            flash('Nenhuma foto selecionada', 'error')
            return redirect(request.url)
        
        if file:
            try:
                filename = secure_filename(file.filename)
                # Cria um nome único para o arquivo
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"spot_{spot_id}_{timestamp}_{filename}"
                
                # Cria a pasta se não existir
                upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'spots')
                os.makedirs(upload_path, exist_ok=True)
                
                # Salva o arquivo
                file_path = os.path.join(upload_path, filename)
                file.save(file_path)
                
                # Cria o registro no banco
                photo = SpotPhotoNew(
                    spot_id=spot_id,
                    filename=filename,
                    title=request.form.get('title'),
                    description=request.form.get('description'),
                    uploaded_by=current_user.id
                )
                
                db.session.add(photo)
                db.session.commit()
                
                flash('Foto adicionada com sucesso!', 'success')
                return redirect(url_for('spots.new_spot_detail', spot_id=spot_id))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao adicionar foto: {str(e)}', 'error')
    
    # As fotos são exibidas/enviadas pela página de detalhe do spot (aba Fotos + modal)
    return redirect(url_for('spots.new_spot_detail', spot_id=spot_id))

@spots.route('/api/spots/search')
def search_spots():
    """API para buscar spots por nome ou localização"""
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    
    spots_found = Spot.query.filter(
        Spot.status == 'approved',
        Spot.is_active == True,
        db.or_(
            Spot.name.contains(query),
            Spot.city.contains(query),
            Spot.state.contains(query)
        )
    ).limit(10).all()
    
    results = []
    for spot in spots_found:
        results.append({
            'id': spot.id,
            'name': spot.name,
            'city': spot.city,
            'state': spot.state,
            'lat': spot.latitude,
            'lng': spot.longitude
        })
    
    return jsonify(results)