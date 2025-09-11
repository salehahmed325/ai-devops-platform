import os
import logging
import base64
import hashlib
from decimal import Decimal
from typing import Any, Dict, List
from dataclasses import dataclass
import json

import boto3
import httpx


# Import types for boto3 for better static analysis
from mypy_boto3_dynamodb.service_resource import (
    DynamoDBServiceResource,
    Table,
)


# --- Configuration ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
API_KEY = os.getenv("API_KEY", "dev-test-key-123")

DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "ai-devops-platform-data")
DYNAMODB_LOGS_TABLE_NAME = os.getenv(
    "DYNAMODB_LOGS_TABLE_NAME", "ai-devops-platform-logs"
)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = (
    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
)

# --- Logging Setup ---
# AWS Lambda automatically configures a logger, so we can just get it
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
logger.info(f"Lambda API Key: {API_KEY}")

# --- DynamoDB Setup ---
dynamodb: DynamoDBServiceResource = boto3.resource("dynamodb")
table: Table = dynamodb.Table(DYNAMODB_TABLE_NAME)
logs_table: Table = dynamodb.Table(DYNAMODB_LOGS_TABLE_NAME)
alert_configs_table: Table = dynamodb.Table(
    os.getenv(
        "DYNAMODB_ALERT_CONFIGS_TABLE_NAME", "ai-devops-platform-alert-configs"
    )
)


# --- Data Models ---
@dataclass
class Metric:
    metric: Dict[str, str]
    value: List[Any]


# --- Helper Functions ---
def convert_floats_to_decimals(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: convert_floats_to_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_floats_to_decimals(elem) for elem in obj]
    return obj


