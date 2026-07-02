"""Abstração de provedor de pagamento para a API (`/api/v1`) — Prompt A9.

O objetivo é permitir que o fluxo de compra de fotos funcione tanto em
produção (com Mercado Pago) quanto em desenvolvimento/testes (sem credenciais
nem rede). Por isso há duas implementações atrás da mesma interface:

- **Mercado Pago** (recomendado: Pix + cartão): ativado quando a env
  ``MERCADOPAGO_ACCESS_TOKEN`` está definida. Cria uma *preference* real via
  ``POST https://api.mercadopago.com/checkout/preferences`` (com ``requests``)
  e devolve ``init_point`` (URL do checkout) e o ``preference_id``. O webhook
  consulta o pagamento em ``GET /v1/payments/{id}`` para confirmar.
- **Modo teste** (fallback): quando NÃO há credencial. Gera um id de pagamento
  fake e a confirmação acontece por um webhook simulado
  (``{"purchase_id": <id>, "status": "paid"}``). Nenhuma rede é tocada.

Envs necessárias (Mercado Pago):
- ``MERCADOPAGO_ACCESS_TOKEN``  → access token do vendedor (obrigatória p/ modo real).
- ``MERCADOPAGO_NOTIFICATION_URL`` (opcional) → URL pública do webhook
  (``/api/v1/webhooks/payments``) para o MP notificar.
- ``MERCADOPAGO_SUCCESS_URL`` / ``MERCADOPAGO_FAILURE_URL`` /
  ``MERCADOPAGO_PENDING_URL`` (opcionais) → back_urls do checkout.

IMPORTANTE (segurança): o preço NUNCA vem do cliente — quem chama estas
funções passa o valor calculado no servidor (em centavos). O provedor recebe o
valor em reais (float) porque é o que o Mercado Pago espera.
"""
import os

import requests

MP_API_BASE = 'https://api.mercadopago.com'
MP_TIMEOUT = 15  # segundos


def _access_token():
    """Access token do Mercado Pago, ou None (força o modo teste)."""
    token = os.environ.get('MERCADOPAGO_ACCESS_TOKEN')
    return token.strip() if token and token.strip() else None


def is_test_mode():
    """True quando não há credencial do Mercado Pago (dev/testes)."""
    return _access_token() is None


def _cents_to_reais(amount_cents):
    return round((amount_cents or 0) / 100.0, 2)


def create_payment(purchase_id, amount_cents, title, payer_email=None):
    """Cria a cobrança no provedor e devolve um dict serializável para o app.

    - `purchase_id`: id da PhotoPurchase (usado como `external_reference` para
      o webhook reconciliar o pagamento com a compra).
    - `amount_cents`: valor final (com desconto já aplicado), em centavos, do
      servidor. Nunca do cliente.

    Retorno (shape estável):
        {
          'provider': 'mercadopago' | 'test',
          'provider_ref': <str>,      # id externo p/ reconciliação
          'init_point': <url|None>,   # URL do checkout (abrir no app)
          'qr': <str|None>,           # dado de QR/Pix quando disponível
          'test_mode': <bool>,
        }
    """
    token = _access_token()
    if token is None:
        return _create_payment_test(purchase_id, amount_cents)
    return _create_payment_mercadopago(token, purchase_id, amount_cents, title, payer_email)


def _create_payment_test(purchase_id, amount_cents):
    """Modo teste: sem rede. O `provider_ref` é determinístico pela compra."""
    ref = f'test_pay_{purchase_id}'
    return {
        'provider': 'test',
        'provider_ref': ref,
        'init_point': None,
        'qr': None,
        'test_mode': True,
        'amount_cents': amount_cents,
    }


def _create_payment_mercadopago(token, purchase_id, amount_cents, title, payer_email):
    """Cria uma preference real no Mercado Pago via API HTTP."""
    payload = {
        'items': [{
            'title': title or 'Foto',
            'quantity': 1,
            'currency_id': 'BRL',
            'unit_price': _cents_to_reais(amount_cents),
        }],
        'external_reference': str(purchase_id),
        'metadata': {'purchase_id': purchase_id},
    }
    notify = os.environ.get('MERCADOPAGO_NOTIFICATION_URL')
    if notify:
        payload['notification_url'] = notify
    back_urls = {
        k: v for k, v in {
            'success': os.environ.get('MERCADOPAGO_SUCCESS_URL'),
            'failure': os.environ.get('MERCADOPAGO_FAILURE_URL'),
            'pending': os.environ.get('MERCADOPAGO_PENDING_URL'),
        }.items() if v
    }
    if back_urls:
        payload['back_urls'] = back_urls
    if payer_email:
        payload['payer'] = {'email': payer_email}

    resp = requests.post(
        f'{MP_API_BASE}/checkout/preferences',
        json=payload,
        headers={'Authorization': f'Bearer {token}'},
        timeout=MP_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        'provider': 'mercadopago',
        'provider_ref': str(data.get('id') or ''),
        'init_point': data.get('init_point') or data.get('sandbox_init_point'),
        'qr': None,
        'test_mode': False,
        'amount_cents': amount_cents,
    }


def fetch_payment_status(payment_id):
    """Consulta um pagamento no Mercado Pago e devolve (status, external_reference).

    Usado pelo webhook do modo real. `status` é a string do MP
    (ex.: 'approved', 'pending', 'rejected'). Devolve (None, None) em erro.
    """
    token = _access_token()
    if token is None:
        return None, None
    try:
        resp = requests.get(
            f'{MP_API_BASE}/v1/payments/{payment_id}',
            headers={'Authorization': f'Bearer {token}'},
            timeout=MP_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get('status'), data.get('external_reference')
    except Exception:
        return None, None
