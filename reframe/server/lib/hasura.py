#!/usr/bin/env python

__authors__ = ["Peter W. Njenga"]
__copyright__ = "Copyright © 2023 ReframeAI, Inc."

# Standard Libraries
from os import environ as os_env
import requests
import configparser

# External Libraries
from loguru import logger

HASURA_GRAPHQL_API_ENDPOINT = os_env.get("HASURA_GRAPHQL_API_ENDPOINT")
HASURA_GRAPHQL_ADMIN_SECRET = os_env.get('HASURA_GRAPHQL_ADMIN_SECRET')

def track_table(connection_name, table_name):
    logger.info(f"Tracking table '{table_name}' from '{connection_name}'")
    res = requests.post(
        f"{HASURA_GRAPHQL_API_ENDPOINT}",
        headers={
            "Content-Type": "application/json",
            "x-hasura-admin-secret": HASURA_GRAPHQL_ADMIN_SECRET,
        },
        json={
            "type": "pg_track_table",
            "args": {
                "source": connection_name,
                "table": {
                    "name": table_name,
                    "schema": "public"
                }
            }
        }
    )
    if res.status_code != 200:
        logger.error(res.json())
    else:
        logger.info("Success tracking table")

    return res

def reload_table_metadata(connection_name, table_name):
    res = requests.post(
        f"{HASURA_GRAPHQL_API_ENDPOINT}",
        headers={
            "Content-Type": "application/json",
            "x-hasura-admin-secret": HASURA_GRAPHQL_ADMIN_SECRET,
        },
        json={
            "type": "reload_metadata",
            "args": {
                "reload_sources": [connection_name]
            }
        }
    )

    res_json = res.json()
    if res.status_code != 200:
        logger.error(res_json)
        raise Exception("Error reloading metadata")
    else:
        logger.info(f"Reloaded table metadata: {res_json}")

    if not res_json.get("is_consistent", False):
        logger.warning("⚠️ Metadata is inconsistent")


    return res_json

def add_source(connection_name, db_url):
    res = requests.post(
        f"{HASURA_GRAPHQL_API_ENDPOINT}",
        headers={
            "Content-Type": "application/json",
            "x-hasura-admin-secret": HASURA_GRAPHQL_ADMIN_SECRET,
        },
        json={
            "type": "pg_add_source",
            "args": {
                "name": connection_name,
                "configuration": {
                    "connection_info": {
                        "database_url": db_url,
                        "pool_settings": {
                            "retries": 1,
                            "idle_timeout": 180,
                            "max_connections": 50
                        }
                    }
                }
            }
        }
    )

    if res.status_code != 200:
        logger.error(res.json())
        raise Exception(f"Failed to add source {connection_name} to hasura")
    else:
        logger.opt(ansi=True).info(f"Added source <green>'{connection_name}'</green> to hasura")

    return res

def untrack_table(connection_name, table_name):
    res = requests.post(
        f"{HASURA_GRAPHQL_API_ENDPOINT}",
        headers={
            "Content-Type": "application/json",
            "x-hasura-admin-secret": HASURA_GRAPHQL_ADMIN_SECRET,
        },
        json={
            "type": "pg_untrack_table",
            "args": {
                "source": connection_name,
                "table": {
                    "name": table_name,
                    "schema": "public"
                }
            }
        }
    )

    if res.status_code != 200:
        logger.error(res.json())
    else:
        logger.info(res.json())

    return res

def give_permission_to_user(connection_name, table_name):
    logger.info(f"Granting permission to user on table '{table_name}' from '{connection_name}'")
    res = requests.post(
        f"{HASURA_GRAPHQL_API_ENDPOINT}",
        headers={
            "Content-Type": "application/json",
            "x-hasura-admin-secret": HASURA_GRAPHQL_ADMIN_SECRET,
        },
        json={
            "type": "pg_create_select_permission",
            "args": {
                "source": connection_name,
                "table": {
                    "name": table_name,
                    "schema": "public"
                },
                "role": "user",
                "permission": {
                    "columns": "*",
                    "subscription_root_fields": ["select"],
                    "query_root_fields": ["select"],
                    "computed_fields": [],
                    "backend_only": False,
                    "filter": {},
                    "limit": None,
                    "allow_aggregations": False
                },
            }
        }
    )

    if res.status_code != 200:
        logger.error(res.json())
    else:
        logger.info('Success granting permission to user')

    return res