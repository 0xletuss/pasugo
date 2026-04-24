#!/usr/bin/env python3
"""Test database connection"""
import sys
import logging
from sqlalchemy import text
from database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    logger.info("Testing database connection...")
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1 as connection_test"))
        logger.info(f"✅ Connection successful! Result: {result.fetchone()}")
        logger.info("Database is ready for use!")
        sys.exit(0)
except Exception as e:
    logger.error(f"❌ Connection failed: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
