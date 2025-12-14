from __future__ import annotations

from fastapi import Depends, HTTPException, status

from app.auth import get_current_user
from app.models import Role, User


def require_roles(*allowed: Role):
    def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        return user

    return _dep

