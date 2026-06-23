"""Roda os alertas de swell uma vez (para cron/CLI).

    python check_swell_alerts.py
"""
from app import app
from swell_alerts import run_swell_alerts

if __name__ == '__main__':
    with app.app_context():
        result = run_swell_alerts()
        print(f"Alertas de swell: {result}")
