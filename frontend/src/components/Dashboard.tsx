import { useEffect, useMemo, useState } from 'react'
import { listTeams } from '../lib/api'
import type { Team } from '../types'
import { Card, ErrorNote, Spinner, StatTile } from './ui'

const CONFEDERATIONS = ['ALL', 'UEFA', 'CONMEBOL', 'CONCACAF', 'CAF', 'AFC', 'OFC'] as const

export default function Dashboard() {
  const [teams, setTeams] = useState<Team[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [conf, setConf] = useState<string>('ALL')

  useEffect(() => {
    listTeams().then((r) => setTeams(r.items)).catch((e) => setError(String(e)))
  }, [])

  const filtered = useMemo(() => {
    if (!teams) return []
    const rows = conf === 'ALL' ? teams : teams.filter((t) => t.confederation === conf)
    return [...rows].sort((a, b) => b.elo_rating - a.elo_rating)
  }, [teams, conf])

  if (error) return <ErrorNote message={error} />
  if (!teams) return <Spinner label="Loading teams…" />

  const top = filtered[0]
  const avgElo = filtered.length
    ? Math.round(filtered.reduce((s, t) => s + t.elo_rating, 0) / filtered.length)
    : 0

  return (
    <div className="space-y-4">
      {/* Filter row scopes everything below it */}
      <div className="flex items-center gap-2">
        <label className="text-sm" style={{ color: 'var(--ink-2)' }} htmlFor="conf">Confederation</label>
        <select
          id="conf"
          value={conf}
          onChange={(e) => setConf(e.target.value)}
          className="card px-3 py-1.5 text-sm"
        >
          {CONFEDERATIONS.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <StatTile label="Qualified teams" value={String(filtered.length)} />
        <StatTile label="Highest ELO" value={top ? top.name : '—'} sub={top ? `${Math.round(top.elo_rating)} rating` : undefined} />
        <StatTile label="Average ELO" value={String(avgElo)} />
      </div>

      <Card title="Teams by ELO rating">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs" style={{ color: 'var(--ink-muted)' }}>
                <th className="py-2 pr-4 font-medium">#</th>
                <th className="py-2 pr-4 font-medium">Team</th>
                <th className="py-2 pr-4 font-medium">Code</th>
                <th className="py-2 pr-4 font-medium">Confederation</th>
                <th className="py-2 text-right font-medium">ELO</th>
              </tr>
            </thead>
            <tbody style={{ fontVariantNumeric: 'tabular-nums' }}>
              {filtered.map((t, i) => (
                <tr key={t.fifa_code} style={{ borderTop: '1px solid var(--grid)' }}>
                  <td className="py-1.5 pr-4" style={{ color: 'var(--ink-muted)' }}>{i + 1}</td>
                  <td className="py-1.5 pr-4">{t.name}</td>
                  <td className="py-1.5 pr-4" style={{ color: 'var(--ink-2)' }}>{t.fifa_code}</td>
                  <td className="py-1.5 pr-4" style={{ color: 'var(--ink-2)' }}>{t.confederation}</td>
                  <td className="py-1.5 text-right">{Math.round(t.elo_rating)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
