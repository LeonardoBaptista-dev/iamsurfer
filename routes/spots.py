from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from models import State, City, SurfSpot, Photographer, SpotPhoto, Spot, SpotPhotoNew, PhotoSession, SessionPhoto, PhotoPurchase, SpotReport
from app import db
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
    approved_spots = Spot.query.filter_by(status='approved', is_active=True).all()
    spots_data = []
    
    for spot in approved_spots:
        cover_photo = SpotPhotoNew.query.filter_by(spot_id=spot.id, is_cover=True).first()
        spots_data.append({
            'id': spot.id,
            'name': spot.name,
            'lat': spot.latitude,
            'lng': spot.longitude,
            'description': spot.description[:100] + '...' if spot.description and len(spot.description) > 100 else spot.description,
            'cover_photo': cover_photo.filename if cover_photo else None,
            'difficulty': spot.difficulty,
            'wave_type': spot.wave_type
        })
    
    # Usa mapa GRATUITO (OpenStreetMap + Leaflet) por padrão
    return render_template('spots/map_free.html', spots=json.dumps(spots_data))

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
    recent_reports = SpotReport.query.filter_by(spot_id=spot_id).order_by(SpotReport.report_date.desc()).limit(5).all()
    
    return render_template('spots/new_detail.html', spot=spot, photos=photos, sessions=sessions, reports=recent_reports)

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
    
    photos = SpotPhotoNew.query.filter_by(spot_id=spot_id).all()
    return render_template('spots/photos.html', spot=spot, photos=photos)

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