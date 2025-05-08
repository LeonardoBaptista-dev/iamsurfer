from app import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    profile_image = db.Column(db.String(255), default='uploads/default_profile.jpg')
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

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
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
            return f"{self.destination.name}, {self.destination.location}"
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