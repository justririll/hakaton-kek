/** Оболочка витрины: навигация, загрузка, маршруты. */

import { NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import { useAppState } from './lib/store'
import { Icon } from './ui/Icon'
import type { IconName } from './ui/Icon'
import { useTheme } from './ui/useTheme'
import { num } from './lib/format'
import { Overview } from './views/Overview'
import { Dynamics } from './views/Dynamics'
import { EngagementView } from './views/Engagement'
import { ClustersView } from './views/Clusters'
import { OrganizationsView } from './views/Organizations'
import { RecommendationsView } from './views/Recommendations'
import { QualityView } from './views/Quality'

const SECTIONS: Array<{ to: string; label: string; icon: IconName; hint: string }> = [
  { to: '/', label: 'Обзор', icon: 'overview', hint: 'Состояние сети одним экраном' },
  { to: '/dynamics', label: 'Динамика', icon: 'dynamics', hint: 'База 2025 → факт → прогноз года' },
  { to: '/engagement', label: 'Вовлечённость', icon: 'people', hint: 'Дошёл ли участник до результата' },
  { to: '/clusters', label: 'Кластеры', icon: 'clusters', hint: 'Аудиторные модели центров' },
  { to: '/organizations', label: 'Организации', icon: 'orgs', hint: 'Двадцать центров в сравнении' },
  { to: '/recommendations', label: 'Рекомендации', icon: 'recs', hint: 'Что программировать дальше' },
  { to: '/quality', label: 'Качество данных', icon: 'quality', hint: 'Что в отчётах не сходится' },
]

function Wordmark() {
  return (
    <div className="flex items-center gap-2.5">
      <svg viewBox="0 0 32 32" className="size-8 shrink-0 rounded-[6px]" aria-hidden>
        <rect width="32" height="32" rx="6" fill="var(--ink)" />
        <g fill="none" stroke="var(--panel)" strokeWidth="1.3" strokeLinecap="round">
          <path d="M8 11h16M8 16h10M8 21h13" />
        </g>
        <circle cx="22" cy="16" r="2.4" fill="var(--c-2)" />
        <circle cx="25" cy="21" r="1.8" fill="var(--c-4)" />
      </svg>
      <div className="min-w-0 leading-tight">
        <div className="font-serif text-[15px] font-semibold tracking-[-0.01em] text-ink">ВитДашборд</div>
        <div className="truncate text-[10.5px] text-ink-3">сеть центров прототипирования</div>
      </div>
    </div>
  )
}

function Loading({ progress }: { progress: number }) {
  return (
    <div className="flex min-h-dvh items-center justify-center px-6">
      <div className="w-full max-w-[300px]">
        <Wordmark />
        <div className="mt-6 h-px w-full overflow-hidden bg-rule">
          <div
            className="h-px bg-ink transition-[width] duration-300 ease-out"
            style={{ width: `${Math.max(8, progress * 100)}%` }}
          />
        </div>
        <p className="mt-3 text-[12px] text-ink-3">
          Собираем аналитический слой: признаки, кластеры, проверки устойчивости.
        </p>
      </div>
    </div>
  )
}

function Failure({ error }: { error: string }) {
  return (
    <div className="flex min-h-dvh items-center justify-center px-6">
      <div className="max-w-[420px]">
        <div className="text-st-crit"><Icon name="alert" size={22} /></div>
        <h1 className="mt-3 font-serif text-[22px] font-semibold text-ink">Аналитика недоступна</h1>
        <p className="mt-2 text-[13px] leading-relaxed text-ink-2">
          Витрина не получила данные от сервиса. Проверьте, что бэкенд поднят на порту 8010
          и успел собрать конвейер — на холодном старте это занимает несколько секунд.
        </p>
        <pre className="mt-3 overflow-x-auto rounded-sm border border-rule bg-panel px-3 py-2 font-mono text-[11.5px] text-ink-3">
          {error}
        </pre>
      </div>
    </div>
  )
}

export function App() {
  const state = useAppState()
  const { resolved, toggle } = useTheme()
  const location = useLocation()

  // Каждый раздел открывается сверху: иначе прокрутка «залипает» от предыдущего.
  useEffect(() => { window.scrollTo({ top: 0 }) }, [location.pathname])

  if (state.phase === 'loading') return <Loading progress={state.progress} />
  if (state.phase === 'error') return <Failure error={state.error} />

  const { overview } = state.data

  return (
    <div className="flex min-h-dvh flex-col lg:flex-row">
      {/* ── боковая колонка ───────────────────────────────────────────────── */}
      <aside className="sticky top-0 z-50 shrink-0 border-b border-rule bg-paper/92 backdrop-blur-sm lg:h-dvh lg:w-[230px] lg:border-r lg:border-b-0 lg:backdrop-blur-none">
        <div className="flex h-full flex-col">
          <div className="flex items-center justify-between gap-3 px-4 py-3 lg:px-5 lg:py-5">
            <Wordmark />
            <button
              onClick={toggle}
              title={resolved === 'dark' ? 'Светлая тема' : 'Тёмная тема'}
              aria-label={resolved === 'dark' ? 'Включить светлую тему' : 'Включить тёмную тему'}
              className="flex size-8 shrink-0 items-center justify-center rounded-sm text-ink-3 transition-colors hover:bg-panel-3 hover:text-ink lg:hidden"
            >
              <Icon name={resolved === 'dark' ? 'sun' : 'moon'} size={16} />
            </button>
          </div>

          <nav
            aria-label="Разделы"
            className="flex gap-1 overflow-x-auto px-3 pb-2.5 lg:flex-col lg:overflow-visible lg:px-3 lg:pb-0"
          >
            <div className="eyebrow mb-1.5 hidden px-2 lg:block">Разделы</div>
            {SECTIONS.map((section) => (
              <NavLink
                key={section.to}
                to={section.to}
                end={section.to === '/'}
                title={section.hint}
                className={({ isActive }) =>
                  `group relative flex shrink-0 items-center gap-2.5 rounded-sm px-2.5 py-[7px] text-[13px] font-medium whitespace-nowrap transition-colors duration-150 ${
                    isActive ? 'bg-panel text-ink shadow-card' : 'text-ink-2 hover:bg-panel-2 hover:text-ink'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <span
                      aria-hidden
                      className={`absolute top-1/2 -left-3 hidden h-4 w-[2px] -translate-y-1/2 rounded-full bg-ink transition-opacity lg:block ${
                        isActive ? 'opacity-100' : 'opacity-0'
                      }`}
                    />
                    <span className={isActive ? 'text-ink' : 'text-ink-3 group-hover:text-ink-2'}>
                      <Icon name={section.icon} size={15} />
                    </span>
                    {section.label}
                  </>
                )}
              </NavLink>
            ))}
          </nav>

          <div className="mt-auto hidden px-5 pb-5 lg:block">
            <dl className="space-y-1 border-t border-rule pt-3 text-[11.5px]">
              {[
                ['Организаций', num(overview.organizations)],
                ['Кластеров', num(overview.clusters)],
                ['Рекомендаций', num(overview.recommendations.total)],
              ].map(([label, value]) => (
                <div key={label} className="flex items-baseline justify-between gap-2">
                  <dt className="text-ink-3">{label}</dt>
                  <dd className="tnum font-medium text-ink-2">{value}</dd>
                </div>
              ))}
            </dl>
            <button
              onClick={toggle}
              className="mt-3 flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-[12px] text-ink-3 transition-colors hover:bg-panel-2 hover:text-ink"
            >
              <Icon name={resolved === 'dark' ? 'sun' : 'moon'} size={14} />
              {resolved === 'dark' ? 'Светлая тема' : 'Тёмная тема'}
            </button>
          </div>
        </div>
      </aside>

      {/* ── содержимое ────────────────────────────────────────────────────── */}
      <main className="min-w-0 flex-1">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/dynamics" element={<Dynamics />} />
          <Route path="/engagement" element={<EngagementView />} />
          <Route path="/clusters" element={<ClustersView />} />
          <Route path="/organizations" element={<OrganizationsView />} />
          <Route path="/recommendations" element={<RecommendationsView />} />
          <Route path="/quality" element={<QualityView />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}
