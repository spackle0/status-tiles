import asyncio
import json
from datetime import datetime
from typing import Any, Dict

import aiohttp
from jsonpath_ng import parse

from ..models import ServiceState, ServiceStatus
from .base import ServiceModule


class HTTPModule(ServiceModule):
    """Module for monitoring HTTP endpoints with JSON response validation"""

    def __init__(self, config: Dict[str, Any]):
        self.name = config["name"]
        self.url = config["url"]
        self.method = config.get("method", "GET")
        self.timeout = config.get("timeout", 30)
        self.expected_status = config.get("expected_status", 200)
        self.headers = config.get("headers", {})
        self.body = config.get("body")
        self.verify_ssl = config.get("verify_ssl", True)
        # New fields for response validation
        self.json_path = config.get("json_path")
        self.expected_values = config.get("expected_values")

    async def get_status(self) -> ServiceState:
        try:
            start_time = datetime.now()
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=self.method,
                    url=self.url,
                    headers=self.headers,
                    json=self.body if self.body else None,
                    timeout=self.timeout,
                    ssl=self.verify_ssl,
                ) as response:
                    end_time = datetime.now()
                    response_time = (end_time - start_time).total_seconds() * 1000  # in ms
                    details = {"status_code": response.status, "response_time_ms": round(response_time, 2)}

                    if response.status != self.expected_status:
                        details["error"] = f"Expected status {self.expected_status}, got {response.status}"
                        return ServiceState(
                            name=self.name,
                            status=ServiceStatus.UNHEALTHY,
                            last_checked=datetime.utcnow(),
                            details=details,
                        )

                    # If JSON path validation is configured, check response content
                    if self.json_path:
                        try:
                            response_json = await response.json()
                            jsonpath_expr = parse(self.json_path)
                            match = jsonpath_expr.find(response_json)

                            if not match:
                                details["error"] = f"JSON path '{self.json_path}' not found in response"
                                return ServiceState(
                                    name=self.name,
                                    status=ServiceStatus.UNHEALTHY,
                                    last_checked=datetime.utcnow(),
                                    details=details,
                                )

                            extracted_value = match[0].value
                            details["status_value"] = extracted_value

                            # Validate against expected values if provided
                            if self.expected_values and extracted_value not in self.expected_values:
                                details["error"] = f"Unexpected value: {extracted_value}"
                                return ServiceState(
                                    name=self.name,
                                    status=ServiceStatus.UNHEALTHY,
                                    last_checked=datetime.utcnow(),
                                    details=details,
                                )

                        except (json.JSONDecodeError, Exception) as e:
                            details["error"] = f"Failed to parse response: {str(e)}"
                            return ServiceState(
                                name=self.name,
                                status=ServiceStatus.UNHEALTHY,
                                last_checked=datetime.utcnow(),
                                details=details,
                            )

                    return ServiceState(
                        name=self.name,
                        status=ServiceStatus.HEALTHY,
                        last_checked=datetime.utcnow(),
                        details=details,
                    )

        except asyncio.TimeoutError:
            return ServiceState(
                name=self.name,
                status=ServiceStatus.UNHEALTHY,
                last_checked=datetime.utcnow(),
                details={"error": "Request timed out"},
            )
        except Exception as e:
            return ServiceState(
                name=self.name,
                status=ServiceStatus.UNHEALTHY,
                last_checked=datetime.utcnow(),
                details={"error": str(e)},
            )

    def get_config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "url": {"type": "string", "format": "uri"},
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"],
                    "default": "GET",
                },
                "timeout": {"type": "number", "default": 30},
                "expected_status": {"type": "integer", "default": 200},
                "headers": {"type": "object", "additionalProperties": {"type": "string"}, "default": {}},
                "body": {"type": ["object", "null"], "default": None},
                "verify_ssl": {"type": "boolean", "default": True},
                "json_path": {"type": ["string", "null"], "default": None},
                "expected_values": {"type": ["array", "null"], "items": {"type": "string"}, "default": None},
            },
            "required": ["name", "url"],
        }
