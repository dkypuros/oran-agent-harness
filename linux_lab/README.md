# Linux lab: Fedora + Podman

Sibling to [`macbook_lab/`](../macbook_lab/README.md). Same containers, same network,
same scenarios. Difference: this runs on Fedora Workstation/Server/CoreOS with `podman` and
`podman-compose` instead of Docker Desktop.

This directory does not duplicate the Dockerfiles or the `docker-compose.yml`. Everything under
`macbook_lab/` is runtime-agnostic and works unchanged with podman. What lives here is a thin
Fedora-flavored wrapper: install scripts, podman compose invocations, and SELinux / rootless
troubleshooting.

## Why podman on Fedora

Three reasons this is the canonical Linux story for the bench:

1. **No Docker Desktop license.** podman is bundled with Fedora and the included `podman-compose`
   is compose-spec compliant. The `docker-compose.yml` under `macbook_lab/` parses identically.
2. **Rootless by default.** Containers run as the invoking user. No daemon, no setuid, no socket
   exposure. Aligns with the bench's read-only, single-user demo posture.
3. **SELinux native.** When the lab moves from a developer machine to a hardened build host or
   into an OpenShift O-Cloud worker (which is RHCOS, the RHEL/Fedora kernel family), the same
   container images, the same compose surface, and the same SELinux boundaries apply.

## Verified runs

This lab has been exercised end-to-end on real Fedora. Capture lives under
`verified_runs/`. Most recent:

  `verified_runs/2026-05-31_fedora42_podman.md`
    Fedora 42 Cloud Edition, podman 5.4.1, podman-compose 1.5.0.
    All lab containers up and healthy; both E scenarios (accepted and SMO-reject paths) walked
    end-to-end producing the expected dual-route output. Reproducible from any Fedora host with
    the two-command quickstart below.

## Prerequisites

Verified on Fedora 42 Cloud Edition. Expected to work on:
- Fedora Workstation 39, 40, 41, 42
- Fedora CoreOS 39 through current
- Fedora Server 40 through current

You need:
- 6 GB free RAM (the lab runs the platform stubs, walker, trace viewer, dashboard, and chat
  client + harness walker do consume real memory at burst)
- ~3 GB free disk for image layers
- An Anthropic API key for the dashboard chat service, or a provider configuration for the
  Router's optional ambiguous-path LLM seam

You do NOT need:
- Docker, Docker Desktop, or any docker-shim
- root access (rootless podman works for the whole stack)
- SELinux to be set to Permissive (the lab works in Enforcing mode)

## Quick start

```bash
cd linux_lab
./setup_fedora.sh    # one-time, installs podman + podman-compose, validates rootless setup
./run.sh             # builds and starts the stack via podman compose
```

`run.sh` cd's into `../macbook_lab/` because the `docker-compose.yml` and the Dockerfiles live
there. Treat `linux_lab/` as the Fedora runtime overlay; treat `macbook_lab/` as the canonical
container definitions.

When the stack is up, open `http://localhost:8097` in your browser. The same services run as
on macbook_lab.

## What gets built

Identical to `macbook_lab`. Refer to [`../macbook_lab/README.md`](../macbook_lab/README.md) for
the full inventory. Briefly:

  ptp-operator-stub        :8091   PTP CloudEvents publisher
  metal3-bmo-stub          :8092   Metal3 BareMetalHost firmware push lifecycle
  redfish-bmc-stub         :8093   DMTF Redfish UpdateService task lifecycle
  tmf921-smo-stub          :8094   TMF921 intent emission
  trace-viewer             :8095   static HTML viewer over shared_trace JSONL
  harness-walker           :8096   the deterministic walker (router + sandbox + guardrail)
  dashboard                :8097   React + Vite UI (profile-gated)
  harness-chat             :8098   oh-my-tiny-oran chat (requires Anthropic API key)

## Stopping

```bash
./stop.sh
```

That removes the running containers but leaves the built images so a re-run is instant. To
remove images too:

```bash
podman compose -f ../macbook_lab/docker-compose.yml --profile dashboard down --rmi all
```

## Switching providers

Same `.env` mechanism as macbook_lab. Edit `../macbook_lab/.env` (created on first run from
`.env.example`):

  LLM_PROVIDER=anthropic       # uses your Anthropic API key
  LLM_PROVIDER=openai          # uses OPENAI_API_KEY
  LLM_PROVIDER=vllm            # uses VLLM_BASE_URL, for example OpenShift AI
  ANTHROPIC_API_KEY=sk-ant-... # needed for dashboard chat and Anthropic live mode
  OPENAI_API_KEY=sk-...        # needed if LLM_PROVIDER=openai
  VLLM_BASE_URL=https://.../v1 # needed if LLM_PROVIDER=vllm
  ORAN_LLM_MODE=live           # set this to actually invoke the LLM on ambiguous-path

Restart with `./run.sh` after changes (it rebuilds and recreates only what changed).

## Differences from macbook_lab

| Item                  | macbook_lab                              | linux_lab                                                       |
|-----------------------|------------------------------------------|-----------------------------------------------------------------|
| Container engine      | Docker Desktop                           | podman (rootless)                                               |
| Compose runner        | `docker compose`                         | `podman compose` (or `podman-compose` fallback)                 |
| Container network     | Docker bridge                            | podman default bridge (CNI / netavark)                          |
| Port forwarding       | Native via Docker Desktop                | slirp4netns (rootless) or netavark (rootful)                    |
| Privilege model       | Daemon as the user's effective uid       | Rootless user namespaces (no daemon, no setuid)                 |
| SELinux               | N/A (macOS)                              | Enforcing by default; volume mounts may need `:Z` (see notes)   |
| Restart on host reboot| Docker Desktop autostart                 | systemd-quadlet generation available (optional, see scripts/)   |

For day-to-day demo usage, none of these differences matter. The README + slash prompts work
identically on both. The differences become relevant only if you want to run the lab as a long-
lived service on a Fedora host.

## SELinux and bind mounts

The bench does NOT use bind mounts in `docker-compose.yml`. Everything is built into the image
at build time via `COPY` in the Dockerfiles. So SELinux contexts are inherited from the image
layers and require no `:Z` or `:z` annotations on volumes.

If you customize the lab to bind-mount your own scenarios or skill bundles, you will need
`:Z` (per-container relabel) on the mount. That is the only SELinux concern.

## Troubleshooting

See [`troubleshooting.md`](./troubleshooting.md) for common Fedora + podman issues:
- "permission denied" on subuid / subgid
- "port already in use" with firewalld
- "no such image" after compose down
- rootless cgroup v2 quirks
- pasta vs slirp4netns network mode selection

## Production-ish posture (optional)

For a Fedora host you want to keep the lab running on (a lab workstation, an internal demo box):

1. Generate quadlet units: `cd ../macbook_lab && podman-compose systemd > /tmp/lab.service`
2. Move the unit files to `~/.config/containers/systemd/`
3. `systemctl --user daemon-reload && systemctl --user enable --now lab.service`
4. The lab starts at boot, restarts on failure, logs via journald

This is out of scope for the nGRG talk but is documented here for the post-talk operator who
wants to keep the bench warm on a real Fedora box.

## File layout

```
linux_lab/
├── README.md             this file
├── run.sh                bring up the stack via podman compose
├── stop.sh               stop the stack
├── setup_fedora.sh       one-time install of podman, podman-compose, rootless validation
├── troubleshooting.md    common Fedora + podman issues
└── scripts/
    ├── bench_run.sh      podman-flavored bench wrapper
    └── tail_traces.sh    follow the shared_trace JSONL files via podman exec
```

## Honest scope

This is a runtime overlay, not a separate lab. It exists so a Fedora user can clone the repo,
run two scripts, and have the same demo running locally. It is not a port: the Dockerfiles
under `macbook_lab/` are the only image definitions, and they were written to be portable from
the start.

If you find a difference between macbook_lab and linux_lab that is not documented in the table
above, file an issue. Either the documentation is incomplete or one of the runtimes is doing
something non-spec.
