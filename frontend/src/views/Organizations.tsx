/** Организации: двадцать центров в одной таблице, с поиском и сортировкой. */

import { useDeferredValue, useMemo, useState } from 'react'
import { useData } from '../lib/store'
import { Page } from '../ui/Page'
import { Panel, Chip, StatusTag, Segmented, Empty } from '../ui/primitives'
import { Icon } from '../ui/Icon'
import { ShareBar } from '../charts/bars'
import { ClusterMark } from '../charts/kit'
import { channelColor, clusterColor, clusterMark, STATUS_META } from '../lib/palette'
import { compact, dec, num, pct, plural } from '../lib/format'
import { OrgSheet } from './OrgSheet'
import type { Organization } from '../lib/types'

const STATUS_ICON = { good: 'check', warn: 'alert', crit: 'alert', serious: 'alert', none: 'minus' } as const

type SortKey =
  | 'short_name' | 'audience_total' | 'supply_total' | 'audience_per_format'
  | 'products_total' | 'product_rate' | 'resident_rate' | 'revenue_total' | 'completion'

const COLUMNS: Array<{
  key: SortKey
  label: string
  align?: 'right'
  width?: string
  render: (org: Organization) => string
  hint?: string
}> = [
  { key: 'audience_total', label: 'Аудитория', align: 'right', render: (org) => num(org.audience_total), hint: 'человек за отчётный период' },
  { key: 'supply_total', label: 'Меропр.', align: 'right', render: (org) => num(org.supply_total), hint: 'проведено форматов' },
  { key: 'audience_per_format', label: 'Наполн.', align: 'right', render: (org) => dec(org.audience_per_format, 1), hint: 'участников на одно мероприятие' },
  { key: 'products_total', label: 'Работы', align: 'right', render: (org) => num(org.products_total), hint: 'творческих продуктов' },
  { key: 'product_rate', label: 'На участн.', align: 'right', render: (org) => dec(org.product_rate, 2), hint: 'творческих продуктов на одного участника' },
  { key: 'resident_rate', label: 'Резиденты', align: 'right', render: (org) => pct(org.resident_rate), hint: 'доля аудитории, ставшая резидентами' },
  { key: 'revenue_total', label: 'Платные услуги', align: 'right', render: (org) => compact(org.revenue_total), hint: 'рублей за отчётный период' },
]

export function OrganizationsView() {
  const { data, derived } = useData()
  const [query, setQuery] = useState('')
  const deferredQuery = useDeferredValue(query)
  const [cluster, setCluster] = useState<'all' | number>('all')
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean }>({ key: 'audience_total', desc: true })
  const [selected, setSelected] = useState<string | null>(null)

  const rows = useMemo(() => {
    const needle = deferredQuery.trim().toLowerCase()
    const filtered = data.organizations.filter((org) => {
      if (cluster !== 'all' && org.cluster !== cluster) return false
      if (!needle) return true
      return (
        org.short_name.toLowerCase().includes(needle) ||
        org.full_name.toLowerCase().includes(needle) ||
        (org.center ?? '').toLowerCase().includes(needle)
      )
    })
    return filtered.sort((a, b) => {
      const left = a[sort.key]
      const right = b[sort.key]
      if (typeof left === 'string' || typeof right === 'string') {
        return sort.desc
          ? String(right).localeCompare(String(left), 'ru')
          : String(left).localeCompare(String(right), 'ru')
      }
      const leftValue = Number(left ?? -1)
      const rightValue = Number(right ?? -1)
      return sort.desc ? rightValue - leftValue : leftValue - rightValue
    })
  }, [data.organizations, deferredQuery, cluster, sort])

  const toggleSort = (key: SortKey) =>
    setSort((current) => (current.key === key ? { key, desc: !current.desc } : { key, desc: true }))

  return (
    <Page
      eyebrow={`Организации · ${data.organizations.length} центров`}
      title="Центры сети в сравнении"
      lede="Один и тот же набор показателей для всех двадцати центров: масштаб аудитории, наполняемость форматов, выход творческих продуктов и платный контур. Строка раскрывается в полную карточку — с положением центра в распределении сети и адресными мерами."
      actions={
        <label className="relative flex items-center">
          <span className="pointer-events-none absolute left-2.5 text-ink-3"><Icon name="search" size={14} /></span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Поиск по названию или центру"
            aria-label="Поиск организации"
            className="h-8 w-[248px] rounded-sm border border-rule bg-panel pr-2.5 pl-8 text-[12.5px] text-ink transition-colors placeholder:text-ink-3 hover:border-rule-2 focus:border-rule-strong focus:outline-none"
          />
        </label>
      }
    >
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Segmented
          ariaLabel="Фильтр по модели"
          size="sm"
          value={String(cluster)}
          onChange={(value) => setCluster(value === 'all' ? 'all' : Number(value))}
          options={[
            { value: 'all', label: `Все · ${data.organizations.length}` },
            ...data.clusters.profiles.map((profile) => ({
              value: String(profile.cluster_id),
              label: `${profile.name} · ${profile.size}`,
              hint: profile.summary,
            })),
          ]}
        />
        {(query || cluster !== 'all') && (
          <button
            onClick={() => { setQuery(''); setCluster('all') }}
            className="inline-flex items-center gap-1 text-[11.5px] text-ink-3 transition-colors hover:text-ink"
          >
            <Icon name="close" size={11} /> Сбросить
          </button>
        )}
        <span className="ml-auto text-[11.5px] text-ink-3">Показано {rows.length} из {data.organizations.length}</span>
      </div>

      <Panel bodyClassName="px-0 pb-0">
        {rows.length === 0 ? (
          <div className="px-4 pb-4"><Empty text="Ничего не найдено — измените запрос или снимите фильтр по модели" /></div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1100px] border-collapse text-[12.5px]">
              <thead>
                <tr className="border-b border-rule">
                  <th className="eyebrow px-4 pb-2 text-left font-medium">
                    <SortButton active={sort.key === 'short_name'} desc={sort.desc} onClick={() => toggleSort('short_name')}>
                      Центр
                    </SortButton>
                  </th>
                  <th className="eyebrow pb-2 pl-2 text-left font-medium">Состав</th>
                  {COLUMNS.map((column) => (
                    <th key={column.key} className="eyebrow pb-2 pl-3 text-right font-medium" title={column.hint}>
                      <SortButton active={sort.key === column.key} desc={sort.desc} onClick={() => toggleSort(column.key)}>
                        {column.label}
                      </SortButton>
                    </th>
                  ))}
                  <th className="eyebrow pb-2 pl-3 text-right font-medium">
                    <SortButton active={sort.key === 'completion'} desc={sort.desc} onClick={() => toggleSort('completion')}>
                      План
                    </SortButton>
                  </th>
                  <th className="eyebrow px-4 pb-2 text-left font-medium">Статус</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rule">
                {rows.map((org) => {
                  const meta = STATUS_META[org.status]
                  const recs = derived.recsByOrg.get(org.org_id)?.length ?? 0
                  const flagged = (derived.anomaliesByOrg.get(org.org_id)?.length ?? 0) > 0
                  return (
                    <tr
                      key={org.org_id}
                      onClick={() => setSelected(org.org_id)}
                      tabIndex={0}
                      onKeyDown={(event) => { if (event.key === 'Enter') setSelected(org.org_id) }}
                      className="group cursor-pointer transition-colors hover:bg-panel-2"
                    >
                      <td className="px-4 py-2.5">
                        <div className="flex items-center gap-2.5">
                          <svg width={12} height={12} viewBox="-7 -7 14 14" aria-hidden className="shrink-0">
                            <ClusterMark shape={clusterMark(org.cluster)} x={0} y={0} r={5} fill={clusterColor(org.cluster)} strokeWidth={0} />
                          </svg>
                          <div className="min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className="truncate font-medium text-ink">{org.short_name}</span>
                              {flagged && (
                                <span className="text-st-warn" title="В отчёте есть расхождения">
                                  <Icon name="alert" size={11} strokeWidth={2.2} />
                                </span>
                              )}
                            </div>
                            <div className="truncate text-[10.5px] text-ink-3">{org.center}</div>
                          </div>
                        </div>
                      </td>
                      <td className="w-[132px] py-2.5 pl-2">
                        <ShareBar
                          height={9}
                          parts={data.meta.channels.map((channel, index) => ({
                            key: channel.key,
                            label: channel.label,
                            value: Number(org[`audience_${channel.key}`] ?? 0),
                            color: channelColor(index),
                          }))}
                        />
                      </td>
                      {COLUMNS.map((column) => (
                        <td key={column.key} className="tnum py-2.5 pl-3 text-right text-ink-2">
                          {column.render(org)}
                        </td>
                      ))}
                      <td className="tnum py-2.5 pl-3 text-right font-medium text-ink">
                        {org.status === 'без базы' ? '—' : pct(org.completion)}
                      </td>
                      <td className="px-4 py-2.5">
                        <div className="flex items-center justify-between gap-2">
                          <StatusTag
                            label={meta?.label ?? org.status}
                            color={meta?.color ?? 'var(--st-none)'}
                            icon={STATUS_ICON[meta?.tone ?? 'none']}
                          />
                          <span className="flex shrink-0 items-center gap-2">
                            {recs > 0 && <Chip>{recs} {plural(recs, ['мера', 'меры', 'мер'])}</Chip>}
                            <span className="text-ink-3 opacity-0 transition-opacity group-hover:opacity-100">
                              <Icon name="chevron" size={13} />
                            </span>
                          </span>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
        <div className="rule-t flex flex-wrap items-center gap-x-5 gap-y-2 bg-panel-2 px-4 py-2.5 text-[11px] text-ink-3">
          <span>Состав аудитории:</span>
          {data.meta.channels.map((channel, index) => (
            <span key={channel.key} className="flex items-center gap-1.5">
              <span className="size-2.5 rounded-[2px]" style={{ background: channelColor(index) }} />
              {channel.label}
            </span>
          ))}
          <span className="ml-auto">Платные услуги — в рублях за отчётный период</span>
        </div>
      </Panel>

      <p className="mt-4 max-w-[86ch] text-[11.5px] leading-relaxed text-ink-3">
        Значки предупреждения отмечают центры, у которых внутри отчёта есть расхождения — например, число
        резидентов не сходится с суммой обученных по каналам. Такие центры остаются в таблице и получают
        рекомендации, но не входят в подтверждённый резерв сети: полный разбор — в разделе «Качество данных».
      </p>

      <OrgSheet orgId={selected} onClose={() => setSelected(null)} />
    </Page>
  )
}

function SortButton({ active, desc, onClick, children }: {
  active: boolean
  desc: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={(event) => { event.stopPropagation(); onClick() }}
      className={`inline-flex items-center gap-1 transition-colors hover:text-ink ${active ? 'text-ink' : ''}`}
    >
      {children}
      <span className={`transition-opacity ${active ? 'opacity-100' : 'opacity-0'}`}>
        <Icon name={desc ? 'arrow-down' : 'arrow-up'} size={10} strokeWidth={2.4} />
      </span>
    </button>
  )
}
