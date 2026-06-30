"""Upload de mídia assinado (Cloudinary) — Prompt A11.

O app sobe o binário **direto** pro Cloudinary (não trafega pelo Flask). A API só
gera a assinatura:

    POST /api/v1/media/sign   → { cloud_name, api_key, timestamp, folder,
                                   signature, resource_type, upload_url }
    POST /api/v1/media/confirm (opcional) → normaliza o descritor da mídia

Fluxo no app:
1. `POST /media/sign` com `resource_type` (image|video).
2. `POST upload_url` (multipart) com: file, api_key, timestamp, folder, signature.
3. Cloudinary devolve `secure_url`/`public_id`; o app passa isso ao criar o post/
   story/reel (A3/A4/A5) — ou chama `/media/confirm` para validar o shape.

Reusa a config Cloudinary do projeto (variável `CLOUDINARY_URL`, lida pelo SDK).
Sem Cloudinary configurado (ex.: dev com storage local), responde 503 claro.
"""
import time

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from .deps import body, current_api_user, require_fields
from .errors import ApiError

media_api = Blueprint('media_api', __name__, url_prefix='/media')

ALLOWED_RESOURCE = {'image', 'video'}
FOLDER_PREFIX = 'iamsurfer/'
DEFAULT_FOLDER = 'iamsurfer/uploads'


def _cloudinary():
    """Retorna o módulo cloudinary configurado, ou levanta 503 se indisponível.

    `cloudinary.config()` é populado automaticamente pela env `CLOUDINARY_URL`.
    """
    try:
        import cloudinary
        import cloudinary.utils  # noqa: F401 (garante o submódulo de assinatura)
    except ImportError:
        raise ApiError('media_unavailable', 'Upload de mídia indisponível neste ambiente.', 503)

    cfg = cloudinary.config()
    if not (cfg.cloud_name and cfg.api_key and cfg.api_secret):
        raise ApiError('media_unavailable',
                       'Upload de mídia indisponível (Cloudinary não configurado).', 503)
    return cloudinary, cfg


def _safe_folder(raw):
    """Confina a folder ao namespace do projeto (evita escrita fora de iamsurfer/)."""
    folder = (raw or DEFAULT_FOLDER).strip().strip('/')
    if not folder:
        return DEFAULT_FOLDER
    if not folder.startswith(FOLDER_PREFIX):
        folder = FOLDER_PREFIX + folder
    return folder


@media_api.route('/sign', methods=['POST'])
@jwt_required()
def sign_upload():
    """Gera assinatura/timestamp/folder para o app subir direto no Cloudinary."""
    current_api_user()  # exige autenticação
    data = body()

    resource_type = (data.get('resource_type') or 'image').strip().lower()
    if resource_type not in ALLOWED_RESOURCE:
        raise ApiError('validation_error', 'Tipo de mídia inválido.', 422,
                       {'resource_type': 'Use "image" ou "video".'})

    cloudinary, cfg = _cloudinary()
    folder = _safe_folder(data.get('folder'))
    timestamp = int(time.time())

    # Apenas estes params são assinados; o app DEVE enviar exatamente os mesmos
    # (mais api_key, signature e o arquivo) no multipart pro Cloudinary.
    params_to_sign = {'timestamp': timestamp, 'folder': folder}
    signature = cloudinary.utils.api_sign_request(params_to_sign, cfg.api_secret)

    return jsonify({
        'cloud_name': cfg.cloud_name,
        'api_key': cfg.api_key,
        'timestamp': timestamp,
        'folder': folder,
        'signature': signature,
        'resource_type': resource_type,
        'upload_url': f'https://api.cloudinary.com/v1_1/{cfg.cloud_name}/{resource_type}/upload',
    })


@media_api.route('/confirm', methods=['POST'])
@jwt_required()
def confirm_upload():
    """Normaliza o descritor da mídia após o upload (opcional).

    Não persiste nada: a mídia é vinculada quando o post/story/reel é criado com
    o `public_id`/`url` retornados aqui. Serve para o app validar o shape e a API
    impor os campos esperados.
    """
    current_api_user()
    data = body()
    require_fields(data, 'public_id')

    resource_type = (data.get('resource_type') or 'image').strip().lower()
    if resource_type not in ALLOWED_RESOURCE:
        raise ApiError('validation_error', 'Tipo de mídia inválido.', 422,
                       {'resource_type': 'Use "image" ou "video".'})

    url = data.get('secure_url') or data.get('url')
    if not url:
        raise ApiError('validation_error', 'URL da mídia ausente.', 422,
                       {'secure_url': 'Obrigatório.'})

    return jsonify({
        'ok': True,
        'media': {
            'public_id': data['public_id'],
            'url': url,
            'resource_type': resource_type,
            'width': data.get('width'),
            'height': data.get('height'),
            'duration': data.get('duration'),  # vídeos
        },
    })
