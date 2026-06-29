"""Formato de erro único da API (`/api/v1`).

Toda resposta de erro segue o contrato do doc (seção 2):

    { "error": { "code": "string", "message": "humano", "fields": { ... } } }

`code` é estável (a máquina decide), `message` é pt-BR (o humano lê) e `fields`
mapeia erros de validação por campo (ex.: {"email": "já cadastrado"}).
"""
from flask import jsonify


class ApiError(Exception):
    """Erro de domínio da API. Levante isto nas rotas em vez de devolver tuplas.

    Ex.: `raise ApiError("not_found", "Usuário não encontrado", status=404)`
    """

    def __init__(self, code, message, status=400, fields=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.fields = fields or {}


def error_response(code, message, status=400, fields=None):
    """Monta `(body, status)` no formato padrão."""
    payload = {'error': {'code': code, 'message': message}}
    if fields:
        payload['error']['fields'] = fields
    return jsonify(payload), status


def register_error_handlers(app, api_blueprint):
    """Liga os handlers de erro. Só intercepta o que é da API: as exceções HTTP
    do site Jinja continuam renderizando as páginas normais.
    """

    @app.errorhandler(ApiError)
    def _handle_api_error(err):
        return error_response(err.code, err.message, err.status, err.fields)

    # Handlers HTTP só para o blueprint da API (não afeta o site).
    @api_blueprint.errorhandler(400)
    def _bad_request(err):
        return error_response('bad_request', 'Requisição inválida.', 400)

    @api_blueprint.errorhandler(401)
    def _unauthorized(err):
        return error_response('unauthorized', 'Autenticação necessária.', 401)

    @api_blueprint.errorhandler(403)
    def _forbidden(err):
        return error_response('forbidden', 'Você não tem permissão para isso.', 403)

    @api_blueprint.errorhandler(404)
    def _not_found(err):
        return error_response('not_found', 'Recurso não encontrado.', 404)

    @api_blueprint.errorhandler(405)
    def _method_not_allowed(err):
        return error_response('method_not_allowed', 'Método não permitido.', 405)

    @api_blueprint.errorhandler(422)
    def _unprocessable(err):
        return error_response('unprocessable', 'Não foi possível processar os dados.', 422)

    @api_blueprint.errorhandler(429)
    def _rate_limited(err):
        return error_response('rate_limited', 'Muitas requisições. Tente novamente em instantes.', 429)

    @api_blueprint.errorhandler(500)
    def _server_error(err):
        return error_response('server_error', 'Erro interno. Tente novamente.', 500)
