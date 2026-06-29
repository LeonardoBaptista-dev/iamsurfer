"""Processamento de mídia de posts (imagem/vídeo), compartilhado entre o
caminho síncrono (request) e o worker assíncrono (RQ).

Cada helper recebe o `post` e um arquivo (Werkzeug FileStorage), chama o
processador apropriado (local em dev, Cloudinary em produção), preenche os
campos de mídia do post e retorna (ok: bool, erro: str|None). NÃO faz commit —
quem chama decide quando persistir.
"""
import os
import hashlib

from flask import url_for


def get_image_processor():
    """Retorna o processador de imagem/vídeo apropriado ao ambiente."""
    use_local = os.environ.get('FLASK_ENV') != 'production'
    if use_local:
        from local_image_processor import LocalImageProcessor
        return LocalImageProcessor
    from image_processor import ImageProcessor
    return ImageProcessor


def apply_image_to_post(post, file):
    """Processa a imagem e preenche image_urls/image_url/image_hash do post."""
    processor = get_image_processor()

    if hasattr(processor, 'process_and_save'):
        # Processador local (dev)
        success, message, urls = processor.process_and_save(file)
        if not success:
            return False, message
        file.seek(0)
        post.image_hash = hashlib.md5(file.read()).hexdigest()
        file.seek(0)
        post.image_urls = urls
        post.image_url = urls.get('medium', urls.get('small', ''))
        return True, None

    # Processador Cloudinary (produção)
    result = processor.process_and_upload_image(file, post.id)
    if not result.get('success'):
        return False, result.get('error')
    post.image_urls = result['urls']
    post.image_hash = result['hash']
    post.image_url = result['urls'].get('medium', result['urls'].get('small', ''))
    return True, None


def apply_video_to_post(post, file, is_reel=False):
    """Comprime/sobe o vídeo e preenche video_url do post."""
    processor = get_image_processor()

    if hasattr(processor, 'process_and_save_video'):
        # Processador local (dev)
        success, message, url_path = processor.process_and_save_video(file, is_reel=is_reel)
        if not success:
            return False, message
        post.video_url = url_for('static', filename=url_path)
        return True, None

    if hasattr(processor, 'process_and_upload_video'):
        # Processador Cloudinary (produção)
        result = processor.process_and_upload_video(file, post.id, is_reel=is_reel)
        if not result.get('success'):
            return False, result.get('error', 'Erro desconhecido')
        post.video_url = result['url']
        return True, None

    return False, 'Processador de vídeo não configurado'
