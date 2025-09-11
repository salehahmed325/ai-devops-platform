import os
import logging
import base64
import hashlib
from decimal import Decimal
from typing import Any, Dict, List
from dataclasses import dataclass

import boto3
import httpx

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database

_sym_db = _symbol_database.Default()

DESCRIPTOR = _descriptor.FileDescriptor(
  name='message.proto',
  package='',
  syntax='proto3',
  serialized_options=None,
  serialized_pb=b'\n\tmessage.proto"\x16\n\x07Message\x12\x0b\n\x03value\x18\x01 \x01(\t'
)

_MESSAGE = _descriptor.Descriptor(
  name='Message',
  full_name='Message',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='value', full_name='Message.value', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=15,
  serialized_end=37
)

Message = _reflection.GeneratedProtocolMessageType('Message', (_message.Message,), {
  'DESCRIPTOR' : _MESSAGE,
  '__module__' : 'message_pb2'
  # @@protoc_insertion_point(class_scope:Message)
  })
_sym_db.RegisterMessage(Message)


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


# --- Telegram Alerting ---
class AlertManager:
    def __init__(self, alert_configs_table: Table):
        self.alert_configs_table = alert_configs_table

    async def send_telegram_alert(self, chat_id: str, message: str):
        if not TELEGRAM_BOT_TOKEN:
            logger.warning(
                (
                    "TELEGRAM_BOT_TOKEN is not set. "
                    "Cannot send Telegram alert."
                )
            )
            return

        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(TELEGRAM_API_URL, json=payload)
                response.raise_for_status()
                logger.info(f"Telegram alert sent to chat ID {chat_id}.")
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while sending Telegram alert: {e}"
            )


# --- Main Lambda Handler ---
def handler(event, context):
    try:
        # --- Security Check ---
        headers = event.get("headers", {})
        logger.info(f"Received headers: {headers}")
        api_key_received = headers.get("x-api-key")
        logger.info(f"API Key received from headers: {api_key_received}")
        if api_key_received != API_KEY:
            logger.warning("Invalid or missing API Key.")
            return {"statusCode": 403, "body": "Forbidden: Invalid API Key"}

        # --- Request Body Processing ---
        body = event.get("body", "").encode('utf-8')

        if not body:
            logger.warning("Request body is empty.")
            return {"statusCode": 400, "body": "Bad Request: Empty body"}

        # Hardcoded binary data for a Person message (name="Test", id=123)
        # This is equivalent to: Person(name="Test", id=123).SerializeToString()
        # You can generate this using: 
        # from simple_pb2 import Person
        # p = Person(name="Test", id=123)
        # print(p.SerializeToString())
        hardcoded_protobuf_data = b'\n\x05Hello'

        message = Message()
        message.ParseFromString(hardcoded_protobuf_data)

        logger.info(f"Parsed Message: Value={message.value}")

        return {"statusCode": 200, "body": "Success"}

    
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        return {"statusCode": 500, "body": "Internal Server Error"}

# Small change to trigger CI/CD pipeline.