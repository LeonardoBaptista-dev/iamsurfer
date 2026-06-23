"""Alertas de swell: notifica quem segue um pico quando ele vai bombar.

Olha a previsão (surf_forecast / Open-Meteo) dos picos que têm seguidores e,
quando a melhor janela dos próximos dias atinge uma qualidade >= GOOD_QUALITY,
cria uma Notification (tipo 'swell') para cada seguidor — com dedupe para não
spammar (no máximo 1 alerta por pico/usuário a cada `dedupe_hours`).

Rodar:
    python check_swell_alerts.py          # via CLI/cron
    GET /cron/swell-alerts?key=CRON_KEY   # via cron externo (rota protegida)
"""
from datetime import datetime, timedelta

from extensions import db
from models import Spot, SpotFollow, Notification
from surf_forecast import get_forecast

GOOD_QUALITY = 4          # 0-5; 4+ = "vai bombar"
HORIZON_DAYS = 2          # avisa com até 2 dias de antecedência
DEDUPE_HOURS = 18         # não repete alerta do mesmo pico antes disso

_COND_TXT = {
    'offshore': 'vento offshore', 'glassy': 'mar glassy',
    'cross': 'vento cross', 'onshore': 'vento onshore',
}


def _best_upcoming(fc, horizon_days):
    """(dia, melhor_qualidade) da melhor janela dentro do horizonte, ou None."""
    if not fc or not fc.get('days'):
        return None
    best = None
    for day in fc['days'][:horizon_days + 1]:
        qualities = [h['quality'] for h in day.get('hours', []) if h.get('quality') is not None]
        hq = max(qualities) if qualities else (day.get('quality') or 0)
        if best is None or hq > best[1]:
            best = (day, hq)
    return best


def _message(spot, day, quality):
    wv = day.get('wave_height')
    wave_txt = f"{wv:.1f}m" if wv else "ondas boas"
    cond_txt = _COND_TXT.get(day.get('cond') or '', '')
    extra = f" · {cond_txt}" if cond_txt else ''
    return f"{spot.name} vai bombar {day.get('label', 'em breve')}! {wave_txt}{extra} · qualidade {quality}/5".strip()


def run_swell_alerts(min_quality=GOOD_QUALITY, horizon_days=HORIZON_DAYS, dedupe_hours=DEDUPE_HOURS):
    """Cria notificações de swell. Retorna um resumo dict."""
    spot_ids = [r[0] for r in db.session.query(SpotFollow.spot_id).distinct().all()]
    if not spot_ids:
        return {'spots_seguidos': 0, 'picos_bombando': 0, 'alertas': 0}

    spots = Spot.query.filter(Spot.id.in_(spot_ids)).all()
    forecast = get_forecast(spots)
    cutoff = datetime.utcnow() - timedelta(hours=dedupe_hours)
    firing, notified = 0, 0

    for spot in spots:
        best = _best_upcoming(forecast.get(spot.id), horizon_days)
        if not best or best[1] < min_quality:
            continue
        firing += 1
        day, quality = best
        content = _message(spot, day, quality)
        follower_ids = [r[0] for r in db.session.query(SpotFollow.user_id)
                        .filter(SpotFollow.spot_id == spot.id).all()]
        for uid in follower_ids:
            recent = Notification.query.filter(
                Notification.user_id == uid,
                Notification.type == 'swell',
                Notification.related_spot_id == spot.id,
                Notification.created_at >= cutoff,
            ).first()
            if recent:
                continue
            db.session.add(Notification(
                user_id=uid, type='swell', content=content,
                related_spot_id=spot.id, read=False))
            notified += 1

    db.session.commit()
    return {'spots_seguidos': len(spots), 'picos_bombando': firing, 'alertas': notified}
