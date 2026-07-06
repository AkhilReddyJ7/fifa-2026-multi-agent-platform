import { useEffect, useState } from 'react'
import { listTeams, predictMatch } from '../lib/api'
import type { Prediction, Team } from '../types'
import { Card, ErrorNote, Spinner, StatTile } from './ui'

const STAGES = ['group', 'r16', 'qf', 'sf', 'final'] as const

/**
 * Home / draw / away is a part-to-whole with polarity, so the stacked bar
 * uses the diverging pair (blue ↔ red) with the neutral gray midpoint for
 * the draw. Segments are separated by 2px surface gaps; a legend always
 * carries identity, and in-segment labels render only when they fit.
 */
function OutcomeBar({ p }: { p: Prediction }) {
  const segments = [
    { label: `${p.home_code} win`, value: p.home_win_prob, color: 'var(--series-1)', ink: '#ffffff' },
    { label: 'Draw', value: p.draw_prob, color: 'var(--neutral-mid)', ink: 'var(--ink)' },
    { label: `${p.away_code} win`, value: p.away_win_prob, color: 'var(--series-6)', ink: '#ffffff' },
  ]
  return (
    <div>
      <div className="flex h-6 w-full overflow-hidden rounded" style={{ gap: 2, background: 'var(--surface)' }}>
        {segments.map((s) => (
          <div
            key={s.label}
            className="flex items-center justify-center rounded-[4px] text-xs font-medium"
            style={{ width: `${s.value * 100}%`, background: s.color, color: s.ink }}
            title={`${s.label}: ${(s.value * 100).toFixed(1)}%`}
          >
            {s.value >= 0.14 ? `${(s.value * 100).toFixed(0)}%` : ''}
          </div>
        ))}
      </div>
      <div className="mt-3 flex flex-wrap gap-4 text-xs" style={{ color: 'var(--ink-2)' }}>
        {segments.map((s) => (
          <span key={s.label} className="flex items-center gap-1.5">
            <span className="inline-block h-3 w-3 rounded-[3px]" style={{ background: s.color }} />
            {s.label}
            <span className="font-semibold" style={{ color: 'var(--ink)', fontVariantNumeric: 'tabular-nums' }}>
              {(s.value * 100).toFixed(1)}%
            </span>
          </span>
        ))}
      </div>
    </div>
  )
}

export default function Predict() {
  const [teams, setTeams] = useState<Team[]>([])
  const [home, setHome] = useState('BRA')
  const [away, setAway] = useState('ARG')
  const [stage, setStage] = useState<string>('group')
  const [result, setResult] = useState<Prediction | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listTeams().then((r) => setTeams(r.items.sort((a, b) => a.name.localeCompare(b.name)))).catch(() => {})
  }, [])

  const run = async () => {
    setLoading(true)
    setError(null)
    try {
      setResult(await predictMatch(home, away, stage))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  const teamSelect = (value: string, onChange: (v: string) => void, id: string) => (
    <select id={id} value={value} onChange={(e) => onChange(e.target.value)} className="card px-3 py-1.5 text-sm">
      {teams.map((t) => <option key={t.fifa_code} value={t.fifa_code}>{t.name} ({t.fifa_code})</option>)}
    </select>
  )

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-xs" style={{ color: 'var(--ink-muted)' }} htmlFor="home">Home</label>
          {teamSelect(home, setHome, 'home')}
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs" style={{ color: 'var(--ink-muted)' }} htmlFor="away">Away</label>
          {teamSelect(away, setAway, 'away')}
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs" style={{ color: 'var(--ink-muted)' }} htmlFor="stage">Stage</label>
          <select id="stage" value={stage} onChange={(e) => setStage(e.target.value)} className="card px-3 py-1.5 text-sm">
            {STAGES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <button
          onClick={run}
          disabled={loading || home === away}
          className="rounded-lg px-4 py-1.5 text-sm font-medium text-white disabled:opacity-50"
          style={{ background: 'var(--series-1)' }}
        >
          Predict
        </button>
      </div>

      {home === away && <p className="text-xs" style={{ color: 'var(--ink-muted)' }}>Pick two different teams.</p>}
      {loading && <Spinner label="Running prediction agents…" />}
      {error && <ErrorNote message={error} />}

      {result && !loading && (
        <>
          <Card title={`${result.home_team} vs ${result.away_team} — outcome probabilities`}>
            <OutcomeBar p={result} />
          </Card>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <StatTile
              label="Expected goals"
              value={`${result.expected_home_goals.toFixed(1)} – ${result.expected_away_goals.toFixed(1)}`}
              sub={`${result.home_code} vs ${result.away_code}`}
            />
            <StatTile label="Model confidence" value={`${(result.confidence * 100).toFixed(0)}%`} />
            <StatTile label="Model" value={result.model_version} />
          </div>

          {result.analyst_summary && (
            <Card title="Analyst summary">
              <p className="whitespace-pre-wrap text-sm leading-relaxed" style={{ color: 'var(--ink-2)' }}>
                {result.analyst_summary}
              </p>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
