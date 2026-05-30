"""
O-RAN WG9 xHaul Transport package.

Implements the WG9 transport node management and timing/synchronization plane as a
5G emulator service: fronthaul / midhaul / backhaul transport nodes and links,
PTP / SyncE timing distribution, clock node types (T-GM grandmaster, T-BC boundary,
T-TSC slave), clock classes / quality, holdover, sync topology, and network sync
health (time-error budget).

Modules
-------
- xhaul : O-RAN.WG9.XTRP-MGT.0-R004-v10.00 + O-RAN.WG9.XTRP-SYN.0-R004-v07.00
          transport + sync service (port 8131)
"""

__version__ = "1.0.0"
__all__ = ["xhaul"]
