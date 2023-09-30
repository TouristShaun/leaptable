#!/usr/bin/env python

__authors__ = ["Peter W. Njenga"]
__copyright__ = "Copyright © 2023 ReframeAI, Co."

# Standard Libraries
import time

# External Libraries
from loguru import logger
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# Internal Libraries
from reframe.server.lib import tenant
from reframe.server.routers import router
from reframe.server.lib.db_session import database_instance

load_dotenv('.env')
logger.info("Loaded .env file")

app = FastAPI(
    title="reframe",
    description="Supercharge your workflows on data tables using LLM agents.",
    version="0.0.1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    print(f"Total request time: {process_time} secs")
    return response


@app.on_event("startup")
async def startup():
    tenant.init_default()
    await database_instance.connect()
    app.state.meta_db = database_instance
    app.state.trace_db = {}
    app.state.data_db = {}


@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down server.")


app.include_router(router)
