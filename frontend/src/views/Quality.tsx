/** Качество данных: что конвейер поправил при разборе и что не сходится в отчётах. */

import { useMemo, useState } from 'react'
import { useData } from '../lib/store'
import { Page, Band } from '../ui/Page'
import { Panel, Segmented, Empty, Chip } from '../ui/primitives'
import { Icon } from '../ui/Icon'
import { RankedBars } from '../charts/bars'
import { SEVERITY_META, clusterColor } from '../lib/palette'
import { dec, num, pct, plural } from '../lib/format'
import { OrgSheet } from './OrgSheet'
import type { Severity } from '../lib/types'

const KIND_LABEL: Record<string, string> = {
  unit_normalized: 'Приведение единиц',
  unit_label_mismatch: 'Подпись единицы не сходится со значением',
  aggregate_mismatch: 'Итог не сходится с подпунктами',
  imputed_zero: 'Пустая строка прочитана как ноль',
  inconsistency: 'Внутреннее противоречие показателей',
  outlier: 'Выброс относительно сети',
  multivariate: 'Нетипичное сочетание показателей',
  duplicate: 'Повтор значения',
  missing: 'Показатель не заполнен',
}

export function QualityView() {
  const { data, derived } = useData()
  const { quality, anomalies, overview } = data
  const [tab, setTab] = useState<'anomalies' | 'parsing'>('anomalies')
  const [severity, setSeverity] = useState<Severity | 'all'>('all')
  const [selected, setSelected] = useState<string | null>(null)

  const anomalyRows = useMemo(
    () => anomalies.filter((row) => (severity === 'all' ? true : row.severity === severity))
      .sort((a, b) => b.score - a.score),
    [anomalies, severity],
  )

  const parsingRows = useMemo(
    () => quality.issues.filter((row) => (severity === 'all' ? true : row.severity === severity)),
    [quality.issues, severity],
  )

  const byOrg = useMemo(() => {
    const counts = new Map<string, number>()
    for (const row of anomalies) counts.set(row.org_id, (counts.get(row.org_id) ?? 0) + 1)
    for (const row of quality.issues) counts.set(row.org_id, (counts.get(row.org_id) ?? 0) + 1)
    return [...counts.entries()]
      .sort((a, b) => b[1] - a[1])
      .map(([orgId, count]) => ({
        id: orgId,
        label: derived.nameOf(orgId),
        value: count,
        color: clusterColor(derived.byId.get(orgId)?.cluster ?? 0),
      }))
  }, [anomalies, quality.issues, derived])

  const kinds = useMemo(() => {
    const counts = new Map<string, number>()
    for (const row of [...anomalies, ...quality.issues]) counts.set(row.kind, (counts.get(row.kind) ?? 0) + 1)
    return [...counts.entries()].sort((a, b) => b[1] - a[1])
  }, [anomalies, quality.issues])

  const severityCounts = (rows: Array<{ severity: Severity }>) => ({
    error: rows.filter((row) => row.severity === 'error').length,
    warning: rows.filter((row) => row.severity === 'warning').length,
    info: rows.filter((row) => row.severity === 'info').length,
  })
  const current = tab === 'anomalies' ? severityCounts(anomalies) : severityCounts(quality.issues)

  return (
    <Page
      eyebrow="Контроль качества исходных данных"
      title="Что в отчётах не сходится"
      lede={
        <>
          Двадцать файлов заполнялись вручную и по-разному: где-то тысячи рублей подписаны рублями,
          где-то итог не сходится с подпунктами, где-то строка просто пустая. Конвейер не молчит об этом
          и не подставляет нули без следа — каждая правка и каждое противоречие записаны. Центры с
          внутренними расхождениями исключены из подтверждённого резерва сети.
        </>
      }
    >
      <div className="panel rise grid grid-cols-2 divide-x divide-y divide-rule overflow-hidden shadow-card md:grid-cols-4 md:divide-y-0">
        {[
          { label: 'Заполненность ячеек', value: pct(quality.cell_coverage), note: `${quality.indicators} показателей × ${quality.organizations} центров` },
          { label: 'Правок при разборе файлов', value: num(quality.issues_total), note: 'приведение единиц, пустые строки, расхождения итогов' },
          { label: 'Противоречий в показателях', value: num(anomalies.length), note: 'проверка на согласованность между формами' },
          { label: 'Центров с пометками', value: `${byOrg.length} из ${quality.organizations}`, note: `${overview.recommendations.flagged_orgs.length} — без вклада в подтверждённый резерв` },
        ].map((tile) => (
          <div key={tile.label} className="px-4 py-3.5">
            <div className="text-[11.5px] leading-snug text-ink-2">{tile.label}</div>
            <div className="figure mt-1.5 text-[25px] leading-none text-ink">{tile.value}</div>
            <div className="mt-1.5 text-[11px] leading-snug text-ink-3">{tile.note}</div>
          </div>
        ))}
      </div>

      <Band title="Журнал разбора">
        <div className="grid items-start grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
          <Panel
            eyebrow={tab === 'anomalies' ? 'Противоречия между показателями' : 'Правки при чтении файлов'}
            title={
              tab === 'anomalies'
                ? 'Показатели, которые не сходятся между собой'
                : 'Что пришлось поправить, чтобы формы стали сопоставимы'
            }
            subtitle={
              tab === 'anomalies'
                ? 'Проверяется согласованность внутри отчёта: резиденты против обученных, форматы против участников, выручка против масштаба'
                : 'Каждая правка обратима и записана: витрина показывает исходное значение и то, во что оно превратилось'
            }
            actions={
              <div className="flex flex-wrap items-center gap-2">
                <Segmented
                  ariaLabel="Журнал"
                  size="sm"
                  value={tab}
                  onChange={setTab}
                  options={[
                    { value: 'anomalies', label: `Противоречия · ${anomalies.length}` },
                    { value: 'parsing', label: `Разбор · ${quality.issues.length}` },
                  ]}
                />
                <Segmented
                  ariaLabel="Уровень"
                  size="sm"
                  value={severity}
                  onChange={setSeverity}
                  options={[
                    { value: 'all', label: 'Все' },
                    ...(['error', 'warning', 'info'] as const)
                      .filter((level) => current[level] > 0)
                      .map((level) => ({ value: level, label: `${SEVERITY_META[level].label} · ${current[level]}` })),
                  ]}
                />
              </div>
            }
          >
            {tab === 'anomalies' ? (
              anomalyRows.length === 0 ? (
                <Empty text="Противоречий этого уровня нет" />
              ) : (
                <ul className="divide-y divide-rule">
                  {anomalyRows.map((row, index) => (
                    <li key={index}>
                      <button
                        onClick={() => setSelected(row.org_id)}
                        className="group flex w-full gap-3 py-3 text-left transition-colors hover:bg-panel-2 first:pt-0"
                      >
                        <span className="mt-[3px] shrink-0" style={{ color: SEVERITY_META[row.severity].color }}>
                          <Icon name="alert" size={14} strokeWidth={2} />
                        </span>
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                            <span className="text-[13px] font-medium text-ink">{row.org_name}</span>
                            <span className="font-mono text-[10.5px] text-ink-3">{row.metric}</span>
                            <Chip color={SEVERITY_META[row.severity].color} mark>
                              {SEVERITY_META[row.severity].label}
                            </Chip>
                          </div>
                          <p className="mt-1 text-[12px] leading-relaxed text-ink-2">{row.message}</p>
                          <div className="mt-1 flex flex-wrap gap-x-4 text-[10.5px] text-ink-3">
                            <span>{KIND_LABEL[row.kind] ?? row.kind}</span>
                            {row.value != null && <span>значение {dec(row.value, 2)}</span>}
                            {row.reference != null && <span>ожидалось около {dec(row.reference, 2)}</span>}
                            <span>оценка расхождения {dec(row.score, 2)}</span>
                          </div>
                        </div>
                        <span className="shrink-0 self-center text-ink-3 opacity-0 transition-opacity group-hover:opacity-100">
                          <Icon name="chevron" size={13} />
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )
            ) : parsingRows.length === 0 ? (
              <Empty text="Правок этого уровня нет" />
            ) : (
              <ul className="divide-y divide-rule">
                {parsingRows.map((row, index) => (
                  <li key={index}>
                    <button
                      onClick={() => setSelected(row.org_id)}
                      className="group flex w-full gap-3 py-2.5 text-left transition-colors hover:bg-panel-2 first:pt-0"
                    >
                      <span className="mt-[2px] shrink-0" style={{ color: SEVERITY_META[row.severity].color }}>
                        <Icon name={row.severity === 'info' ? 'info' : 'alert'} size={13} strokeWidth={2} />
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-baseline gap-x-2">
                          <span className="text-[12.5px] font-medium text-ink">{derived.nameOf(row.org_id)}</span>
                          <span className="font-mono text-[10.5px] text-ink-3">{row.indicator}</span>
                        </div>
                        <p className="mt-0.5 text-[12px] leading-snug text-ink-2">{row.message}</p>
                        <span className="mt-0.5 block text-[10.5px] text-ink-3">{KIND_LABEL[row.kind] ?? row.kind}</span>
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <div className="flex flex-col gap-4">
            <Panel
              eyebrow="По центрам"
              title="Где пометок больше всего"
              subtitle="Считаются и противоречия, и правки при разборе файла"
            >
              {byOrg.length === 0 ? (
                <Empty text="Пометок нет" />
              ) : (
                <RankedBars items={byOrg} format={(value) => num(value)} labelWidth={150} valueWidth={26} onSelect={setSelected} />
              )}
            </Panel>

            <Panel eyebrow="По типам" title="Что встречается чаще" subtitle="Тип пометки подсказывает, что править в самой форме">
              <ul className="space-y-2.5">
                {kinds.map(([kind, count]) => (
                  <li key={kind}>
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="text-[12px] text-ink-2">{KIND_LABEL[kind] ?? kind}</span>
                      <span className="tnum shrink-0 text-[12.5px] font-medium text-ink">{count}</span>
                    </div>
                    <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-panel-3">
                      <div
                        className="bar-grow h-full rounded-full bg-ink-2"
                        style={{ width: `${(count / kinds[0][1]) * 100}%` }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            </Panel>

            <Panel eyebrow="Принцип" title="Как обходятся с плохими данными">
              <ul className="space-y-2.5">
                {[
                  'Пустая строка становится нулём только там, где ноль содержателен («центр не ведёт переподготовку»), и это записывается в журнал.',
                  'Подпись единицы проверяется на правдоподобие: если перевод в рубли даёт величину в сотни раз выше медианы сети, подпись признаётся ошибочной.',
                  'Центр с внутренним противоречием получает рекомендации, но его резерв не попадает в общую сумму по сети.',
                  'NaN и бесконечности не подменяются нулями: витрина показывает «нет данных», а не выдумывает значение.',
                ].map((item, index) => (
                  <li key={index} className="flex gap-2.5">
                    <span className="eyebrow mt-[3px] w-3.5 shrink-0 tabular-nums">{index + 1}</span>
                    <span className="text-[12px] leading-snug text-ink-2">{item}</span>
                  </li>
                ))}
              </ul>
            </Panel>
          </div>
        </div>
      </Band>

      <p className="mt-6 max-w-[86ch] text-[11.5px] leading-relaxed text-ink-3">
        Всего разобрано {num(quality.organizations)} {plural(quality.organizations, ['файл', 'файла', 'файлов'])} годовой
        отчётности, {num(quality.indicators)} показателей в каждом. Заполненность ячеек — {pct(quality.cell_coverage)}:
        структура форм выдержана везде, расхождения касаются содержания, а не полноты.
      </p>

      <OrgSheet orgId={selected} onClose={() => setSelected(null)} />
    </Page>
  )
}
