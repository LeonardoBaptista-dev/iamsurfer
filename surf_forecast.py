"""Previsão de surf via Open-Meteo (gratuita, sem chave de API).

Busca a previsão de ondas (Marine API) e vento (Forecast API) para todos os
picos de uma vez, usando as coordenadas já cadastradas. Resultado fica em cache
na memória por 1 hora para não sobrecarregar a API a cada acesso.
"""
import time
from datetime import datetime

import requests

MARINE_URL = 'https://marine-api.open-meteo.com/v1/marine'
WEATHER_URL = 'https://api.open-meteo.com/v1/forecast'
TTL = 3600  # segundos (1 hora)

_CACHE = {'key': None, 'data': None, 'ts': 0.0}

_DIRS = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
         'S', 'SSO', 'SO', 'OSO', 'O', 'ONO', 'NO', 'NNO']
_WEEKDAYS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']


def deg_to_compass(deg):
    """Converte graus (0-360) em ponto cardeal abreviado (PT)."""
    if deg is None:
        return None
    return _DIRS[int((deg / 22.5) + 0.5) % 16]


def _normalize(resp):
    # Open-Meteo devolve um objeto para 1 coordenada e uma lista para várias.
    return resp if isinstance(resp, list) else [resp]


def _day_label(date_str):
    try:
        return _WEEKDAYS[datetime.strptime(date_str, '%Y-%m-%d').weekday()]
    except (ValueError, TypeError):
        return date_str


def _col(daily, name, n):
    """Retorna a lista de uma métrica diária, preenchendo com None se faltar."""
    return (daily.get(name) or [None] * n)


def get_forecast(spots):
    """Recebe uma lista de Spot (com latitude/longitude) e retorna um dict
    {spot_id: {'current': {...}, 'days': [...]}}. Em caso de falha de rede ou
    pico sem previsão, o valor é None. Retorna {} se não houver picos válidos.
    """
    spots = [s for s in spots if s.latitude is not None and s.longitude is not None]
    if not spots:
        return {}

    key = ','.join(str(s.id) for s in sorted(spots, key=lambda s: s.id))
    now = time.time()
    if _CACHE['key'] == key and _CACHE['data'] is not None and (now - _CACHE['ts']) < TTL:
        return _CACHE['data']

    lats = ','.join(str(s.latitude) for s in spots)
    lons = ','.join(str(s.longitude) for s in spots)
    try:
        marine = _normalize(requests.get(MARINE_URL, params={
            'latitude': lats, 'longitude': lons,
            'current': 'wave_height,wave_direction,wave_period',
            'daily': 'wave_height_max,wave_direction_dominant,wave_period_max',
            'timezone': 'auto', 'forecast_days': 5,
        }, timeout=12).json())
        weather = _normalize(requests.get(WEATHER_URL, params={
            'latitude': lats, 'longitude': lons,
            'current': 'wind_speed_10m,wind_direction_10m',
            'daily': 'wind_speed_10m_max,wind_direction_10m_dominant',
            'timezone': 'auto', 'forecast_days': 5,
        }, timeout=12).json())
    except Exception:
        return {}  # rede indisponível -> sem previsão

    result = {}
    for i, spot in enumerate(spots):
        try:
            m = marine[i] if i < len(marine) else {}
            w = weather[i] if i < len(weather) else {}
            mc, wc = m.get('current') or {}, w.get('current') or {}
            md, wd = m.get('daily') or {}, w.get('daily') or {}
            times = md.get('time') or []
            n = len(times)
            days = []
            for j, date in enumerate(times):
                days.append({
                    'label': _day_label(date),
                    'date': date,
                    'wave_height': _col(md, 'wave_height_max', n)[j],
                    'wave_period': _col(md, 'wave_period_max', n)[j],
                    'wave_dir': deg_to_compass(_col(md, 'wave_direction_dominant', n)[j]),
                    'wind_speed': _col(wd, 'wind_speed_10m_max', n)[j],
                    'wind_dir': deg_to_compass(_col(wd, 'wind_direction_10m_dominant', n)[j]),
                })
            result[spot.id] = {
                'current': {
                    'wave_height': mc.get('wave_height'),
                    'wave_period': mc.get('wave_period'),
                    'wave_dir': deg_to_compass(mc.get('wave_direction')),
                    'wind_speed': wc.get('wind_speed_10m'),
                    'wind_dir': deg_to_compass(wc.get('wind_direction_10m')),
                },
                'days': days,
            }
        except Exception:
            result[spot.id] = None

    _CACHE.update(key=key, data=result, ts=now)
    return result
