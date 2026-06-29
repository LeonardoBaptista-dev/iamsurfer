"""Fila assíncrona de processamento de mídia (RQ + Redis).

RETROCOMPATÍVEL: se REDIS_URL não estiver definido — ou se redis/rq estiverem
indisponíveis — `queue_enabled()` retorna False e o upload é processado de
forma síncrona no próprio request, exatamente como antes. Ou seja, dá pra
deployar este código com segurança ANTES de provisionar o Redis no Coolify.

Quando o Redis está configurado:
- o request salva o arquivo em disco e enfileira um job, retornando na hora;
- um worker (`rq worker iamsurfer-media`) processa a mídia e atualiza o post.
"""
import os

QUEUE_NAME = 'iamsurfer-media'
_queue = None
_checked = False


def _redis_url():
    return os.environ.get('REDIS_URL')


def get_queue():
    """Retorna a Queue do RQ, ou None se o Redis não estiver disponível."""
    global _queue, _checked
    if _queue is not None:
        return _queue
    if _checked:
        return None
    _checked = True
    url = _redis_url()
    if not url:
        return None
    try:
        from redis import Redis
        from rq import Queue
        conn = Redis.from_url(url)
        conn.ping()
        _queue = Queue(QUEUE_NAME, connection=conn, default_timeout=900)
        print('[media_jobs] Redis conectado — uploads serão processados em background.')
        return _queue
    except Exception as e:  # pragma: no cover
        print(f'[media_jobs] Redis indisponível ({e}); processamento síncrono.')
        return None


def queue_enabled():
    return get_queue() is not None


def enqueue_media(post_id, tmp_path, original_filename, is_image, is_video, is_reel):
    """Enfileira o processamento da mídia. Retorna o job ou None."""
    q = get_queue()
    if q is None:
        return None
    return q.enqueue(
        process_media_job,
        post_id, tmp_path, original_filename, is_image, is_video, is_reel,
        job_timeout=900,
    )


def process_media_job(post_id, tmp_path, original_filename, is_image, is_video, is_reel):
    """Executado no worker RQ: processa a mídia e atualiza media_status do post."""
    from app import app, db
    from models import Post
    from werkzeug.datastructures import FileStorage
    from media_processing import apply_image_to_post, apply_video_to_post

    with app.app_context():
        post = Post.query.get(post_id)
        if post is None:
            _cleanup(tmp_path)
            return
        try:
            with open(tmp_path, 'rb') as fh:
                fs = FileStorage(stream=fh, filename=original_filename)
                if is_image:
                    ok, msg = apply_image_to_post(post, fs)
                else:
                    ok, msg = apply_video_to_post(post, fs, is_reel=is_reel)
            post.media_status = 'ready' if ok else 'failed'
            if not ok:
                print(f'[media_jobs] falha no post {post_id}: {msg}')
            db.session.commit()
        except Exception as e:  # pragma: no cover
            db.session.rollback()
            p = Post.query.get(post_id)
            if p is not None:
                p.media_status = 'failed'
                db.session.commit()
            print(f'[media_jobs] erro ao processar post {post_id}: {e}')
        finally:
            _cleanup(tmp_path)


def _cleanup(path):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass
