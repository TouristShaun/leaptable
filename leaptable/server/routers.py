#!/usr/bin/env python

__authors__ = ["Peter W. Njenga"]
__copyright__ = "Copyright © 2023 Leaptable, Co."

from fastapi import APIRouter

from leaptable.server.api import (
    agents,
    prompt,
    user,
    namespace,
    system,
    dataframe,
)

router = APIRouter()
api_prefix = "/api/v1"

router.include_router(agents.router, tags=["Agent"], prefix=api_prefix)
router.include_router(user.router, tags=["User"], prefix=api_prefix)
router.include_router(prompt.router, tags=["Prompt"], prefix=api_prefix)
router.include_router(namespace.router, tags=["Namespace"], prefix=api_prefix)
router.include_router(system.router, tags=["System"], prefix=api_prefix)
router.include_router(dataframe.router, tags=["Prompt"], prefix=api_prefix)
