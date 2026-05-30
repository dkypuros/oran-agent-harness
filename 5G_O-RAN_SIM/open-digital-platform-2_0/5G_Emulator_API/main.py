import subprocess
import logging
import os
import argparse
import psutil
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Protocol mode: passed to NFs that support it
protocol_mode = "rest"

# NFs that support --protocol-mode flag
PROTOCOL_AWARE_NFS = {
    "core_network/amf.py",
    "core_network/smf.py",
    "core_network/upf.py",
    "ran/gnb.py",
}

def kill_process_on_port(port):
    for conn in psutil.net_connections():
        if conn.laddr.port == port:
            try:
                process = psutil.Process(conn.pid)
                process.terminate()
                logger.info(f"Terminated process on port {port}")
                return True
            except psutil.NoSuchProcess:
                pass
    return False

def start_nf(file_path, port):
    full_path = os.path.join(current_dir, file_path)
    if kill_process_on_port(port):
        time.sleep(1)  # Wait for the port to be released
    try:
        cmd = ["python", full_path, "--host", "0.0.0.0", "--port", str(port)]
        # Pass --protocol-mode to NFs that support it
        if file_path in PROTOCOL_AWARE_NFS:
            cmd.extend(["--protocol-mode", protocol_mode])
        process = subprocess.Popen(cmd)
        mode_label = f" [protocol-mode={protocol_mode}]" if file_path in PROTOCOL_AWARE_NFS else ""
        logger.info(f"Started {file_path} on port {port}{mode_label}")
        return process
    except Exception as e:
        logger.error(f"Failed to start {file_path}: {str(e)}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="5G Emulator API - Launch all network functions")
    parser.add_argument("--protocol-mode", choices=["rest", "real"], default="rest",
                        help="Transport mode: rest (HTTP only, default) or "
                             "real (enables 3GPP transport protocols: "
                             "SCTP/TCP for NGAP, UDP for GTP-U/PFCP, TUN for N6)")
    args = parser.parse_args()
    protocol_mode = args.protocol_mode

    if protocol_mode == "real":
        logger.info("=" * 70)
        logger.info("  PROTOCOL MODE: REAL")
        logger.info("  Enabling 3GPP transport protocols alongside REST APIs:")
        logger.info("    - AMF: NGAP server on TCP port 38412 (N2)")
        logger.info("    - SMF: PFCP client on UDP port 8805 (N4)")
        logger.info("    - UPF: GTP-U on UDP port 2152 (N3) + PFCP on UDP 8805 (N4)")
        logger.info("    - gNB: NGAP client on TCP port 38412 (N2) + GTP-U (N3)")
        logger.info("  All existing REST APIs remain active for demo visibility.")
        logger.info("=" * 70)

    processes = []

    # Start NRF
    processes.append(start_nf("core_network/nrf.py", 8000))

    # Start Network Functions
    processes.append(start_nf("core_network/amf.py", 9000))
    processes.append(start_nf("core_network/smf.py", 9001))
    processes.append(start_nf("core_network/upf.py", 9002))
    processes.append(start_nf("core_network/ausf.py", 9003))
    processes.append(start_nf("core_network/udm.py", 9004))
    processes.append(start_nf("core_network/udr.py", 9005))
    processes.append(start_nf("core_network/udsf.py", 9006))

    # Start CU and DU
    processes.append(start_nf("ran/cu/cu.py", 9008))
    processes.append(start_nf("ran/du/du.py", 9007))

    # Start RRU
    processes.append(start_nf("ran/rru/rru.py", 9009))

    # Start PTP
    processes.append(start_nf("ptp/ptp.py", 9010))

    # Start Service Assurance
    processes.append(start_nf("service_assurance/assurance_api.py", 9011))

    # =====================================================================
    # O-RAN enhancement layer (WG1-WG11) - spec-cited FastAPI services
    # =====================================================================
    logger.info("Starting O-RAN enhancement layer (WG1-WG11)...")

    # WG2/WG1 SMO framework coordinator (OAD / Non-RT-RIC-ARCH)
    processes.append(start_nf("smo/smo_framework.py", 8122))
    # WG2 R1 interface (rApp <-> SMO: SME + DME)
    processes.append(start_nf("smo/r1.py", 8124))

    # WG3 Y1 RAN Analytics
    processes.append(start_nf("ran/ric/y1.py", 8123))

    # WG4 Open Fronthaul O-RU (M-Plane + CUS-Plane)
    processes.append(start_nf("ran/fronthaul/o_ru.py", 8120))

    # WG10 O1 / OAM and Topology Exposure & Inventory
    processes.append(start_nf("oam/o1.py", 8125))
    processes.append(start_nf("oam/teiv.py", 8126))

    # WG6 O-Cloud Notification API
    processes.append(start_nf("etsi/o2/o_cloud_notification.py", 8127))

    # WG11 Security (OAuth2 / Zero-Trust / PQC / cert)
    processes.append(start_nf("security/security_service.py", 8128))

    # WG1 RAN Slicing (NSSMF) and Network Energy Savings (NES)
    processes.append(start_nf("ran/slicing/oran_slicing.py", 8129))
    processes.append(start_nf("ran/energy/nes.py", 8130))

    # WG9 xHaul Transport and Synchronization
    processes.append(start_nf("transport/xhaul.py", 8131))

    # Front-end aggregation gateway (serves the dashboard contract on :8088)
    processes.append(start_nf("api_gateway/oran_gateway.py", 8088))

    logger.info("All components started (5G core + RAN + O-RAN WG1-WG11 + gateway :8088)")

    # Wait for all processes to finish
    for process in processes:
        if process:
            process.wait()

    logger.info("All components have finished")