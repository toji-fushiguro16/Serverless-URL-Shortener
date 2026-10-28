"""AWS Lambda handler for a DynamoDB-backed URL shortener."""
from __future__ import annotations

import json
import os
import re
import secrets
from datetime import datetime, timezone
from urllib.parse import urlsplit

import boto3
from botocore.exceptions import ClientError

TABLE_NAME = os.environ["TABLE_NAME"]
table = boto3.resource("dynamodb").Table(TABLE_NAME)
CODE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8}$")


def response(status: int, body: dict, headers: dict | None = None) -> dict:
    result_headers = {"content-type": "application/json; charset=utf-8", "cache-control": "no-store"}
    if headers:
        result_headers.update(headers)
    return {"statusCode": status, "headers": result_headers, "body": json.dumps(body)}


def valid_target(value: object) -> bool:
    if not isinstance(value, str) or len(value) > 2048:
        return False
    parsed = urlsplit(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.hostname) and not parsed.username and not parsed.password


def handler(event: dict, _context: object) -> dict:
    http = event.get("requestContext", {}).get("http", {})
    method = http.get("method", "")
    path = event.get("rawPath", "/")

    if method == "GET" and path == "/health":
        return response(200, {"status": "ok"})

    if method == "POST" and path == "/shorten":
        try:
            raw_body = event.get("body") or "{}"
            if event.get("isBase64Encoded"):
                import base64
                raw_body = base64.b64decode(raw_body).decode("utf-8")
            payload = json.loads(raw_body)
        except (ValueError, UnicodeDecodeError):
            return response(400, {"error": "Request body must be valid JSON."})

        target = payload.get("url") if isinstance(payload, dict) else None
        if not valid_target(target):
            return response(400, {"error": "Provide a valid HTTP or HTTPS URL (maximum 2048 characters)."})

        for _ in range(5):
            code = secrets.token_urlsafe(6)[:8]
            try:
                table.put_item(
                    Item={"short_code": code, "target_url": target, "created_at": datetime.now(timezone.utc).isoformat()},
                    ConditionExpression="attribute_not_exists(short_code)",
                )
                domain = event.get("headers", {}).get("host", "")
                scheme = event.get("headers", {}).get("x-forwarded-proto", "https")
                return response(201, {"code": code, "short_url": f"{scheme}://{domain}/{code}"})
            except ClientError as error:
                if error.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
                    raise
        return response(503, {"error": "Could not allocate a short code. Try again."})

    if method == "GET":
        code = event.get("pathParameters", {}).get("code", "")
        if not CODE_PATTERN.fullmatch(code):
            return response(404, {"error": "Short link not found."})
        item = table.get_item(Key={"short_code": code}).get("Item")
        if not item:
            return response(404, {"error": "Short link not found."})
        return {"statusCode": 302, "headers": {"location": item["target_url"], "cache-control": "no-store"}, "body": ""}

    return response(404, {"error": "Route not found."})
