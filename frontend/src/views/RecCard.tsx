/**
 * Карточка рекомендации.
 *
 * Каждая мера показывается вместе с доказательной базой: собственное значение,
 * квартили сопоставимых центров, лучший результат в группе и оценка эффекта.
 * Уверенность и пометка о качестве данных стоят рядом с приоритетом — мера,
 * посчитанная на противоречивом отчёте, не должна выглядеть так же уверенно,
 * как остальные.
 */

import { useState } from 'react'
import type { Recommendation } from '../lib/types'
import { Icon } from '../ui/Icon'
import { Chip, Hint } from '../ui/primitives'
import { REC_META } from '../lib/palette'
import { compact, dec, money, num, pct } from '../lib/format'

const EVIDENCE_LABEL: Record<string, string> = {
  own_fill: 'Своя наполняемость',
  own_rate: 'Своё значение',
  own_supply: 'Проведено мероприятий',
  own_value: 'Своё значение',
  own_revenue: 'Своя выручка',
  own_share: 'Своя доля',
  peer_p25: 'Нижний квартиль группы',
  peer_median: 'Медиана группы',
  peer_best: 'Лучший в группе',
  peers: 'Центров в сравнении',
  scope: 'Круг сравнения',
  best_peer: 'Лучший центр',
  gap: 'Разрыв',
  required_rate: 'Нужный темп',
  current_rate: 'Текущий темп',
  months_left: 'Месяцев осталось',
}

const SCOPE_LABEL: Record<string, string> = {
  network: 'вся сеть',
  cluster: 'своя модель',
}

function formatEvidence(key: string, value: number | string | null): string {
  if (value == null) return '—'
  if (key === 'scope') return SCOPE_LABEL[String(value)] ?? String(value)
  if (typeof value === 'string') return value
  if (key.includes('revenue')) return money(value)
  if (key === 'peers' || key === 'months_left') return num(value)
  if (key.includes('share')) return pct(value, 1)
  return dec(value, 2)
}

export function RecCard({ rec, showOrg = true, onOrgClick }: {
  rec: Recommendation
  showOrg?: boolean
  onOrgClick?: (orgId: string) => void
}) {
  const [open, setOpen] = useState(false)
  const evidence = Object.entries(rec.evidence).filter(([, value]) => value != null)

  return (
    <article className="panel overflow-hidden shadow-card transition-[border-color] duration-150 hover:border-rule-strong">
      <div className="flex gap-3.5 p-4">
        {/* приоритет */}
        <div className="flex w-11 shrink-0 flex-col items-center">
          <Hint text="Приоритет 0–100: размер резерва, надёжность данных и доля аудитории, которую затрагивает мера">
            <span className="figure cursor-help text-[20px] leading-none text-ink">{rec.priority}</span>
          </Hint>
          <span className="mt-1 text-[9.5px] text-ink-3">приоритет</span>
          <div className="mt-2 flex h-14 w-[5px] flex-col justify-end overflow-hidden rounded-full bg-panel-3">
            <div className="w-full rounded-full bg-ink-2" style={{ height: `${Math.max(4, rec.priority)}%` }} />
          </div>
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <h3 className="text-[13.5px] font-medium text-ink">{rec.title}</h3>
            {showOrg && (
              <button
                onClick={() => onOrgClick?.(rec.org_id)}
                className={`text-[12px] text-ink-3 ${onOrgClick ? 'underline decoration-rule-2 underline-offset-2 hover:text-ink' : ''}`}
              >
                {rec.org_name}
              </button>
            )}
          </div>

          <p className="mt-1.5 text-[12.5px] leading-relaxed text-ink-2">{rec.action}</p>

          <div className="mt-2.5 flex flex-wrap items-center gap-x-2 gap-y-1.5">
            <Chip>{REC_META[rec.rec_type]?.short ?? rec.rec_type}</Chip>
            {rec.impact_value != null && (
              <Chip color="var(--c-4)" mark>
                +{rec.impact_unit === '₽' ? money(rec.impact_value) : `${compact(rec.impact_value)} ${rec.impact_unit ?? ''}`}
              </Chip>
            )}
            <Hint text="Доля прогонов на возмущённых данных, в которых мера сохранилась">
              <Chip color={rec.confidence >= 0.5 ? 'var(--st-good)' : 'var(--st-warn)'} mark>
                уверенность {pct(rec.confidence)}
              </Chip>
            </Hint>
            {rec.data_flag && (
              <Hint text="У центра есть внутренние расхождения в отчёте: мера остаётся в списке, но в подтверждённый резерв сети не входит">
                <Chip color="var(--st-warn)" mark>данные под вопросом</Chip>
              </Hint>
            )}
          </div>

          <button
            onClick={() => setOpen((value) => !value)}
            aria-expanded={open}
            className="mt-2.5 inline-flex items-center gap-1 text-[11.5px] font-medium text-ink-3 transition-colors hover:text-ink"
          >
            <span className={`transition-transform duration-200 ${open ? 'rotate-90' : ''}`}>
              <Icon name="chevron" size={12} />
            </span>
            {open ? 'Свернуть обоснование' : 'Почему так'}
          </button>

          {open && (
            <div className="rise mt-2.5 border-t border-rule pt-2.5">
              <p className="text-[12px] leading-relaxed text-ink-2">{rec.rationale}</p>
              {evidence.length > 0 && (
                <dl className="mt-3 grid grid-cols-2 gap-x-5 gap-y-2 sm:grid-cols-3">
                  {evidence.map(([key, value]) => (
                    <div key={key}>
                      <dt className="text-[10.5px] leading-snug text-ink-3">{EVIDENCE_LABEL[key] ?? key}</dt>
                      <dd className="tnum mt-0.5 text-[12.5px] font-medium text-ink">
                        {formatEvidence(key, value as number | string | null)}
                      </dd>
                    </div>
                  ))}
                </dl>
              )}
            </div>
          )}
        </div>
      </div>
    </article>
  )
}
