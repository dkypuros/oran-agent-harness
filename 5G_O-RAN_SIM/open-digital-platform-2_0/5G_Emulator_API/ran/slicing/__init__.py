"""
O-RAN WG1 RAN Slicing package.

Implements the WG1 Slicing Architecture as a 5G emulator service: S-NSSAI driven
Network Slice Instances (NSI) and Network Slice Subnet Instances (NSSI), per-slice
SLA (throughput / latency / reliability), per-slice RRM PRB-allocation policy, and
slice-level KPIs.

Modules
-------
- oran_slicing : O-RAN.WG1.TS.Slicing-Architecture-R004-v14.01 NSSMF service (port 8129)
"""

__version__ = "1.0.0"
__all__ = ["oran_slicing"]
