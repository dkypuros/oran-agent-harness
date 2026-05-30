# File location: 5G_Emulator_API/core_network/upf.py
# Enhanced with 3GPP TS 29.244 PFCP protocol support for N4 interface
# Real protocol mode: GTP-U (UDP 2152) + TUN interface + PFCP (UDP 8805)
from fastapi import FastAPI, Request, HTTPException
import uvicorn
import requests
import logging
import json
import asyncio
from contextlib import asynccontextmanager
from typing import Dict
from datetime import datetime
import os
import sys
import uuid
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource

# Create logs directory if it doesn't exist
logs_dir = "logs"
os.makedirs(logs_dir, exist_ok=True)

# Set up logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"{logs_dir}/upf_{timestamp}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Set up tracing
resource = Resource.create({"service.name": "upf-service"})
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

nrf_url = "http://127.0.0.1:8000"

# Protocol mode: "rest" (default) or "real" (GTP-U + TUN + PFCP)
PROTOCOL_MODE = os.environ.get("PROTOCOL_MODE", "rest")

# This dictionary simulates the UPF's forwarding table
# In a real UPF, this would program hardware/kernel forwarding tables
forwarding_rules: Dict[str, Dict] = {}
pfcp_sessions: Dict[str, Dict] = {}  # PFCP session state

# Real protocol transport instances (initialized in lifespan if mode=real)
_gtpu_transport = None
_pfcp_transport = None
_tun_interface = None

# TEID-to-UE-IP mapping for GTP-U forwarding
_teid_map: Dict[int, str] = {}


async def _handle_gtpu_packet(teid: int, payload: bytes, addr):
    """Handle incoming GTP-U packet on N3 interface (uplink from gNB)."""
    ue_ip = _teid_map.get(teid)
    logger.info(f"UPF GTP-U: Received {len(payload)} byte packet, "
                f"TEID={teid}, from={addr}, UE-IP={ue_ip or 'unknown'}")
    # Decapsulated inner IP packet -> forward to TUN (N6 toward data network)
    if _tun_interface:
        await _tun_interface.write(payload)
    else:
        logger.debug(f"UPF GTP-U: TUN not active, simulating N6 forward for TEID={teid}")


async def _handle_tun_packet(packet: bytes):
    """Handle packet from TUN interface (downlink from data network toward UE)."""
    # Extract destination IP from IPv4 header to find matching TEID
    if len(packet) >= 20 and (packet[0] >> 4) == 4:
        dest_ip = f"{packet[16]}.{packet[17]}.{packet[18]}.{packet[19]}"
        # Find TEID for this UE IP (reverse lookup)
        for teid_val, ue_ip in _teid_map.items():
            if ue_ip == dest_ip:
                # Re-encapsulate and send back to gNB via GTP-U
                if _gtpu_transport:
                    # In a full deployment, we'd look up the gNB endpoint
                    logger.info(f"UPF GTP-U: Downlink {len(packet)} bytes to "
                                f"UE {dest_ip}, TEID={teid_val}")
                return
    logger.debug(f"UPF TUN: No matching TEID for downlink packet ({len(packet)} bytes)")


async def _handle_pfcp_message(msg_type: int, seid: int, seq: int,
                                ie_data: bytes, addr):
    """Handle incoming PFCP message on N4 interface (from SMF)."""
    from core_network.transport import (
        PFCP_SESSION_ESTABLISHMENT_REQUEST, PFCP_SESSION_ESTABLISHMENT_RESPONSE,
        PFCP_SESSION_MODIFICATION_REQUEST, PFCP_SESSION_MODIFICATION_RESPONSE,
        PFCP_SESSION_DELETION_REQUEST, PFCP_SESSION_DELETION_RESPONSE,
        PFCP_ASSOCIATION_SETUP_REQUEST, PFCP_ASSOCIATION_SETUP_RESPONSE,
        build_pfcp_header
    )

    logger.info(f"UPF PFCP: Received msg_type={msg_type}, SEID={seid}, "
                f"seq={seq}, from={addr}")

    if msg_type == PFCP_ASSOCIATION_SETUP_REQUEST:
        # Respond with Association Setup Response
        if _pfcp_transport:
            await _pfcp_transport.send_message(
                PFCP_ASSOCIATION_SETUP_RESPONSE, 0, b'', addr, seq_number=seq)
        logger.info(f"UPF PFCP: Association established with SMF at {addr}")

    elif msg_type == PFCP_SESSION_ESTABLISHMENT_REQUEST:
        upf_seid = abs(hash(uuid.uuid4())) & 0xFFFFFFFFFFFFFFFF
        pfcp_sessions[str(seid)] = {
            "upfSeid": upf_seid, "state": "ACTIVE", "smf_addr": addr
        }
        logger.info(f"UPF PFCP: Session established, SMF-SEID={seid}, UPF-SEID={upf_seid}")
        if _pfcp_transport:
            await _pfcp_transport.send_message(
                PFCP_SESSION_ESTABLISHMENT_RESPONSE, upf_seid, b'', addr,
                seq_number=seq)

    elif msg_type == PFCP_SESSION_MODIFICATION_REQUEST:
        logger.info(f"UPF PFCP: Session modified, SEID={seid}")
        if _pfcp_transport:
            await _pfcp_transport.send_message(
                PFCP_SESSION_MODIFICATION_RESPONSE, seid, b'', addr,
                seq_number=seq)

    elif msg_type == PFCP_SESSION_DELETION_REQUEST:
        pfcp_sessions.pop(str(seid), None)
        logger.info(f"UPF PFCP: Session deleted, SEID={seid}")
        if _pfcp_transport:
            await _pfcp_transport.send_message(
                PFCP_SESSION_DELETION_RESPONSE, seid, b'', addr,
                seq_number=seq)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _gtpu_transport, _pfcp_transport, _tun_interface

    # Startup
    nf_registration = {
        "nf_type": "UPF",
        "ip": "127.0.0.1",
        "port": 9002
    }
    try:
        response = requests.post(f"{nrf_url}/register", json=nf_registration)
        response.raise_for_status()
        logger.info("UPF registered with NRF")
    except requests.RequestException as e:
        logger.error(f"Failed to register UPF with NRF: {str(e)}")

    # Start real protocol transports if mode=real
    if PROTOCOL_MODE == "real":
        try:
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from core_network.transport import GtpuTransport, PfcpTransport, TunInterface

            # 1. GTP-U on UDP port 2152 (N3 interface)
            _gtpu_transport = GtpuTransport()
            await _gtpu_transport.start(_handle_gtpu_packet)

            # 2. PFCP on UDP port 8805 (N4 interface)
            _pfcp_transport = PfcpTransport()
            await _pfcp_transport.start(_handle_pfcp_message)

            # 3. TUN interface for N6 (toward data network)
            _tun_interface = TunInterface(name='ogstun')
            tun_ok = await _tun_interface.open(packet_handler=_handle_tun_packet)
            if not tun_ok:
                logger.info("UPF: TUN interface unavailable, N6 forwarding in simulation mode")

            logger.info("UPF: Real protocol transports started "
                        "(GTP-U:2152, PFCP:8805, TUN:ogstun)")
        except Exception as e:
            logger.error(f"UPF: Failed to start real transports: {e}")
            logger.info("UPF: Falling back to REST-only mode")

    yield

    # Shutdown real transports
    if _gtpu_transport:
        await _gtpu_transport.stop()
    if _pfcp_transport:
        await _pfcp_transport.stop()
    if _tun_interface:
        await _tun_interface.close()

app = FastAPI(lifespan=lifespan)

@app.post("/n4/sessions")
async def n4_session_management(request: Request):
    """
    Models the N4 interface, receiving PFCP-like messages from the SMF.
    Reference: 3GPP TS 29.244 - PFCP Protocol
    """
    pfcp_message = await request.json()
    session_id = pfcp_message.get("seid")
    message_type = pfcp_message.get("messageType")
    
    logger.info(f"UPF <- SMF: Received {message_type} for SEID {session_id}")
    
    if message_type == "PFCP_SESSION_ESTABLISHMENT_REQUEST":
        with tracer.start_as_current_span("upf_pfcp_session_establishment") as span:
            span.set_attribute("3gpp.interface", "N4")
            span.set_attribute("3gpp.protocol", "PFCP")
            span.set_attribute("pfcp.seid", session_id)
            span.set_attribute("pfcp.message.type", message_type)
            
            # Generate UPF's own Session Endpoint ID
            upf_seid = f"upf-seid-{str(uuid.uuid4())[:8]}"
            
            # "Install" the forwarding rules from the message
            session_rules = {
                "seid": session_id,
                "upfSeid": upf_seid,
                "state": "ACTIVE",
                "pdrs": [],
                "fars": [],
                "qers": []
            }
            
            # Process PDRs (Packet Detection Rules)
            for pdr in pfcp_message.get("createPDR", []):
                ue_ip = pdr.get("pdi", {}).get("ueIpAddress")
                pdr_id = pdr.get("pdrId")
                if ue_ip:
                    # Find the matching forwarding action
                    far_id = pdr.get("farId")
                    far_rule = next((far for far in pfcp_message.get("createFAR", []) if far.get("farId") == far_id), None)
                    if far_rule:
                        forwarding_rules[ue_ip] = {
                            "far": far_rule.get("forwardingParameters"),
                            "pdr_id": pdr_id,
                            "far_id": far_id,
                            "session_id": session_id
                        }
                        session_rules["pdrs"].append(pdr)
                        session_rules["fars"].append(far_rule)
                        
                        logger.info(f"UPF: Installed forwarding rule for UE IP {ue_ip} -> {far_rule['forwardingParameters']['destinationInterface']}")
            
            # Process QERs (QoS Enforcement Rules)
            for qer in pfcp_message.get("createQER", []):
                session_rules["qers"].append(qer)
                logger.info(f"UPF: Installed QoS rule QER ID {qer.get('qerId')} with QFI {qer.get('qfi')}")
            
            # Store the session
            pfcp_sessions[session_id] = session_rules
            
            # In a real scenario, the UPF would respond with its own SEID and N3 endpoint info
            response = {
                "status": "SESSION_CREATED",
                "cause": "REQUEST_ACCEPTED",
                "upfSeid": upf_seid,
                "n3_endpoint": "192.168.1.100",  # N3 interface endpoint
                "createdPDR": [pdr.get("pdrId") for pdr in pfcp_message.get("createPDR", [])],
                "createdFAR": [far.get("farId") for far in pfcp_message.get("createFAR", [])],
                "createdQER": [qer.get("qerId") for qer in pfcp_message.get("createQER", [])]
            }
            
            span.add_event("pfcp_session_established", {
                "upf.seid": upf_seid,
                "rules.installed": len(forwarding_rules),
                "n3.endpoint": response["n3_endpoint"]
            })
            
            logger.info(f"UPF -> SMF: PFCP Session Establishment Response sent")
            return response
            
    elif message_type == "PFCP_SESSION_MODIFICATION_REQUEST":
        logger.info(f"UPF: Processing session modification for SEID {session_id}")
        # Handle session modifications (simplified)
        return {"status": "SESSION_MODIFIED", "cause": "REQUEST_ACCEPTED"}
        
    elif message_type == "PFCP_SESSION_DELETION_REQUEST":
        logger.info(f"UPF: Processing session deletion for SEID {session_id}")
        # Clean up forwarding rules
        if session_id in pfcp_sessions:
            session = pfcp_sessions[session_id]
            # Remove forwarding rules for this session
            ue_ips_to_remove = [ue_ip for ue_ip, rule in forwarding_rules.items() 
                               if rule.get("session_id") == session_id]
            for ue_ip in ue_ips_to_remove:
                del forwarding_rules[ue_ip]
                logger.info(f"UPF: Removed forwarding rule for UE IP {ue_ip}")
            del pfcp_sessions[session_id]
        
        return {"status": "SESSION_DELETED", "cause": "REQUEST_ACCEPTED"}
    
    return {"status": "UNKNOWN_MESSAGE", "cause": "MESSAGE_TYPE_NOT_SUPPORTED"}

@app.get("/upf/forwarding-rules")
async def get_forwarding_rules():
    """Get current forwarding rules - for debugging/monitoring"""
    return {
        "activeRules": len(forwarding_rules),
        "activeSessions": len(pfcp_sessions),
        "rules": forwarding_rules
    }

@app.post("/upf/simulate-traffic")
async def simulate_traffic(traffic_data: dict):
    """Simulate user plane traffic processing"""
    src_ip = traffic_data.get("src_ip")
    dest_ip = traffic_data.get("dest_ip")
    packet_size = traffic_data.get("packet_size", 1500)
    
    # Check if we have forwarding rules for this traffic
    if src_ip in forwarding_rules:
        rule = forwarding_rules[src_ip]
        logger.info(f"UPF: Processing traffic from {src_ip} -> {dest_ip} via {rule['far']['destinationInterface']}")
        
        # Simulate packet processing
        processed_packet = {
            "original": traffic_data,
            "processed_via": rule['far']['destinationInterface'],
            "tunnel_info": rule['far'].get('outerHeaderCreation'),
            "qos_applied": True
        }
        
        return {"status": "FORWARDED", "packet_info": processed_packet}
    else:
        logger.warning(f"UPF: No forwarding rule found for src_ip {src_ip} - DROPPING")
        return {"status": "DROPPED", "reason": "NO_FORWARDING_RULE"}

@app.get("/upf_service")
def upf_service():
    return {"message": "UPF service response"}

@app.get("/upf/transport-stats")
async def transport_stats():
    """Get real protocol transport statistics (only active in real mode)."""
    result = {"protocol_mode": PROTOCOL_MODE}
    if _gtpu_transport:
        result["gtpu"] = _gtpu_transport.stats
    if _pfcp_transport:
        result["pfcp"] = _pfcp_transport.stats
    if _tun_interface:
        result["tun"] = {"active": _tun_interface.active, "name": _tun_interface.name}
    return result

@app.get("/health")
def health_check():
    """Health check endpoint for UPF - TS 29.244"""
    return {
        "status": "healthy",
        "service": "UPF",
        "compliance": "3GPP TS 29.244",
        "version": "1.0.0",
        "protocol_mode": PROTOCOL_MODE,
        "gtpu_active": _gtpu_transport is not None and _gtpu_transport.transport is not None,
        "pfcp_active": _pfcp_transport is not None and _pfcp_transport.transport is not None,
        "tun_active": _tun_interface is not None and _tun_interface.active
    }

if __name__ == "__main__":
    import argparse
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.ports import get_port

    parser = argparse.ArgumentParser(description="UPF - User Plane Function")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=get_port("upf"), help="Port to bind to")
    parser.add_argument("--protocol-mode", choices=["rest", "real"], default="rest",
                        help="Transport mode: rest (HTTP only) or real (GTP-U/PFCP/TUN)")
    args = parser.parse_args()
    PROTOCOL_MODE = args.protocol_mode
    uvicorn.run(app, host=args.host, port=args.port)