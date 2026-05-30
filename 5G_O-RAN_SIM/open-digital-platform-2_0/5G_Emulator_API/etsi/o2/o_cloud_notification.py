#!/usr/bin/env python3
"""O-RAN WG6 O-Cloud Notification API.

Spec: O-RAN.WG6.O-Cloud Notification API-v04.00.

Implements the O-Cloud event subscription + notification delivery plane in the
CNCF / CloudEvents style. Consumers subscribe to O-Cloud resource events
(e.g. ResourcePool / DeploymentManager / hardware lifecycle changes); publishers
post events that are fanned out best-effort to matching subscribers' callbacks.

Self-contained: does not import the security libraries.

Port: 8127
"""
import argparse, logging, uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional
import requests, uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from opentelemetry import trace
    _tracer = trace.get_tracer(__name__)
except Exception:
    class _NoopSpan:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def set_attribute(self, *a, **k): pass
    class _NoopTracer:
        def start_as_current_span(self, *a, **k): return _NoopSpan()
    _tracer = _NoopTracer()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("svc")

SERVICE_PORT = 8127
NRF_URL = "http://127.0.0.1:8000"

# CloudEvents spec version emitted in every notification.
CE_SPEC_VERSION = "1.0"


def _now() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# Enumerations
# =============================================================================

class ResourceEventType(str, Enum):
    """O-Cloud resource event types (CloudEvents 'type' attribute, reverse-DNS)."""
    RESOURCE_CREATED = "o-ran.ocloud.resource.created"
    RESOURCE_MODIFIED = "o-ran.ocloud.resource.modified"
    RESOURCE_DELETED = "o-ran.ocloud.resource.deleted"
    RESOURCE_POOL_CHANGED = "o-ran.ocloud.resourcepool.changed"
    DEPLOYMENT_MANAGER_CHANGED = "o-ran.ocloud.deploymentmanager.changed"
    INFRASTRUCTURE_ALARM = "o-ran.ocloud.infrastructure.alarm"
    INFRASTRUCTURE_FAULT_CLEARED = "o-ran.ocloud.infrastructure.faultcleared"


# =============================================================================
# In-memory stores
# =============================================================================

# subscription_id -> subscription record
_SUBSCRIPTIONS: Dict[str, Dict[str, Any]] = {}
# bounded ring of recently published events for replay/debug
_EVENT_HISTORY: List[Dict[str, Any]] = []
_MAX_HISTORY = 200


# =============================================================================
# Pydantic models
# =============================================================================

class SubscriptionRequest(BaseModel):
    """O-Cloud event subscription (CNCF/CloudEvents consumer registration)."""
    callback: str = Field(..., description="Consumer callback URI for notification POSTs")
    resourceType: Optional[str] = Field(
        default=None, description="Filter: O-Cloud resource type (e.g. ResourcePool)")
    eventTypes: Optional[List[str]] = Field(
        default=None, description="Filter: CloudEvents types of interest; null = all")
    consumerSubscriptionId: Optional[str] = Field(
        default=None, description="Consumer-side correlation id")


class EventPublish(BaseModel):
    """An O-Cloud event to publish (mapped into a CloudEvent on fan-out)."""
    eventType: str = Field(..., description="CloudEvents 'type', e.g. o-ran.ocloud.resource.modified")
    source: str = Field(default="/o-cloud", description="CloudEvents 'source'")
    resourceType: Optional[str] = Field(default=None, description="Affected O-Cloud resource type")
    resourceId: Optional[str] = Field(default=None, description="Affected resource id")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Event payload")


# =============================================================================
# Lifespan / app
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        requests.post(
            f"{NRF_URL}/register",
            json={"nf_type": "O_CLOUD_NOTIF", "ip": "127.0.0.1", "port": SERVICE_PORT},
            timeout=3,
        )
        logger.info("O-Cloud Notification service registered with NRF")
    except requests.RequestException:
        logger.warning("Could not register O-Cloud Notification service with NRF")
    yield


app = FastAPI(
    title="O-RAN WG6 O-Cloud Notification API",
    description="CloudEvents-style O-Cloud event subscription and notification (port 8127)",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# =============================================================================
# Helpers
# =============================================================================

def _to_cloud_event(pub: EventPublish) -> Dict[str, Any]:
    """Wrap a published event in a CloudEvents 1.0 envelope."""
    return {
        "specversion": CE_SPEC_VERSION,
        "id": str(uuid.uuid4()),
        "type": pub.eventType,
        "source": pub.source,
        "time": _now().isoformat(),
        "datacontenttype": "application/json",
        "subject": pub.resourceId,
        "data": {
            "resourceType": pub.resourceType,
            "resourceId": pub.resourceId,
            **(pub.data or {}),
        },
    }


def _matches(sub: Dict[str, Any], pub: EventPublish) -> bool:
    """Subscription filter: resourceType (if set) AND eventTypes (if set) must match."""
    if sub.get("resourceType") and pub.resourceType:
        if sub["resourceType"].lower() != pub.resourceType.lower():
            return False
    elif sub.get("resourceType") and not pub.resourceType:
        return False
    event_types = sub.get("eventTypes")
    if event_types:
        if pub.eventType not in event_types:
            return False
    return True


def _deliver(callback: str, cloud_event: Dict[str, Any]) -> bool:
    """Best-effort POST of a CloudEvent to a consumer callback."""
    try:
        resp = requests.post(callback, json=cloud_event, timeout=3)
        return 200 <= resp.status_code < 300
    except requests.RequestException:
        return False


# =============================================================================
# API root
# =============================================================================

@app.get("/o-cloud/v1/")
async def api_root():
    """O-Cloud Notification API root / capability discovery."""
    return {
        "spec": "O-RAN.WG6.O-Cloud Notification API-v04.00",
        "cloudEventsVersion": CE_SPEC_VERSION,
        "subscriptionCount": len(_SUBSCRIPTIONS),
        "supportedEventTypes": [e.value for e in ResourceEventType],
        "endpoints": [
            "POST /o-cloud/v1/subscriptions",
            "GET /o-cloud/v1/subscriptions",
            "DELETE /o-cloud/v1/subscriptions/{id}",
            "POST /o-cloud/v1/events",
            "GET /o-cloud/v1/health",
        ],
    }


# =============================================================================
# Subscriptions
# =============================================================================

@app.post("/o-cloud/v1/subscriptions", status_code=201)
async def create_subscription(req: SubscriptionRequest):
    """Subscribe to O-Cloud resource events."""
    with _tracer.start_as_current_span("create_subscription"):
        sub_id = str(uuid.uuid4())
        record = {
            "subscriptionId": sub_id,
            "callback": req.callback,
            "resourceType": req.resourceType,
            "eventTypes": req.eventTypes,
            "consumerSubscriptionId": req.consumerSubscriptionId,
            "createdAt": _now().isoformat(),
        }
        _SUBSCRIPTIONS[sub_id] = record
        logger.info(f"O-Cloud subscription {sub_id} -> {req.callback}")
        return record


@app.get("/o-cloud/v1/subscriptions")
async def list_subscriptions():
    """List all active O-Cloud event subscriptions."""
    return {"count": len(_SUBSCRIPTIONS), "subscriptions": list(_SUBSCRIPTIONS.values())}


@app.get("/o-cloud/v1/subscriptions/{sub_id}")
async def get_subscription(sub_id: str):
    """Get a specific subscription."""
    sub = _SUBSCRIPTIONS.get(sub_id)
    if sub is None:
        raise HTTPException(status_code=404, detail=f"Subscription {sub_id} not found")
    return sub


@app.delete("/o-cloud/v1/subscriptions/{sub_id}", status_code=204)
async def delete_subscription(sub_id: str):
    """Unsubscribe from O-Cloud events."""
    if _SUBSCRIPTIONS.pop(sub_id, None) is None:
        raise HTTPException(status_code=404, detail=f"Subscription {sub_id} not found")
    return None


# =============================================================================
# Event publication / fan-out
# =============================================================================

@app.post("/o-cloud/v1/events")
async def publish_event(pub: EventPublish):
    """Publish an O-Cloud event; fan out best-effort to matching subscribers."""
    with _tracer.start_as_current_span("publish_event") as span:
        span.set_attribute("event.type", pub.eventType)
        cloud_event = _to_cloud_event(pub)

        delivered = 0
        failed = 0
        targets: List[str] = []
        for sub in list(_SUBSCRIPTIONS.values()):
            if not _matches(sub, pub):
                continue
            targets.append(sub["subscriptionId"])
            if _deliver(sub["callback"], cloud_event):
                delivered += 1
            else:
                failed += 1

        record = {
            "cloudEvent": cloud_event,
            "matchedSubscriptions": targets,
            "delivered": delivered,
            "failed": failed,
        }
        _EVENT_HISTORY.append(record)
        if len(_EVENT_HISTORY) > _MAX_HISTORY:
            del _EVENT_HISTORY[: len(_EVENT_HISTORY) - _MAX_HISTORY]

        return {
            "eventId": cloud_event["id"],
            "matched": len(targets),
            "delivered": delivered,
            "failed": failed,
        }


@app.get("/o-cloud/v1/events")
async def list_events(limit: int = 50):
    """Recent published events (most recent first)."""
    events = list(reversed(_EVENT_HISTORY))[:limit]
    return {"count": len(events), "events": events}


# =============================================================================
# Health
# =============================================================================

@app.get("/o-cloud/v1/health")
async def ocloud_health():
    return {
        "status": "healthy",
        "service": "o-cloud-notification",
        "spec": "O-RAN.WG6.O-Cloud Notification API-v04.00",
        "subscriptions": len(_SUBSCRIPTIONS),
        "eventsPublished": len(_EVENT_HISTORY),
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "o-cloud-notification",
        "spec": "O-RAN.WG6.O-Cloud Notification API-v04.00",
        "port": SERVICE_PORT,
    }


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=SERVICE_PORT)
    a = p.parse_args()
    logger.info(f"Starting O-RAN WG6 O-Cloud Notification API on {a.host}:{a.port}")
    uvicorn.run(app, host=a.host, port=a.port)
