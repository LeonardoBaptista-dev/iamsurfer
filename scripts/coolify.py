#!/usr/bin/env python3
"""Cliente mínimo da API do Coolify — inspeciona o deploy da VPS.

Lê credenciais de variáveis de ambiente (NUNCA hardcode um token aqui):
    COOLIFY_URL    = https://<host-do-painel-coolify>      (ex.: http://72.60.58.118:8000)
    COOLIFY_TOKEN  = <API token criado em Coolify → Keys & Tokens → API Tokens>

Uso:
    python scripts/coolify.py servers        # servidores + recursos (CPU/RAM/disco)
    python scripts/coolify.py apps           # aplicações e status
    python scripts/coolify.py deployments    # deploys recentes
    python scripts/coolify.py resources      # visão geral de tudo
    python scripts/coolify.py raw /api/v1/<qualquer-endpoint>

A API do Coolify v4 fica em <COOLIFY_URL>/api/v1/... com Bearer token.
Docs: https://coolify.io/docs/api-reference
"""
import json
import os
import sys
import urllib.request
import urllib.error


def _get(path):
    base = os.environ.get('COOLIFY_URL', '').rstrip('/')
    token = os.environ.get('COOLIFY_TOKEN', '')
    if not base or not token:
        sys.exit('Defina COOLIFY_URL e COOLIFY_TOKEN no ambiente primeiro.')
    url = base + path
    req = urllib.request.Request(url, headers={
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
    })
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        sys.exit(f'HTTP {e.code} em {path}: {e.read().decode("utf-8", "ignore")[:400]}')
    except Exception as e:
        sys.exit(f'Erro ao chamar {path}: {e}')


def _print(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'resources'
    if cmd == 'servers':
        _print(_get('/api/v1/servers'))
    elif cmd == 'apps':
        _print(_get('/api/v1/applications'))
    elif cmd == 'deployments':
        _print(_get('/api/v1/deployments'))
    elif cmd == 'resources':
        _print({
            'servers': _get('/api/v1/servers'),
            'applications': _get('/api/v1/applications'),
        })
    elif cmd == 'raw' and len(sys.argv) > 2:
        _print(_get(sys.argv[2]))
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
