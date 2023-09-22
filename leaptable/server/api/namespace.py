#!/usr/bin/env python

__authors__ = ["Peter W. Njenga"]
__copyright__ = "Copyright © 2023 Leaptable, Inc."

# Standard Libraries
import json
from os import environ as os_env

# External Libraries
from fastapi import APIRouter, Request, HTTPException, status
from loguru import logger
from pprint import pformat, pprint

# Internal Libraries
from slugify import slugify
from uuid6 import uuid7

from leaptable.server.lib import sql_text, hasura
from leaptable.server.lib.api_key import generate_api_key
from leaptable.server.lib.db_connection import Database
from leaptable.server.lib.db_models.namespace import Namespace

# Global Variables
router = APIRouter()

class Serial(dict):
    def __getitem__(self, key):
        return f"${list(self.keys()).index(key) + 1}"

@router.post("/namespace/", name="Create Namespace", description="Create Workspace or Namespace")
async def create_namespace(request: Request, namespace: Namespace):
    """Agents endpoint"""
    try:
        # Check that the slug is valid. It should be in snake case, alphanumeric, and lowercase.
        if slugify(namespace.slug, separator='_') != namespace.slug:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid slug '{namespace.slug}'. Must be lowercase, alphanumeric, and snake case"
            )

        pprint(namespace.dict())

        namespace_short_id = str(namespace.id_).split("-")[3]
        data_db_name = f"leaptable_datadb_{namespace_short_id}_{namespace.slug}"
        trace_db_name = f"leaptable_tracedb_{namespace_short_id}_{namespace.slug}"

        namespace.data_db_params = {
            "host": os_env.get("LEAPTABLE_DATA_DB_HOST"),
            "database": data_db_name,
            "password": os_env.get("LEAPTABLE_DATA_DB_PASS"),
            "user": os_env.get("LEAPTABLE_DATA_DB_USER"),
            "port": os_env.get("LEAPTABLE_DATA_DB_PORT")
        }
        namespace.trace_db_params = {
            "host": os_env.get("LEAPTABLE_TRACE_DB_HOST"),
            "database": trace_db_name,
            "password": os_env.get("LEAPTABLE_TRACE_DB_PASS"),
            "user": os_env.get("LEAPTABLE_DATA_DB_USER"),
            "port": os_env.get("LEAPTABLE_DATA_DB_PORT")
        }

        namespace.hasura_params = {
            "data_db": data_db_name,
            "trace_db": trace_db_name
        }

        # TODO: These commands always create a database in the existing metadata DB host. Refactor
        # to enable to them use separate datadb and tracedb hosts.

        # Create the data database and grant privileges to the leaptable user.
        await request.app.state.meta_db.execute(
            "CREATE DATABASE {db_name}".format(db_name=data_db_name)
        )

        await request.app.state.meta_db.execute(
            "GRANT ALL PRIVILEGES ON DATABASE {db_name} TO leaptable".format(db_name=data_db_name)
        )
        logger.info(f"Created Data database {data_db_name} for workspace {namespace.slug}")

        logger.info(f"Created Data database {data_db_name} for workspace {namespace.slug}")

        # Create the trace database and grant privileges to the leaptable user.
        await request.app.state.meta_db.execute(
            "CREATE DATABASE {db_name}".format(db_name=trace_db_name)
        )

        await request.app.state.meta_db.execute(
            "GRANT ALL PRIVILEGES ON DATABASE {db_name} TO leaptable".format(db_name=trace_db_name)
        )
        logger.info(f"Created Trace database {trace_db_name} for workspace {namespace.slug}")

        try:
            pprint(namespace.data_db_params)
            namespace.data_db = Database(**namespace.data_db_params)
            await namespace.data_db.connect()
            request.app.state.data_db[str(namespace.id_)] = namespace.data_db
            logger.info("Connected to namespace data_db")
            await namespace.data_db.execute("CREATE EXTENSION IF NOT EXISTS moddatetime")

            namespace.trace_db = Database(**namespace.trace_db_params)
            await namespace.trace_db.connect()
            request.app.state.trace_db[str(namespace.id_)] = namespace.trace_db
            logger.info("Connected to namespace trace_db")
            await namespace.trace_db.execute("CREATE EXTENSION IF NOT EXISTS moddatetime")
        except Exception as e:
            logger.error(f"Error connecting to data database: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error connecting to data database: {e}"
            )  from None

        await request.app.state.meta_db.execute(
            """ 
            INSERT INTO namespace (_id, slug, name, data_db_params, trace_db_params, hasura_params)
            VALUES (%(id_)s, %(slug)s, %(name)s, %(data_db_params)s, %(trace_db_params)s, %(hasura_params)s)
            RETURNING _id, slug, name
            """, namespace.dict())

        logger.info(f"Created new namespace: {pformat(namespace.dict(include=['id_', 'name', 'slug']))}")

        api_key = generate_api_key()
        namespace.api_key = api_key
        await request.app.state.meta_db.execute(
            """
            INSERT INTO api_key (_id, key, namespace_id, name)
            VALUES (%(_id)s, %(key)s, %(namespace_id)s, %(name)s)
            RETURNING _id
            """, {
                "_id": uuid7(),
                "key": api_key,
                "namespace_id": namespace.id_,
                'name': f"Default API Key for {namespace.name}"
            })

        logger.info("Created new API Key")

        # Connect to the new database and create the trace schema
        await namespace.trace_db.execute("CREATE SCHEMA IF NOT EXISTS trace")


        # Create the trace tables
        tables = {
            'trace': sql_text.CREATE_TABLE_TRACE,
            'job': sql_text.CREATE_TABLE_JOB,
            'thread': sql_text.CREATE_TABLE_THREAD,
            'agent': sql_text.CREATE_TABLE_AGENT,
            'tool': sql_text.CREATE_TABLE_TOOL,
        }

        for table_name, table_sql in tables.items():
            await namespace.trace_db.execute(table_sql.format(table_name=table_name))
            logger.info(f"Created new table: {table_name}")

        # Track the databases on Hasura.
        hasura_connections = {
            data_db_name: namespace.data_db.to_url_str(),
            trace_db_name: namespace.trace_db.to_url_str()
        }

        for connection_name, connection_url in hasura_connections.items():
            try:
                print(connection_name, connection_url)
                hasura.add_source(connection_name, connection_url)
            except Exception as e:
                logger.error(f"Error adding source {connection_name} to Hasura: {e}")


        logger.info(f"Done initializing namespace: {pformat({k : namespace.dict()[k] for k in ['id_', 'name', 'slug']})}")

        return {"success": True, "data": {k : namespace.dict()[k] for k in ['id_', 'name', 'slug', 'api_key']}}
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )