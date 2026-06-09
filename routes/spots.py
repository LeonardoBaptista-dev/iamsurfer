from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from models import State, City, SurfSpot, Photographer, SpotPhoto, Spot, SpotPhotoNew, PhotoSession, SessionPhoto, PhotoPurchase, SpotReport, Business, Coupon
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
    
    for spot in approved_spots:
        cover_photo = SpotPhotoNew.query.filter_by(spot_id=spot.id, is_cover=True).first()
        
        # Buscar a última interação (relato/post mais recente desse pico)
        last_post = Post.query.filter_by(spot_id=spot.id).order_by(Post.created_at.desc()).first()
        last_interaction = last_post.created_at.isoformat() if last_post else "2000-01-01T00:00:00"

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
            'wave_type': spot.wave_type
        })
    
    # Usa mapa GRATUITO (OpenStreetMap + Leaflet) por padrão
    return render_template('spots/map_free.html', spots=json.dumps(spots_data))

@spots.route('/forecast')
def forecast():
    """Previsão de surf (ondas + vento) de todos os picos aprovados."""
    from surf_forecast import get_forecast
    approved = Spot.query.filter_by(status='approved', is_active=True).order_by(Spot.name).all()
    forecasts = get_forecast(approved)
    return render_template('spots/forecast.html', spots=approved, forecasts=forecasts)

@spots.route('/spots/add', methods=['GET', 'POST'])
@login_required
def add_spot():
    """Adiciona um novo spot (pendente de aprovação) - suporta HTML e JSON"""
    if request.method == 'POST':
        try:
            # Verifica se é requisição JSON (modo rápido) ou HTML form (formulário completo)
            if request.is_json:
                data = request.get_json()
                spot = Spot(
                    name=data['name'],
                    description=data.get('description'),
                    latitude=float(data['latitude']),
                    longitude=float(data['longitude']),
                    difficulty=data.get('difficulty', 'Intermediário'),
                    wave_type=data.get('wave_type', 'Beach Break'),
                    created_by=current_user.id,
                    status='pending',
                    is_active=True
                )
                
                db.session.add(spot)
                db.session.commit()
                
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

    return render_template('spots/new_detail.html', spot=spot, photos=photos,
                           sessions=sessions, businesses=businesses, reports=recent_reports)


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