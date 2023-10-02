#!/usr/bin/env python

__authors__ = ["Peter W. Njenga"]
__copyright__ = "Copyright © 2023 ReframeAI, Inc."

# Standard Libraries
import asyncio
import inspect
from os import environ as os_env
import hashlib
from abc import ABCMeta, abstractmethod
import json
import platform
from datetime import datetime, timezone
from pprint import pprint, pformat

# External Libraries
import redis
from loguru import logger

# Internal Libraries
from reframe.lib.utils import fmt_payload
from reframe.lib.core import RedisStreamProcessor

# Global Variables
CACHE_EXPIRATION_DURATION = 60 * 60 * 24 * 90 # 90 days
TASK_EXPIRATION_DURATION = 60 * 60 * 24 * 2 # 48 Hours

REDIS_STREAM_HOST=os_env.get('REDIS_STREAM_HOST', "localhost")
REDIS_CACHE_HOST=os_env.get('REDIS_CACHE_HOST', "localhost")
REDIS_PASSWORD=os_env.get('REDIS_PASSWORD')
REDIS_USER=os_env.get('REDIS_USER')
red_stream = redis.StrictRedis(
    REDIS_STREAM_HOST, 6379, charset="utf-8", username=REDIS_USER,
    password=REDIS_PASSWORD, decode_responses=True)
red_cache = redis.StrictRedis(
    REDIS_CACHE_HOST, 6379, charset="utf-8", username=REDIS_USER,
    password=REDIS_PASSWORD, decode_responses=True)
# ------------------------------

def _hasattr(C, attr):
    return any(attr in B.__dict__ for B in C.__mro__)

# Class to be inherited by all tools.
# AsyncTool is an abstract class that defines the interface for all tools.
class AsyncTool(RedisStreamProcessor):
    def __init__(self, name, invoke_commands, read_cache=True, write_cache=True, *args, **kwargs):
        self.name = name
        self.tool_name = name
        self.invoke_commands = invoke_commands
        self.read_cache = read_cache
        self.write_cache = write_cache


        super().__init__(instream_key=f"tool->{self.tool_name}")

    @abstractmethod
    def async_exec(self, *args, **kwargs):
        raise NotImplementedError("Must override function async_exec")

    # Receive messages from the stream and execute the async_exec function.
    # This function is called in an infinite loop by the run function.
    async def _inner(self, *args, **kwargs):
        last_processed_message_id = self.get_last_processed_message_id()
        items = red_stream.xread(count=3, streams={self.instream_key: last_processed_message_id}, block=1000)

        for _k in items:
            stream_key, stream_messages = _k
            for _j in stream_messages:
                message_id, message_data = _j

                correlation_id = message_data.get('correlation_id')
                payload = json.loads(message_data.get('payload'))
                agent = message_data.get('agent')

                arg_names = inspect.getfullargspec(self.async_exec)[0]
                kwarg_names = inspect.getfullargspec(self.async_exec)[2]

                # Extract the function arguments from the payload
                # Todo: Add support for kwargs
                args = [payload.get(arg_name) for arg_name in arg_names if arg_name not in ['self']]
                args_dict = {arg_name: payload.get(arg_name, None) for arg_name in arg_names if arg_name not in ['self']}

                logger.opt(ansi=True).info(f"Running tool for agent:: <yellow>{agent}</yellow> with args: {args} and kwargs: {kwargs}. payload: {payload} correlation_id: <yellow>{correlation_id}</yellow>")
                arg_dict_str = json.dumps(args_dict, sort_keys=True)
                arg_dict_hash = hashlib.sha256(arg_dict_str.encode('utf-8')).hexdigest()
                cache_key = f"reframe::fn-cache::agent-run::tool->{self.tool_name}::elem->{arg_dict_hash}"

                found_in_cache = False
                if self.read_cache:
                    cache_val = red_cache.get(cache_key)

                    if cache_val:
                        logger.opt(ansi=True).debug(f'Found element in cache - returning cached results. <green>{fmt_payload(cache_val)}...</green>')
                        try:
                            # Attempt to load the cache value as a json.
                            result_dict = json.loads(cache_val)
                            found_in_cache = True
                        except Exception as e:
                            logger.exception(e)
                    else:
                        logger.debug(f'No cache found for key {cache_key}')

                # Not found in cache or using cache. Run the agent.
                if not found_in_cache:
                    logger.debug('No cache found or skipping cache - running function')
                    try:
                        start_time = datetime.now(timezone.utc)
                        tool_result = await self.async_exec(*args)
                        end_time = datetime.now(timezone.utc)
                        logger.info(f"Run tool::{self.tool_name} execution time:{end_time - start_time}")

                        # If success. The result is a dict with the result and status
                        result_dict = {
                            "result": tool_result,
                            "status": "SUCCESS",
                            "start_time": start_time,
                            "end_time": end_time,
                        }
                    except Exception as e:
                        logger.exception(e)
                        # If error. The result is a dict with the error and status
                        result_dict = {
                            "error": str(e),
                            "status": "ERROR",
                        }
                    finally:
                        # Write the result to cache
                        if self.write_cache:
                            red_cache.set(
                                cache_key,
                                json.dumps(result_dict, default=str),
                                ex=CACHE_EXPIRATION_DURATION
                            )
                # Write the results to the outstream to be picked up by the agent
                res_stream_key = f"reframe::outstream::agent->{agent}::tool->{self.tool_name}"

                red_stream.xadd(res_stream_key, {
                    'payload': json.dumps(result_dict, default=str),
                    'correlation_id': correlation_id,
                })
                self.set_last_processed_message_id(message_id)
                logger.info(f"Finished running tool::{self.tool_name}. Set last processed message id to {message_id}. Wrote result to stream {res_stream_key}")

        return None

    def run(self, *args, **kwargs):
        logger.debug("Running AsyncTool", *args, **kwargs)
        self.new_event_loop = asyncio.new_event_loop()
        try:
            while True:
                self.new_event_loop.run_until_complete(self._inner())
        except redis.exceptions.ConnectionError as redis_connection_error:
            pass
            logger.critical(f"Redis connection error: {redis_connection_error}. Is Redis running and variable 'REDIS_STREAM_HOST' set?")
        finally:
            self.new_event_loop.close()


# Class to be inherited by all tools.
# AsyncTool is an abstract class that defines the interface for all tools.
class Tool(RedisStreamProcessor):
    def __init__(self, name, invoke_commands, read_cache=True, write_cache=True, *args, **kwargs):
        self.name = name
        self.tool_name = name
        self.invoke_commands = invoke_commands
        self.read_cache = read_cache
        self.write_cache = write_cache
        self._last_processed_message_id = '0-0'
        self.stream_start_id = '0-0'
        self.check_backlog = True


        super().__init__(instream_key=f"tool->{self.tool_name}")

    @abstractmethod
    def exec(self, *args, **kwargs):
        raise NotImplementedError("Must override function async_exec")

    # Receive messages from the stream and execute the async_exec function.
    # This function is called in an infinite loop by the run function.
    async def _inner(self, *args, **kwargs):
        items = red_stream.xreadgroup(self.groupname, consumername=platform.node(), count=3,
                                      streams={self.instream_key: self.stream_start_id}, block=500)

        if len(items) == 0:
            return None

        self.stream_start_id = '>'

        # self.check_backlog = False if len(items[0][1]) == 0 else True

        for _k in items:
            stream_key, stream_messages = _k
            for _j in stream_messages:
                message_id, message_data = _j

                correlation_id = message_data.get('correlation_id')
                payload = json.loads(message_data.get('payload'))
                agent = message_data.get('agent')

                arg_names = inspect.getfullargspec(self.exec)[0]
                kwarg_names = inspect.getfullargspec(self.exec)[2]

                # Extract the function arguments from the payload
                # Todo: Add support for kwargs
                args = [payload.get(arg_name) for arg_name in arg_names if arg_name not in ['self']]
                args_dict = {arg_name: payload.get(arg_name, None) for arg_name in arg_names if arg_name not in ['self']}

                logger.opt(ansi=True).info(f"Running tool for agent:: <yellow>{agent}</yellow> with args: {args} and kwargs: {kwargs}. payload: {payload} correlation_id: <yellow>{correlation_id}</yellow>")

                arg_dict_str = json.dumps(args_dict, sort_keys=True)
                arg_dict_hash = hashlib.sha256(arg_dict_str.encode('utf-8')).hexdigest()
                cache_key = f"reframe::fn-cache::agent-run::tool->{self.tool_name}::elem->{arg_dict_hash}"

                found_in_cache = False
                if self.read_cache:
                    cache_val = red_cache.get(cache_key)

                    if cache_val:
                        logger.opt(ansi=True).debug(f'Found element in cache - returning cached results. <green>{fmt_payload(cache_val)}...</green>')
                        try:
                            # Attempt to load the cache value as a json.
                            result_dict = json.loads(cache_val)
                            found_in_cache = True
                        except Exception as e:
                            logger.exception(e)
                    else:
                        logger.debug(f'No cache found for key {cache_key}')

                # Not found in cache or using cache. Run the agent.
                if not found_in_cache:
                    logger.debug('No cache found or skipping cache - running function')
                    try:
                        start_time = datetime.now(timezone.utc)
                        tool_result = self.exec(*args)
                        end_time = datetime.now(timezone.utc)
                        logger.info(f"Run tool::{self.tool_name} execution time:{end_time - start_time}")

                        # If success. The result is a dict with the result and status
                        result_dict = {
                            "result": tool_result,
                            "status": "SUCCESS",
                            "start_time": start_time,
                            "end_time": end_time,
                        }
                    except Exception as e:
                        logger.exception(e)
                        # If error. The result is a dict with the error and status
                        result_dict = {
                            "error": str(e),
                            "status": "ERROR",
                        }
                    finally:
                        # Write the result to cache
                        if self.write_cache:
                            red_cache.set(
                                cache_key,
                                json.dumps(result_dict, default=str),
                                ex=CACHE_EXPIRATION_DURATION
                            )
                # Write the results to the outstream to be picked up by the agent
                res_stream_key = f"reframe::outstream::agent->{agent}::tool->{self.tool_name}"

                red_stream.xadd(res_stream_key, {
                    'payload': json.dumps(result_dict, default=str),
                    'correlation_id': correlation_id,
                })
                # self.set_last_processed_message_id(message_id)
                self._last_processed_message_id = message_id
                red_stream.xack(stream_key, self.groupname, message_id)
                logger.info(f"Finished running tool::{self.tool_name}. Set last processed message id to {message_id}. Wrote result to stream {res_stream_key}")

        return None

    def run(self, *args, **kwargs):
        logger.debug("Running Sync Tool", *args, **kwargs)
        self.new_event_loop = asyncio.new_event_loop()
        try:
            while True:
                self.new_event_loop.run_until_complete(self._inner())
        except redis.exceptions.ConnectionError as redis_connection_error:
            pass
            logger.critical(f"Redis connection error: {redis_connection_error}. Is Redis running and variable 'REDIS_STREAM_HOST' set?")
        finally:
            self.new_event_loop.close()