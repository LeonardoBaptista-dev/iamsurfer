from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from models import User, SurfSpot, SurfTrip, TripParticipant
from app import db
from datetime import datetime
from sqlalchemy import desc
from wtforms import StringField, TextAreaField, DateTimeField, IntegerField, FloatField, SelectField
from wtforms.validators import DataRequired, Optional, NumberRange
from flask_wtf import FlaskForm

trips = Blueprint('trips', __name__)

class SurfTripForm(FlaskForm):
    title = StringField('Título', validators=[DataRequired()])
    departure_location = StringField('Local de Partida', validators=[DataRequired()])
    destination_id = SelectField('Destino (Praia)', coerce=int, validators=[DataRequired()])
    departure_time = DateTimeField('Hora de Saída', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    return_time = DateTimeField('Hora de Retorno (opcional)', format='%Y-%m-%dT%H:%M', validators=[Optional()])
    description = TextAreaField('Descrição', validators=[Optional()])
    available_seats = IntegerField('Lugares Disponíveis', validators=[DataRequired(), NumberRange(min=1, max=10)])
    contribution = FloatField('Contribuição Sugerida (R$)', validators=[Optional()])
    vehicle_info = StringField('Informações do Veículo', validators=[Optional()])
    intermediate_stops = TextAreaField('Paradas Intermediárias', validators=[Optional()])

@trips.route('/trips')
def list_trips():
    # Lista todas as viagens futuras
    today = datetime.utcnow()
    upcoming_trips = SurfTrip.query.filter(
        SurfTrip.departure_time > today,
        SurfTrip.status == 'Scheduled'
    ).order_by(SurfTrip.departure_time).all()
    
    return render_template('trips/list.html', trips=upcoming_trips)

@trips.route('/trips/create', methods=['GET', 'POST'])
@login_required
def create_trip():
    form = SurfTripForm()
    
    # Carrega os destinos para o select field
    form.destination_id.choices = [(spot.id, f"{spot.name} - {spot.location}") 
                                   for spot in SurfSpot.query.order_by(SurfSpot.name).all()]
    
    if form.validate_on_submit():
        trip = SurfTrip(
            title=form.title.data,
            creator_id=current_user.id,
            departure_location=form.departure_location.data,
            destination_id=form.destination_id.data,
            departure_time=form.departure_time.data,
            return_time=form.return_time.data,
            description=form.description.data,
            available_seats=form.available_seats.data,
            contribution=form.contribution.data,
            vehicle_info=form.vehicle_info.data,
            intermediate_stops=form.intermediate_stops.data
        )
        
        db.session.add(trip)
        db.session.commit()
        
        flash('Sua viagem de surf foi criada com sucesso!', 'success')
        return redirect(url_for('trips.view_trip', trip_id=trip.id))
    
    return render_template('trips/create.html', form=form)

@trips.route('/trips/<int:trip_id>')
def view_trip(trip_id):
    trip = SurfTrip.query.get_or_404(trip_id)
    
    # Verifica se o usuário atual é participante
    is_participant = False
    if current_user.is_authenticated:
        is_participant = TripParticipant.query.filter_by(
            trip_id=trip.id, 
            user_id=current_user.id,
            status='Confirmed'
        ).first() is not None
    
    # Recupera lista de participantes confirmados
    confirmed_participants = TripParticipant.query.filter_by(
        trip_id=trip.id, 
        status='Confirmed'
    ).all()
    
    return render_template('trips/view.html', 
                          trip=trip, 
                          is_participant=is_participant,
                          confirmed_participants=confirmed_participants)

@trips.route('/trips/<int:trip_id>/join', methods=['GET', 'POST'])
@login_required
def join_trip(trip_id):
    trip = SurfTrip.query.get_or_404(trip_id)
    
    # Verifica se a viagem ainda tem vagas
    if trip.get_available_seats() <= 0:
        flash('Esta viagem não tem mais vagas disponíveis!', 'danger')
        return redirect(url_for('trips.view_trip', trip_id=trip.id))
    
    # Verifica se o usuário já é participante
    existing_participant = TripParticipant.query.filter_by(
        trip_id=trip.id, 
        user_id=current_user.id
    ).first()
    
    if existing_participant:
        if existing_participant.status == 'Confirmed':
            flash('Você já está confirmado nesta viagem!', 'info')
        elif existing_participant.status == 'Pending':
            flash('Sua solicitação está pendente de aprovação!', 'info')
        else:
            flash('Você não pode participar desta viagem!', 'danger')
        return redirect(url_for('trips.view_trip', trip_id=trip.id))
    
    # Se o criador da viagem for o próprio usuário, adiciona diretamente como confirmado
    if trip.creator_id == current_user.id:
        flash('Você é o criador desta viagem!', 'info')
        return redirect(url_for('trips.view_trip', trip_id=trip.id))
    
    if request.method == 'POST':
        message = request.form.get('message', '')
        
        participant = TripParticipant(
            trip_id=trip.id,
            user_id=current_user.id,
            message=message,
            status='Pending'  # Aguarda confirmação do criador
        )
        
        db.session.add(participant)
        db.session.commit()
        
        flash('Sua solicitação foi enviada e aguarda aprovação do organizador!', 'success')
        return redirect(url_for('trips.view_trip', trip_id=trip.id))
    
    return render_template('trips/join.html', trip=trip)

@trips.route('/trips/<int:trip_id>/manage_participants')
@login_required
def manage_participants(trip_id):
    trip = SurfTrip.query.get_or_404(trip_id)
    
    # Apenas o criador pode gerenciar participantes
    if trip.creator_id != current_user.id:
        abort(403)
    
    pending_requests = TripParticipant.query.filter_by(
        trip_id=trip.id, 
        status='Pending'
    ).all()
    
    confirmed_participants = TripParticipant.query.filter_by(
        trip_id=trip.id, 
        status='Confirmed'
    ).all()
    
    return render_template('trips/manage_participants.html', 
                          trip=trip, 
                          pending_requests=pending_requests,
                          confirmed_participants=confirmed_participants)

@trips.route('/trips/participant/<int:participant_id>/action/<action>', methods=['POST'])
@login_required
def participant_action(participant_id, action):
    participant = TripParticipant.query.get_or_404(participant_id)
    trip = SurfTrip.query.get_or_404(participant.trip_id)
    
    # Apenas o criador pode realizar ações nos participantes
    if trip.creator_id != current_user.id:
        abort(403)
    
    if action == 'approve':
        # Verificar se ainda há vagas
        if trip.get_available_seats() <= 0:
            flash('Não há mais vagas disponíveis nesta viagem!', 'danger')
            return redirect(url_for('trips.manage_participants', trip_id=trip.id))
        
        participant.status = 'Confirmed'
        participant.confirmation_time = datetime.utcnow()
        db.session.commit()
        flash(f'Participação de {participant.user.username} aprovada com sucesso!', 'success')
    
    elif action == 'reject':
        participant.status = 'Rejected'
        db.session.commit()
        flash(f'Participação de {participant.user.username} rejeitada.', 'info')
    
    else:
        flash('Ação inválida!', 'danger')
    
    return redirect(url_for('trips.manage_participants', trip_id=trip.id))

@trips.route('/trips/<int:trip_id>/cancel', methods=['GET', 'POST'])
@login_required
def cancel_trip(trip_id):
    trip = SurfTrip.query.get_or_404(trip_id)
    
    # Apenas o criador pode cancelar a viagem
    if trip.creator_id != current_user.id:
        abort(403)
    
    if request.method == 'POST':
        trip.status = 'Cancelled'
        db.session.commit()
        
        flash('Sua viagem foi cancelada com sucesso!', 'info')
        return redirect(url_for('trips.my_trips'))
    
    return render_template('trips/cancel.html', trip=trip)

@trips.route('/trips/my-trips')
@login_required
def my_trips():
    created_trips = SurfTrip.query.filter_by(creator_id=current_user.id).order_by(desc(SurfTrip.departure_time)).all()
    
    participating_trips = SurfTrip.query.join(TripParticipant).filter(
        TripParticipant.user_id == current_user.id,
        TripParticipant.status == 'Confirmed'
    ).order_by(desc(SurfTrip.departure_time)).all()
    
    pending_trips = SurfTrip.query.join(TripParticipant).filter(
        TripParticipant.user_id == current_user.id,
        TripParticipant.status == 'Pending'
    ).order_by(desc(SurfTrip.departure_time)).all()
    
    return render_template('trips/my_trips.html', 
                          created_trips=created_trips,
                          participating_trips=participating_trips,
                          pending_trips=pending_trips)