# MacBook lab dashboard

Minimal React + Vite + TypeScript + shadcn-style UI that gives a Mac user a visual view of
the harness platform. Six tabs, each polling its corresponding HTTP wrapper container every
3 seconds. No charts library, no state management library, no auth, no websockets. Just
useState + useEffect + fetch.

## Stack

- Vite + React 18 + TypeScript
- Tailwind CSS (configured for shadcn-style HSL CSS variables)
- @radix-ui/react-tabs and @radix-ui/react-scroll-area (the headless primitives shadcn wraps)
- lucide-react icons (available; the current UI uses none yet)
- class-variance-authority + clsx + tailwind-merge for the `cn()` helper

## Layout

```
dashboard/
├── package.json
├── vite.config.ts            (proxy /api/<service>/* to the right container)
├── tsconfig.json
├── tailwind.config.js
├── postcss.config.js
├── index.html
├── .dockerignore
└── src/
    ├── main.tsx
    ├── App.tsx               (header + Tabs + 6 TabsContent)
    ├── index.css             (Tailwind + shadcn HSL variables)
    ├── lib/utils.ts          (cn() helper)
    ├── api/
    │   ├── client.ts         (fetchJson wrapper)
    │   ├── harness.ts        (/api/harness/*)
    │   ├── ptp.ts            (/api/ptp/*)
    │   ├── metal3.ts         (/api/metal3/*)
    │   ├── redfish.ts        (/api/redfish/*)
    │   └── smo.ts            (/api/smo/*)
    ├── hooks/usePolling.ts   (interval-driven re-fetch with refresh button)
    └── components/
        ├── ui/               (hand-rolled shadcn-style Card, Tabs, Badge, Button, ScrollArea)
        └── tabs/             (6 tab components)
            ├── OverviewTab.tsx        (bench summary + trace file list)
            ├── SmoTab.tsx             (TMF921 companion intents)
            ├── HardwareManagerTab.tsx (Metal3 BMO firmware phases)
            ├── OCloudTab.tsx          (Redfish BMC task lifecycle)
            ├── AlertsTab.tsx          (PTP CloudEvents stream)
            └── PtpLogsTab.tsx         (per-scenario trace JSONL with scenario picker)
```

## How to run

Inside the macbook_lab docker-compose stack:

```bash
cd macbook_lab
./run.sh
# wait for containers to come up
open http://localhost:8097
```

The Dockerfile (`macbook_lab/Dockerfile.dashboard`) installs npm deps at build time and runs
`npm run dev -- --host 0.0.0.0`. Hot reload is enabled for source edits if you bind-mount
the directory (not enabled by default to keep the image self-contained).

## Adding a tab

1. Add an API helper at `src/api/<service>.ts` calling `fetchJson` against `/api/<service>/...`.
   Make sure `vite.config.ts` has a proxy rule for `/api/<service>/`.
2. Add a tab component at `src/components/tabs/<Name>Tab.tsx`. Pattern: one Card with a header,
   a refresh button, the data area. Use `usePolling()` for the auto-refresh.
3. Register the tab in `src/App.tsx`: add to `TAB_IDS`, add a `<TabsTrigger>` and a
   `<TabsContent>`.

## Honest scope

This is a VIEWER, not a console. The dashboard does NOT trigger remediations, configure
agents, modify state, or call action endpoints. Refresh buttons re-fetch; that is the only
interaction. To trigger a fresh PTP alarm, Metal3 apply, etc., use the curl one-liners from
the macbook_lab README.

The visual stays intentionally minimal: cards, badges, tabs, a sparkline-style progress bar
where it helps (O-Cloud task progress). No chart library. No animation library. The teaching
goal is to make the harness pieces visible; anything that does not serve that goal is out of
scope.
