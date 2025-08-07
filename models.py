from app import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    profile_image = db.Column(db.String(255), default='uploads/default_profile.jpg')  # Mantido para compatibilidade
    profile_image_urls = db.Column(db.JSON, nullable=True)  # Novas URLs múltiplas para perfil
    profile_image_hash = db.Column(db.String(32), nullable=True)  # Hash para deduplicação
    bio = db.Column(db.Text)
    location = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    posts = db.relationship('Post', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    likes = db.relationship('Like', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    # Relacionamentos para mensagens enviadas/recebidas
    messages_sent = db.relationship('Message', 
                                   foreign_keys='Message.sender_id', 
                                   backref='sender', 
                                   lazy='dynamic',
                                   cascade='all, delete-orphan')
    messages_received = db.relationship('Message', 
                                       foreign_keys='Message.recipient_id', 
                                       backref='recipient', 
                                       lazy='dynamic')
    
    # Relacionamentos para seguidores/seguindo
    followed = db.relationship(
        'Follow',
        foreign_keys='Follow.follower_id',
        backref=db.backref('follower', lazy='joined'),
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    
    following = db.relationship(
        'Follow',
        foreign_keys='Follow.followed_id',
        backref=db.backref('followed', lazy='joined'),
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def follow(self, user):
        if not self.is_following(user):
            follow = Follow(follower_id=self.id, followed_id=user.id)
            db.session.add(follow)
    
    def unfollow(self, user):
        follow = self.followed.filter_by(followed_id=user.id).first()
        if follow:
            db.session.delete(follow)
    
    def is_following(self, user):
        return self.followed.filter_by(followed_id=user.id).first() is not None
    
    @property
    def followers(self):
        return Follow.query.filter_by(followed_id=self.id)
    
    def has_liked_post(self, post):
        """Verifica se o usuário já curtiu um post específico"""
        return Like.query.filter(
            Like.user_id == self.id,
            Like.post_id == post.id
        ).first() is not None

    @property
    def has_multiple_profile_images(self):
        """Verifica se o usuário tem o novo sistema de múltiplas imagens de perfil"""
        return self.profile_image_urls is not None and isinstance(self.profile_image_urls, dict)
    
    @property
    def display_profile_image_url(self):
        """Retorna a URL de imagem de perfil para exibição (compatibilidade)"""
        if self.has_multiple_profile_images:
            # Retorna a versão small como padrão para perfil
            return self.profile_image_urls.get('small', self.profile_image_urls.get('thumbnail', ''))
        return self.profile_image or 'uploads/default_profile.jpg'
    
    @property
    def profile_thumbnail_url(self):
        """Retorna URL do thumbnail de perfil"""
        if self.has_multiple_profile_images:
            return self.profile_image_urls.get('thumbnail', self.profile_image_urls.get('small', ''))
        return self.profile_image or 'uploads/default_profile.jpg'
    
    @property
    def profile_avatar_url(self):
        """Retorna URL apropriada para avatar (pequeno)"""
        if self.has_multiple_profile_images:
            return self.profile_image_urls.get('small', self.profile_image_urls.get('thumbnail', ''))
        return self.profile_image or 'uploads/default_profile.jpg'
    
    @property
    def profile_large_url(self):
        """Retorna URL da imagem de perfil grande para visualização completa"""
        if self.has_multiple_profile_images:
            return self.profile_image_urls.get('medium', self.profile_image_urls.get('small', ''))
        return self.profile_image or 'uploads/default_profile.jpg'
    
    @property
    def unread_notifications_count(self):
        """Retorna o número de notificações não lidas"""
        return self.notifications.filter_by(read=False).count()
    
    @property
    def unread_messages_count(self):
        """Retorna o número de mensagens não lidas"""
        return self.messages_received.filter_by(read=False).count()
    
    def get_recent_notifications(self, limit=10):
        """Retorna as notificações mais recentes"""
        return self.notifications.order_by(Notification.created_at.desc()).limit(limit).all()

    def get_conversations(self):
        """Retorna lista de conversas únicas com outros usuários"""
        from sqlalchemy import or_, and_, func
        
        # Query para buscar conversas únicas
        subquery = db.session.query(
            func.greatest(Message.sender_id, Message.recipient_id).label('user1'),
            func.least(Message.sender_id, Message.recipient_id).label('user2'),
            func.max(Message.timestamp).label('last_message_time')
        ).filter(
            or_(Message.sender_id == self.id, Message.recipient_id == self.id)
        ).group_by(
            func.greatest(Message.sender_id, Message.recipient_id),
            func.least(Message.sender_id, Message.recipient_id)
        ).subquery()
        
        # Busca as últimas mensagens de cada conversa
        conversations = db.session.query(Message).join(
            subquery,
            and_(
                Message.timestamp == subquery.c.last_message_time,
                or_(
                    and_(Message.sender_id == subquery.c.user1, Message.recipient_id == subquery.c.user2),
                    and_(Message.sender_id == subquery.c.user2, Message.recipient_id == subquery.c.user1)
                )
            )
        ).order_by(Message.timestamp.desc()).all()
        
        return conversations

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255), nullable=True)  # Mantido para compatibilidade
    image_urls = db.Column(db.JSON, nullable=True)  # Novas URLs múltiplas
    image_hash = db.Column(db.String(32), nullable=True)  # Hash para deduplicação
    video_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=True, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relacionamentos
    comments = db.relationship('Comment', backref='post', lazy=True, cascade="all, delete-orphan")
    likes = db.relationship('Like', backref='post', lazy=True, cascade="all, delete-orphan")

    @property
    def date_posted(self):
        return self.created_at
    
    @property
    def has_multiple_images(self):
        """Verifica se o post tem o novo sistema de múltiplas imagens"""
        return self.image_urls is not None and isinstance(self.image_urls, dict)
    
    @property
    def display_image_url(self):
        """Retorna a URL de imagem para exibição (compatibilidade)"""
        if self.has_multiple_images:
            # Retorna a versão medium como padrão
            return self.image_urls.get('medium', self.image_urls.get('small', ''))
        return self.image_url
    
    @property
    def thumbnail_url(self):
        """Retorna URL do thumbnail"""
        if self.has_multiple_images:
            return self.image_urls.get('thumbnail', self.image_urls.get('small', ''))
        return self.image_url
    
    @property
    def feed_image_url(self):
        """Retorna URL apropriada para feed"""
        if self.has_multiple_images:
            return self.image_urls.get('medium', self.image_urls.get('small', ''))
        return self.image_url
    
    @property
    def large_image_url(self):
        """Retorna URL da imagem grande para visualização completa"""
        if self.has_multiple_images:
            return self.image_urls.get('large', self.image_urls.get('original', self.image_urls.get('medium', '')))
        return self.image_url

    def __repr__(self):
        return f"Post('{self.content[:20]}...', '{self.created_at}')"

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    
    def __repr__(self):
        return f'<Comment {self.id} by {self.author.username}>'

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Garantir que um usuário só pode curtir um post uma vez
    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='_user_post_like_uc'),)
    
    def __repr__(self):
        return f'<Like {self.id} by {self.user.username} on Post {self.post_id}>'
    
    @classmethod
    def count(cls, count=None):
        """Método para contar likes que aceita um parâmetro opcional para compatibilidade"""
        # O parâmetro count é ignorado, mantido apenas para compatibilidade com chamadas existentes
        return cls.query.count()

class Follow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Garantir que um usuário só pode seguir outro usuário uma vez
    __table_args__ = (db.UniqueConstraint('follower_id', 'followed_id', name='_follower_followed_uc'),)
    
    def __repr__(self):
        return f'<Follow {self.follower.username} -> {self.followed.username}>'

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<Message {self.id} from {self.sender.username} to {self.recipient.username}>' 
    
class SurfSpot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'), nullable=True)
    wave_type = db.Column(db.String(50), nullable=True)
    difficulty_level = db.Column(db.String(50), nullable=True)
    
    # Relacionamentos
    city = db.relationship('City', backref='surf_spots', lazy=True)
    photos = db.relationship('SpotPhoto', backref='spot', lazy=True)
    
    def __repr__(self):
        return f'<SurfSpot {self.name}>'

# Modelo para SurfTrip em models.py

class SurfTrip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    
    # Informações do criador da viagem
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    creator = db.relationship('User', foreign_keys=[creator_id], backref='created_trips')
    
    # Informações de origem e destino
    departure_location = db.Column(db.String(100), nullable=False)
    
    # Manter o relacionamento existente
    destination_id = db.Column(db.Integer, db.ForeignKey('surf_spot.id'), nullable=False)
    destination = db.relationship('SurfSpot', backref='trips')
    
    # Adicionar o campo de texto para destino livre
    destination_text = db.Column(db.String(100), nullable=True)
    
    # Informações de horários
    departure_time = db.Column(db.DateTime, nullable=False)
    return_time = db.Column(db.DateTime, nullable=True)
    
    # Informações adicionais
    description = db.Column(db.Text, nullable=True)
    available_seats = db.Column(db.Integer, nullable=False, default=3)
    contribution = db.Column(db.Float, nullable=True)  # Valor sugerido para contribuição
    vehicle_info = db.Column(db.String(100), nullable=True)
    intermediate_stops = db.Column(db.Text, nullable=True)  # Paradas intermediárias (opcional)
    
    # Status da viagem
    TRIP_STATUS = ['Scheduled', 'Ongoing', 'Completed', 'Cancelled']
    status = db.Column(db.String(20), nullable=False, default='Scheduled')
    
    # Data de criação e atualização
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # Relacionamentos
    participants = db.relationship('TripParticipant', backref='trip', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<SurfTrip {self.title} to {self.destination}>'
    
    def get_available_seats(self):
        """Retorna o número de assentos ainda disponíveis"""
        booked_seats = TripParticipant.query.filter_by(
            trip_id=self.id, 
            status='Confirmed'
        ).count()
        return self.available_seats - booked_seats

    def get_destination_display(self):
        """Retorna o texto do destino para exibição"""
        if hasattr(self, 'destination_text') and self.destination_text:
            return self.destination_text
        elif self.destination:
            return f"{self.destination.name}, {self.destination.city.name}"
        else:
            return "Destino não especificado"

class TripParticipant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('surf_trip.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='trip_participations')
    
    # Status da participação
    PARTICIPANT_STATUS = ['Pending', 'Confirmed', 'Cancelled', 'Rejected']
    status = db.Column(db.String(20), nullable=False, default='Pending')
    
    # Data de solicitação e confirmação
    request_time = db.Column(db.DateTime, default=datetime.utcnow)
    confirmation_time = db.Column(db.DateTime)
    
    # Mensagem opcional do participante
    message = db.Column(db.Text)
    
    __table_args__ = (db.UniqueConstraint('trip_id', 'user_id', name='_trip_user_uc'),)
    
    def __repr__(self):
        return f'<TripParticipant {self.user.username} on trip {self.trip_id}>'

class State(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    uf = db.Column(db.String(2), nullable=False, unique=True)
    cities = db.relationship('City', backref='state', lazy=True)

    def __repr__(self):
        return f'<State {self.name}>'

class City(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    state_id = db.Column(db.Integer, db.ForeignKey('state.id'), nullable=False)
    
    # O relacionamento já está definido no SurfSpot como backref
    # surf_spots = db.relationship('SurfSpot', backref='city', lazy=True)
    
    def __repr__(self):
        return f'<City {self.name}>'

class Photographer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    spot_id = db.Column(db.Integer, db.ForeignKey('surf_spot.id'), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    subscription_status = db.Column(db.String(20), default='free')
    photos = db.relationship('SpotPhoto', backref='photographer', lazy=True)

    def __repr__(self):
        return f'<Photographer {self.id}>'

class SpotPhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spot_id = db.Column(db.Integer, db.ForeignKey('surf_spot.id'), nullable=False)
    photographer_id = db.Column(db.Integer, db.ForeignKey('photographer.id'), nullable=False)
    image_url = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=True)
    is_for_sale = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<SpotPhoto {self.id}>'

class Spot(db.Model):
    """Modelo para spots de surf colaborativo"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    address = db.Column(db.String(200))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100), default='Brasil')
    
    # Características do spot
    bottom_type = db.Column(db.String(50))  # pedra, areia, coral, etc.
    wave_type = db.Column(db.String(50))    # point break, beach break, reef break
    difficulty = db.Column(db.String(20))   # iniciante, intermediário, avançado
    crowd_level = db.Column(db.String(20))  # baixo, médio, alto
    
    # Condições ideais
    best_wind_direction = db.Column(db.String(20))
    best_swell_direction = db.Column(db.String(20))
    best_tide = db.Column(db.String(20))    # baixa, média, alta, todas
    min_swell_size = db.Column(db.Float)
    max_swell_size = db.Column(db.Float)
    
    # Status e moderação
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    is_active = db.Column(db.Boolean, default=True)
    
    # Relacionamentos
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    approved_at = db.Column(db.DateTime)
    rejected_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    rejected_at = db.Column(db.DateTime)
    
    # Relacionamentos
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_spots')
    approver = db.relationship('User', foreign_keys=[approved_by])
    rejecter = db.relationship('User', foreign_keys=[rejected_by])
    spot_photos = db.relationship('SpotPhotoNew', backref='spot', lazy='dynamic', cascade='all, delete-orphan')
    photo_sessions = db.relationship('PhotoSession', backref='spot', lazy='dynamic', cascade='all, delete-orphan')
    spot_reports = db.relationship('SpotReport', backref='spot', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Spot {self.name}>'

class SpotPhotoNew(db.Model):
    """Modelo para fotos dos spots colaborativos"""
    __tablename__ = 'spot_photo_new'
    
    id = db.Column(db.Integer, primary_key=True)
    spot_id = db.Column(db.Integer, db.ForeignKey('spot.id'), nullable=False)
    filename = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(100))
    description = db.Column(db.Text)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_cover = db.Column(db.Boolean, default=False)
    
    uploader = db.relationship('User', backref='spot_photos_new')

    def __repr__(self):
        return f'<SpotPhotoNew {self.filename}>'

class PhotoSession(db.Model):
    """Modelo para sessões de fotos nos spots"""
    id = db.Column(db.Integer, primary_key=True)
    spot_id = db.Column(db.Integer, db.ForeignKey('spot.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    session_date = db.Column(db.Date, nullable=False)
    photographer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    price_per_photo = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    photographer = db.relationship('User', backref='photo_sessions')
    session_photos = db.relationship('SessionPhoto', backref='session', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<PhotoSession {self.title}>'

class SessionPhoto(db.Model):
    """Modelo para fotos de sessões específicas"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('photo_session.id'), nullable=False)
    filename = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(100))
    price = db.Column(db.Float, default=0.0)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    purchases = db.relationship('PhotoPurchase', backref='photo', lazy='dynamic')

    def __repr__(self):
        return f'<SessionPhoto {self.filename}>'

class PhotoPurchase(db.Model):
    """Modelo para compras de fotos"""
    id = db.Column(db.Integer, primary_key=True)
    photo_id = db.Column(db.Integer, db.ForeignKey('session_photo.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)
    amount_paid = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='completed')  # pending, completed, refunded
    
    user = db.relationship('User', backref='photo_purchases')

    def __repr__(self):
        return f'<PhotoPurchase {self.id}>'

class SpotReport(db.Model):
    """Modelo para relatórios de condições dos spots"""
    id = db.Column(db.Integer, primary_key=True)
    spot_id = db.Column(db.Integer, db.ForeignKey('spot.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    wave_height = db.Column(db.Float)
    wind_direction = db.Column(db.String(20))
    wind_speed = db.Column(db.Float)
    conditions = db.Column(db.String(50))  # flat, poor, fair, good, epic
    crowd_level = db.Column(db.String(20))
    water_temp = db.Column(db.Float)
    notes = db.Column(db.Text)
    report_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='spot_reports')

    def __repr__(self):
        return f'<SpotReport {self.id}>'

class Notification(db.Model):
    """Sistema de notificações para atividades sociais"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Quem recebe a notificação
    type = db.Column(db.String(50), nullable=False)  # follow, like, comment, message, follow_request
    content = db.Column(db.Text, nullable=False)  # Texto da notificação
    related_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Usuário que gerou a notificação
    related_post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=True)  # Post relacionado (se for like/comment)
    related_message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=True)  # Mensagem relacionada
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    user = db.relationship('User', foreign_keys=[user_id], backref='notifications')
    related_user = db.relationship('User', foreign_keys=[related_user_id])
    related_post = db.relationship('Post', foreign_keys=[related_post_id])
    related_message = db.relationship('Message', foreign_keys=[related_message_id])

    def __repr__(self):
        return f'<Notification {self.id}: {self.type} for {self.user.username}>'
    
    def mark_as_read(self):
        """Marca a notificação como lida"""
        self.read = True
        db.session.commit()
    
    @classmethod
    def create_follow_notification(cls, follower, followed):
        """Cria notificação de novo seguidor"""
        notification = cls(
            user_id=followed.id,
            type='follow',
            content=f'{follower.username} começou a te seguir',
            related_user_id=follower.id
        )
        db.session.add(notification)
        db.session.commit()
        return notification
    
    @classmethod
    def create_like_notification(cls, user, post):
        """Cria notificação de like em post"""
        if user.id != post.user_id:  # Não notifica se curtiu próprio post
            notification = cls(
                user_id=post.user_id,
                type='like',
                content=f'{user.username} curtiu seu post',
                related_user_id=user.id,
                related_post_id=post.id
            )
            db.session.add(notification)
            db.session.commit()
            return notification
    
    @classmethod
    def create_comment_notification(cls, user, post, comment_content):
        """Cria notificação de comentário em post"""
        if user.id != post.user_id:  # Não notifica se comentou próprio post
            notification = cls(
                user_id=post.user_id,
                type='comment',
                content=f'{user.username} comentou em seu post: "{comment_content[:50]}..."',
                related_user_id=user.id,
                related_post_id=post.id
            )
            db.session.add(notification)
            db.session.commit()
            return notification
    
    @classmethod
    def create_message_notification(cls, sender, recipient, message):
        """Cria notificação de nova mensagem"""
        notification = cls(
            user_id=recipient.id,
            type='message',
            content=f'Nova mensagem de {sender.username}',
            related_user_id=sender.id,
            related_message_id=message.id
        )
        db.session.add(notification)
        db.session.commit()
        return notification