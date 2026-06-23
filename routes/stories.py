"""
Stories estilo Instagram: mídia efêmera (imagem ou vídeo) que expira em 24h.

- Vídeos são comprimidos (FFmpeg, alvo ~8MB) antes de subir, igual aos posts.
- Stories expirados têm a mídia apagada (Cloudinary ou local) para não acumular
  e estourar a cota do plano grátis.
"""
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, jsonify, abort, current_app as app)
from flask_login import login_required, current_user
from models import Story, StoryView
from extensions import db
from datetime import datetime, timedelta
import os
import uuid
import tempfile

stories = Blueprint('stories', __name__)

STORY_TTL_HOURS = 24
IMAGE_EXTS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
VIDEO_EXTS = {'mp4', 'mov', 'webm'}


def _is_production():
    return bool(os.environ.get('RENDER', False)) or os.environ.get('FLASK_ENV') == 'production'


def _resolve_url(u):
    """Resolve um caminho de mídia/avatar para URL exibível (Cloudinary ou /static)."""
    if not u:
        return url_for('static', filename='uploads/default_profile.jpg')
    if u.startswith('http://') or u.startswith('https://') or 'cloudinary.com' in u:
        return u
    return url_for('static', filename=u)


# ─────────────────────────── limpeza / mídia ───────────────────────────

def _delete_story_media(story):
    """Apaga a mídia do story (Cloudinary ou arquivo local). Best-effort."""
    try:
        if story.cloud_public_id:
            import cloudinary.uploader
            cloudinary.uploader.destroy(
                story.cloud_public_id,
                resource_type=story.cloud_resource_type or 'image',
            )
        elif story.media_url and not story.media_url.startswith('http'):
            path = os.path.join(app.root_path, 'static', story.media_url)
            if os.path.exists(path):
                os.remove(path)
    except Exception as e:
        print(f"[story] falha ao apagar mídia: {e}")


def cleanup_expired_stories():
    """Remove stories vencidos e suas mídias. Chamado ao montar a barra."""
    expired = Story.query.filter(Story.expires_at <= datetime.utcnow()).all()
    for s in expired:
        _delete_story_media(s)
        db.session.delete(s)
    if expired:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()


def build_story_bar(user):
    """Monta os dados da barra de stories do feed para `user`."""
    cleanup_expired_stories()
    now = datetime.utcnow()

    following_ids = [f.followed_id for f in user.followed.all()]
    relevant_ids = set(following_ids + [user.id])

    active = Story.query.filter(
        Story.user_id.in_(relevant_ids),
        Story.expires_at > now,
    ).order_by(Story.created_at.asc()).all()

    viewed_ids = {v.story_id for v in StoryView.query.filter_by(user_id=user.id).all()}

    grouped = {}
    for s in active:
        grouped.setdefault(s.user_id, []).append(s)

    bar = []
    for uid, items in grouped.items():
        author = items[0].author
        avatar = (author.profile_image_urls.get('small') or author.profile_image_urls.get('thumbnail')
                  if getattr(author, 'profile_image_urls', None) else None)
        bar.append({
            'user_id': uid,
            'username': author.username,
            'avatar': _resolve_url(avatar or author.profile_image),
            'is_self': uid == user.id,
            'has_unseen': any(s.id not in viewed_ids for s in items),
            'stories': [
                {
                    'id': s.id,
                    'url': s.display_media_url,
                    'type': s.media_type,
                    'when': s.created_at.strftime('%d/%m %H:%M'),
                    'can_delete': uid == user.id,
                }
                for s in items
            ],
        })

    # Eu primeiro, depois quem tem story não visto, depois o resto
    bar.sort(key=lambda b: (not b['is_self'], not b['has_unseen']))
    return bar


# ─────────────────────────── upload ───────────────────────────

def _save_story_local(file, is_video):
    folder = os.path.join(app.root_path, 'static', 'uploads', 'stories')
    os.makedirs(folder, exist_ok=True)

    if is_video:
        from video_utils import compress_video
        name = f"{uuid.uuid4().hex}.mp4"
        final = os.path.join(folder, name)
        tmp = os.path.join(folder, f"tmp_{uuid.uuid4().hex}")
        file.seek(0)
        file.save(tmp)
        try:
            ok, _ = compress_video(tmp, final, target_mb=8, is_reel=True)
            if not (ok and os.path.exists(final)):
                if os.path.exists(final):
                    os.remove(final)
                os.rename(tmp, final)
        finally:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
        return {'url': f"uploads/stories/{name}"}

    # imagem: redimensiona para caber em 1080x1920 e salva como jpg
    from PIL import Image, ImageOps
    name = f"{uuid.uuid4().hex}.jpg"
    final = os.path.join(folder, name)
    file.seek(0)
    img = Image.open(file)
    img = ImageOps.exif_transpose(img)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    img.thumbnail((1080, 1920), Image.Resampling.LANCZOS)
    img.save(final, format='JPEG', quality=88, optimize=True, progressive=True)
    return {'url': f"uploads/stories/{name}"}


def _upload_story_cloud(file, is_video):
    import cloudinary.uploader
    public_id = f"story_{current_user.id}_{uuid.uuid4().hex[:8]}"

    if is_video:
        from video_utils import compress_video, ffmpeg_available
        tmpdir = tempfile.mkdtemp(prefix='iamsurfer_story_')
        ext = (file.filename.rsplit('.', 1)[-1].lower() if '.' in (file.filename or '') else 'mp4')
        raw = os.path.join(tmpdir, f"raw.{ext}")
        out = os.path.join(tmpdir, "out.mp4")
        file.seek(0)
        file.save(raw)
        upload_path = raw
        try:
            if ffmpeg_available():
                ok, _ = compress_video(raw, out, target_mb=8, is_reel=True)
                if ok and os.path.exists(out):
                    upload_path = out
            res = cloudinary.uploader.upload(
                upload_path, resource_type='video',
                public_id=public_id, folder='iamsurfer/stories',
            )
        finally:
            for p in (raw, out):
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass
            try:
                os.rmdir(tmpdir)
            except OSError:
                pass
        return {'url': res['secure_url'], 'public_id': res['public_id'], 'resource_type': 'video'}

    res = cloudinary.uploader.upload(
        file, resource_type='image',
        public_id=public_id, folder='iamsurfer/stories',
        transformation=[{'width': 1080, 'height': 1920, 'crop': 'limit', 'quality': 'auto'}],
    )
    return {'url': res['secure_url'], 'public_id': res['public_id'], 'resource_type': 'image'}


@stories.route('/story/new', methods=['GET', 'POST'])
@login_required
def new_story():
    if request.method == 'POST':
        if 'media' not in request.files or not request.files['media'].filename:
            flash('Selecione uma imagem ou vídeo.', 'danger')
            return redirect(url_for('stories.new_story'))

        file = request.files['media']
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        is_video = ext in VIDEO_EXTS
        is_image = ext in IMAGE_EXTS
        if not (is_video or is_image):
            flash('Formato não suportado. Use imagem (JPG/PNG) ou vídeo (MP4).', 'danger')
            return redirect(url_for('stories.new_story'))

        if is_video:
            max_v = app.config.get('MAX_VIDEO_UPLOAD_SIZE', 100 * 1024 * 1024)
            file.seek(0, os.SEEK_END)
            size = file.tell()
            file.seek(0)
            if size > max_v:
                flash(f'Vídeo muito grande (máx {max_v // (1024*1024)}MB).', 'danger')
                return redirect(url_for('stories.new_story'))

        try:
            if _is_production():
                result = _upload_story_cloud(file, is_video)
            else:
                result = _save_story_local(file, is_video)
        except Exception as e:
            flash(f'Erro ao processar story: {e}', 'danger')
            return redirect(url_for('stories.new_story'))

        if not result:
            flash('Falha ao processar a mídia do story.', 'danger')
            return redirect(url_for('stories.new_story'))

        story = Story(
            user_id=current_user.id,
            media_url=result['url'],
            media_type='video' if is_video else 'image',
            cloud_public_id=result.get('public_id'),
            cloud_resource_type=result.get('resource_type'),
            expires_at=datetime.utcnow() + timedelta(hours=STORY_TTL_HOURS),
        )
        db.session.add(story)
        db.session.commit()
        flash('Story publicado! Ele some em 24h.', 'success')
        return redirect(url_for('main.index'))

    return render_template('stories/new_story.html')


@stories.route('/story/<int:story_id>/seen', methods=['POST'])
@login_required
def mark_seen(story_id):
    Story.query.get_or_404(story_id)
    exists = StoryView.query.filter_by(story_id=story_id, user_id=current_user.id).first()
    if not exists:
        db.session.add(StoryView(story_id=story_id, user_id=current_user.id))
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()  # corrida com a constraint única: ignora
    return jsonify({'ok': True})


@stories.route('/story/<int:story_id>/delete', methods=['POST'])
@login_required
def delete_story(story_id):
    story = Story.query.get_or_404(story_id)
    if story.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    _delete_story_media(story)
    db.session.delete(story)
    db.session.commit()
    flash('Story excluído.', 'info')
    return redirect(url_for('main.index'))
