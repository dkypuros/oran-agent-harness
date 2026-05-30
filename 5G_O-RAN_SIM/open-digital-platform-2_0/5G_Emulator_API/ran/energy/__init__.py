"""
O-RAN WG1 Network Energy Savings (NES) package.

Implements the WG1 Network Energy Savings technical report as a 5G emulator
service: cell-level sleep modes (cell switch-off, carrier / RF-chain shutdown,
advanced symbol-level sleep), energy KPIs (power consumption, energy efficiency),
energy-savings (ES) policies driven via rApp / A1, and wake-up triggers.

Modules
-------
- nes : O-RAN.WG1.Network-Energy-Savings-Technical-Report-R003-v02.00 NES service (port 8130)
"""

__version__ = "1.0.0"
__all__ = ["nes"]
