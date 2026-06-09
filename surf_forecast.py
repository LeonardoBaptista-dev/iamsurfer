"""Previsão de surf via Open-Meteo (gratuita, sem chave de API).

Busca ondas (Marine API) + vento (Forecast API) de todos os picos numa única
requisição, com cache em memória de 1h. Retorna, por pico:
  - current: condições atuais (altura/período/direção da onda + vento)
  - days:    resumo dos próximos dias (com graus p/ setas e um rating de tamanho)
  - hourly:  séries horárias (próximas ~48h) p/ os gráficos (onda, vento, maré)
"""
import time
from datetime import datetime

import requests

MARINE_URL = 'https://marine-api.open-meteo.com/v1/marine'
WEATHER_URL = 'https://api.open-meteo.com/v1/forecast'
TTL = 3600          # 1 hora
HOURLY_SPAN = 48    # horas exibidas no gráfico

_CACHE = {'key': None, 'data': None, 'ts': 0.0}

_DIRS = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
         'S', 'SSO', 'SO', 'OSO', 'O', 'ONO', 'NO', 'NNO']
_WEEKDAYS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']


def deg_to_compass(deg):
    if deg is None:
        return None
    return _DIRS[int((deg / 22.5) + 0.5) % 16]


def _rating(wave_height):
    """Indicador de tamanho da onda (0-5) — honesto: mede tamanho, não 'qualidade'."""
    if wave_height is None:
        return 0
    for limit, stars in ((0.3, 0), (0.6, 1), (1.0, 2), (1.5, 3), (2.2, 4)):
        if wave_height < limit:
            return stars
    return 5


def _normalize(resp):
    return resp if isinstance(resp, list) else [resp]


def _day_label(date_str):
    try:
        return _WEEKDAYS[datetime.strptime(date_str, '%Y-%m-%d').weekday()]
    except (ValueError, TypeError):
        return date_str


def _col(daily, name, n):
    return (daily.get(name) or [None] * n)


def _build_hourly(mh, wh, current_time):
    """Monta as séries horárias (próximas HOURLY_SPAN horas) para o gráfico."""
    times = mh.get('time') or []
    if not times:
        return {'labels': [], 'wave': [], 'wind': [], 'tide': []}
    n = len(times)
    start = 0
    if current_time:
        pref = current_time[:13]
        for i, t in enumerate(times):
            if t[:13] >= pref:
                start = i
                break
    wave = _col(mh, 'wave_height', n)
    tide = _col(mh, 'sea_level_height_msl', n)
    wind = _col(wh, 'wind_speed_10m', n)
    out = {'labels': [], 'wave': [], 'wind': [], 'tide': []}
    for i in range(start, min(start + HOURLY_SPAN, n)):
        try:
            dt = datetime.strptime(times[i], '%Y-%m-%dT%H:%M')
            label = f"{_WEEKDAYS[dt.weekday()]} {dt.strftime('%Hh')}"
        except (ValueError, TypeError):
            label = times[i]
        out['labels'].append(label)
        out['wave'].append(round(wave[i], 2) if i < len(wave) and wave[i] is not None else None)
        out['wind'].append(round(wind[i]) if i < len(wind) and wind[i] is not None else None)
        out['tide'].append(round(tide[i], 2) if i < len(tide) and tide[i] is not None else None)
    return out


def get_forecast(spots):
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
            'hourly': 'wave_height,wave_direction,wave_period,sea_level_height_msl',
            'daily': 'wave_height_max,wave_direction_dominant,wave_period_max',
            'timezone': 'auto', 'forecast_days': 5,
        }, timeout=15).json())
        weather = _normalize(requests.get(WEATHER_URL, params={
            'latitude': lats, 'longitude': lons,
            'current': 'wind_speed_10m,wind_direction_10m',
            'hourly': 'wind_speed_10m,wind_direction_10m',
            'daily': 'wind_speed_10m_max,wind_direction_10m_dominant',
            'timezone': 'auto', 'forecast_days': 5,
        }, timeout=15).json())
    except Exception:
        return {}

    result = {}
    for i, spot in enumerate(spots):
        try:
            m = marine[i] if i < len(marine) else {}
            w = weather[i] if i < len(weather) else {}
            mc, wc = m.get('current') or {}, w.get('current') or {}
            md, wd = m.get('daily') or {}, w.get('daily') or {}
            mh, wh = m.get('hourly') or {}, w.get('hourly') or {}

            times = md.get('time') or []
            n = len(times)
            days = []
            for j, date in enumerate(times):
                wv = _col(md, 'wave_height_max', n)[j]
                wave_deg = _col(md, 'wave_direction_dominant', n)[j]
                wind_deg = _col(wd, 'wind_direction_10m_dominant', n)[j]
                days.append({
                    'label': _day_label(date), 'date': date,
                    'wave_height': wv,
                    'wave_period': _col(md, 'wave_period_max', n)[j],
                    'wave_dir': deg_to_compass(wave_deg), 'wave_deg': wave_deg,
                    'wind_speed': _col(wd, 'wind_speed_10m_max', n)[j],
                    'wind_dir': deg_to_compass(wind_deg), 'wind_deg': wind_deg,
                    'rating': _rating(wv),
                })

            result[spot.id] = {
                'current': {
                    'wave_height': mc.get('wave_height'),
                    'wave_period': mc.get('wave_period'),
                    'wave_dir': deg_to_compass(mc.get('wave_direction')),
                    'wave_deg': mc.get('wave_direction'),
                    'wind_speed': wc.get('wind_speed_10m'),
                    'wind_dir': deg_to_compass(wc.get('wind_direction_10m')),
                    'wind_deg': wc.get('wind_direction_10m'),
                    'rating': _rating(mc.get('wave_height')),
                },
                'days': days,
                'hourly': _build_hourly(mh, wh, mc.get('time') or wc.get('time')),
            }
        except Exception:
            result[spot.id] = None

    _CACHE.update(key=key, data=result, ts=now)
    return result
