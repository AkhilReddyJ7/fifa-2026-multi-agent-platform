import { useState } from 'react'
import Chat from './components/Chat'
import Dashboard from './components/Dashboard'
import Predict from './components/Predict'
import Simulate from './components/Simulate'

const TABS = [
  { id: 'dashboard', label: 'Dashboard', view: <Dashboard /> },
  { id: 'predict', label: 'Predict', view: <Predict /> },
  { id: 'simulate', label: 'Simulate', view: <Simulate /> },
  { id: 'chat', label: 'Analyst Chat', view: <Chat /> },
] as const

type TabId = (typeof TABS)[number]['id']

export default function App() {
  const [tab, setTab] = useState<TabId>('dashboard')

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <header className="mb-6">
        <h1 className="text-xl font-semibold">FIFA 2026 Intelligence</h1>
        <p className="text-sm" style={{ color: 'var(--ink-2)' }}>
          Multi-agent match predictions, tournament simulation, and analyst chat
        </p>
      </header>

      <nav className="mb-6 flex gap-1 border-b" style={{ borderColor: 'var(--grid)' }}>
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className="px-4 py-2 text-sm font-medium"
            style={
              tab === t.id
                ? { color: 'var(--series-1)', borderBottom: '2px solid var(--series-1)', marginBottom: -1 }
                : { color: 'var(--ink-2)' }
            }
          >
            {t.label}
          </button>
        ))}
      </nav>

      {/* keep views mounted so results survive tab switches */}
      {TABS.map((t) => (
        <div key={t.id} hidden={tab !== t.id}>
          {t.view}
        </div>
      ))}
    </div>
  )
}
