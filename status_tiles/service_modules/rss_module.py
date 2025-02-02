import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict

import aiohttp
import feedparser

from ..models import ServiceState, ServiceStatus
from .base import ServiceModule

logger = logging.getLogger("status_tiles")


class RSSModule(ServiceModule):
    def __init__(self, config: Dict[str, Any]):
        self.name = config["name"]
        self.feed_url = config["feed_url"]
        self.timeout = config.get("timeout", 30)
        # How far back to look for incidents (default 24 hours)
        self.check_period = config.get("check_period_hours", 24)
        # Keywords that indicate incidents
        self.incident_keywords = config.get(
            "incident_keywords", ["incident", "outage", "degraded", "issue", "maintenance"]
        )
        self.exclude_keywords = config.get("exclude_keywords", [])

    def _check_entry_for_incidents(self, entry: Dict[str, Any], recent_threshold: datetime) -> Dict[str, Any] | None:
        """
        Check if an RSS entry indicates an incident and is recent enough to care about.
        """
        try:
            # Parse entry date
            published_tuple = entry.get("published_parsed")
            if not published_tuple:
                logger.debug(f"No published date for entry: {entry.get('title')}")
                return None

            entry_date = datetime.fromtimestamp(time.mktime(published_tuple))

            # Skip if entry is too old
            if entry_date < recent_threshold:
                logger.debug(f"Entry too old: {entry.get('title')} - {entry_date} < {recent_threshold}")
                return None

            title = entry.get("title", "").lower()
            description = entry.get("description", "").lower()

            # Skip if it contains exclude keywords
            for exclude in getattr(self, "exclude_keywords", []):
                if exclude.lower() in description.lower() or exclude.lower() in title.lower():
                    logger.debug(f"Excluding entry due to keyword '{exclude}': {entry.get('title')}")
                    return None

            # Look for incident keywords
            found_keyword = False
            for keyword in self.incident_keywords:
                if keyword.lower() in title or keyword.lower() in description:
                    found_keyword = True
                    logger.debug(f"Found incident keyword '{keyword}' in entry: {entry.get('title')}")
                    break

            if found_keyword:
                # Additional check for resolved/completed in description
                if any(status in description.lower() for status in ["resolved", "completed"]):
                    logger.debug(f"Incident marked as resolved/completed: {entry.get('title')}")
                    return None

                return {
                    "title": entry.get("title"),
                    "date": entry_date.isoformat(),
                    "link": entry.get("link"),
                    "description": entry.get("description"),
                }

            logger.debug(f"No matching incident keywords found for: {entry.get('title')}")
            return None

        except Exception as e:
            logger.warning(f"Error parsing entry: {e}", exc_info=True)
            return None

    async def get_status(self) -> ServiceState:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.feed_url, timeout=self.timeout) as response:
                    if response.status != 200:
                        logger.error(f"HTTP error {response.status} for {self.feed_url}")
                        return ServiceState(
                            name=self.name,
                            status=ServiceStatus.UNHEALTHY,
                            last_checked=datetime.utcnow(),
                            details={"error": f"HTTP {response.status}"},
                        )

                    content = await response.text()
                    feed = feedparser.parse(content)

                    if feed.bozo:
                        logger.error(f"Feed parsing error for {self.feed_url}: {feed.bozo_exception}")
                        return ServiceState(
                            name=self.name,
                            status=ServiceStatus.UNHEALTHY,
                            last_checked=datetime.utcnow(),
                            details={"error": str(feed.bozo_exception)},
                        )

                    # Check recent entries for incidents
                    recent_threshold = datetime.utcnow() - timedelta(hours=self.check_period)
                    active_incidents = []

                    logger.debug(f"Checking {len(feed.entries)} entries for incidents")

                    for entry in feed.entries:
                        logger.debug(f"Checking entry: {entry.get('title')}")
                        incident = self._check_entry_for_incidents(entry, recent_threshold)
                        if incident:
                            logger.debug(f"Found incident: {incident['title']}")
                            active_incidents.append(incident)
                        else:
                            logger.debug(f"No incident found in entry: {entry.get('title')}")

                    current_status = ServiceStatus.HEALTHY
                    details = {
                        "title": feed.feed.get("title", "Unknown"),
                        "last_updated": feed.feed.get("updated", "Unknown"),
                        "entries_count": len(feed.entries),
                    }

                    if active_incidents:
                        current_status = ServiceStatus.UNHEALTHY
                        details["active_incidents"] = active_incidents
                        details["incident_count"] = len(active_incidents)
                        details["latest_incident"] = active_incidents[0]["title"]

                    logger.debug(f"Final status: {current_status}, Active incidents: {len(active_incidents)}")

                    return ServiceState(
                        name=self.name,
                        status=current_status,
                        last_checked=datetime.utcnow(),
                        details=details,
                    )

        except Exception as e:
            logger.exception(f"Error checking RSS feed {self.feed_url}")
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
                "feed_url": {"type": "string", "format": "uri"},
                "timeout": {"type": "number", "default": 30},
                "check_period_hours": {"type": "number", "default": 24},
                "incident_keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["incident", "outage", "degraded", "issue", "maintenance"],
                },
            },
            "required": ["name", "feed_url"],
        }
