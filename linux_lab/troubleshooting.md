# Linux lab troubleshooting

Common issues you might hit when running the bench on Fedora + podman, with one-paragraph
fixes. Keep this file open in a second terminal during first-run.

## "permission denied" when podman tries to use subuid / subgid

Symptom: `ERRO[0000] cannot find UID/GID for user ...: lookup error in /etc/subuid: lookup ...`

Fix: Your user lacks a subuid / subgid range. The `setup_fedora.sh` script handles this, but
if you skipped it:

```bash
sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 "$USER"
podman system migrate
```

Then log out and back in so the new namespace ranges take effect.

## "port already in use" with firewalld

Symptom: `Error: rootlessport listen tcp 0.0.0.0:8097: bind: address already in use`

Cause: another process is bound to the port (often dnsmasq, libvirtd, or a previous lab run
that did not exit cleanly).

Fix:

```bash
ss -lntp | grep :8097    # find who has the port
./stop.sh                # cleans up any prior lab containers
```

If a non-lab service holds the port, change the port mapping in `macbook_lab/docker-compose.yml`.

## "no such image" after compose down

Symptom: `Error: macbook_lab-harness-walker:latest: image not known`

Cause: podman compose may not auto-rebuild after `down --rmi all`. The `run.sh` includes
`--build` which forces a rebuild, but if you ran a manual `podman compose up` it might skip.

Fix:

```bash
./stop.sh
./run.sh    # forces --build
```

## Rootless cgroup v2 quirks

Symptom: `Error: OCI runtime error: crun: cannot allocate memory for cgroup ...`

Cause: cgroup v2 delegation is configured per-user. If your distro upgraded from cgroup v1
recently, the user-level cgroup hierarchy may need a one-time re-init.

Fix:

```bash
systemctl --user daemon-reload
loginctl enable-linger "$USER"
```

Log out and back in. The user-level systemd will own cgroups for rootless podman.

## Network mode: pasta vs slirp4netns

Symptom: Containers cannot reach `host.containers.internal` or you see "no route to host"
when one container tries to call another by service name.

Cause: Newer podman versions default to pasta (Fedora 39+); older default to slirp4netns. The
compose network bridge handles container-to-container by service name, but some host-bound
traffic differs.

Fix: this rarely matters for the lab (everything is inside the compose network). If you do
hit it, force slirp4netns:

```bash
export PODMAN_USERNS=keep-id
podman network rm macbook_lab_default 2>/dev/null
./run.sh
```

## SELinux denials in the journal

Symptom: Containers start but health checks fail with permission errors, and
`journalctl -t setroubleshoot` shows AVC denials.

Cause: Unusual for the rootless build-from-Dockerfile path the bench uses. If you customized
the compose to bind-mount a host directory (the upstream compose does not), missing `:Z`
labels cause denials.

Fix:

```bash
# Inspect the denial
sudo ausearch -m AVC -ts recent | head

# If a bind mount is missing :Z, add it to the volume spec
#   - ./my-data:/app/data:Z      # per-container label
#   - ./my-data:/app/data:z      # shared label (multiple containers share access)
```

For the upstream bench (no bind mounts) you should never see SELinux denials.

## "podman compose" command not found

Symptom: `podman: 'compose' is not a podman command`

Cause: Built-in compose was added in podman 4.1+. Older Fedora releases (37 and earlier) ship
older podman.

Fix:

```bash
# Option A: upgrade podman from Fedora's main repo
sudo dnf upgrade podman

# Option B: install standalone podman-compose
pip install --user podman-compose
```

`run.sh` auto-detects which is available and falls back to `podman-compose`.

## Containers run but the dashboard returns 502

Symptom: `curl http://localhost:8097` returns 502 Bad Gateway.

Cause: The dashboard service's vite dev server takes about 5 to 10 seconds to start after the
container reports healthy. The container is up; the application inside is still booting.

Fix: wait. If still 502 after 30 seconds:

```bash
podman logs oran-dashboard | tail -30
```

Most likely cause: npm install failed during build (network blip). `./stop.sh && ./run.sh`
forces a rebuild.

## API key not picked up

Symptom: oh-my-tiny-oran chat returns "[Anthropic API error]" or the harness-chat container
health check fails.

Cause: The `.env` file under `macbook_lab/` was not edited, or the key is wrapped in quotes.

Fix:

```bash
grep ANTHROPIC_API_KEY ../macbook_lab/.env
# Should look like (no quotes, no spaces):
#   ANTHROPIC_API_KEY=sk-ant-...
```

Then `./stop.sh && ./run.sh`. The harness-chat container reads `.env` at startup.

## Rootless podman is slow on first run

Symptom: First `./run.sh` takes 5+ minutes for image builds.

Cause: Rootless podman uses `fuse-overlayfs` instead of kernel overlayfs by default; build
performance differs.

Fix: This is normal on first run. Subsequent runs reuse cached layers and complete in under
30 seconds. If you want native overlay performance, see the
[podman storage docs](https://docs.podman.io/en/latest/markdown/podman.1.html#storage)
for switching the rootless backend (requires `metacopy=on` and may need a custom
`/etc/containers/storage.conf`).

## When in doubt: nuke and reload

```bash
./stop.sh
podman system prune -a    # removes all unused images and layers
./run.sh                  # rebuilds from scratch
```

That clears any state inconsistency between podman, compose, and the image cache. Takes ~5
minutes but always works.
