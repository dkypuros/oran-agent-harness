'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Network,
  Radio,
  RefreshCw,
  ShieldCheck,
  Layers,
  Clock,
  CheckCircle2,
  CircleSlash,
  CloudOff,
  Activity,
  Cpu,
  GitBranch,
} from 'lucide-react'
import {
  ORAN_DOMAINS,
  fetchOranDomain,
  fetchOranOverview,
  fetchOranSpecCoverage,
  type OranDomain,
  type OranDomainResponse,
  type OranFunctionStatus,
  type OranOverviewResponse,
  type OranSpecCoverageResponse,
  type OranSpecEntry,
} from '@/lib/api'

// ---------------------------------------------------------------------------
// Working-group identity. O-RAN Alliance organizes work into WG1..WG11; each
// gets a stable accent so the coverage chips and matrix rows are scannable.
// ---------------------------------------------------------------------------
const WG_META: Record<string, { label: string; accent: string }> = {
  WG1: { label: 'Use Cases & Architecture', accent: 'text-sky-400 border-sky-500/40 bg-sky-500/10' },
  WG2: { label: 'Non-RT RIC & A1/R1', accent: 'text-cyan-400 border-cyan-500/40 bg-cyan-500/10' },
  WG3: { label: 'Near-RT RIC & E2', accent: 'text-teal-400 border-teal-500/40 bg-teal-500/10' },
  WG4: { label: 'Open Fronthaul', accent: 'text-emerald-400 border-emerald-500/40 bg-emerald-500/10' },
  WG5: { label: 'Open F1/W1/E1/X2/Xn', accent: 'text-lime-400 border-lime-500/40 bg-lime-500/10' },
  WG6: { label: 'Cloudification & O2', accent: 'text-amber-400 border-amber-500/40 bg-amber-500/10' },
  WG7: { label: 'White-box Hardware', accent: 'text-orange-400 border-orange-500/40 bg-orange-500/10' },
  WG8: { label: 'Stack Reference Design', accent: 'text-rose-400 border-rose-500/40 bg-rose-500/10' },
  WG9: { label: 'Open X-haul Transport', accent: 'text-fuchsia-400 border-fuchsia-500/40 bg-fuchsia-500/10' },
  WG10: { label: 'OAM & O1', accent: 'text-violet-400 border-violet-500/40 bg-violet-500/10' },
  WG11: { label: 'Security', accent: 'text-indigo-400 border-indigo-500/40 bg-indigo-500/10' },
}

const WG_ORDER = ['WG1', 'WG2', 'WG3', 'WG4', 'WG5', 'WG6', 'WG7', 'WG8', 'WG9', 'WG10', 'WG11']

const DOMAIN_META: Record<OranDomain, { label: string; wg: string; icon: typeof Radio }> = {
  fronthaul: { label: 'Open Fronthaul', wg: 'WG4', icon: Radio },
  e2: { label: 'E2 / Near-RT RIC', wg: 'WG3', icon: Cpu },
  security: { label: 'Security Posture', wg: 'WG11', icon: ShieldCheck },
  slicing: { label: 'Network Slicing', wg: 'WG1', icon: Layers },
  energy: { label: 'Energy Saving', wg: 'WG1', icon: Activity },
  transport: { label: 'X-haul Transport', wg: 'WG9', icon: GitBranch },
  a1: { label: 'A1 Policy', wg: 'WG2', icon: Network },
  r1: { label: 'R1 Services', wg: 'WG2', icon: Network },
  o1: { label: 'O1 / OAM', wg: 'WG10', icon: Network },
  o2: { label: 'O2 / O-Cloud', wg: 'WG6', icon: CloudOff },
}

// ---------------------------------------------------------------------------
// Defensive helpers for the variable per-domain payloads.
// ---------------------------------------------------------------------------
function wgChip(wg: string): string {
  return WG_META[wg]?.accent ?? 'text-muted-foreground border-border bg-muted'
}

function isUp(status: string): boolean {
  return status === 'up'
}

/** Count array-valued, non-underscore keys in a domain payload (item counts). */
function arrayCounts(payload: OranDomainResponse): { key: string; count: number }[] {
  const out: { key: string; count: number }[] = []
  for (const [key, value] of Object.entries(payload)) {
    if (key.startsWith('_') || key === 's_plane') continue
    if (Array.isArray(value)) {
      out.push({ key, count: value.length })
    }
  }
  return out
}

function StatusDot({ up }: { up: boolean }) {
  return (
    <span
      className={`inline-block h-2 w-2 shrink-0 rounded-full ${
        up ? 'bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.7)]' : 'bg-rose-500'
      }`}
      aria-hidden
    />
  )
}

interface DomainResult {
  domain: OranDomain
  data: OranDomainResponse | null
  ok: boolean
}

export function OranView() {
  const [overview, setOverview] = useState<OranOverviewResponse | null>(null)
  const [coverage, setCoverage] = useState<OranSpecCoverageResponse | null>(null)
  const [domains, setDomains] = useState<DomainResult[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [errorCount, setErrorCount] = useState(0)

  const load = useCallback(async (isInitial: boolean) => {
    if (isInitial) setLoading(true)
    else setRefreshing(true)

    const settled = await Promise.allSettled([
      fetchOranOverview(),
      fetchOranSpecCoverage(),
      ...ORAN_DOMAINS.map((d) => fetchOranDomain(d)),
    ])

    const [overviewRes, coverageRes, ...domainRes] = settled
    let failures = 0

    if (overviewRes.status === 'fulfilled') setOverview(overviewRes.value)
    else failures += 1

    if (coverageRes.status === 'fulfilled') setCoverage(coverageRes.value)
    else failures += 1

    const domainResults: DomainResult[] = ORAN_DOMAINS.map((domain, i) => {
      const res = domainRes[i]
      if (res && res.status === 'fulfilled') {
        return { domain, data: res.value, ok: true }
      }
      failures += 1
      return { domain, data: null, ok: false }
    })
    setDomains(domainResults)

    setErrorCount(failures)
    setLastUpdated(new Date())
    setLoading(false)
    setRefreshing(false)
  }, [])

  useEffect(() => {
    void load(true)
    const interval = setInterval(() => {
      void load(false)
    }, 5000)
    return () => clearInterval(interval)
  }, [load])

  const allFailed = !loading && !overview && !coverage && domains.every((d) => !d.ok)

  const summary = overview?.spec_coverage ?? coverage?.summary ?? null

  const implementedPct = useMemo(() => {
    if (!summary || !summary.spec_catalog_total) return 0
    return Math.min(100, Math.round((summary.implemented / summary.spec_catalog_total) * 100))
  }, [summary])

  const mappedPct = useMemo(() => {
    if (!summary || !summary.spec_catalog_total) return 0
    return Math.min(100, Math.round((summary.specs_mapped / summary.spec_catalog_total) * 100))
  }, [summary])

  // Group spec entries by working group, ordered WG1..WG11.
  const specsByWg = useMemo(() => {
    const map = new Map<string, OranSpecEntry[]>()
    for (const spec of coverage?.specs ?? []) {
      const list = map.get(spec.wg) ?? []
      list.push(spec)
      map.set(spec.wg, list)
    }
    const ordered: { wg: string; specs: OranSpecEntry[] }[] = []
    for (const wg of WG_ORDER) {
      if (map.has(wg)) {
        ordered.push({ wg, specs: map.get(wg) ?? [] })
        map.delete(wg)
      }
    }
    // Any WG not in the canonical order, appended alphabetically.
    for (const wg of [...map.keys()].sort()) {
      ordered.push({ wg, specs: map.get(wg) ?? [] })
    }
    return ordered
  }, [coverage])

  const fronthaul = domains.find((d) => d.domain === 'fronthaul')?.data ?? null
  const sPlane = fronthaul?.s_plane ?? null
  const teWithinBudget =
    sPlane?.time_error_ns != null && sPlane?.max_te_budget_ns != null
      ? sPlane.time_error_ns <= sPlane.max_te_budget_ns
      : null

  // ----- Empty / loading states ------------------------------------------
  if (allFailed) {
    return (
      <Card className="h-full">
        <CardContent className="flex h-full flex-col items-center justify-center gap-4 text-center">
          <CloudOff className="h-12 w-12 text-muted-foreground" />
          <div className="space-y-1">
            <div className="text-lg font-semibold">O-RAN gateway unavailable</div>
            <p className="max-w-md text-sm text-muted-foreground">
              No response from the O-RAN enhancement gateway. Confirm the dashboard service is
              running, then it will reconnect automatically.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void load(true)}
            className="inline-flex items-center gap-2 rounded-md border bg-background px-3 py-1.5 text-sm font-medium hover:bg-accent"
          >
            <RefreshCw className="h-4 w-4" />
            Retry now
          </button>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="flex h-full flex-col gap-0 overflow-hidden py-0">
      {/* Header strip ----------------------------------------------------- */}
      <CardHeader className="gap-2 border-b py-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Network className="h-5 w-5 text-emerald-400" />
              {overview?.title ?? 'O-RAN Enhancement Layer'}
            </CardTitle>
            <CardDescription>
              WG1-WG11 spec-to-code coverage
              {overview?.source ? ` • ${overview.source}` : ''}
              {errorCount > 0 ? ` • ${errorCount} endpoint(s) degraded` : ''}
            </CardDescription>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            <span>
              {lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString()}` : 'Connecting…'}
            </span>
          </div>
        </div>

        {/* Spec coverage summary band */}
        {summary && (
          <div className="mt-2 grid gap-4 lg:grid-cols-[auto_1fr]">
            <div className="flex items-end gap-6">
              <div>
                <div className="flex items-baseline gap-1">
                  <span className="font-mono text-3xl font-bold tabular-nums text-emerald-400">
                    {summary.implemented}
                  </span>
                  <span className="text-sm text-muted-foreground">implemented</span>
                </div>
                <div className="text-xs text-muted-foreground">
                  {summary.specs_mapped} mapped / {summary.spec_catalog_total} in catalog
                </div>
              </div>
              <div className="hidden sm:block">
                <div className="flex items-baseline gap-1">
                  <span className="font-mono text-2xl font-semibold tabular-nums text-cyan-400">
                    {summary.referenced}
                  </span>
                  <span className="text-sm text-muted-foreground">referenced</span>
                </div>
                <div className="text-xs text-muted-foreground">
                  {summary.working_groups_covered.length} working groups
                </div>
              </div>
            </div>

            <div className="flex flex-col justify-center gap-1.5">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Implemented vs catalog</span>
                <span className="font-mono tabular-nums">{implementedPct}%</span>
              </div>
              <div className="relative">
                <Progress value={mappedPct} className="h-2.5 bg-muted [&>[data-slot=progress-indicator]]:bg-cyan-500/40" />
                <Progress
                  value={implementedPct}
                  className="absolute inset-0 h-2.5 bg-transparent [&>[data-slot=progress-indicator]]:bg-emerald-500"
                />
              </div>
              <div className="flex items-center gap-4 text-[11px] text-muted-foreground">
                <span className="flex items-center gap-1">
                  <span className="inline-block h-2 w-2 rounded-sm bg-emerald-500" /> Implemented
                </span>
                <span className="flex items-center gap-1">
                  <span className="inline-block h-2 w-2 rounded-sm bg-cyan-500/40" /> Mapped
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Per-working-group chips WG1..WG11 */}
        {summary && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {WG_ORDER.map((wg) => {
              const wgData = summary.by_working_group[wg]
              const covered = summary.working_groups_covered.includes(wg)
              if (!wgData && !covered) {
                return (
                  <Badge
                    key={wg}
                    variant="outline"
                    className="gap-1 text-[11px] opacity-40"
                    title={WG_META[wg]?.label}
                  >
                    {wg}
                  </Badge>
                )
              }
              const impl = wgData?.implemented ?? 0
              const total = wgData?.total ?? 0
              return (
                <span
                  key={wg}
                  title={`${wg} ,  ${WG_META[wg]?.label ?? ''}`}
                  className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-medium ${wgChip(
                    wg
                  )}`}
                >
                  {wg}
                  {total > 0 && (
                    <span className="font-mono tabular-nums opacity-80">
                      {impl}/{total}
                    </span>
                  )}
                </span>
              )
            })}
          </div>
        )}
      </CardHeader>

      {/* Body ------------------------------------------------------------- */}
      <CardContent className="min-h-0 flex-1 overflow-hidden p-0">
        <Tabs defaultValue="matrix" className="flex h-full flex-col">
          <TabsList className="mx-4 mt-3 grid w-[min(420px,calc(100%-2rem))] grid-cols-2">
            <TabsTrigger value="matrix">
              <GitBranch className="mr-2 h-4 w-4" />
              Spec-to-Code Matrix
            </TabsTrigger>
            <TabsTrigger value="health">
              <Activity className="mr-2 h-4 w-4" />
              Function & Domain Health
            </TabsTrigger>
          </TabsList>

          {/* Spec-to-Code matrix (the showcase) --------------------------- */}
          <TabsContent value="matrix" className="mt-3 min-h-0 flex-1 overflow-auto px-4 pb-4">
            {specsByWg.length === 0 ? (
              <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                Spec coverage map not yet available.
              </div>
            ) : (
              <div className="overflow-hidden rounded-lg border">
                <Table>
                  <TableHeader className="sticky top-0 z-10 bg-card">
                    <TableRow>
                      <TableHead className="w-20">WG</TableHead>
                      <TableHead className="w-40">Spec</TableHead>
                      <TableHead>Title</TableHead>
                      <TableHead className="w-48">Module</TableHead>
                      <TableHead className="w-32">Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {specsByWg.map(({ wg, specs }) => (
                      <WgGroup key={wg} wg={wg} specs={specs} />
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </TabsContent>

          {/* Health: function grid + fronthaul + domain status ------------ */}
          <TabsContent value="health" className="mt-3 min-h-0 flex-1 space-y-4 overflow-auto px-4 pb-4">
            {/* Open Fronthaul (WG4) S-plane highlight */}
            {sPlane && (
              <Card className="border-emerald-500/30 bg-emerald-500/[0.03] py-4">
                <CardHeader className="py-0">
                  <CardTitle className="flex items-center gap-2 text-sm">
                    <Radio className="h-4 w-4 text-emerald-400" />
                    Open Fronthaul (WG4) ,  S-Plane Synchronization
                    {teWithinBudget != null && (
                      <Badge
                        variant="outline"
                        className={
                          teWithinBudget
                            ? 'border-emerald-500/40 text-emerald-400'
                            : 'border-rose-500/40 text-rose-400'
                        }
                      >
                        {teWithinBudget ? (
                          <CheckCircle2 className="mr-1 h-3 w-3" />
                        ) : (
                          <CircleSlash className="mr-1 h-3 w-3" />
                        )}
                        {teWithinBudget ? 'TE within budget' : 'TE budget exceeded'}
                      </Badge>
                    )}
                  </CardTitle>
                </CardHeader>
                <CardContent className="py-0">
                  <div className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3 lg:grid-cols-6">
                    <SPlaneField label="Sync State" value={sPlane.sync_state} mono />
                    <SPlaneField label="PTP Profile" value={sPlane.ptp_profile} mono />
                    <SPlaneField label="LLS Topology" value={sPlane.lls_topology} mono />
                    <SPlaneField
                      label="Clock Class"
                      value={sPlane.clock_class != null ? String(sPlane.clock_class) : undefined}
                      mono
                    />
                    <SPlaneField
                      label="Time Error"
                      value={sPlane.time_error_ns != null ? `${sPlane.time_error_ns} ns` : undefined}
                      mono
                      tone={teWithinBudget === false ? 'bad' : 'good'}
                    />
                    <SPlaneField
                      label="Max TE Budget"
                      value={
                        sPlane.max_te_budget_ns != null ? `${sPlane.max_te_budget_ns} ns` : undefined
                      }
                      mono
                    />
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Function health grid */}
            {overview && overview.functions.length > 0 && (
              <div>
                <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  <Cpu className="h-3.5 w-3.5" />
                  Function Health
                  <span className="font-mono normal-case tabular-nums text-emerald-400">
                    {overview.functions.filter((f) => isUp(f.status)).length}/
                    {overview.functions.length} up
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
                  {overview.functions.map((fn) => (
                    <FunctionCell key={fn.id} fn={fn} />
                  ))}
                </div>
              </div>
            )}

            {/* Per-domain health grid */}
            <div>
              <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <Layers className="h-3.5 w-3.5" />
                O-RAN Domain Health
              </div>
              <div className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-3">
                {domains.map((d) => (
                  <DomainCell key={d.domain} result={d} />
                ))}
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function WgGroup({ wg, specs }: { wg: string; specs: OranSpecEntry[] }) {
  const implemented = specs.filter((s) => s.status === 'implemented').length
  return (
    <>
      <TableRow className="border-b-0 bg-muted/40 hover:bg-muted/40">
        <TableCell colSpan={5} className="py-1.5">
          <div className="flex items-center gap-2">
            <span
              className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-semibold ${wgChip(
                wg
              )}`}
            >
              {wg}
            </span>
            <span className="text-xs font-medium text-foreground">
              {WG_META[wg]?.label ?? 'Working Group'}
            </span>
            <span className="font-mono text-[11px] tabular-nums text-muted-foreground">
              {implemented}/{specs.length} implemented
            </span>
          </div>
        </TableCell>
      </TableRow>
      {specs.map((spec) => (
        <TableRow key={`${spec.wg}-${spec.spec}-${spec.module}`} className="text-sm">
          <TableCell className="text-muted-foreground">{spec.wg}</TableCell>
          <TableCell className="font-mono text-xs">{spec.spec}</TableCell>
          <TableCell>
            <div className="font-medium">{spec.title}</div>
            {spec.procedures.length > 0 && (
              <div className="mt-0.5 flex flex-wrap gap-1">
                {spec.procedures.slice(0, 4).map((proc) => (
                  <span
                    key={proc}
                    className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
                  >
                    {proc}
                  </span>
                ))}
                {spec.procedures.length > 4 && (
                  <span className="text-[10px] text-muted-foreground">
                    +{spec.procedures.length - 4} more
                  </span>
                )}
              </div>
            )}
          </TableCell>
          <TableCell className="font-mono text-xs text-muted-foreground">{spec.module}</TableCell>
          <TableCell>
            <Badge
              variant={spec.status === 'implemented' ? 'default' : 'secondary'}
              className={
                spec.status === 'implemented'
                  ? 'border-transparent bg-emerald-600 text-white hover:bg-emerald-600'
                  : ''
              }
            >
              {spec.status === 'implemented' ? (
                <CheckCircle2 className="mr-1 h-3 w-3" />
              ) : (
                <GitBranch className="mr-1 h-3 w-3" />
              )}
              {spec.status}
            </Badge>
          </TableCell>
        </TableRow>
      ))}
    </>
  )
}

function FunctionCell({ fn }: { fn: OranFunctionStatus }) {
  const up = isUp(fn.status)
  return (
    <div
      className={`flex items-center justify-between gap-2 rounded-lg border px-3 py-2 ${
        up ? 'bg-card' : 'border-rose-500/30 bg-rose-500/[0.04]'
      }`}
    >
      <div className="min-w-0">
        <div className="flex items-center gap-1.5">
          <StatusDot up={up} />
          <span className="truncate text-sm font-medium" title={fn.label}>
            {fn.label}
          </span>
        </div>
        <div className="mt-0.5 font-mono text-[11px] text-muted-foreground">:{fn.port}</div>
      </div>
      <Badge
        variant="outline"
        className={
          up
            ? 'border-emerald-500/40 text-emerald-400'
            : 'border-rose-500/40 text-rose-400'
        }
      >
        {fn.status}
      </Badge>
    </div>
  )
}

function DomainCell({ result }: { result: DomainResult }) {
  const meta = DOMAIN_META[result.domain]
  const Icon = meta?.icon ?? Network
  const statusMap = result.data?._status ?? {}
  const entries = Object.entries(statusMap)
  const upCount = entries.filter(([, v]) => isUp(v)).length
  const counts = result.data ? arrayCounts(result.data) : []

  return (
    <div
      className={`rounded-lg border px-3 py-2.5 ${
        result.ok ? 'bg-card' : 'border-amber-500/30 bg-amber-500/[0.04]'
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">{meta?.label ?? result.domain}</span>
          <span
            className={`rounded border px-1.5 py-0 text-[10px] font-medium ${wgChip(meta?.wg ?? '')}`}
          >
            {meta?.wg}
          </span>
        </div>
        {result.ok ? (
          entries.length > 0 ? (
            <span className="font-mono text-[11px] tabular-nums text-muted-foreground">
              {upCount}/{entries.length} up
            </span>
          ) : (
            <span className="text-[11px] text-muted-foreground">no probes</span>
          )
        ) : (
          <Badge variant="outline" className="border-amber-500/40 text-amber-400">
            unreachable
          </Badge>
        )}
      </div>

      {/* Status badge grid */}
      {result.ok && entries.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {entries.map(([name, value]) => (
            <span
              key={name}
              className="inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] text-muted-foreground"
              title={`${name}: ${value}`}
            >
              <StatusDot up={isUp(value)} />
              <span className="font-mono">{name}</span>
            </span>
          ))}
        </div>
      )}

      {/* Array item counts (defensive: only when arrays exist) */}
      {counts.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-x-3 gap-y-0.5 text-[11px] text-muted-foreground">
          {counts.map(({ key, count }) => (
            <span key={key} className="font-mono">
              {key}: <span className="tabular-nums text-foreground">{count}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

function SPlaneField({
  label,
  value,
  mono,
  tone,
}: {
  label: string
  value?: string
  mono?: boolean
  tone?: 'good' | 'bad'
}) {
  const toneClass =
    tone === 'bad' ? 'text-rose-400' : tone === 'good' ? 'text-emerald-400' : 'text-foreground'
  return (
    <div className="flex items-center gap-1.5">
      <Clock className="mt-0.5 hidden h-3 w-3 shrink-0 text-muted-foreground sm:block" />
      <div className="min-w-0">
        <div className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</div>
        <div className={`truncate text-sm ${mono ? 'font-mono' : ''} ${toneClass}`}>
          {value ?? ', '}
        </div>
      </div>
    </div>
  )
}
