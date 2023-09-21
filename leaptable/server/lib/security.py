#!/usr/bin/env python

__authors__ = ["Peter W. Njenga"]
__copyright__ = "Copyright © 2023 Leaptable, Inc."

# Standard Libraries
import json

# External Libraries
from loguru import logger
from fastapi.security import HTTPBearer
from fastapi import Request, HTTPException, Depends, Security, status

# Internal Libraries
from leaptable.server.lib.db_connection import Database
from fastapi.security import APIKeyHeader
from leaptable.server.lib.db_models.namespace import Namespace

# Scheme for the Authorization header
token_auth_scheme = HTTPBearer()

api_key_header = APIKeyHeader(name="X-API-KEY")
async def get_api_key(request: Request, api_key_header: str = Security(api_key_header)) -> str:

    print(api_key_header)
    # Check the API key
    db_api_key = await request.app.state.meta_db.fetch_one(
        """SELECT * FROM API_KEY WHERE key = %(key)s""",
        {'key': api_key_header})
    if db_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )

    try:
        namespace_id = db_api_key['namespace_id']
        # Update the usage count
        await request.app.state.meta_db.execute(
            """UPDATE api_key 
                   SET usage_count = usage_count + 1
                WHERE _id = %(_id)s;
            """, {'_id': db_api_key['_id']})

        # Get the namespace
        db_namespace = await request.app.state.meta_db.fetch_one(
            """SELECT * FROM namespace WHERE _id = %(_id)s""",
            {'_id': namespace_id})

        # Connect to the namespace and create the trace schema
        if namespace_id not in request.app.state.trace_db:
            trace_db = Database(**json.loads(db_namespace['trace_db_params']))
            await trace_db.connect()

            request.app.state.trace_db[namespace_id] = trace_db
            logger.info(f"Created new connection to namespace trace_db {trace_db}")

        if namespace_id not in request.app.state.data_db:
            data_db = Database(**json.loads(db_namespace['data_db_params']))
            await data_db.connect()

            request.app.state.data_db[namespace_id] = data_db
            logger.info(f"Created new connection to namespace data_db {data_db}")

        logger.info(f"Using namespace->{db_namespace['slug']} ({db_namespace['name']})")

        ns ={
            **db_namespace,
            'trace_db': request.app.state.trace_db[namespace_id],
            'data_db': request.app.state.data_db[namespace_id],
            'trace_db_params': {},
            'data_db_params': {}
        }

        return Namespace(**ns)

    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )