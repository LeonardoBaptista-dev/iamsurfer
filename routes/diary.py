"""Diário de surfe: registro pessoal de sessões de surf.

Cada usuário anota suas sessões (data, pico, condições, prancha, nota e
observações), com foto opcional. Lista própria com estatísticas + diário
público de qualquer usuário.
"""
import os
import hashlib
from datetime import datetime

from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, abort)
from flask_login import login_required, current_user

from extensions import db
from models import SurfSession, Spot, User

diary = Blueprint('diary', __name__)


def get_image_processor():
    """Retorna o processador de imagem apropriado (local em dev, cloud em prod)."""
    use_local = os.environ.get('FLASK_ENV') != 'production'
    if use_local:
        from local_image_processor import LocalImageProcessor
        return LocalImageProcessor
    from image_processor import ImageProcessor
    return ImageProcessor


def _allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}


def _save_photo(file):
    """Processa e salva uma foto, retornando (urls_dict, url_fallback) ou (None, None)."""
    if not file or not file.filename or not _allowed_image(file.filename):
        return None, None
    processor = get_image_processor()
    try:
        success, _message, urls = processor.process_and_save(file)
    except Exception:
        return None, None
    if not success or not urls:
        return None, None
    fallback = urls.get('medium', urls.get('small', urls.get('large', '')))
    return urls, fallback


def _spots_for_select():
    """Picos aprovados/ativos para o seletor (datalist)."""
    return Spot.query.filter(
        Spot.is_active.is_(True),
        Spot.status == 'approved',
    ).order_by(Spot.name).all()


def _parse_session_form(form):
    """Lê e valida o formulário. Retorna (data_dict, erro_str)."""
    spot_name = (form.get('spot_name') or '').strip()
    spot_id = form.get('spot_id') or None

    spot = None
    if spot_id:
        spot = Spot.query.get(spot_id)
        if spot and not spot_name:
            spot_name = spot.name
        if not spot:
            spot_id = None

    if not spot_name:
        return None, 'Informe o pico onde você surfou.'

    # Data (input type=date -> YYYY-MM-DD); default hoje
    date_raw = (form.get('session_date') or '').strip()
    try:
        session_date = datetime.strptime(date_raw, '%Y-%m-%d').date() if date_raw else datetime.utcnow().date()
    except ValueError:
        return None, 'Data inválida.'

    def _int(name):
        v = (form.get(name) or '').strip()
        try:
            return int(v) if v else None
        except ValueError:
            return None

    def _float(name):
        v = (form.get(name) or '').strip().replace(',', '.')
        try:
            return float(v) if v else None
        except ValueError:
            return None

    rating = _int('rating') or 3
    rating = min(5, max(1, rating))

    conditions = (form.get('conditions') or '').strip() or None
    valid_conditions = {c[0] for c in SurfSession.CONDITIONS}
    if conditions not in valid_conditions:
        conditions = None

    data = dict(
        spot_id=int(spot_id) if spot_id else None,
        spot_name=spot_name[:120],
        session_date=session_date,
        duration_min=_int('duration_min'),
        wave_height=_float('wave_height'),
        wave_count=_int('wave_count'),
        board=((form.get('board') or '').strip() or None),
        conditions=conditions,
        rating=rating,
        notes=((form.get('notes') or '').strip() or None),
    )
    return data, None


_MES = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']


def _diary_stats(sessions):
    """Estatísticas agregadas + série mensal + conquistas para o diário."""
    from collections import Counter

    total = len(sessions)
    total_min = sum(s.duration_min or 0 for s in sessions)
    rated = [s.rating for s in sessions if s.rating]
    avg_rating = round(sum(rated) / len(rated), 1) if rated else 0

    spot_counter = Counter(s.spot_name for s in sessions if s.spot_name)
    distinct_spots = len({(s.spot_id or (s.spot_name or '').lower()) for s in sessions})
    fav_spot = spot_counter.most_common(1)[0][0] if spot_counter else None
    best = max((s.rating or 0 for s in sessions), default=0)

    # Série dos últimos 6 meses (rótulos + contagem)
    today = datetime.utcnow().date()
    seq = []
    for i in range(5, -1, -1):
        mm, yy = today.month - i, today.year
        while mm <= 0:
            mm += 12
            yy -= 1
        seq.append((yy, mm))
    counts = Counter((s.session_date.year, s.session_date.month)
                     for s in sessions if s.session_date)
    monthly = {'labels': [_MES[mm] for (_, mm) in seq],
               'data': [counts.get(key, 0) for key in seq]}

    achievements = [
        {'label': 'Primeira sessão', 'icon': 'bi-droplet-fill', 'done': total >= 1},
        {'label': '10 sessões', 'icon': 'bi-collection-fill', 'done': total >= 10},
        {'label': '50 sessões', 'icon': 'bi-trophy-fill', 'done': total >= 50},
        {'label': '5 picos diferentes', 'icon': 'bi-geo-alt-fill', 'done': distinct_spots >= 5},
        {'label': "24h n'água", 'icon': 'bi-stopwatch-fill', 'done': total_min >= 24 * 60},
        {'label': 'Sessão nota 5', 'icon': 'bi-star-fill', 'done': best >= 5},
    ]

    return {
        'total': total,
        'hours': round(total_min / 60, 1) if total_min else 0,
        'avg_rating': avg_rating,
        'spots': distinct_spots,
        'fav_spot': fav_spot,
        'best': best,
        'monthly': monthly,
        'achievements': achievements,
    }


@diary.route('/diary')
@login_required
def my_diary():
    sessions = SurfSession.query.filter_by(user_id=current_user.id).order_by(
        SurfSession.session_date.desc(), SurfSession.id.desc()
    ).all()
    return render_template('diary/list.html',
                           sessions=sessions,
                           stats=_diary_stats(sessions),
                           owner=current_user,
                           is_owner=True)


@diary.route('/diary/u/<username>')
def user_diary(username):
    user = User.query.filter_by(username=username).first_or_404()
    sessions = SurfSession.query.filter_by(user_id=user.id).order_by(
        SurfSession.session_date.desc(), SurfSession.id.desc()
    ).all()
    is_owner = current_user.is_authenticated and current_user.id == user.id
    return render_template('diary/list.html',
                           sessions=sessions,
                           stats=_diary_stats(sessions),
                           owner=user,
                           is_owner=is_owner)


@diary.route('/diary/new', methods=['GET', 'POST'])
@login_required
def new_session():
    if request.method == 'POST':
        data, error = _parse_session_form(request.form)
        if error:
            flash(error, 'danger')
            return render_template('diary/form.html', spots=_spots_for_select(),
                                   session=None, form_data=request.form)

        session = SurfSession(user_id=current_user.id, **data)

        if 'photo' in request.files:
            urls, fallback = _save_photo(request.files['photo'])
            if urls:
                session.photo_urls = urls
                session.photo_url = fallback

        db.session.add(session)
        from gamification import award
        award(current_user, 'session_log')

        # Cross-post opcional: publica a sessão também no feed
        if request.form.get('cross_post'):
            _make_cross_post(session)
            award(current_user, 'post')

        db.session.commit()

        flash('Sessão registrada no seu diário!', 'success')
        return redirect(url_for('diary.view_session', session_id=session.id))

    # GET: pré-preenche o pico quando vem do detalhe de um pico (?spot_id&spot_name)
    return render_template('diary/form.html', spots=_spots_for_select(),
                           session=None, form_data=(request.args or None))


def _make_cross_post(session):
    """Cria um Post no feed a partir de uma sessão do diário."""
    from models import Post

    head = f"Sessão em {session.spot_name} — nota {session.rating}/5"
    if session.conditions:
        head += f" · {session.conditions_label}"
    parts = [head]
    if session.duration_label:
        parts.append(f"Duração: {session.duration_label}")
    if session.notes:
        parts.append(session.notes)

    post = Post(content="\n".join(parts), user_id=session.user_id,
                spot_id=session.spot_id, post_type='regular')
    if session.photo_urls:
        post.image_urls = session.photo_urls
        post.image_url = session.photo_url
    db.session.add(post)
    return post


@diary.route('/diary/<int:session_id>')
def view_session(session_id):
    session = SurfSession.query.get_or_404(session_id)
    is_owner = current_user.is_authenticated and current_user.id == session.user_id
    return render_template('diary/detail.html', session=session, is_owner=is_owner)


@diary.route('/diary/<int:session_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_session(session_id):
    session = SurfSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        data, error = _parse_session_form(request.form)
        if error:
            flash(error, 'danger')
            return render_template('diary/form.html', spots=_spots_for_select(),
                                   session=session, form_data=request.form)

        for key, value in data.items():
            setattr(session, key, value)

        if 'photo' in request.files and request.files['photo'].filename:
            urls, fallback = _save_photo(request.files['photo'])
            if urls:
                session.photo_urls = urls
                session.photo_url = fallback

        db.session.commit()
        flash('Sessão atualizada.', 'success')
        return redirect(url_for('diary.view_session', session_id=session.id))

    return render_template('diary/form.html', spots=_spots_for_select(),
                           session=session, form_data=None)


@diary.route('/diary/<int:session_id>/delete', methods=['POST'])
@login_required
def delete_session(session_id):
    session = SurfSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        abort(403)
    db.session.delete(session)
    db.session.commit()
    flash('Sessão removida do diário.', 'info')
    return redirect(url_for('diary.my_diary'))
