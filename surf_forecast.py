"""Previsão de surf via Open-Meteo (gratuita, sem chave de API).

Por pico retorna:
  - current: condições atuais (onda/período/direção + vento + maré + qualidade)
  - days:    próximos dias (rating de tamanho, qualidade, condição de vento e as
             horas do dia em passos de 3h)
  - hourly:  séries horárias das próximas 48h p/ o gráfico (onda, vento, maré)

A "qualidade" combina o tamanho da onda com o vento em relação ao vento ideal
do pico (Spot.best_wind_direction): offshore/glassy melhora, onshore piora.
"""
import re
import time
from datetime import datetime

import requests

MARINE_URL = 'https://marine-api.open-meteo.com/v1/marine'
WEATHER_URL = 'https://api.open-meteo.com/v1/forecast'
TTL = 3600          # 1 hora
HOURLY_SPAN = 48    # horas no gráfico
DAY_STEP = 3        # passo (h) do detalhe por dia

_CACHE = {}         # key -> {'data':..., 'ts':...}

_DIRS = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
         'S', 'SSO', 'SO', 'OSO', 'O', 'ONO', 'NO', 'NNO']
_WEEKDAYS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']

# Nomes/abreviações (PT e EN) -> graus
_NAME2DEG = {
    'N': 0, 'NORTE': 0, 'NNE': 22.5, 'NE': 45, 'NORDESTE': 45, 'ENE': 67.5,
    'E': 90, 'L': 90, 'LESTE': 90, 'EAST': 90, 'ESE': 112.5, 'SE': 135, 'SUDESTE': 135, 'SSE': 157.5,
    'S': 180, 'SUL': 180, 'SOUTH': 180, 'SSO': 202.5, 'SSW': 202.5, 'SO': 225, 'SW': 225, 'SUDOESTE': 225,
    'OSO': 247.5, 'WSW': 247.5, 'O': 270, 'W': 270, 'OESTE': 270, 'WEST': 270, 'ONO': 292.5, 'WNW': 292.5,
    'NO': 315, 'NW': 315, 'NOROESTE': 315, 'NNO': 337.5, 'NNW': 337.5,
}


def deg_to_compass(deg):
    if deg is None:
        return None
    return _DIRS[int((deg / 22.5) + 0.5) % 16]


def parse_ideal_deg(text):
    """Extrai os graus do vento ideal a partir do texto (ex.: 'Sudoeste (SO)')."""
    if not text:
        return None
    for tok in re.findall(r'[A-Za-zÀ-ú]+', text.upper()):
        if tok in _NAME2DEG:
            return _NAME2DEG[tok]
    return None


def _ang_diff(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def _rating(wave_height):
    """Tamanho da onda (0-5)."""
    if wave_height is None:
        return 0
    for limit, stars in ((0.3, 0), (0.6, 1), (1.0, 2), (1.5, 3), (2.2, 4)):
        if wave_height < limit:
            return stars
    return 5


def _wind_condition(wind_speed, wind_deg, ideal_deg):
    if wind_speed is not None and wind_speed < 8:
        return 'glassy'
    if ideal_deg is None or wind_deg is None:
        return None
    diff = _ang_diff(wind_deg, ideal_deg)
    if diff <= 50:
        return 'offshore'
    if diff <= 110:
        return 'cross'
    return 'onshore'


def _quality(wave_height, wind_speed, wind_deg, ideal_deg):
    """Qualidade (0-5): tamanho ajustado pelo vento."""
    size = _rating(wave_height)
    if size == 0:
        return 0
    cond = _wind_condition(wind_speed, wind_deg, ideal_deg)
    q = size
    if cond in ('offshore', 'glassy'):
        q += 1
    elif cond == 'cross':
        q -= 1
    elif cond == 'onshore':
        q -= 2
    if wind_speed is not None and wind_speed >= 35:
        q -= 1
    return max(0, min(5, q))


def _normalize(resp):
    return resp if isinstance(resp, list) else [resp]


def _day_label(date_str):
    try:
        return _WEEKDAYS[datetime.strptime(date_str, '%Y-%m-%d').weekday()]
    except (ValueError, TypeError):
        return date_str


def _col(d, name, n):
    return (d.get(name) or [None] * n)


def _chart_hourly(mh, wh, current_time):
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
    wave, tide = _col(mh, 'wave_height', n), _col(mh, 'sea_level_height_msl', n)
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


def _day_hours(mh, wh, date_str, ideal_deg):
    times = mh.get('time') or []
    n = len(times)
    wave, wdir = _col(mh, 'wave_height', n), _col(mh, 'wave_direction', n)
    wind, windd = _col(wh, 'wind_speed_10m', n), _col(wh, 'wind_direction_10m', n)
    hours = []
    for i, t in enumerate(times):
        if not t.startswith(date_str):
            continue
        try:
            hh = datetime.strptime(t, '%Y-%m-%dT%H:%M')
        except (ValueError, TypeError):
            continue
        if hh.hour % DAY_STEP != 0:
            continue
        ws = round(wind[i]) if i < len(wind) and wind[i] is not None else None
        wdg = windd[i] if i < len(windd) else None
        hours.append({
            'h': hh.strftime('%Hh'),
            'wave': round(wave[i], 1) if i < len(wave) and wave[i] is not None else None,
            'wave_dir': deg_to_compass(wdir[i] if i < len(wdir) else None),
            'wave_deg': wdir[i] if i < len(wdir) else None,
            'wind': ws, 'wind_dir': deg_to_compass(wdg), 'wind_deg': wdg,
            'cond': _wind_condition(ws, wdg, ideal_deg),
            'quality': _quality(wave[i] if i < len(wave) else None, ws, wdg, ideal_deg),
        })
    return hours


def get_forecast(spots):
    spots = [s for s in spots if s.latitude is not None and s.longitude is not None]
    if not spots:
        return {}

    key = ','.join(str(s.id) for s in sorted(spots, key=lambda s: s.id))
    now = time.time()
    cached = _CACHE.get(key)
    if cached and (now - cached['ts']) < TTL:
        return cached['data']

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
            ideal = parse_ideal_deg(getattr(spot, 'best_wind_direction', None))

            times = md.get('time') or []
            n = len(times)
            days = []
            for j, date in enumerate(times):
                wv = _col(md, 'wave_height_max', n)[j]
                wave_deg = _col(md, 'wave_direction_dominant', n)[j]
                wsp = _col(wd, 'wind_speed_10m_max', n)[j]
                wind_deg = _col(wd, 'wind_direction_10m_dominant', n)[j]
                days.append({
                    'label': _day_label(date), 'date': date,
                    'wave_height': wv, 'wave_period': _col(md, 'wave_period_max', n)[j],
                    'wave_dir': deg_to_compass(wave_deg), 'wave_deg': wave_deg,
                    'wind_speed': wsp, 'wind_dir': deg_to_compass(wind_deg), 'wind_deg': wind_deg,
                    'rating': _rating(wv),
                    'quality': _quality(wv, wsp, wind_deg, ideal),
                    'cond': _wind_condition(wsp, wind_deg, ideal),
                    'hours': _day_hours(mh, wh, date, ideal),
                })

            cur_wave = mc.get('wave_height')
            cur_wind = wc.get('wind_speed_10m')
            cur_wind_deg = wc.get('wind_direction_10m')
            result[spot.id] = {
                'ideal_wind_deg': ideal,
                'current': {
                    'wave_height': cur_wave, 'wave_period': mc.get('wave_period'),
                    'wave_dir': deg_to_compass(mc.get('wave_direction')), 'wave_deg': mc.get('wave_direction'),
                    'wind_speed': cur_wind, 'wind_dir': deg_to_compass(cur_wind_deg), 'wind_deg': cur_wind_deg,
                    'rating': _rating(cur_wave),
                    'quality': _quality(cur_wave, cur_wind, cur_wind_deg, ideal),
                    'cond': _wind_condition(cur_wind, cur_wind_deg, ideal),
                },
                'days': days,
                'hourly': _chart_hourly(mh, wh, mc.get('time') or wc.get('time')),
            }
        except Exception:
            result[spot.id] = None

    _CACHE[key] = {'data': result, 'ts': now}
    return result
