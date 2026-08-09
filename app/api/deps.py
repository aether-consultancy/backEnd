from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt

from app.db.connection import get_db
from app.db.models import Parent, Kid
from app.security.tokens import decode_token
from app.cache.redis_client import redis_client

bearer_scheme = HTTPBearer()


def _decode(credentials: HTTPAuthorizationCredentials) -> dict:
    token = credentials.credentials
    if redis_client.get(f"blacklist:{token}"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token has been logged out")
    try:
        return decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")


def get_current_parent(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Parent:
    claims = _decode(credentials)
    if claims.get("type") != "parent":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Parent token required")
    parent = db.query(Parent).filter(Parent.id == int(claims["sub"])).first()
    if not parent:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Parent not found")
    return parent


def get_current_kid(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Kid:
    claims = _decode(credentials)
    if claims.get("type") != "kid":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Kid token required")
    kid = db.query(Kid).filter(Kid.id == int(claims["sub"])).first()
    if not kid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Kid not found")
    return kid
