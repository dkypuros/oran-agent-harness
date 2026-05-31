#!/usr/bin/env bash
# One-time Fedora setup for the linux_lab. Installs podman + podman-compose,
# validates rootless configuration, and prints next steps. Idempotent: safe to
# re-run.

set -euo pipefail

if [ "$(id -u)" -eq 0 ]; then
  echo "Do not run setup_fedora.sh as root. Rootless podman is the intended posture."
  exit 1
fi

if ! grep -q "Fedora" /etc/os-release 2>/dev/null; then
  echo "Warning: /etc/os-release does not report Fedora. The setup may still work on RHEL"
  echo "or CentOS Stream, but is untested. Continuing in 3 seconds; ctrl-c to abort."
  sleep 3
fi

echo "==> Installing podman, podman-compose, jq, and dependencies"
sudo dnf install -y podman podman-compose jq

echo ""
echo "==> podman version"
podman version | head -5

echo ""
echo "==> Checking rootless prerequisites"

# subuid / subgid entries
USER_NAME="${USER:-$(id -un)}"
if ! grep -q "^${USER_NAME}:" /etc/subuid 2>/dev/null; then
  echo "  /etc/subuid has no entry for ${USER_NAME}; adding"
  sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 "${USER_NAME}"
else
  echo "  /etc/subuid entry for ${USER_NAME}: OK"
fi

# user namespaces sysctl (default on Fedora 34+; check anyway)
NS_MAX=$(sysctl -n user.max_user_namespaces 2>/dev/null || echo 0)
if [ "${NS_MAX}" -lt 10000 ]; then
  echo "  user.max_user_namespaces is ${NS_MAX}; raising to 28633"
  echo "user.max_user_namespaces=28633" | sudo tee /etc/sysctl.d/userns.conf > /dev/null
  sudo sysctl -p /etc/sysctl.d/userns.conf
else
  echo "  user.max_user_namespaces: ${NS_MAX} (OK)"
fi

# Migrate rootless storage if subuid/subgid were just configured
if [ -d "$HOME/.local/share/containers" ]; then
  echo "  Running podman system migrate (safe if no containers exist)"
  podman system migrate || true
fi

echo ""
echo "==> Validating compose"
if podman compose version > /dev/null 2>&1; then
  echo "  podman compose (built-in): $(podman compose version | head -1)"
elif command -v podman-compose > /dev/null; then
  echo "  podman-compose: $(podman-compose --version)"
else
  echo "  ERROR: no compose runner found. Manual recovery: pip install --user podman-compose"
  exit 1
fi

echo ""
echo "==> Test rootless container"
podman run --rm docker.io/library/hello-world > /dev/null && echo "  rootless containers: OK"

echo ""
echo "==> Setup complete. Next step:"
echo "  ./run.sh"
echo ""
echo "If anything failed, see linux_lab/troubleshooting.md."
