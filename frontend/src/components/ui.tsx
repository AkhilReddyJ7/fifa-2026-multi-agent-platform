import { useState, type ReactNode } from 'react'

/** Shared percent formatter: 0.266 → "26.6%" */
export const pct = (v: number | null | undefined, digits = 1) =>
  `${((v ?? 0) * 100).toFixed(digits)}%`

export function Card({ title, children, className = '' }: { title?: string; children: ReactNode; className?: string }) {
  return (
    <section className={`card p-5 ${className}`}>
      {title && <h2 className="text-sm font-medium mb-4" style={{ color: 'var(--ink-2)' }}>{title}</h2>}
      {children}
    </section>
  )
}

export function StatTile({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="card p-4">
      <div className="text-xs" style={{ color: 'var(--ink-muted)' }}>{label}</div>
      <div className="text-2xl font-semibold mt-1">{value}</div>
      {sub && <div className="text-xs mt-1" style={{ color: 'var(--ink-2)' }}>{sub}</div>}
    </div>
  )
}

export interface TooltipState {
  x: number
  y: number
  title: string
  rows: { label: string; value: string }[]
}

/** Chart tooltip — values lead (strong), labels follow (secondary). */
export function ChartTooltip({ tip }: { tip: TooltipState | null }) {
  if (!tip) return null
  return (
    <div
      className="pointer-events-none absolute z-10 card px-3 py-2 text-xs shadow-lg"
      style={{ left: tip.x + 12, top: tip.y + 12 }}
    >
      <div className="font-medium mb-1">{tip.title}</div>
      {tip.rows.map((r) => (
        <div key={r.label} className="flex gap-3 justify-between">
          <span style={{ color: 'var(--ink-2)' }}>{r.label}</span>
          <span className="font-semibold" style={{ fontVariantNumeric: 'tabular-nums' }}>{r.value}</span>
        </div>
      ))}
    </div>
  )
}

export function useTooltip() {
  const [tip, setTip] = useState<TooltipState | null>(null)
  return { tip, setTip }
}

export function Spinner({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 text-sm" style={{ color: 'var(--ink-2)' }}>
      <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
      {label}
    </div>
  )
}

export function ErrorNote({ message }: { message: string }) {
  return (
    <p className="text-sm" style={{ color: 'var(--series-6)' }} role="alert">
      {message}
    </p>
  )
}
