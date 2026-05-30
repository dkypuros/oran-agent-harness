"""
O-RAN O1 Performance Management (PM) library.

Spec: O-RAN.WG10.TS.O1PMeas-R005-v05.00 (O1 Performance Measurements), aligned
      with 3GPP TS 28.552 / TS 28.622 measurement definitions and TS 32.435
      file-based reporting.

This module is a pure library (no FastAPI app). It provides:
- Granularity periods (collection intervals) per O1PMeas / 3GPP TS 28.550
- Reporting methods (FILE_BASED, STREAM_BASED) per the O1 PM service
- 3GPP-style measurement families and measurement types
  (RRC.ConnEstab*, DRB.PdcpSduVolume*, RRU.PrbUsed*, CARR.*, etc.)
- Pydantic descriptors for measurement jobs and measurement reports
- A ``PmJobManager`` class that owns PM job state and produces simulated PM
  data files (3GPP-style measurement result files) on disk.

The O1 service (oam/o1.py) imports ``PmJobManager`` to back its PM job and PM
data routes; the VES measurement domain (oam/ves.py) reuses the same
measurement families when emitting streaming PM events.
"""

import json
import os
import random
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def _now() -> datetime:
    """UTC timestamp helper (timezone-aware per O-RAN logging conventions)."""
    return datetime.now(timezone.utc)


# =============================================================================
# Enumerations (per O-RAN.WG10.TS.O1PMeas-R005-v05.00)
# =============================================================================

class GranularityPeriod(int, Enum):
    """
    PM collection granularity periods (seconds) per O-RAN.WG10.TS.O1PMeas and
    3GPP TS 28.550. A measurement job samples its counters once per granularity
    period; the granularity period must divide the reporting period.
    """
    GP_1S = 1
    GP_5S = 5
    GP_10S = 10
    GP_30S = 30
    GP_1MIN = 60
    GP_5MIN = 300
    GP_15MIN = 900
    GP_30MIN = 1800
    GP_1HOUR = 3600


class ReportingMethod(str, Enum):
    """
    PM reporting method per O-RAN.WG10.TS.O1PMeas Section 4. FILE_BASED writes
    3GPP TS 32.435 measurement result files; STREAM_BASED emits VES measurement
    events (O-RAN.WG10 streaming PM) to a VES collector.
    """
    FILE_BASED = "FILE_BASED"
    STREAM_BASED = "STREAM_BASED"


class PmJobState(str, Enum):
    """Lifecycle states of a PM measurement job."""
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    STOPPED = "STOPPED"


class MeasurementResultStatus(str, Enum):
    """Per-measurement suspect/validity flag per 3GPP TS 28.550."""
    VALID = "VALID"
    SUSPECT = "SUSPECT"


# =============================================================================
# 3GPP-style measurement families & catalog
# =============================================================================

class MeasurementFamily(str, Enum):
    """
    3GPP-style measurement family (measurement group prefix) per TS 28.552 as
    referenced by O-RAN.WG10.TS.O1PMeas. The family is the leading dotted token
    of a measurement type name (e.g. ``RRC`` in ``RRC.ConnEstabAtt``).
    """
    RRC = "RRC"      # Radio Resource Control connection measurements
    DRB = "DRB"      # Data Radio Bearer / PDCP volume & throughput
    RRU = "RRU"      # Radio Resource Utilization (PRB usage)
    CARR = "CARR"    # Per-carrier aggregate measurements
    UECNTX = "UECNTX"  # UE context measurements
    HO = "HO"        # Handover measurements
    MAC = "MAC"      # MAC layer / scheduling measurements
    PDCP = "PDCP"    # PDCP layer measurements


# Catalog of measurement types keyed by family. Each entry carries the leaf
# measurement name and a plausible value range used by the simulator.
MEASUREMENT_CATALOG: Dict[MeasurementFamily, List[Dict[str, Any]]] = {
    MeasurementFamily.RRC: [
        {"name": "RRC.ConnEstabAtt", "unit": "count", "low": 0, "high": 5000},
        {"name": "RRC.ConnEstabSucc", "unit": "count", "low": 0, "high": 5000},
        {"name": "RRC.ConnEstabFail", "unit": "count", "low": 0, "high": 200},
        {"name": "RRC.ConnMean", "unit": "count", "low": 0, "high": 1200},
        {"name": "RRC.ConnMax", "unit": "count", "low": 0, "high": 2000},
    ],
    MeasurementFamily.DRB: [
        {"name": "DRB.PdcpSduVolumeDL", "unit": "kbit", "low": 0, "high": 50_000_000},
        {"name": "DRB.PdcpSduVolumeUL", "unit": "kbit", "low": 0, "high": 20_000_000},
        {"name": "DRB.UEThpDl", "unit": "kbps", "low": 0, "high": 1_000_000},
        {"name": "DRB.UEThpUl", "unit": "kbps", "low": 0, "high": 400_000},
        {"name": "DRB.MeanActiveUeDl", "unit": "count", "low": 0, "high": 400},
    ],
    MeasurementFamily.RRU: [
        {"name": "RRU.PrbUsedDl", "unit": "prb", "low": 0, "high": 273},
        {"name": "RRU.PrbUsedUl", "unit": "prb", "low": 0, "high": 273},
        {"name": "RRU.PrbAvailDl", "unit": "prb", "low": 273, "high": 273},
        {"name": "RRU.PrbAvailUl", "unit": "prb", "low": 273, "high": 273},
        {"name": "RRU.PrbTotDl", "unit": "prb", "low": 0, "high": 273},
    ],
    MeasurementFamily.CARR: [
        {"name": "CARR.AvgCqi", "unit": "cqi", "low": 1, "high": 15},
        {"name": "CARR.AvgMcsDl", "unit": "mcs", "low": 0, "high": 28},
        {"name": "CARR.WBCqiDistr", "unit": "count", "low": 0, "high": 5000},
        {"name": "CARR.ActiveCarriers", "unit": "count", "low": 1, "high": 8},
    ],
    MeasurementFamily.UECNTX: [
        {"name": "UECNTX.SetupAtt", "unit": "count", "low": 0, "high": 5000},
        {"name": "UECNTX.SetupSucc", "unit": "count", "low": 0, "high": 5000},
        {"name": "UECNTX.RelReqMax", "unit": "count", "low": 0, "high": 1500},
    ],
    MeasurementFamily.HO: [
        {"name": "HO.InterGnbOutAtt", "unit": "count", "low": 0, "high": 800},
        {"name": "HO.InterGnbOutSucc", "unit": "count", "low": 0, "high": 800},
        {"name": "HO.IntraGnbAtt", "unit": "count", "low": 0, "high": 1200},
    ],
    MeasurementFamily.MAC: [
        {"name": "MAC.SchedActivityDl", "unit": "count", "low": 0, "high": 100000},
        {"name": "MAC.HarqNackDl", "unit": "count", "low": 0, "high": 50000},
    ],
    MeasurementFamily.PDCP: [
        {"name": "PDCP.PdcpPduVolumeDl", "unit": "kbit", "low": 0, "high": 50_000_000},
        {"name": "PDCP.PdcpDelayDl", "unit": "ms", "low": 0, "high": 200},
    ],
}


def list_measurement_types(family: Optional[MeasurementFamily] = None) -> List[str]:
    """Return measurement type names, optionally filtered to one family."""
    families = [family] if family is not None else list(MEASUREMENT_CATALOG.keys())
    out: List[str] = []
    for fam in families:
        for entry in MEASUREMENT_CATALOG.get(fam, []):
            out.append(entry["name"])
    return out


def _catalog_entry(measurement_type: str) -> Optional[Dict[str, Any]]:
    """Look up a catalog entry by measurement type name (e.g. RRU.PrbUsedDl)."""
    prefix = measurement_type.split(".", 1)[0]
    try:
        fam = MeasurementFamily(prefix)
    except ValueError:
        return None
    for entry in MEASUREMENT_CATALOG.get(fam, []):
        if entry["name"] == measurement_type:
            return entry
    return None


# =============================================================================
# Data Models (Pydantic)
# =============================================================================

class PmMeasurementJob(BaseModel):
    """
    PM measurement job per O-RAN.WG10.TS.O1PMeas. A job binds a set of
    measurement types to one or more managed object instances, at a chosen
    granularity period, delivered via a reporting method over a reporting period.
    """
    jobId: str = Field(default_factory=lambda: f"pmjob-{uuid.uuid4().hex[:12]}")
    jobName: str = Field(default="", description="Human-readable job name")
    measurementTypes: List[str] = Field(
        default_factory=list,
        description="3GPP-style measurement type names (e.g. RRU.PrbUsedDl)",
    )
    measuredObjectDns: List[str] = Field(
        default_factory=list,
        description="Distinguished names of measured managed objects (cells/functions)",
    )
    granularityPeriod: GranularityPeriod = Field(default=GranularityPeriod.GP_15MIN)
    reportingPeriod: int = Field(
        default=900, description="Reporting period in seconds (file/stream emission cadence)"
    )
    reportingMethod: ReportingMethod = Field(default=ReportingMethod.FILE_BASED)
    fileReportingPath: Optional[str] = Field(
        default=None, description="Directory for FILE_BASED measurement result files"
    )
    streamTargetUri: Optional[str] = Field(
        default=None, description="VES collector URI for STREAM_BASED reporting"
    )
    state: PmJobState = Field(default=PmJobState.CREATED)
    createdAt: datetime = Field(default_factory=_now)


class MeasurementValue(BaseModel):
    """A single measured value for one measurement type on one object."""
    measurementType: str
    value: float
    unit: str = Field(default="count")
    status: MeasurementResultStatus = Field(default=MeasurementResultStatus.VALID)


class MeasurementResult(BaseModel):
    """Measurement results for one measured object over one granularity period."""
    measuredObjectDn: str
    granularityPeriodSec: int
    values: List[MeasurementValue] = Field(default_factory=list)


class MeasurementReport(BaseModel):
    """
    A PM measurement report (one granularity period) per 3GPP TS 28.550 /
    TS 32.435. For FILE_BASED jobs this is serialized into the result file; for
    STREAM_BASED jobs it maps onto a VES measurement event.
    """
    jobId: str
    beginTime: datetime
    endTime: datetime
    granularityPeriodSec: int
    results: List[MeasurementResult] = Field(default_factory=list)


# =============================================================================
# PmJobManager
# =============================================================================

class PmJobManager:
    """
    Owns PM measurement job state and produces simulated PM data.

    For FILE_BASED jobs the manager writes 3GPP TS 32.435-style measurement
    result files (JSON-encoded ``MeasurementReport``) under a base output
    directory; for STREAM_BASED jobs it returns the in-memory report so the
    caller can map it onto a VES measurement event. Values are generated from
    the measurement catalog ranges so produced data is plausible.
    """

    def __init__(self, base_output_dir: Optional[str] = None) -> None:
        self.jobs: Dict[str, PmMeasurementJob] = {}
        # Per-job list of produced file paths (FILE_BASED).
        self.files: Dict[str, List[str]] = {}
        # Per-job list of produced reports (most recent first).
        self.reports: Dict[str, List[MeasurementReport]] = {}
        self.base_output_dir = base_output_dir or os.path.join(
            tempfile.gettempdir(), "oran_o1_pm"
        )
        try:
            os.makedirs(self.base_output_dir, exist_ok=True)
        except OSError:
            # Fall back to tmp root if the chosen directory is not writable.
            self.base_output_dir = tempfile.gettempdir()

    # -- job lifecycle --------------------------------------------------------

    def create_job(self, job: PmMeasurementJob) -> PmMeasurementJob:
        """Register a PM job, defaulting unset measurement types to a baseline set."""
        if not job.measurementTypes:
            job.measurementTypes = [
                "RRC.ConnEstabAtt",
                "RRC.ConnEstabSucc",
                "DRB.PdcpSduVolumeDL",
                "DRB.PdcpSduVolumeUL",
                "RRU.PrbUsedDl",
                "RRU.PrbUsedUl",
                "CARR.AvgCqi",
            ]
        if not job.measuredObjectDns:
            job.measuredObjectDns = ["ManagedElement=gnb-001,NRCellDU=cell-1"]
        if job.reportingMethod == ReportingMethod.FILE_BASED and not job.fileReportingPath:
            job.fileReportingPath = os.path.join(self.base_output_dir, job.jobId)
            try:
                os.makedirs(job.fileReportingPath, exist_ok=True)
            except OSError:
                job.fileReportingPath = self.base_output_dir
        job.state = PmJobState.ACTIVE
        self.jobs[job.jobId] = job
        self.files.setdefault(job.jobId, [])
        self.reports.setdefault(job.jobId, [])
        return job

    def get_job(self, job_id: str) -> Optional[PmMeasurementJob]:
        return self.jobs.get(job_id)

    def list_jobs(self, state: Optional[PmJobState] = None) -> List[PmMeasurementJob]:
        jobs = list(self.jobs.values())
        if state is not None:
            jobs = [j for j in jobs if j.state == state]
        return jobs

    def stop_job(self, job_id: str) -> Optional[PmMeasurementJob]:
        job = self.jobs.get(job_id)
        if job is not None:
            job.state = PmJobState.STOPPED
        return job

    # -- data generation ------------------------------------------------------

    def _measure(self, measurement_type: str) -> MeasurementValue:
        """Generate one plausible measured value from the catalog ranges."""
        entry = _catalog_entry(measurement_type)
        if entry is None:
            value = float(random.randint(0, 1000))
            unit = "count"
        else:
            low, high = int(entry["low"]), int(entry["high"])
            value = float(random.randint(low, high)) if high > low else float(low)
            unit = str(entry["unit"])
        status = (
            MeasurementResultStatus.SUSPECT
            if random.random() < 0.02
            else MeasurementResultStatus.VALID
        )
        return MeasurementValue(
            measurementType=measurement_type, value=value, unit=unit, status=status
        )

    def generate_report(self, job_id: str) -> Optional[MeasurementReport]:
        """Generate one granularity-period measurement report for a job."""
        job = self.jobs.get(job_id)
        if job is None:
            return None
        gp = int(job.granularityPeriod.value)
        end = _now()
        begin = end - timedelta(seconds=gp)
        results: List[MeasurementResult] = []
        for dn in job.measuredObjectDns:
            values = [self._measure(mt) for mt in job.measurementTypes]
            results.append(
                MeasurementResult(
                    measuredObjectDn=dn, granularityPeriodSec=gp, values=values
                )
            )
        return MeasurementReport(
            jobId=job.jobId,
            beginTime=begin,
            endTime=end,
            granularityPeriodSec=gp,
            results=results,
        )

    def produce(self, job_id: str, periods: int = 1) -> Dict[str, Any]:
        """
        Produce ``periods`` granularity-period reports for a job.

        FILE_BASED jobs are written to disk as 3GPP TS 32.435-style result files
        (one file per report); the report objects are also retained in memory so
        STREAM_BASED jobs (and the O1 PM data route) can read them back.
        """
        job = self.jobs.get(job_id)
        if job is None:
            return {"jobId": job_id, "status": "not-found", "reports": [], "files": []}
        produced_reports: List[MeasurementReport] = []
        produced_files: List[str] = []
        for _ in range(max(1, periods)):
            report = self.generate_report(job_id)
            if report is None:
                continue
            produced_reports.append(report)
            if job.reportingMethod == ReportingMethod.FILE_BASED:
                path = self._write_file(job, report)
                if path:
                    produced_files.append(path)
        # Retain most-recent-first in memory.
        self.reports[job_id] = produced_reports + self.reports.get(job_id, [])
        self.files.setdefault(job_id, []).extend(produced_files)
        return {
            "jobId": job_id,
            "status": "produced",
            "reportingMethod": job.reportingMethod.value,
            "reports": [r.model_dump(mode="json") for r in produced_reports],
            "files": produced_files,
        }

    def _write_file(self, job: PmMeasurementJob, report: MeasurementReport) -> Optional[str]:
        """Write a 3GPP TS 32.435-style measurement result file to disk."""
        out_dir = job.fileReportingPath or self.base_output_dir
        # 3GPP file naming convention: A<startTime>.<endTime>_<element>.json
        ts_begin = report.beginTime.strftime("%Y%m%d.%H%M")
        ts_end = report.endTime.strftime("%H%M")
        fname = f"A{ts_begin}-{ts_end}_{job.jobId}.json"
        path = os.path.join(out_dir, fname)
        payload = {
            "measDataCollection": {
                "measFileHeader": {
                    "fileFormatVersion": "32.435 V10.0",
                    "vendorName": "ORAN-Emulator",
                    "dnPrefix": "DC=oran-emulator",
                    "measCollec": {"beginTime": report.beginTime.isoformat()},
                },
                "measData": report.model_dump(mode="json"),
                "measFileFooter": {
                    "measCollec": {"endTime": report.endTime.isoformat()}
                },
            }
        }
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2)
        except OSError:
            return None
        return path

    # -- read-back ------------------------------------------------------------

    def get_data(self, job_id: str, limit: int = 10) -> Dict[str, Any]:
        """Return recent reports and produced file paths for a job."""
        job = self.jobs.get(job_id)
        if job is None:
            return {"jobId": job_id, "status": "not-found", "reports": [], "files": []}
        if not self.reports.get(job_id):
            # Lazily produce one report so callers always see data.
            self.produce(job_id, periods=1)
        reports = self.reports.get(job_id, [])[: max(1, limit)]
        return {
            "jobId": job_id,
            "jobName": job.jobName,
            "reportingMethod": job.reportingMethod.value,
            "granularityPeriodSec": int(job.granularityPeriod.value),
            "files": self.files.get(job_id, []),
            "reports": [r.model_dump(mode="json") for r in reports],
        }

    def summary(self) -> Dict[str, Any]:
        """Aggregate counts for the PM subsystem."""
        return {
            "spec": "O-RAN.WG10.TS.O1PMeas-R005-v05.00",
            "jobs": len(self.jobs),
            "activeJobs": len(self.list_jobs(state=PmJobState.ACTIVE)),
            "files": sum(len(v) for v in self.files.values()),
            "measurementFamilies": [f.value for f in MeasurementFamily],
            "baseOutputDir": self.base_output_dir,
        }
