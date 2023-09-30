#!/usr/bin/env python

__authors__ = ["Peter W. Njenga"]
__copyright__ = "Copyright © 2023 ReframeAI, Inc."

# Standard Libraries
from os import environ as env
from time import sleep
from pprint import pformat

def fmt_payload(messages, preview_len=400):
    msg = pformat(messages)

    if len(msg) > preview_len * 2:
        msg = f"{msg[:preview_len]}\n\n...\n\n{msg[-preview_len:]}"

    return msg