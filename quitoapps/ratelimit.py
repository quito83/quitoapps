"""Límite de intentos guardado en BD (válido en entornos serverless)."""
from datetime import timedelta

from flask import request

from . import db
from .models import RateEvent, utcnow


def client_ip():
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.headers.get("X-Real-Ip") or request.remote_addr or "unknown"


def is_limited(kind, key, limit, window_minutes):
    since = utcnow() - timedelta(minutes=window_minutes)
    count = (
        db.session.query(RateEvent)
        .filter(RateEvent.kind == kind, RateEvent.key == key, RateEvent.created_at >= since)
        .count()
    )
    return count >= limit


def record(kind, key):
    db.session.add(RateEvent(kind=kind, key=key))
    # Limpieza oportunista de eventos de más de un día.
    db.session.query(RateEvent).filter(RateEvent.created_at < utcnow() - timedelta(days=1)).delete()
    db.session.commit()


def clear(kind, key):
    db.session.query(RateEvent).filter(RateEvent.kind == kind, RateEvent.key == key).delete()
    db.session.commit()
