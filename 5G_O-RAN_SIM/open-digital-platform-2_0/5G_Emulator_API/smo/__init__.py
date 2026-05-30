"""
O-RAN SMO Framework package.

Implements the WG2 R1 interface, the WG1/WG2 SMO coordinator (framework), and the
WG2 AI/ML workflow library for the 5G emulator.

Modules
-------
- aiml          : O-RAN.WG2.AIML-v01.03 AI/ML workflow descriptors + AimlModelRegistry
- r1            : O-RAN.WG2.TS.R1AP/R1GAP/R1TD R1 interface service (port 8124)
- smo_framework : O-RAN.WG1.TS.OAD / WG2.TS.Non-RT-RIC-ARCH SMO coordinator (port 8122)
"""

__version__ = "1.0.0"
__all__ = ["aiml", "r1", "smo_framework"]
