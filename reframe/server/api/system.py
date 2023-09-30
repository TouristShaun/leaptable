#!/usr/bin/env python

__authors__ = ["Peter W. Njenga"]
__copyright__ = "Copyright © 2023 ReframeAI, Co."

# Standard Libraries

# External Libraries
from loguru import logger
from fastapi import APIRouter
from fastapi import Request

router = APIRouter()

@router.get("/system/health/", name="System Health", description="Checks the Health of the API Server")
async def system_health(request: Request):
    """Health check endpoint"""

    # Create the data database and grant privileges to the postgres user.
    await request.app.state.meta_db.execute("SELECT 1")
    # await request.app.state.data_db.execute("SELECT 1")
    # await request.app.state.trace_db.execute("SELECT 1")

    # TODO (Peter). Check other systems like redis and hasura
    logger.info(f"Healthy 🩵")

    return {"status": "success", "message": "Healthy 🩵"}, 200
