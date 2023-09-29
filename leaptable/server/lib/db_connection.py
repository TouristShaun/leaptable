#!/usr/bin/env python

__authors__ = ["Peter W. Njenga"]
__copyright__ = "Copyright © 2023 Leaptable, Inc."

# Standard Libraries
import collections
import itertools
import json
from os import environ as os_env
from typing import Any, Dict, Tuple, List
from contextlib import contextmanager, asynccontextmanager

from pprint import pformat

# External Libraries
import asyncpg
from dotenv import load_dotenv
from loguru import logger
from pydantic import BaseModel
from dataclasses import dataclass

load_dotenv('.env')
logger.info("Loaded .env file")

def pyformat2psql(query: str, named_args: Dict[str, Any]) -> Tuple[str, List[Any]]:
    positional_generator = itertools.count(1)
    positional_map = collections.defaultdict(lambda: '${}'.format(next(positional_generator)))
    formatted_query = query % positional_map
    positional_items = sorted(
        positional_map.items(),
        key=lambda item: int(item[1].replace('$', '')),
    )
    positional_args = []
    for named_arg, _ in positional_items:
        _arg = named_args[named_arg]
        if isinstance(_arg, BaseModel):
            _arg = _arg.dict()
        elif isinstance(_arg, list):
            _arg = pformat(_arg)
        elif isinstance(_arg, dict):
            _arg = json.dumps(_arg)
        elif isinstance(_arg, (str, int, float, bool)):
            _arg = _arg
        else:
            _arg = str(_arg)
        positional_args.append(_arg)
    return formatted_query, positional_args

@dataclass
class Database():
    database: str = os_env.get('LEAPTABLE_META_DB_NAME', 'postgres')
    host: str = os_env.get('LEAPTABLE_META_DB_HOST', "localhost")
    user: str = os_env.get('LEAPTABLE_META_DB_USER', 'postgres')
    password: str = os_env.get('LEAPTABLE_META_DB_PASS')
    port: str = os_env.get('LEAPTABLE_META_DB_PORT', 5432)

    def __init__(self,
                 host: str = None, user: str = None,
                 password: str = None, port: str = None,
                 database: str = None) -> None:

        # Set self.host to the value passed in or default to checking environment variable
        self.host = host or self.host
        self.user = user or self.user
        self.password = password or self.password
        self.port = port or self.port
        self.database = database or self.database
        self._cursor = None

        self._connection_pool = None
        self.con = None

    async def connect(self):
        if not self._connection_pool:
            try:
                self._connection_pool = await asyncpg.create_pool(
                    min_size=1,
                    max_size=10,
                    command_timeout=60,
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                )
                logger.debug(f"Connected to database {self}")
            except Exception as e:
                logger.exception(e)

    @asynccontextmanager
    async def transaction(self) -> asyncpg.Record:
        if not self._connection_pool:
            await self.connect()

        self.con = await self._connection_pool.acquire()
        yield self.con
        await self._connection_pool.release(self.con)

    async def fetch_list(self, query: str, params: dict = {}) -> list[asyncpg.Record]:
        if not self._connection_pool:
            await self.connect()

        self.con = await self._connection_pool.acquire()
        try:
            new_query, positional_args = pyformat2psql(query, params)
            result = await self.con.fetch(new_query, *positional_args)
            return result
        except Exception as e:
            logger.exception(e)
        finally:
            await self._connection_pool.release(self.con)

    async def fetch_one(self, query: str, params: dict = {}) -> asyncpg.Record:
        if not self._connection_pool:
            await self.connect()

        self.con = await self._connection_pool.acquire()
        try:
            new_query, positional_args = pyformat2psql(query, params)
            result = await self.con.fetchrow(new_query, *positional_args)
            return result
        except Exception as e:
            logger.exception(e)
        finally:
            await self._connection_pool.release(self.con)

    async def execute(self, query: str, params: dict = {}) -> asyncpg.Record:
        if not self._connection_pool:
            await self.connect()

        self.con = await self._connection_pool.acquire()
        try:
            new_query, positional_args = pyformat2psql(query, params)
            result = await self.con.execute(new_query, *positional_args)
            return result
        except asyncpg.exceptions.UndefinedColumnError as undefined_column_error:
            logger.error(f"""
            Error: {undefined_column_error}
            Query: {new_query}
            """)
            raise undefined_column_error
        except asyncpg.exceptions.NotNullViolationError as not_null_violation_error:
            logger.error(f""" NotNullViolationError↵
            Error: {not_null_violation_error}
            Query: {new_query}
            Params: {positional_args}
            """)
            raise not_null_violation_error
        except asyncpg.exceptions.DataError as data_error:
            logger.error(f""" DataError↵
                Error: {data_error}
                Query: {new_query}
                Params: {positional_args}
                """)
            raise data_error
        except Exception as e:
            logger.exception(e)
            raise e
        finally:
            await self._connection_pool.release(self.con)

    def __str__(self):
        connection = {
            'host': self.host,
            'user': self.user,
            'password': "****",
            'port': self.port,
            'database': self.database
        }
        return f'{pformat(connection)}'

    def to_url_str(self):
        return f'postgresql://{self.user}:{self.password}@{self.host}/{self.database}'


