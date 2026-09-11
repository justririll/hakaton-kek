/** Рекомендации: очередь мер по программированию с доказательной базой. */

import { useDeferredValue, useMemo, useState } from 'react'
import { useData } from '../lib/store'
import { Page, Band } from '../ui/Page'
import { Panel, Segmented, Empty, InfoDot } from '../ui/primitives'
import { Icon } from '../ui/Icon'
import { RankedBars } from '../charts/bars'
import { REC_META, clusterColor } from '../lib/palette'
import { compact, dec, money, num, pct, plural } from '../lib/format'
import { RecCard } from './RecCard'
import { OrgSheet } from './OrgSheet'
import type { RecType } from '../lib/types'

const IMPACT_LABEL: Record<string, string> = {
  participants: 'Участники',
  products: 'Творческие продукты',
  revenue: 'Платные услуги',
  publications: 'Публикации',
  formats: 'Мероприятия',
}

export function RecommendationsView() {
  const { data, derived } = useData()
  const { recommendations, overview, clusters } = data
  const [type, setType] = useState<RecType | 'all'>('all')
  const [scope, setScope] = useState<'all' | 'verified'>('all')
  const [query, setQuery] = useState('')
  const deferredQuery = useDeferredValue(query)
  const [selected, setSelected] = useState<string | null>(null)

  const filtered = useMemo(() => {
    const needle = deferredQuery.trim().toLowerCase()
    return recommendations
      .filter((rec) => (type === 'all' ? true : rec.rec_type === type))
      .filter((rec) => (scope === 'verified' ? !rec.data_flag : true))
      .filter((rec) =>
        needle
          ? rec.org_name.toLowerCase().includes(needle) ||
            rec.title.toLowerCase().includes(needle) ||
            rec.action.toLowerCase().includes(needle)
          : true,
      )
      .sort((a, b) => b.priority - a.priority)
  }, [recommendations, type, scope, deferredQuery])

  /* Сколько мер приходится на каждый центр — где сосредоточен резерв сети. */
  const byOrg = useMemo(() => {
    const counts = new Map<string, number>()
    for (const rec of filtered) counts.set(rec.org_id, (counts.get(rec.org_id) ?? 0) + 1)
    return [...counts.entries()]
      .sort((a, b) => b[1] - a[1])
      .map(([orgId, count]) => ({
        id: orgId,
        label: derived.nameOf(orgId),
        value: count,
        color: clusterColor(derived.byId.get(orgId)?.cluster ?? 0),
      }))
  }, [filtered, derived])

  const impact = scope === 'verified' ? overview.recommendations.impact_verified : overview.recommendations.impact

  return (
    <Page
      eyebrow={`Рекомендации · ${recommendations.length} мер`}
      title="Что программировать дальше"
      lede={
        <>
          Каждая мера выведена из разрыва между центром и медианой сопоставимых центров — сначала
          внутри своей аудиторной модели, а если группа мала, то по всей сети. Рядом с мерой стоят
          её доказательства: собственное значение, квартили группы, лучший результат и оценка эффекта.
          Приоритет учитывает и надёжность исходных данных.
        </>
      }
      actions={
        <label className="relative flex items-center">
          <span className="pointer-events-none absolute left-2.5 text-ink-3"><Icon name="search" size={14} /></span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Поиск по центру или мере"
            aria-label="Поиск рекомендации"
            className="h-8 w-[248px] rounded-sm border border-rule bg-panel pr-2.5 pl-8 text-[12.5px] text-ink transition-colors placeholder:text-ink-3 hover:border-rule-2 focus:border-rule-strong focus:outline-none"
          />
        </label>
      }
    >
      {/* ── совокупный эффект ────────────────────────────────────────────── */}
      <div className="panel rise grid grid-cols-2 divide-x divide-y divide-rule overflow-hidden shadow-card md:grid-cols-3 xl:grid-cols-5 xl:divide-y-0">
        {Object.entries(IMPACT_LABEL).map(([key, label]) => {
          const entry = impact[key]
          return (
            <div key={key} className="px-4 py-3.5">
              <div className="flex items-start gap-1.5">
                <span className="text-[11.5px] leading-snug text-ink-2">{label}</span>
                {key === 'revenue' && (
                  <InfoDot text="Оценка сверху: резерв считается как разрыв с медианой сопоставимых центров при неизменном числе мероприятий." />
                )}
              </div>
              <div className="figure mt-1.5 text-[24px] leading-none text-ink">
                {entry ? `+${entry.unit === '₽' ? money(entry.total) : compact(entry.total)}` : '—'}
              </div>
              <div className="mt-1.5 text-[11px] text-ink-3">
                {entry ? `${entry.count} ${plural(entry.count, ['центр', 'центра', 'центров'])} · ${entry.unit}` : 'мер нет'}
              </div>
            </div>
          )
        })}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Segmented
          ariaLabel="Круг мер"
          size="sm"
          value={scope}
          onChange={setScope}
          options={[
            { value: 'all', label: `Все меры · ${recommendations.length}` },
            { value: 'verified', label: `Только с надёжными данными · ${recommendations.filter((rec) => !rec.data_flag).length}` },
          ]}
        />
        <span className="text-[11.5px] text-ink-3">
          {scope === 'verified'
            ? `Скрыто ${overview.recommendations.flagged} ${plural(overview.recommendations.flagged, ['мера', 'меры', 'мер'])} по ${overview.recommendations.flagged_orgs.length} ${plural(overview.recommendations.flagged_orgs.length, ['центру', 'центрам', 'центрам'])} с расхождениями в отчётности`
            : 'Меры по центрам с расхождениями помечены отдельно'}
        </span>
      </div>

      {/* ── фильтр по типам ──────────────────────────────────────────────── */}
      <div className="mt-4 flex flex-wrap gap-1.5">
        <TypeChip active={type === 'all'} onClick={() => setType('all')} count={recommendations.length}>
          Все типы
        </TypeChip>
        {Object.entries(overview.recommendations.by_type)
          .sort((a, b) => b[1] - a[1])
          .map(([key, count]) => (
            <TypeChip
              key={key}
              active={type === key}
              onClick={() => setType(type === key ? 'all' : (key as RecType))}
              count={count}
              hint={REC_META[key]?.label}
            >
              {REC_META[key]?.short ?? key}
            </TypeChip>
          ))}
      </div>

      <div className="mt-5 grid items-start gap-4 xl:grid-cols-[minmax(0,1.55fr)_minmax(0,1fr)]">
        {/* очередь */}
        <div>
          <div className="mb-2.5 flex items-baseline justify-between gap-3">
            <h2 className="font-serif text-[17px] font-semibold text-ink">
              {type === 'all' ? 'Очередь мер' : REC_META[type]?.label ?? 'Очередь мер'}
            </h2>
            <span className="text-[11.5px] text-ink-3">
              {filtered.length} {plural(filtered.length, ['мера', 'меры', 'мер'])} · средний приоритет{' '}
              {filtered.length ? dec(filtered.reduce((sum, rec) => sum + rec.priority, 0) / filtered.length, 0) : '—'}
            </span>
          </div>
          {filtered.length === 0 ? (
            <Empty text="По этим условиям мер нет — снимите фильтр или измените запрос" />
          ) : (
            <ul className="stagger space-y-2.5">
              {filtered.map((rec, index) => (
                <li key={`${rec.org_id}-${rec.rec_type}-${rec.channel}-${index}`}>
                  <RecCard rec={rec} onOrgClick={setSelected} />
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* правая колонка */}
        <div className="flex flex-col gap-4 xl:sticky xl:top-4">
          <Panel
            eyebrow="Где сосредоточен резерв"
            title="Число мер по центрам"
            subtitle="Много мер — не приговор: чаще это центр, который отчитался подробно и потому сравним"
          >
            {byOrg.length === 0 ? (
              <Empty text="Нет данных для текущего фильтра" />
            ) : (
              <RankedBars
                items={byOrg}
                format={(value) => num(value)}
                labelWidth={156}
                valueWidth={26}
                onSelect={setSelected}
              />
            )}
          </Panel>

          <Panel
            eyebrow="Устойчивость"
            title="Меры проверены пересборкой"
            subtitle={`${data.validation.recommendations.runs} прогонов на возмущённых данных`}
            footnote="Неустойчивая мера остаётся в списке, но с низкой уверенностью — решение по ней требует ручной проверки."
          >
            <div className="space-y-3">
              {[
                ['Доля устойчивых мер', data.validation.recommendations.stable_share],
                ['Средняя выживаемость', data.validation.recommendations.mean_survival],
              ].map(([label, value]) => (
                <div key={label as string}>
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="text-[12.5px] text-ink-2">{label}</span>
                    <span className="tnum text-[15px] font-semibold text-ink">{pct(value as number, 1)}</span>
                  </div>
                  <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-panel-3">
                    <div className="bar-grow h-full rounded-full bg-st-good" style={{ width: `${(value as number) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
            {data.validation.recommendations.unstable.length > 0 && (
              <div className="mt-3.5 border-t border-rule pt-3">
                <div className="eyebrow mb-1.5">Требуют проверки</div>
                <ul className="space-y-1.5">
                  {data.validation.recommendations.unstable.map((item, index) => (
                    <li key={index} className="flex items-baseline justify-between gap-3 text-[11.5px]">
                      <span className="truncate text-ink-2">
                        {derived.nameOf(item.org_id)} · {REC_META[item.rec_type]?.short ?? item.rec_type}
                      </span>
                      <span className="tnum shrink-0 text-ink-3">{pct(item.rate)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Panel>

          <Panel eyebrow="Как это считается" title="Логика вывода мер">
            <ol className="space-y-2.5">
              {[
                'Центр сравнивается с медианой своей аудиторной модели; если в модели меньше пяти центров — со всей сетью.',
                'Разрыв переводится в натуральную величину: участники, работы, рубли, публикации.',
                'Приоритет учитывает размер разрыва, долю затронутой аудитории и надёжность исходных данных.',
                'Мера пересобирается на возмущённых данных — так проверяется, что она не артефакт одной выборки.',
              ].map((step, index) => (
                <li key={index} className="flex gap-2.5">
                  <span className="eyebrow mt-[3px] w-3.5 shrink-0 tabular-nums">{index + 1}</span>
                  <span className="text-[12px] leading-snug text-ink-2">{step}</span>
                </li>
              ))}
            </ol>
          </Panel>
        </div>
      </div>

      <Band title="Типы мер и их вклад" note="Сводка по всем рекомендациям сети">
        <div className="stagger grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {Object.entries(overview.recommendations.by_type)
            .sort((a, b) => b[1] - a[1])
            .map(([key, count]) => {
              const sample = recommendations.filter((rec) => rec.rec_type === key)
              const meanPriority = sample.reduce((sum, rec) => sum + rec.priority, 0) / (sample.length || 1)
              return (
                <button
                  key={key}
                  onClick={() => setType(type === key ? 'all' : (key as RecType))}
                  className={`panel flex flex-col gap-2 p-4 text-left shadow-card transition-[border-color,transform] duration-150 hover:-translate-y-0.5 hover:border-rule-strong ${
                    type === key ? 'border-rule-strong' : ''
                  }`}
                >
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-[13px] font-medium text-ink">{REC_META[key]?.short ?? key}</span>
                    <span className="tnum text-[11px] text-ink-3">{count} {plural(count, ['мера', 'меры', 'мер'])}</span>
                  </div>
                  <p className="text-[11.5px] leading-snug text-ink-3">{REC_META[key]?.label ?? key}</p>
                  <div className="mt-auto flex items-baseline gap-2 border-t border-rule pt-2">
                    <span className="tnum text-[16px] font-semibold text-ink">{dec(meanPriority, 0)}</span>
                    <span className="text-[10.5px] text-ink-3">средний приоритет</span>
                  </div>
                </button>
              )
            })}
        </div>
      </Band>

      <p className="mt-6 max-w-[86ch] text-[11.5px] leading-relaxed text-ink-3">
        Кластеров в сети {clusters.k}, и для трёх из них группа слишком мала, чтобы служить эталоном, —
        там сравнение автоматически расширяется до всей сети. Круг сравнения указан в доказательствах каждой меры.
      </p>

      <OrgSheet orgId={selected} onClose={() => setSelected(null)} />
    </Page>
  )
}

function TypeChip({ active, onClick, count, hint, children }: {
  active: boolean
  onClick: () => void
  count: number
  hint?: string
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      title={hint}
      className={`inline-flex items-center gap-1.5 rounded-sm border px-2.5 py-[5px] text-[12px] font-medium transition-colors duration-150 ${
        active
          ? 'border-ink bg-ink text-ink-inv'
          : 'border-rule-2 text-ink-2 hover:border-rule-strong hover:text-ink'
      }`}
    >
      {children}
      <span className={`tnum text-[10.5px] ${active ? 'opacity-70' : 'text-ink-3'}`}>{count}</span>
    </button>
  )
}
