"""
O-RAN WG10 OAM / O1 / TE&IV package.

Implements the WG10 management plane for the 5G emulator: the O1 interface
termination (FCAPS over a NETCONF/YANG-style Network Resource Model), the
Performance Management (PM) measurement library, the VES (Virtual Event
Streaming) 7.x common event format used by O1, and the Topology Exposure &
Inventory (TE&IV) graph service.

Modules
-------
- pm    : O-RAN.WG10.TS.O1PMeas-R005-v05.00 PM measurement model + PmJobManager
- ves   : VES 7.x common event format, VesEventBuilder + VesCollectorClient
- o1    : O-RAN.WG10.TS.O1-Interface.0-R005-v18.00 O1 termination (port 8125)
- teiv  : O-RAN.WG10.TS.TE&IV-API.0-R005-v04.00 topology + inventory (port 8126)
"""

__version__ = "1.0.0"
__all__ = ["pm", "ves", "o1", "teiv"]
