"""5G_O-RAN_SIM LLM inference layer.

Provides a unified completion() function across Anthropic Claude, the OpenAI
API, and OpenAI-compatible on-prem vLLM endpoints such as Red Hat OpenShift AI.
Configured via 5G_O-RAN_SIM/.env (template in .env.example).
"""

from .inference_client import completion

__all__ = ["completion"]
