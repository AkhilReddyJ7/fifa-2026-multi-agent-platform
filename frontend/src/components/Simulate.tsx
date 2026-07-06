import { useState } from 'react'
import { runSimulation } from '../lib/api'
import type { SimulationResult } from '../types'
import { Card, ChartTooltip, ErrorNote, Spinner, StatTile, useTooltip } from './ui'

const RUN_OPTIONS = [500, 1000, 2000, 5000]

/**
 * One measure (championship probability) across teams → single-hue bars
 * (categorical slot 1), value at the tip, hairline baseline. Per-mark hover
 * tooltip adds final/semifinal odds; the table below is the full data twin.
 */
function WinProbChart({ sim }: { sim: SimulationResult }) {
  const { tip, setTip } = useTooltip()
  const rows = Object.entries(sim.win_probabilities)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
  const max = rows.length ? rows[0][1] : 1

  return (
    <div className="relative">
      <div className="space-y-2">
        {rows.map(([code, prob]) => (
          <div
            key={code}
            className="flex items-center gap-3"
            onMouseMove={(e) => {
              const host = e.currentTarget.closest('.relative')!.getBoundingClientRect()
              setTip({
                x: e.clientX - host.left,
                y: e.clientY - host.top,
                title: code,
                rows: [
                  { label: 'Champion', value: `${(prob * 100).toFixed(1)}%` },
                  { label: 'Reaches final', value: `${((sim.final_probabilities[code] ?? 0) * 100).toFixed(1)}%` },
                  { label: 'Reaches semis', value: `${((sim.semifinal_probabilities[code] ?? 0) * 100).toFixed(1)}%` },
                ],
              })
            }}
            onMouseLeave={() => setTip(null)}
          >
            <span className="w-10 shrink-0 text-xs" style={{ color: 'var(--ink-2)' }}>{code}</span>
            <div className="h-5 flex-1" style={{ borderLeft: '1px solid var(--baseline)' }}>
              <div
                className="h-full"
                style={{
                  width: `${(prob / max) * 100}%`,
                  background: 'var(--series-1)',
                  borderRadius: '0 4px 4px 0',
                }}
              />
            </div>
            <span
              className="w-12 shrink-0 text-right text-xs font-semibold"
              style={{ fontVariantNumeric: 'tabular-nums' }}
            >
              {(prob * 100).toFixed(1)}%
            </span>
          </div>
        ))}
      </div>
      <ChartTooltip tip={tip} />
    </div>
  )
}

function ProbTable({ sim }: { sim: SimulationResult }) {
  const rows = Object.entries(sim.win_probabilities).sort((a, b) => b[1] - a[1])
  const pct = (v: number | undefined) => `${((v ?? 0) * 100).toFixed(1)}%`
  return (
    <div className="max-h-80 overflow-auto">
      <table className="w-full text-sm">
        <thead className="sticky top-0" style={{ background: 'var(--surface)' }}>
          <tr className="text-left text-xs" style={{ color: 'var(--ink-muted)' }}>
            <th className="py-2 pr-4 font-medium">Team</th>
            <th className="py-2 pr-4 text-right font-medium">Champion</th>
            <th className="py-2 pr-4 text-right font-medium">Final</th>
            <th className="py-2 text-right font-medium">Semifinal</th>
          </tr>
        </thead>
        <tbody style={{ fontVariantNumeric: 'tabular-nums' }}>
          {rows.map(([code, prob]) => (
            <tr key={code} style={{ borderTop: '1px solid var(--grid)' }}>
              <td className="py-1.5 pr-4">{code}</td>
              <td className="py-1.5 pr-4 text-right">{pct(prob)}</td>
              <td className="py-1.5 pr-4 text-right">{pct(sim.final_probabilities[code])}</td>
              <td className="py-1.5 text-right">{pct(sim.semifinal_probabilities[code])}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function Simulate() {
  const [nSims, setNSims] = useState(1000)
  const [result, setResult] = useState<SimulationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const run = async () => {
    setLoading(true)
    setError(null)
    try {
      setResult(await runSimulation(nSims))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  const favorite = result
    ? Object.entries(result.win_probabilities).sort((a, b) => b[1] - a[1])[0]
    : null

  return (
    <div className="space-y-4">
      <div className="flex items-end gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-xs" style={{ color: 'var(--ink-muted)' }} htmlFor="nsims">Monte Carlo runs</label>
          <select id="nsims" value={nSims} onChange={(e) => setNSims(Number(e.target.value))} className="card px-3 py-1.5 text-sm">
            {RUN_OPTIONS.map((n) => <option key={n} value={n}>{n.toLocaleString()}</option>)}
          </select>
        </div>
        <button
          onClick={run}
          disabled={loading}
          className="rounded-lg px-4 py-1.5 text-sm font-medium text-white disabled:opacity-50"
          style={{ background: 'var(--series-1)' }}
        >
          Simulate tournament
        </button>
      </div>

      {loading && <Spinner label={`Simulating ${nSims.toLocaleString()} tournaments…`} />}
      {error && <ErrorNote message={error} />}

      {result && !loading && (
        <div style={loading ? { opacity: 0.5 } : undefined} className="space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <StatTile
              label="Title favorite"
              value={favorite ? favorite[0] : '—'}
              sub={favorite ? `${(favorite[1] * 100).toFixed(1)}% champion probability` : undefined}
            />
            <StatTile label="Simulations" value={result.n_simulations.toLocaleString()} />
            <StatTile label="Teams with a title path" value={String(Object.keys(result.win_probabilities).length)} />
          </div>

          <Card title="Championship probability — top 10">
            <WinProbChart sim={result} />
          </Card>

          <Card title="All teams — knockout round probabilities">
            <ProbTable sim={result} />
          </Card>

          {result.analyst_summary && (
            <Card title="Analyst summary">
              <p className="whitespace-pre-wrap text-sm leading-relaxed" style={{ color: 'var(--ink-2)' }}>
                {result.analyst_summary}
              </p>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
