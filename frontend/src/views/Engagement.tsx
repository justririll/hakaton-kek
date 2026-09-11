/**
 * Вовлечённость и обратная связь.
 *
 * Прямой обратной связи в ведомственной отчётности нет: ни оценок, ни отзывов,
 * ни повторных визитов по идентификатору участника. Раздел построен на
 * наблюдаемых заменителях, которые отвечают на тот же управленческий вопрос —
 * «дошёл ли участник до результата и вернулся ли он»:
 *
 *   довёл ли работу до результата   → конверсия в арт-продукт;
 *   закрепился ли в центре          → доля резидентов;
 *   заметен ли результат снаружи    → публикации и федеральные площадки.
 *
 * Ни одно число здесь не додумано. Чего в данных нет — сказано прямо, отдельной
 * панелью, а не спрятано за красивой шкалой.
 */

import { useMemo, useState } from 'react'
import { useData } from '../lib/store'
import { Page, Band } from '../ui/Page'
import { Panel, Segmented, InfoDot, Chip } from '../ui/primitives'
import { Icon } from '../ui/Icon'
import { ChartBox, Legend, ClusterMark } from '../charts/kit'
import { QuadrantScatter } from '../charts/quadrant'
import { RankedBars } from '../charts/bars'
import { StripPlot } from '../charts/shapes'
import { clusterColor, clusterMark } from '../lib/palette'
import { dec, num, pct, plural } from '../lib/format'
import { OrgSheet } from './OrgSheet'

type Proxy = 'product_rate' | 'resident_rate' | 'publicity_per_format' | 'audience_per_format'

const PROXIES: Record<Proxy, { label: string; short: string; format: (value: number) => string; question: string }> = {
  product_rate: {
    label: 'Конверсия в творческий продукт',
    short: 'Конверсия в продукт',
    format: (value) => dec(value, 2),
    question: 'Довёл ли участник работу до результата',
  },
  resident_rate: {
    label: 'Доля аудитории, ставшая резидентами',
    short: 'Доля резидентов',
    format: (value) => pct(value),
    question: 'Закрепился ли участник в центре',
  },
  publicity_per_format: {
    label: 'Публичность на одно мероприятие',
    short: 'Публичность',
    format: (value) => dec(value, 2),
    question: 'Заметен ли результат за пределами центра',
  },
  audience_per_format: {
    label: 'Наполняемость мероприятия',
    short: 'Наполняемость',
    format: (value) => dec(value, 1),
    question: 'Приходят ли на то, что центр предлагает',
  },
}

export function EngagementView() {
  const { data, derived } = useData()
  const { overview, organizations } = data
  const [proxy, setProxy] = useState<Proxy>('product_rate')
  const [selected, setSelected] = useState<string | null>(null)
  const [activeCluster, setActiveCluster] = useState<number | null>(null)

  const meta = PROXIES[proxy]

  /* Ступени вовлечённости. Это не воронка: единицы на ступенях разные
     (люди → люди → работы → публикации → события), поэтому показывается сама
     величина и коэффициент перехода, а не вложенная геометрия. */
  const ladder = useMemo(
    () => [
      {
        key: 'audience',
        label: 'Прошли обучение',
        value: overview.audience_total,
        unit: 'чел.',
        note: 'Все, кто попал в отчётные формы как обученные по четырём каналам',
        ratio: null,
      },
      {
        key: 'residents',
        label: 'Стали резидентами',
        value: overview.residents_total,
        unit: 'чел.',
        note: 'Закрепились в центре после обучения — строка 3 Формы 2',
        ratio: { text: `${pct(overview.residents_total / overview.audience_total)} от прошедших обучение` },
      },
      {
        key: 'products',
        label: 'Выпустили творческий продукт',
        value: overview.products_total,
        unit: 'раб.',
        note: 'Готовые работы: макеты, записи, изделия, цифровой контент',
        ratio: { text: `${dec(overview.products_total / overview.audience_total, 2)} работы на участника` },
      },
      {
        key: 'publications',
        label: 'Получили публикацию',
        value: overview.publications_total,
        unit: 'шт.',
        note: 'Материалы о результатах в медиа',
        ratio: { text: `${dec(overview.publications_total / overview.products_total, 2)} публикации на работу` },
      },
      {
        key: 'federal',
        label: 'Вышли на федеральный уровень',
        value: overview.federal_events_total,
        unit: 'шт.',
        note: 'Участие в федеральных мероприятиях и площадках',
        ratio: { text: `${pct(overview.federal_events_total / overview.publications_total)} от числа публикаций` },
      },
    ],
    [overview],
  )

  const maxLadder = Math.max(...ladder.map((step) => step.value))

  const points = useMemo(
    () =>
      organizations.map((org) => ({
        id: org.org_id,
        label: org.short_name,
        cluster: org.cluster,
        x: org.product_rate,
        y: org.resident_rate,
        size: org.audience_total,
      })),
    [organizations],
  )

  const ranked = useMemo(
    () =>
      [...organizations]
        .sort((a, b) => Number(b[proxy]) - Number(a[proxy]))
        .map((org) => ({
          id: org.org_id,
          label: org.short_name,
          value: Number(org[proxy]),
          color: clusterColor(org.cluster),
        })),
    [organizations, proxy],
  )

  const values = ranked.map((item) => item.value).sort((a, b) => a - b)
  const quantile = (q: number) => values[Math.min(values.length - 1, Math.floor(q * (values.length - 1)))]
  const belowMedian = ranked.filter((item) => item.value < quantile(0.5))

  return (
    <Page
      eyebrow="Вовлечённость и обратная связь"
      title="Дошёл ли участник до результата"
      lede={
        <>
          Прямой обратной связи — оценок, отзывов, повторных визитов по участнику — в ведомственной
          отчётности нет ни у одного центра. Вместо того чтобы нарисовать шкалу удовлетворённости из
          воздуха, витрина работает на наблюдаемых заменителях: конверсии в готовую работу, доле
          закрепившихся резидентов и внешней заметности результата. Чего в данных нет — сказано отдельно.
        </>
      }
      actions={
        <div className="flex items-center gap-2 rounded-sm border border-rule bg-panel px-3 py-1.5">
          <span className="shrink-0 text-st-warn"><Icon name="info" size={14} /></span>
          <span className="text-[12px] text-ink-2">Показатели-заменители, не опрос аудитории</span>
        </div>
      }
    >
      {/* ── ступени ──────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
        <Panel
          eyebrow="Ступени вовлечённости · вся сеть"
          title="От участия к внешнему признанию"
          subtitle="Единицы на ступенях разные, поэтому это не воронка: рядом с каждой стоит своя величина и коэффициент перехода"
          footnote="Коэффициент «публикаций на работу» больше единицы там, где об одном результате писали несколько раз, — это нормально и не означает ошибки."
        >
          <ol className="divide-y divide-rule">
            {ladder.map((step, index) => (
              <li key={step.key} className="py-3 first:pt-0 last:pb-0">
                <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                  <div className="flex min-w-0 items-baseline gap-2.5">
                    <span className="eyebrow shrink-0 tabular-nums">{index + 1}</span>
                    <span className="text-[13px] font-medium text-ink">{step.label}</span>
                  </div>
                  <div className="flex shrink-0 items-baseline gap-1.5">
                    <span className="tnum text-[19px] font-semibold text-ink">{num(step.value)}</span>
                    <span className="text-[11px] text-ink-3">{step.unit}</span>
                  </div>
                </div>
                <div className="mt-1.5 ml-[26px]">
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-panel-3">
                    <div
                      className="bar-grow h-full rounded-full"
                      style={{ width: `${(step.value / maxLadder) * 100}%`, background: 'var(--ink-2)' }}
                    />
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5">
                    <span className="text-[11px] text-ink-3">{step.note}</span>
                    {step.ratio && (
                      <span className="tnum text-[11px] font-medium text-ink-2">{step.ratio.text}</span>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </Panel>

        <Panel
          eyebrow="Чего в данных нет"
          title="Контур настоящей обратной связи не подключён"
          subtitle="Раздел честно ограничен тем, что есть в формах. Ниже — чего не хватает и что это дало бы"
          footnote="Ни один показатель на витрине не подменяет эти источники: там, где данных нет, стоит «нет данных», а не ноль."
        >
          <ul className="space-y-3">
            {[
              {
                title: 'Оценка мероприятия участником',
                gap: 'В формах нет ни одной строки об удовлетворённости',
                gain: 'Позволило бы отделить «пришли, потому что интересно» от «пришли, потому что направили»',
              },
              {
                title: 'Повторные визиты по участнику',
                gap: 'Обученные считаются суммарно, без идентификатора человека',
                gain: 'Дало бы настоящую удерживаемость вместо доли резидентов как заменителя',
              },
              {
                title: 'Отказы и незавершённые записи',
                gap: 'Учитываются только состоявшиеся мероприятия',
                gain: 'Показало бы спрос, который центр не смог обслужить',
              },
              {
                title: 'Свободные отзывы и обращения',
                gap: 'Текстовых источников в отчётности нет',
                gain: 'Дало бы темы, по которым аудитория просит программу',
              },
            ].map((item) => (
              <li key={item.title} className="rounded-sm border border-dashed border-rule-2 p-3">
                <div className="flex items-start gap-2">
                  <span className="mt-[3px] shrink-0 text-ink-3"><Icon name="minus" size={12} strokeWidth={2.4} /></span>
                  <div className="min-w-0">
                    <div className="text-[12.5px] font-medium text-ink">{item.title}</div>
                    <p className="mt-0.5 text-[11.5px] leading-snug text-ink-3">{item.gap}</p>
                    <p className="mt-1 text-[11.5px] leading-snug text-ink-2">→ {item.gain}</p>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      {/* ── карта вовлечённости ──────────────────────────────────────────── */}
      <Band
        title="Карта вовлечённости"
        note="Медианы сети делят поле на четыре четверти — у каждой своё управленческое имя"
      >
        <Panel
          eyebrow="Конверсия против удержания"
          title="Кто доводит до результата, а кто удерживает"
          subtitle="По горизонтали — сколько готовых работ выходит на участника, по вертикали — какая доля аудитории закрепилась резидентами. Размер точки — величина аудитории"
          footnote="Доля резидентов выше 100 % означает, что центр ведёт резидентов и обученных по разным контурам — такие случаи разобраны в «Качестве данных»."
        >
          <ChartBox height={420}>
            {({ width, height }) => (
              <QuadrantScatter
                width={width}
                height={height}
                points={points}
                xLabel="Работ на участника"
                yLabel="Доля резидентов"
                xFormat={(value) => dec(value, 1)}
                yFormat={(value) => pct(value)}
                clamp={{ y: 1.6 }}
                selected={selected}
                onSelect={setSelected}
                quadrants={[
                  'ни глубины, ни выхода',
                  'производство без удержания',
                  'удержание без выхода',
                  'глубокая работа с результатом',
                ]}
              />
            )}
          </ChartBox>
          <Legend
            className="mt-2"
            active={activeCluster}
            onHover={(id) => setActiveCluster(id as number | null)}
            items={data.clusters.profiles.map((profile) => ({
              id: profile.cluster_id,
              label: profile.name,
              color: clusterColor(profile.cluster_id),
              shape: clusterMark(profile.cluster_id),
            }))}
          />
        </Panel>
      </Band>

      {/* ── заменители по отдельности ────────────────────────────────────── */}
      <Band title="Каждый заменитель по отдельности" note="Переключатель меняет показатель во всех панелях ниже">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <Segmented
            ariaLabel="Показатель вовлечённости"
            value={proxy}
            onChange={setProxy}
            options={(Object.keys(PROXIES) as Proxy[]).map((key) => ({
              value: key,
              label: PROXIES[key].short,
              hint: PROXIES[key].question,
            }))}
          />
          <span className="text-[12px] text-ink-3">{meta.question}</span>
        </div>

        <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
          <Panel
            eyebrow="Распределение по сети"
            title={meta.label}
            subtitle="Серая полоса — где лежит половина сети; точка — центр"
            actions={<InfoDot text="Двадцати наблюдений мало для гистограммы: точки показывают и разброс, и выбросы, и положение конкретного центра." />}
          >
            <StripPlot
              items={ranked}
              median={quantile(0.5)}
              p25={quantile(0.25)}
              p75={quantile(0.75)}
              format={meta.format}
              height={82}
              onSelect={setSelected}
            />
            <dl className="mt-3 grid grid-cols-4 gap-3 border-t border-rule pt-3">
              {[
                ['Минимум', values[0]],
                ['25-й проц.', quantile(0.25)],
                ['Медиана', quantile(0.5)],
                ['Максимум', values[values.length - 1]],
              ].map(([label, value]) => (
                <div key={label as string}>
                  <dt className="text-[10.5px] leading-snug text-ink-3">{label}</dt>
                  <dd className="tnum mt-0.5 text-[13px] font-medium text-ink">{meta.format(value as number)}</dd>
                </div>
              ))}
            </dl>
            <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-rule pt-3">
              <span className="text-[12px] text-ink-2">
                Ниже медианы — {belowMedian.length} {plural(belowMedian.length, ['центр', 'центра', 'центров'])}:
              </span>
              {belowMedian.slice(0, 6).map((item) => (
                <button key={item.id} onClick={() => setSelected(item.id)}>
                  <Chip color={item.color} mark>{item.label}</Chip>
                </button>
              ))}
              {belowMedian.length > 6 && <Chip>+{belowMedian.length - 6}</Chip>}
            </div>
          </Panel>

          <Panel
            eyebrow="Рейтинг"
            title={`${meta.short}: от большего к меньшему`}
            subtitle="Цвет столбца — аудиторная модель центра. Строка открывает карточку"
          >
            <RankedBars
              items={ranked}
              format={meta.format}
              labelWidth={178}
              valueWidth={66}
              onSelect={setSelected}
            />
          </Panel>
        </div>
      </Band>

      {/* ── вовлечённость по моделям ─────────────────────────────────────── */}
      <Band title="Вовлечённость по аудиторным моделям" note="Медиана показателя внутри каждой модели">
        <div className="stagger grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
          {data.clusters.profiles.map((profile) => {
            const members = profile.members
              .map((id) => derived.byId.get(id))
              .filter((org): org is NonNullable<typeof org> => Boolean(org))
            const medianOf = (key: Proxy) => {
              const sorted = members.map((org) => Number(org[key])).sort((a, b) => a - b)
              const middle = Math.floor(sorted.length / 2)
              return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2
            }
            return (
              <Panel key={profile.cluster_id} className="h-full">
                <div className="flex min-w-0 items-center gap-2">
                  <svg width={13} height={13} viewBox="-7 -7 14 14" aria-hidden className="shrink-0">
                    <ClusterMark shape={clusterMark(profile.cluster_id)} x={0} y={0} r={5} fill={clusterColor(profile.cluster_id)} strokeWidth={0} />
                  </svg>
                  <span className="truncate text-[13px] font-medium text-ink">{profile.name}</span>
                </div>
                <ul className="mt-3 space-y-2">
                  {(Object.keys(PROXIES) as Proxy[]).map((key) => {
                    const value = medianOf(key)
                    const networkMedian = (() => {
                      const sorted = organizations.map((org) => Number(org[key])).sort((a, b) => a - b)
                      const middle = Math.floor(sorted.length / 2)
                      return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2
                    })()
                    const above = value >= networkMedian
                    return (
                      <li key={key} className="flex items-baseline justify-between gap-2">
                        <span className="truncate text-[11.5px] text-ink-2">{PROXIES[key].short}</span>
                        <span className="tnum flex shrink-0 items-center gap-1 text-[11.5px] font-medium text-ink">
                          {PROXIES[key].format(value)}
                          <span style={{ color: above ? 'var(--st-good)' : 'var(--st-none)' }}>
                            <Icon name={above ? 'arrow-up' : 'arrow-down'} size={10} strokeWidth={2.6} />
                          </span>
                        </span>
                      </li>
                    )
                  })}
                </ul>
                <p className="mt-3 border-t border-rule pt-2 text-[10.5px] leading-snug text-ink-3">
                  Стрелка — положение относительно медианы всей сети
                </p>
              </Panel>
            )
          })}
        </div>
      </Band>

      <OrgSheet orgId={selected} onClose={() => setSelected(null)} />
    </Page>
  )
}
