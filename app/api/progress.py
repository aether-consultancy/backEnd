import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.connection import get_db
from app.db.models import Kid, UserProgress
from app.cache.redis_client import redis_client
from app.api.deps import get_current_kid

router = APIRouter(prefix="/progress", tags=["progress"])
CACHE_TTL = 60 * 60


def _cache_key(kid_id: int) -> str:
    return f"progress:{kid_id}"


@router.get("/{kid_id}")
def get_progress(kid_id: int, db: Session = Depends(get_db), kid: Kid = Depends(get_current_kid)):
    if kid.id != kid_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your progress")

    cached = redis_client.get(_cache_key(kid_id))
    if cached:
        return json.loads(cached)

    row = db.query(UserProgress).filter(UserProgress.kid_id == kid_id).first()
    data = row.data if row else {}
    redis_client.setex(_cache_key(kid_id), CACHE_TTL, json.dumps(data))
    return data


@router.put("/{kid_id}")
def update_progress(kid_id: int, payload: dict, db: Session = Depends(get_db), kid: Kid = Depends(get_current_kid)):
    if kid.id != kid_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your progress")

    row = db.query(UserProgress).filter(UserProgress.kid_id == kid_id).first()
    if row:
        row.data = payload
    else:
        row = UserProgress(kid_id=kid_id, data=payload)
        db.add(row)
    db.commit()

    redis_client.setex(_cache_key(kid_id), CACHE_TTL, json.dumps(payload))
    return {"status": "ok"}
