#!/usr/bin/env python

__authors__ = ["Peter W. Njenga"]
__copyright__ = "Copyright © 2023 ReframeAI, Inc."

# Standard Libraries
from os import environ as os_env

# External Libraries
import redis
from loguru import logger

# Internal Libraries

# Global Variables
REDIS_STREAM_HOST=os_env.get('REDIS_STREAM_HOST', "localhost")
REDIS_PASSWORD=os_env.get('REDIS_PASSWORD')
REDIS_USER=os_env.get('REDIS_USER')
red_stream = redis.StrictRedis(
    REDIS_STREAM_HOST, 6379, charset="utf-8", username=REDIS_USER,
    password=REDIS_PASSWORD, decode_responses=True)
# ------------------------------

# Class for processing redis streams.
#
# Keeps track of the last processed message id via a redis set.
# Create an abstract class that defines the interface for tools and agents that process streams.
# The class is not meant to be instantiated directly. It is meant to be inherited by other classes.
# This class is a mixin class. It is meant to be inherited by other classes.
# https://stackoverflow.com/questions/533631/what-is-a-mixin-and-why-is-it-useful
class RedisStreamProcessor:

    # Params
    # @instream_key: The redis set key used to track the last processed message id.
    def __init__(self, instream_key, *args, **kwargs):
        super().__init__(*args, **kwargs)  # forwards all unused arguments

        self.instream_key = f"reframe::instream::{instream_key }"
        self.groupname = f"{self.instream_key}::group"
        self.last_processed_stream_key = f"{self.instream_key}::processed_pointer"
        self.last_processed_message_id = red_stream.get(self.last_processed_stream_key)
        logger.debug(f"Instream key:: {self.instream_key}")
        logger.debug(f"Last processed message id: {self.last_processed_message_id}")

        self.create_group(self.instream_key, self.groupname)

    # Return the last processed redis message id or "0-0" if none is found.
    def get_last_processed_message_id(self):
        last_processed_message_id = red_stream.get(self.last_processed_stream_key)
        if last_processed_message_id is None:
            last_processed_message_id = "0-0"

        return last_processed_message_id


    def set_last_processed_message_id(self, message_id):
        last_processed_message_id = self.get_last_processed_message_id()

        old_ts, old_seq = last_processed_message_id.split("-")
        old_ts, old_seq = int(old_ts), int(old_seq)

        new_ts, new_seq = message_id.split("-")
        new_ts, new_seq = int(new_ts), int(new_seq)

        if new_ts > old_ts:
            last_processed_message_id = message_id
        elif new_ts == old_ts and new_seq > old_seq:
            last_processed_message_id = message_id
        else:
            # Somehow we got an older message id. This should never happen.
            # Screaming and dying is the only reasonable response.
            logger.critical(f"Got an older message to process. Old: {last_processed_message_id}, New: {message_id}. Exiting")
            exit(3)

        red_stream.set(self.last_processed_stream_key, last_processed_message_id)

        return last_processed_message_id

    def create_group(self, stream_key: str, groupname: str) -> None:
        try:
            red_stream.xgroup_create(name=stream_key, groupname=groupname, id=0, mkstream=self.instream_key)
        except redis.ResponseError as e:
            logger.warning(f"raised: {e}")