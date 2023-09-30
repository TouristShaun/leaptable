#!/usr/bin/env python

__authors__ = ["Peter W. Njenga"]
__copyright__ = "Copyright © 2023 ReframeAI, Inc."

# Standard Libraries

# External Libraries
from loguru import logger

# Internal Libraries

# Global Variables

# Functions
def init_default():
    # agent = prisma.tenant.find_unique(where={"slug": 'default'}, include={"prompt": True})

    logger.info("🏠 Initialized default tenant")