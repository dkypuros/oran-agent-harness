#!/usr/bin/env python3
"""Topology Exposure & Inventory (TE&IV) service (O-RAN WG10 OAM).

Spec: O-RAN.WG10.TS.TE&IV-API.0-R005-v04.00 (TE&IV API),
      O-RAN.WG10.TS.TE&IV-CIMI.0-R005-v06.00 (Common Information Model Instances),
      O-RAN.WG10.TS.TE&IV-DM.0-R005-v04.00 (Data Model).

TE&IV exposes the topology and inventory of the O-RAN deployment as a graph of
entities and relationships. Entity types follow the CIMI/DM: O-CU, O-DU, O-RU,
NRCell, AntennaModule. Relationship types: REALISED_BY, INSTALLED_AT, SERVES.

The graph is consumable as nodes+edges (``/teiv/topology``) for SMO topology
visualization, and as typed CIMI entity collections (``/teiv/entities``).

Port: 8126
"""
import argparse, logging, uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
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
logger = logging.getLogger("teiv")

SERVICE_PORT = 8126
NRF_URL = "http://127.0.0.1:8000"


def _now() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# Enumerations (per O-RAN.WG10.TS.TE&IV-CIMI / TE&IV-DM)
# =============================================================================

class EntityType(str, Enum):
    """TE&IV CIMI entity types (managed topology objects)."""
    O_CU = "O-CU"                # O-RAN Central Unit
    O_DU = "O-DU"                # O-RAN Distributed Unit
    O_RU = "O-RU"                # O-RAN Radio Unit
    NR_CELL = "NRCell"           # NR cell
    ANTENNA_MODULE = "AntennaModule"  # Antenna module / array


class RelationshipType(str, Enum):
    """TE&IV relationship (association) types per TE&IV-DM."""
    REALISED_BY = "REALISED_BY"    # logical entity realised by a physical one
    INSTALLED_AT = "INSTALLED_AT"  # physical entity installed at a site/location
    SERVES = "SERVES"              # entity serves another (e.g. O-DU SERVES NRCell)


# =============================================================================
# Data models (TE&IV-DM)
# =============================================================================

class Entity(BaseModel):
    """
    A TE&IV entity (graph node) per O-RAN.WG10.TS.TE&IV-DM. ``attributes`` carry
    the CIMI attribute set for the entity type (free-form to keep the data model
    extensible across CIMI revisions).
    """
    id: str = Field(default_factory=lambda: f"entity-{uuid.uuid4().hex[:12]}")
    type: EntityType
    name: str = Field(default="")
    sourceIds: Dict[str, str] = Field(
        default_factory=dict, description="External source identifiers (e.g. cmHandle)"
    )
    attributes: Dict[str, Any] = Field(default_factory=dict)
    createdAt: datetime = Field(default_factory=_now)


class Relationship(BaseModel):
    """A TE&IV relationship (graph edge) connecting two entities by ID."""
    id: str = Field(default_factory=lambda: f"rel-{uuid.uuid4().hex[:12]}")
    type: RelationshipType
    aSide: str = Field(..., description="A-side entity ID (source)")
    bSide: str = Field(..., description="B-side entity ID (target)")
    attributes: Dict[str, Any] = Field(default_factory=dict)
    createdAt: datetime = Field(default_factory=_now)


# =============================================================================
# In-memory TE&IV graph
# =============================================================================

entities: Dict[str, Entity] = {}
relationships: Dict[str, Relationship] = {}


def _seed_topology() -> None:
    """Seed a representative O-CU/O-DU/O-RU/NRCell/Antenna graph."""
    ocu = Entity(id="ocu-1", type=EntityType.O_CU, name="O-CU-1",
                 sourceIds={"cmHandle": "ocu-1"},
                 attributes={"gnbId": 1001, "plmnId": "00101"})
    odu = Entity(id="odu-1", type=EntityType.O_DU, name="O-DU-1",
                 sourceIds={"cmHandle": "odu-1"},
                 attributes={"gnbDuId": 1, "site": "site-A"})
    oru = Entity(id="oru-1", type=EntityType.O_RU, name="O-RU-1",
                 sourceIds={"cmHandle": "oru-1"},
                 attributes={"vendor": "ORAN-Emulator", "site": "site-A"})
    cell = Entity(id="cell-1", type=EntityType.NR_CELL, name="NRCell-1",
                  attributes={"cellLocalId": 1, "nrPci": 1, "nrTac": 7})
    antenna = Entity(id="ant-1", type=EntityType.ANTENNA_MODULE, name="AntennaModule-1",
                     attributes={"gainDbi": 18, "elements": 64, "site": "site-A"})
    for ent in (ocu, odu, oru, cell, antenna):
        entities[ent.id] = ent

    seed_rels = [
        Relationship(type=RelationshipType.SERVES, aSide=odu.id, bSide=cell.id),
        Relationship(type=RelationshipType.REALISED_BY, aSide=cell.id, bSide=oru.id),
        Relationship(type=RelationshipType.INSTALLED_AT, aSide=oru.id, bSide=antenna.id),
        Relationship(type=RelationshipType.SERVES, aSide=ocu.id, bSide=odu.id),
    ]
    for rel in seed_rels:
        relationships[rel.id] = rel


# =============================================================================
# FastAPI application
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    _seed_topology()
    try:
        requests.post(f"{NRF_URL}/register", json={"nf_type": "TEIV", "ip": "127.0.0.1", "port": SERVICE_PORT}, timeout=3)
    except requests.RequestException:
        pass
    logger.info("TE&IV service ready on port %s", SERVICE_PORT)
    yield


app = FastAPI(
    title="TE&IV (O-RAN WG10)",
    description="O-RAN Topology Exposure & Inventory: entity/relationship graph",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# =============================================================================
# Entity types & entities
# =============================================================================

@app.get("/teiv/entity-types")
async def list_entity_types():
    """List supported CIMI entity types and relationship types."""
    return {
        "spec": "O-RAN.WG10.TS.TE&IV-CIMI.0-R005-v06.00",
        "entityTypes": [e.value for e in EntityType],
        "relationshipTypes": [r.value for r in RelationshipType],
    }


@app.get("/teiv/entities")
async def list_entities():
    """List all TE&IV entities."""
    with _tracer.start_as_current_span("teiv_list_entities") as span:
        span.set_attribute("teiv.entities", len(entities))
        return [e.model_dump(mode="json") for e in entities.values()]


@app.get("/teiv/entities/{type}")
async def list_entities_by_type(type: str):
    """List entities of a given CIMI type (e.g. O-DU, NRCell)."""
    try:
        et = EntityType(type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown entity type: {type}")
    return [e.model_dump(mode="json") for e in entities.values() if e.type == et]


@app.post("/teiv/entities", status_code=201)
async def create_entity(entity: Entity):
    """Create a TE&IV entity (CIMI instance)."""
    entities[entity.id] = entity
    logger.info("Created TE&IV entity %s (%s)", entity.id, entity.type.value)
    return entity.model_dump(mode="json")


# =============================================================================
# Relationships
# =============================================================================

@app.get("/teiv/relationships")
async def list_relationships(type: Optional[str] = None):
    """List TE&IV relationships, optionally filtered by type."""
    result = list(relationships.values())
    if type is not None:
        try:
            rt = RelationshipType(type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown relationship type: {type}")
        result = [r for r in result if r.type == rt]
    return [r.model_dump(mode="json") for r in result]


# =============================================================================
# Topology (nodes + edges)
# =============================================================================

@app.get("/teiv/topology")
async def get_topology():
    """Return the topology as a nodes+edges graph for visualization."""
    nodes = [
        {
            "id": e.id,
            "type": e.type.value,
            "label": e.name or e.id,
            "attributes": e.attributes,
        }
        for e in entities.values()
    ]
    edges = [
        {
            "id": r.id,
            "type": r.type.value,
            "source": r.aSide,
            "target": r.bSide,
        }
        for r in relationships.values()
    ]
    return {
        "spec": "O-RAN.WG10.TS.TE&IV-DM.0-R005-v04.00",
        "nodes": nodes,
        "edges": edges,
        "counts": {"nodes": len(nodes), "edges": len(edges)},
    }


# =============================================================================
# Health
# =============================================================================

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "teiv", "spec": "O-RAN.WG10.TS.TE&IV-API.0-R005-v04.00"}


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--host", default="0.0.0.0"); p.add_argument("--port", type=int, default=SERVICE_PORT)
    a = p.parse_args(); uvicorn.run(app, host=a.host, port=a.port)
