"""5G_O-RAN_SIM LLM inference layer.

Provides a unified completion() function across Anthropic Claude, OpenAI GPT,
and a local OpenShift AI vLLM mock. Configured via 5G_O-RAN_SIM/.env (template
in .env.example).
"""

from .inference_client import completion

__all__ = ["completion"]
