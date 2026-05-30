#!/bin/bash
#
# Start the O-RAN enhancement layer (WG1-WG11) + aggregation gateway.
# Brings up the NRF first (registration target), then every O-RAN service,
# then the front-end gateway on :8088. Use stop_services.sh to tear down.
#
# This is additive to start_3gpp_services.sh; run that for the 5G core if you
# want the full core network alongside the O-RAN layer.

set -u
cd "$(dirname "$0")/5G_Emulator_API" || exit 1

PY="python3"
if [ -d "venv" ]; then
    # shellcheck disable=SC1091
    source venv/bin/activate
    PY="python"
fi

PIDFILE="../.oran_service_pids"
rm -f "$PIDFILE"

start() {
    local name="$1"; local file="$2"; local port="$3"
    echo "Starting ${name} on :${port} ..."
    ${PY} "${file}" --host 0.0.0.0 --port "${port}" >/dev/null 2>&1 &
    echo $! >> "$PIDFILE"
    sleep 1
}

echo "Starting NRF (registration target) ..."
${PY} core_network/nrf.py --host 0.0.0.0 --port 8000 >/dev/null 2>&1 &
echo $! >> "$PIDFILE"
sleep 2

# WG3 Near-RT RIC / WG2 Non-RT RIC (RIC layer)
start "Near-RT RIC"  "ran/ric/near_rt_ric.py" 8095
start "Non-RT RIC"   "ran/ric/non_rt_ric.py"  8096

# SMO framework + R1 (WG1 OAD / WG2 R1)
start "SMO framework" "smo/smo_framework.py" 8122
start "R1"            "smo/r1.py"            8124

# WG3 Y1
start "Y1"           "ran/ric/y1.py"        8123

# WG4 Open Fronthaul O-RU
start "O-RU"         "ran/fronthaul/o_ru.py" 8120

# WG10 O1 / TE&IV
start "O1"           "oam/o1.py"            8125
start "TE&IV"        "oam/teiv.py"          8126

# WG6 O-Cloud Notification
start "O-Cloud Notif" "etsi/o2/o_cloud_notification.py" 8127

# WG11 Security
start "Security"     "security/security_service.py" 8128

# WG1 Slicing + Energy
start "Slicing"      "ran/slicing/oran_slicing.py" 8129
start "Energy (NES)" "ran/energy/nes.py"   8130

# WG9 xHaul transport / sync
start "xHaul"        "transport/xhaul.py"  8131

# Front-end aggregation gateway
start "Gateway"      "api_gateway/oran_gateway.py" 8088

echo ""
echo "O-RAN layer up. Gateway: http://localhost:8088/api/oran/overview"
echo "Spec coverage:           http://localhost:8088/api/oran/spec-coverage"
echo "PIDs recorded in ${PIDFILE}"
