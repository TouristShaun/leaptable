#!/usr/bin/env python

__authors__ = ["Peter W. Njenga"]
__copyright__ = "Copyright © 2023 ReframeAI, Inc."

# Standard Libraries
from typing import Annotated

# External Libraries
from loguru import logger
from asyncpg.exceptions import UniqueViolationError

# Internal Libraries
from fastapi import APIRouter, Request, HTTPException, status, Depends
from reframe.server.lib.db_models.user import User
from reframe.server.lib.db_models.namespace import Namespace, NamespaceMembership
from reframe.server.lib.security import get_api_key

router = APIRouter()


@router.post("/user/")
async def create_user(request: Request, namespace: Annotated[Namespace, Depends(get_api_key)], user: User):
    print(user)
    print(user.dict())

    try:
        await request.app.state.meta_db.execute(f"""
                INSERT INTO "user" (_id, name, email, picture)
                VALUES (%(id_)s, %(name)s, %(email)s, %(picture)s);
                """,
                user.dict()
            )

        namespace_membership = NamespaceMembership(namespace_id=namespace.id_, user_id=user.id_)
        print(namespace_membership)
        await request.app.state.meta_db.execute(f"""
                INSERT INTO namespace_membership (_id, namespace_id, user_id)
                VALUES (%(id_)s, %(namespace_id)s, %(user_id)s);
                """,
                namespace_membership.dict()
            )
    except UniqueViolationError as unique_violation_exption:
        logger.exception(unique_violation_exption)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User already exists"
        ) from None

    return {"status": "success", "message": "Created user", "user": user.dict()}

@router.get("/users/{userId}")
async def read_user(userId: str):
    user = prisma.user.find_unique(where={"id": userId}, include={"profile": True})

    if user:
        return {"success": True, "data": user}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"User with id {userId} not found",
    )
