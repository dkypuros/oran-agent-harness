#!/usr/bin/env python3
"""
O-RAN AI/ML Workflow library.

Spec: O-RAN.WG2.AIML-v01.03 (AI/ML workflow description and requirements for the
O-RAN Non-RT RIC / SMO framework).

This module is a pure library (no FastAPI app). It provides:
- ML model lifecycle states (TRAINING, TRAINED, DEPLOYED, RETIRED, ...)
- The six canonical O-RAN AI/ML workflow stages (data collection, training,
  validation, deployment, inference, monitoring)
- Pydantic descriptors for training jobs, deployment jobs, and model registry
  entries
- An ``AimlModelRegistry`` class that owns model + job state and drives models
  through the AI/ML workflow.

The R1 service (smo/r1.py) imports ``AimlModelRegistry`` to expose AI/ML-related
R1 services to rApps; the SMO framework references the same AI/ML stages when it
advertises framework-service capability.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def _now() -> datetime:
    """UTC timestamp helper (timezone-aware per O-RAN logging conventions)."""
    return datetime.now(timezone.utc)


# =============================================================================
# Enumerations (per O-RAN.WG2.AIML-v01.03)
# =============================================================================

class ModelLifecycleState(str, Enum):
    """
    ML model lifecycle states per O-RAN.WG2.AIML-v01.03 Section 5 (AI/ML model
    lifecycle management).

    A model is REGISTERED on catalog onboarding, transitions to TRAINING while a
    training job runs, becomes TRAINED once validation passes, DEPLOYED when an
    inference instance is instantiated, and RETIRED when withdrawn from service.
    FAILED captures training or validation failure.
    """
    REGISTERED = "REGISTERED"
    TRAINING = "TRAINING"
    TRAINED = "TRAINED"
    VALIDATED = "VALIDATED"
    DEPLOYED = "DEPLOYED"
    RETIRED = "RETIRED"
    FAILED = "FAILED"


class WorkflowStage(str, Enum):
    """
    O-RAN AI/ML workflow stages per O-RAN.WG2.AIML-v01.03 Section 6 (AI/ML
    workflow). The Non-RT RIC framework orchestrates a model through these stages.
    """
    DATA_COLLECTION = "DATA_COLLECTION"
    TRAINING = "TRAINING"
    VALIDATION = "VALIDATION"
    DEPLOYMENT = "DEPLOYMENT"
    INFERENCE = "INFERENCE"
    MONITORING = "MONITORING"


class TrainingJobState(str, Enum):
    """Training-job execution states (AI/ML training host / training function)."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class DeploymentJobState(str, Enum):
    """Deployment-job execution states (AI/ML inference host)."""
    PENDING = "PENDING"
    DEPLOYING = "DEPLOYING"
    RUNNING = "RUNNING"
    TERMINATED = "TERMINATED"
    FAILED = "FAILED"


class ModelLocation(str, Enum):
    """Where an AI/ML function (training or inference) is hosted."""
    NON_RT_RIC = "NON_RT_RIC"
    NEAR_RT_RIC = "NEAR_RT_RIC"
    SMO = "SMO"
    O_CLOUD = "O_CLOUD"


# Canonical, ordered list of the six O-RAN AI/ML workflow stages.
AIML_WORKFLOW_STAGES: List[WorkflowStage] = [
    WorkflowStage.DATA_COLLECTION,
    WorkflowStage.TRAINING,
    WorkflowStage.VALIDATION,
    WorkflowStage.DEPLOYMENT,
    WorkflowStage.INFERENCE,
    WorkflowStage.MONITORING,
]


# =============================================================================
# Data Models (Pydantic)
# =============================================================================

class ModelMetrics(BaseModel):
    """Validation / monitoring metrics for an ML model."""
    accuracy: Optional[float] = Field(default=None, description="Validation accuracy [0..1]")
    precision: Optional[float] = Field(default=None, description="Validation precision [0..1]")
    recall: Optional[float] = Field(default=None, description="Validation recall [0..1]")
    f1Score: Optional[float] = Field(default=None, description="F1 score [0..1]")
    customMetrics: Dict[str, float] = Field(default_factory=dict, description="Vendor-specific metrics")


class DataCollectionSpec(BaseModel):
    """
    Data-collection descriptor (AI/ML workflow stage 1).

    Describes the training/validation data the AI/ML workflow consumes. In a real
    deployment this is sourced over the R1 Data Management & Exposure (DME)
    services or the O1 measurement collection interface.
    """
    sourceType: str = Field(default="DME", description="Data source: DME, O1, A1-EI, FILE")
    dataTypeId: Optional[str] = Field(default=None, description="DME data type identifier")
    featureSet: List[str] = Field(default_factory=list, description="Feature names")
    samples: Optional[int] = Field(default=None, description="Number of training samples")
    windowSeconds: Optional[int] = Field(default=None, description="Collection window (s)")


class TrainingJob(BaseModel):
    """
    AI/ML training-job descriptor per O-RAN.WG2.AIML-v01.03 Section 6.2.

    Submitted to the AI/ML training host (typically in the Non-RT RIC). Drives a
    model from REGISTERED/TRAINING to TRAINED.
    """
    trainingJobId: str = Field(default_factory=lambda: str(uuid.uuid4()))
    modelId: str = Field(..., description="Target model registry ID")
    trainingHost: ModelLocation = Field(default=ModelLocation.NON_RT_RIC)
    dataSpec: DataCollectionSpec = Field(default_factory=DataCollectionSpec)
    hyperParameters: Dict[str, Any] = Field(default_factory=dict, description="Training hyper-parameters")
    state: TrainingJobState = Field(default=TrainingJobState.PENDING)
    progressPercent: int = Field(default=0, ge=0, le=100)
    metrics: Optional[ModelMetrics] = Field(default=None)
    createdAt: datetime = Field(default_factory=_now)
    updatedAt: datetime = Field(default_factory=_now)
    error: Optional[str] = Field(default=None)


class DeploymentJob(BaseModel):
    """
    AI/ML deployment-job descriptor per O-RAN.WG2.AIML-v01.03 Section 6.4.

    Submitted to the AI/ML inference host to instantiate a TRAINED model for
    serving. Drives a model to DEPLOYED.
    """
    deploymentJobId: str = Field(default_factory=lambda: str(uuid.uuid4()))
    modelId: str = Field(..., description="Model registry ID to deploy")
    inferenceHost: ModelLocation = Field(default=ModelLocation.NEAR_RT_RIC)
    targetEndpoint: Optional[str] = Field(default=None, description="Inference serving endpoint")
    replicas: int = Field(default=1, ge=1, description="Number of inference instances")
    state: DeploymentJobState = Field(default=DeploymentJobState.PENDING)
    createdAt: datetime = Field(default_factory=_now)
    updatedAt: datetime = Field(default_factory=_now)
    error: Optional[str] = Field(default=None)


class ModelRegistryEntry(BaseModel):
    """
    ML model registry entry / model descriptor per O-RAN.WG2.AIML-v01.03
    Section 5.2 (AI/ML model registration).
    """
    modelId: str = Field(default_factory=lambda: str(uuid.uuid4()))
    modelName: str = Field(..., description="Human-readable model name")
    version: str = Field(default="1.0.0")
    vendor: Optional[str] = Field(default=None)
    description: str = Field(default="")
    modelType: str = Field(default="inference", description="e.g. classification, regression, RL")
    targetUseCase: Optional[str] = Field(default=None, description="e.g. TrafficSteering, AnomalyDetection")
    state: ModelLifecycleState = Field(default=ModelLifecycleState.REGISTERED)
    currentStage: Optional[WorkflowStage] = Field(default=None, description="Active AI/ML workflow stage")
    trainingHost: ModelLocation = Field(default=ModelLocation.NON_RT_RIC)
    inferenceHost: ModelLocation = Field(default=ModelLocation.NEAR_RT_RIC)
    artifactUri: Optional[str] = Field(default=None, description="Trained model artifact location")
    metrics: Optional[ModelMetrics] = Field(default=None)
    activeTrainingJobId: Optional[str] = Field(default=None)
    activeDeploymentJobId: Optional[str] = Field(default=None)
    registeredAt: datetime = Field(default_factory=_now)
    updatedAt: datetime = Field(default_factory=_now)


# =============================================================================
# AI/ML Model Registry
# =============================================================================

class AimlModelRegistry:
    """
    O-RAN AI/ML model registry and workflow orchestrator.

    Per O-RAN.WG2.AIML-v01.03, owns:
    - The model catalog (``ModelRegistryEntry`` keyed by modelId)
    - Training jobs and deployment jobs
    - Lifecycle transitions across the six AI/ML workflow stages

    This is an in-memory implementation suitable for the emulator. The R1 service
    proxies the catalog to rApps via the AI/ML-related R1 services.
    """

    def __init__(self, registry_id: str = "aiml-registry-001"):
        self.registry_id = registry_id
        self.models: Dict[str, ModelRegistryEntry] = {}
        self.training_jobs: Dict[str, TrainingJob] = {}
        self.deployment_jobs: Dict[str, DeploymentJob] = {}
        self._seed_default_models()

    def _seed_default_models(self) -> None:
        """Pre-load representative O-RAN AI/ML use-case models."""
        defaults = [
            ModelRegistryEntry(
                modelId="model-traffic-steering",
                modelName="Traffic Steering Predictor",
                version="1.2.0",
                vendor="ORAN-SC",
                description="Predicts optimal cell for UE traffic steering",
                modelType="classification",
                targetUseCase="TrafficSteering",
                state=ModelLifecycleState.DEPLOYED,
                currentStage=WorkflowStage.INFERENCE,
                metrics=ModelMetrics(accuracy=0.94, precision=0.92, recall=0.91, f1Score=0.915),
                artifactUri="model://registry/traffic-steering/1.2.0",
            ),
            ModelRegistryEntry(
                modelId="model-anomaly-detection",
                modelName="RAN Anomaly Detector",
                version="0.9.0",
                vendor="ORAN-SC",
                description="Detects KPI anomalies in RAN measurements",
                modelType="regression",
                targetUseCase="AnomalyDetection",
                state=ModelLifecycleState.TRAINED,
                currentStage=WorkflowStage.VALIDATION,
                metrics=ModelMetrics(accuracy=0.88),
            ),
            ModelRegistryEntry(
                modelId="model-energy-saving",
                modelName="Energy Saving Optimizer",
                version="1.0.0",
                vendor="ORAN-SC",
                description="Reinforcement-learning cell sleep scheduler",
                modelType="RL",
                targetUseCase="EnergySaving",
                state=ModelLifecycleState.REGISTERED,
                currentStage=WorkflowStage.DATA_COLLECTION,
            ),
        ]
        for entry in defaults:
            self.models[entry.modelId] = entry

    # -- Model catalog --------------------------------------------------------

    def register_model(self, entry: ModelRegistryEntry) -> ModelRegistryEntry:
        """Register (onboard) a model into the catalog."""
        entry.state = ModelLifecycleState.REGISTERED
        entry.currentStage = WorkflowStage.DATA_COLLECTION
        entry.updatedAt = _now()
        self.models[entry.modelId] = entry
        return entry

    def get_model(self, model_id: str) -> Optional[ModelRegistryEntry]:
        """Return a model entry or None."""
        return self.models.get(model_id)

    def list_models(
        self,
        state: Optional[ModelLifecycleState] = None,
        use_case: Optional[str] = None,
    ) -> List[ModelRegistryEntry]:
        """List models, optionally filtered by lifecycle state or use case."""
        result = list(self.models.values())
        if state is not None:
            result = [m for m in result if m.state == state]
        if use_case is not None:
            result = [m for m in result if m.targetUseCase == use_case]
        return result

    def retire_model(self, model_id: str) -> Optional[ModelRegistryEntry]:
        """Withdraw a model from service (RETIRED)."""
        entry = self.models.get(model_id)
        if entry is None:
            return None
        entry.state = ModelLifecycleState.RETIRED
        entry.currentStage = None
        entry.updatedAt = _now()
        return entry

    # -- Training jobs (workflow stages 1-3) ---------------------------------

    def submit_training_job(self, job: TrainingJob) -> Optional[TrainingJob]:
        """
        Submit a training job for a registered model. Moves the model into the
        TRAINING lifecycle state and the TRAINING workflow stage.
        """
        entry = self.models.get(job.modelId)
        if entry is None:
            return None
        job.state = TrainingJobState.RUNNING
        job.updatedAt = _now()
        self.training_jobs[job.trainingJobId] = job
        entry.state = ModelLifecycleState.TRAINING
        entry.currentStage = WorkflowStage.TRAINING
        entry.activeTrainingJobId = job.trainingJobId
        entry.trainingHost = job.trainingHost
        entry.updatedAt = _now()
        return job

    def complete_training_job(
        self,
        training_job_id: str,
        metrics: Optional[ModelMetrics] = None,
        artifact_uri: Optional[str] = None,
    ) -> Optional[TrainingJob]:
        """Mark a training job complete and advance the model to TRAINED/VALIDATION."""
        job = self.training_jobs.get(training_job_id)
        if job is None:
            return None
        job.state = TrainingJobState.COMPLETED
        job.progressPercent = 100
        job.metrics = metrics or job.metrics
        job.updatedAt = _now()
        entry = self.models.get(job.modelId)
        if entry is not None:
            entry.state = ModelLifecycleState.TRAINED
            entry.currentStage = WorkflowStage.VALIDATION
            entry.metrics = job.metrics
            entry.artifactUri = artifact_uri or entry.artifactUri
            entry.updatedAt = _now()
        return job

    def get_training_job(self, training_job_id: str) -> Optional[TrainingJob]:
        return self.training_jobs.get(training_job_id)

    def list_training_jobs(self) -> List[TrainingJob]:
        return list(self.training_jobs.values())

    # -- Deployment jobs (workflow stages 4-6) -------------------------------

    def submit_deployment_job(self, job: DeploymentJob) -> Optional[DeploymentJob]:
        """
        Deploy a TRAINED/VALIDATED model to an inference host. Moves the model to
        DEPLOYED / INFERENCE.
        """
        entry = self.models.get(job.modelId)
        if entry is None:
            return None
        job.state = DeploymentJobState.RUNNING
        job.updatedAt = _now()
        self.deployment_jobs[job.deploymentJobId] = job
        entry.state = ModelLifecycleState.DEPLOYED
        entry.currentStage = WorkflowStage.INFERENCE
        entry.activeDeploymentJobId = job.deploymentJobId
        entry.inferenceHost = job.inferenceHost
        entry.updatedAt = _now()
        return job

    def terminate_deployment_job(self, deployment_job_id: str) -> Optional[DeploymentJob]:
        """Terminate an inference deployment; model returns to TRAINED."""
        job = self.deployment_jobs.get(deployment_job_id)
        if job is None:
            return None
        job.state = DeploymentJobState.TERMINATED
        job.updatedAt = _now()
        entry = self.models.get(job.modelId)
        if entry is not None and entry.state == ModelLifecycleState.DEPLOYED:
            entry.state = ModelLifecycleState.TRAINED
            entry.currentStage = WorkflowStage.MONITORING
            entry.activeDeploymentJobId = None
            entry.updatedAt = _now()
        return job

    def get_deployment_job(self, deployment_job_id: str) -> Optional[DeploymentJob]:
        return self.deployment_jobs.get(deployment_job_id)

    def list_deployment_jobs(self) -> List[DeploymentJob]:
        return list(self.deployment_jobs.values())

    # -- Workflow introspection ----------------------------------------------

    def workflow_stages(self) -> List[str]:
        """Return the ordered O-RAN AI/ML workflow stage names."""
        return [stage.value for stage in AIML_WORKFLOW_STAGES]

    def summary(self) -> Dict[str, Any]:
        """Registry summary for SMO inventory / health surfaces."""
        by_state: Dict[str, int] = {}
        for entry in self.models.values():
            by_state[entry.state.value] = by_state.get(entry.state.value, 0) + 1
        return {
            "registryId": self.registry_id,
            "spec": "O-RAN.WG2.AIML-v01.03",
            "totalModels": len(self.models),
            "modelsByState": by_state,
            "trainingJobs": len(self.training_jobs),
            "deploymentJobs": len(self.deployment_jobs),
            "workflowStages": self.workflow_stages(),
        }


__all__ = [
    "ModelLifecycleState",
    "WorkflowStage",
    "TrainingJobState",
    "DeploymentJobState",
    "ModelLocation",
    "AIML_WORKFLOW_STAGES",
    "ModelMetrics",
    "DataCollectionSpec",
    "TrainingJob",
    "DeploymentJob",
    "ModelRegistryEntry",
    "AimlModelRegistry",
]
