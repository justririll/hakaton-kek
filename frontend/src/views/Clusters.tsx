/** Кластеры: аудиторные модели центров и проверка их устойчивости. */

import { useMemo, useState } from 'react'
import { useData } from '../lib/store'
import { Page, Band } from '../ui/Page'
import { Panel, Chip, InfoDot, Segmented, Empty } from '../ui/primitives'
import { Icon } from '../ui/Icon'
import { ChartBox, ClusterMark, Legend } from '../charts/kit'
import { ClusterScatter } from '../charts/scatter'
import { ZLollipop, Heatmap, SeqLegend } from '../charts/diverging'
import { Dendrogram, MetricLine } from '../charts/shapes'
import { clusterColor, clusterMark } from '../lib/palette'
import { dec, num, pct, plural } from '../lib/format'
import { OrgSheet } from './OrgSheet'

export function ClustersView() {
  const { data, derived } = useData()
  const { clusters, validation, organizations } = data
  const [active, setActive] = useState<number | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [matrix, setMatrix] = useState<'co' | 'loadings'>('co')
  const [asTable, setAsTable] = useState(false)

  const profile = active != null ? derived.clusterById.get(active) : null
  const report = validation.clustering

  const legendItems = clusters.profiles.map((item) => ({
    id: item.cluster_id,
    label: item.name,
    color: clusterColor(item.cluster_id),
    shape: clusterMark(item.cluster_id),
  }))

  /* Матрица совместного попадания: доля бутстрап-прогонов, в которых два центра
     оказались в одном кластере. Порядок строк — по кластерам, иначе блоки не видны. */
  const coRows = useMemo(() => {
    const order = clusters.profiles.flatMap((item) => item.members)
    return order.map((id) => ({ id, label: derived.nameOf(id) }))
  }, [clusters.profiles, derived])

  const coValue = useMemo(() => {
    const index = new Map(validation.co_assignment.map((row) => [row.org_id, row]))
    return (rowId: string, columnId: string) => Number(index.get(rowId)?.[columnId] ?? 0)
  }, [validation.co_assignment])

  const loadingRows = clusters.loadings.map((row) => ({
    id: String(row.feature),
    label: clusters.feature_descriptions[String(row.feature)] ?? String(row.feature),
  }))
  const pcColumns = Array.from({ length: Math.min(5, clusters.components) }, (_, index) => ({
    id: `pc${index + 1}`,
    label: `PC${index + 1} · ${pct(clusters.explained_variance[index], 0)}`,
  }))
  const loadingValue = useMemo(() => {
    const index = new Map(clusters.loadings.map((row) => [String(row.feature), row]))
    // Нормируем модуль нагрузки: тепловая карта показывает силу связи, знак —
    // в подсказке, иначе шкала перестаёт быть последовательной.
    return (rowId: string, columnId: string) => Math.abs(Number(index.get(rowId)?.[columnId] ?? 0)) / 0.7
  }, [clusters.loadings])

  const bestK = clusters.k
  const cutHeight = useMemo(() => {
    const heights = [...clusters.dendrogram.merge_heights].sort((a, b) => b - a)
    // Разрез между (k-1)-м и k-м по величине слиянием даёт ровно k ветвей.
    return heights.length >= bestK ? (heights[bestK - 2] + heights[bestK - 1]) / 2 : undefined
  }, [clusters.dendrogram.merge_heights, bestK])

  return (
    <Page
      eyebrow={`Кластеризация · ${clusters.algorithm} · k = ${clusters.k}`}
      title="Пять аудиторных моделей"
      lede={
        <>
          Центры различаются не размером, а тем, как они работают с аудиторией: чем наполняют
          форматы, насколько глубоко ведут участника и что получают на выходе. Признаковое
          пространство собрано из четырёх блоков, доли каналов переведены в CLR — обычная
          стандартизация для состава некорректна. Разбиение проверено перестановочным тестом
          и исключением по одному.
        </>
      }
      actions={
        <div className="flex items-center gap-2 rounded-sm border border-rule bg-panel px-3 py-1.5">
          <span className="shrink-0 text-st-good"><Icon name="check" size={14} strokeWidth={2.2} /></span>
          <span className="text-[12px] text-ink-2">{report.verdict}</span>
        </div>
      }
    >
      {/* ── карта ────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.45fr)_minmax(0,1fr)]">
        <Panel
          eyebrow="Карта моделей · первые две главные компоненты"
          title="Где центр находится относительно остальных"
          subtitle="Размер точки — величина аудитории. Кластер кодируется цветом и формой сразу: одного цвета для пяти групп недостаточно"
          footnote={
            <>
              Пять компонент объясняют {pct(clusters.explained_variance.slice(0, 5).reduce((sum, value) => sum + value, 0))}{' '}
              разброса. На плоскости показаны первые две — остальные участвуют в кластеризации, но не в этой проекции.
            </>
          }
        >
          <ChartBox height={420}>
            {({ width, height }) => (
              <ClusterScatter
                width={width}
                height={height}
                points={clusters.embedding}
                profiles={clusters.profiles}
                explained={clusters.explained_variance}
                activeCluster={active}
                selected={selected}
                onSelect={setSelected}
              />
            )}
          </ChartBox>
          <Legend items={legendItems} className="mt-2" active={active} onHover={(id) => setActive(id as number | null)} />
        </Panel>

        <div className="flex flex-col gap-3">
          <div className="stagger flex flex-col gap-2.5">
            {clusters.profiles.map((item) => {
              const isActive = active === item.cluster_id
              return (
                <button
                  key={item.cluster_id}
                  onClick={() => setActive(isActive ? null : item.cluster_id)}
                  onMouseEnter={() => setActive(item.cluster_id)}
                  className={`panel flex w-full flex-col gap-2 p-3.5 text-left shadow-card transition-[border-color,background-color] duration-150 hover:border-rule-strong ${
                    isActive ? 'border-rule-strong bg-panel-2' : ''
                  }`}
                >
                  <div className="flex min-w-0 items-start justify-between gap-3">
                    <div className="flex min-w-0 items-center gap-2">
                      <svg width={14} height={14} viewBox="-7 -7 14 14" aria-hidden className="shrink-0">
                        <ClusterMark shape={clusterMark(item.cluster_id)} x={0} y={0} r={5} fill={clusterColor(item.cluster_id)} strokeWidth={0} />
                      </svg>
                      <span className="truncate text-[13.5px] font-medium text-ink">{item.name}</span>
                    </div>
                    <span className="tnum shrink-0 text-[11px] text-ink-3">
                      {item.size} {plural(item.size, ['центр', 'центра', 'центров'])}
                    </span>
                  </div>
                  <p className="text-[11.5px] leading-snug text-ink-2">{item.summary}</p>
                  <div className="flex min-w-0 items-center gap-3 text-[10.5px] text-ink-3">
                    <span className="shrink-0">силуэт {dec(item.mean_silhouette, 2)}</span>
                    <span className="h-2.5 w-px shrink-0 bg-rule-2" />
                    <span className="truncate">{item.member_names.join(' · ')}</span>
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* ── профиль выбранного кластера ──────────────────────────────────── */}
      <Band
        title={profile ? `Профиль модели «${profile.name}»` : 'Чем модели отличаются друг от друга'}
        note={profile ? 'Отклонение от среднего по сети в стандартных отклонениях' : 'Наведите на модель выше, чтобы раскрыть её профиль'}
      >
        {profile ? (
          <div className="grid items-start grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)]">
            <Panel
              eyebrow="Отличительные признаки"
              title={profile.summary}
              subtitle="Ноль — среднее по сети. Плечо вправо: признак выражен сильнее, чем у типичного центра"
              actions={<InfoDot text="Значения — координаты центроида кластера в стандартизованном пространстве признаков, то есть в единицах стандартного отклонения по сети." />}
            >
              <ZLollipop
                color={clusterColor(profile.cluster_id)}
                items={Object.entries(profile.centroid)
                  .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
                  .map(([feature, value]) => ({
                    label: clusters.feature_descriptions[feature] ?? feature,
                    value,
                    hint: feature,
                  }))}
              />
            </Panel>

            <Panel eyebrow="Состав" title={`${profile.size} ${plural(profile.size, ['центр', 'центра', 'центров'])} в модели`} subtitle="Уверенность принадлежности — доля бутстрап-прогонов, в которых центр остался в этом кластере">
              <ul className="divide-y divide-rule">
                {profile.members.map((memberId, index) => {
                  const org = derived.byId.get(memberId)
                  const confidence = report.membership_confidence[memberId] ?? 1
                  return (
                    <li key={memberId}>
                      <button
                        onClick={() => setSelected(memberId)}
                        className="group flex w-full items-center gap-3 py-2.5 text-left transition-colors hover:bg-panel-2"
                      >
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-[13px] font-medium text-ink">{profile.member_names[index]}</div>
                          <div className="truncate text-[11px] text-ink-3">{org?.center ?? ''}</div>
                        </div>
                        <div className="shrink-0 text-right">
                          <div className="tnum text-[12px] font-medium text-ink">{pct(confidence)}</div>
                          <div className="text-[10px] text-ink-3">уверенность</div>
                        </div>
                        <span className="shrink-0 text-ink-3 transition-transform group-hover:translate-x-0.5">
                          <Icon name="chevron" size={13} />
                        </span>
                      </button>
                    </li>
                  )
                })}
              </ul>
            </Panel>
          </div>
        ) : (
          <div className="stagger grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
            {clusters.profiles.map((item) => (
              <Panel key={item.cluster_id} className="h-full">
                <div className="flex min-w-0 items-center gap-2">
                  <svg width={13} height={13} viewBox="-7 -7 14 14" aria-hidden className="shrink-0">
                    <ClusterMark shape={clusterMark(item.cluster_id)} x={0} y={0} r={5} fill={clusterColor(item.cluster_id)} strokeWidth={0} />
                  </svg>
                  <span className="truncate text-[13px] font-medium text-ink">{item.name}</span>
                </div>
                <ul className="mt-3 space-y-2">
                  {item.distinctive.map((feature) => (
                    <li key={feature.feature}>
                      <div className="flex items-baseline justify-between gap-2">
                        <span className="truncate text-[11.5px] text-ink-2">{feature.label}</span>
                        <span className="tnum shrink-0 text-[11px] font-medium text-ink">
                          {feature.z > 0 ? '+' : '−'}{Math.abs(feature.z).toFixed(2)}
                        </span>
                      </div>
                      <div className="mt-1 h-1 w-full rounded-full bg-panel-3">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${Math.min(100, (Math.abs(feature.z) / 3) * 100)}%`,
                            background: clusterColor(item.cluster_id),
                          }}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
              </Panel>
            ))}
          </div>
        )}
      </Band>

      {/* ── проверка ─────────────────────────────────────────────────────── */}
      <Band
        title="Почему этому разбиению можно верить"
        note="Двадцать наблюдений — мало, поэтому проверок несколько и каждая отвечает на свой вопрос"
      >
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Panel
            eyebrow="Перестановочный тест"
            title="Структура есть, а не померещилась"
            subtitle="Признаки перемешиваются внутри столбцов и кластеризация повторяется — так получается, какой силуэт даёт шум"
          >
            <PermutationPlot
              observed={report.observed_silhouette}
              mean={report.permutation_mean}
              std={report.permutation_std}
            />
            <dl className="mt-3 grid grid-cols-3 gap-3 border-t border-rule pt-3">
              {[
                ['Наблюдаемый силуэт', dec(report.observed_silhouette, 2)],
                ['p-значение', report.permutation_p_value < 0.001 ? '< 0,001' : dec(report.permutation_p_value, 3)],
                ['Размер эффекта', `${dec(report.effect_size, 1)} σ`],
              ].map(([label, value]) => (
                <div key={label}>
                  <dt className="text-[10.5px] leading-snug text-ink-3">{label}</dt>
                  <dd className="tnum mt-0.5 text-[15px] font-semibold text-ink">{value}</dd>
                </div>
              ))}
            </dl>
          </Panel>

          <Panel
            eyebrow="Исключение по одному"
            title="Разбиение не держится на одном центре"
            subtitle="Каждый центр по очереди убирается, модель пересобирается, результат сравнивается с исходным по индексу Рэнда"
          >
            <div className="flex flex-col gap-4 py-2">
              {[
                ['Средний ARI', report.loo_mean_ari, 'по всем двадцати прогонам'],
                ['Худший ARI', report.loo_min_ari, 'самый неудачный прогон'],
              ].map(([label, value, note]) => (
                <div key={label as string}>
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="text-[12.5px] text-ink-2">{label}</span>
                    <span className="tnum text-[18px] font-semibold text-ink">{dec(value as number, 3)}</span>
                  </div>
                  <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-panel-3">
                    <div className="bar-grow h-full rounded-full bg-st-good" style={{ width: `${(value as number) * 100}%` }} />
                  </div>
                  <p className="mt-1 text-[10.5px] text-ink-3">{note}</p>
                </div>
              ))}
              <p className="mt-auto border-t border-rule pt-3 text-[11.5px] leading-snug text-ink-3">
                {report.unstable_members.length === 0
                  ? 'Ни один центр не меняет кластер при исключении соседей.'
                  : `Неустойчивы: ${report.unstable_members.map(derived.nameOf).join(', ')}.`}
              </p>
            </div>
          </Panel>

          <Panel
            eyebrow="Согласие алгоритмов"
            title="Три метода дают одно и то же"
            subtitle="Разные семейства алгоритмов сходятся на близком разбиении — значит, дело в данных, а не в методе"
          >
            <ul className="space-y-3">
              {Object.entries(clusters.agreement).map(([pair, value]) => (
                <li key={pair}>
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="font-mono text-[11.5px] text-ink-2">{pair}</span>
                    <span className="tnum text-[13px] font-medium text-ink">{dec(value, 3)}</span>
                  </div>
                  <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-panel-3">
                    <div className="bar-grow h-full rounded-full" style={{ width: `${value * 100}%`, background: 'var(--ink-2)' }} />
                  </div>
                </li>
              ))}
            </ul>
            <div className="mt-4 border-t border-rule pt-3">
              <div className="eyebrow mb-1.5">Устойчивость рекомендаций</div>
              <p className="text-[11.5px] leading-snug text-ink-2">
                {pct(validation.recommendations.stable_share)} рекомендаций переживают{' '}
                {validation.recommendations.runs} прогонов на возмущённых данных; средняя выживаемость{' '}
                {pct(validation.recommendations.mean_survival)}.
              </p>
            </div>
          </Panel>
        </div>
      </Band>

      {/* ── выбор k ──────────────────────────────────────────────────────── */}
      <Band title="Как выбрано число кластеров" note="Четыре метрики против одной: каждая по отдельности обманывает на малой выборке">
        <div className="grid items-start grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
          <Panel
            eyebrow="Кандидаты"
            title={`k = ${bestK} даёт лучший сводный балл`}
            subtitle="Силуэт — плотность групп, стабильность — повторяемость на бутстрапе, баланс — отсутствие кластера-одиночки"
          >
            <div className="overflow-x-auto">
              <table className="w-full min-w-[440px] border-collapse text-[12.5px]">
                <thead>
                  <tr className="border-b border-rule text-left">
                    {['k', 'Силуэт', 'Стабильность', 'Баланс', 'Дэвис—Болдин', 'Балл', 'Размеры'].map((head, index) => (
                      <th key={head} className={`eyebrow pb-2 font-medium ${index > 0 && index < 6 ? 'pl-4 text-right' : ''} ${index === 6 ? 'pl-4' : ''}`}>
                        {head}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-rule">
                  {clusters.candidates.map((candidate) => {
                    const chosen = candidate.k === bestK
                    return (
                      <tr key={candidate.k} className={chosen ? 'bg-panel-2' : ''}>
                        <td className="py-2 font-medium text-ink">
                          <span className="inline-flex items-center gap-1.5">
                            {candidate.k}
                            {chosen && <Chip tone="solid">выбрано</Chip>}
                          </span>
                        </td>
                        <td className="tnum py-2 pl-4 text-right text-ink-2">{dec(candidate.silhouette, 3)}</td>
                        <td className="tnum py-2 pl-4 text-right text-ink-2">{dec(candidate.stability, 3)}</td>
                        <td className="tnum py-2 pl-4 text-right text-ink-2">{dec(candidate.balance, 3)}</td>
                        <td className="tnum py-2 pl-4 text-right text-ink-2">{dec(candidate.davies_bouldin, 3)}</td>
                        <td className="tnum py-2 pl-4 text-right font-medium text-ink">{dec(candidate.score, 3)}</td>
                        <td className="py-2 pl-4 font-mono text-[11px] text-ink-3">{candidate.sizes.join('·')}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <div className="mt-4 grid grid-cols-3 gap-4 border-t border-rule pt-3">
              {([
                ['silhouette', 'Силуэт'],
                ['stability', 'Стабильность'],
                ['score', 'Сводный балл'],
              ] as const).map(([key, label]) => (
                <div key={key}>
                  <div className="eyebrow mb-1">{label}</div>
                  <ChartBox height={92}>
                    {({ width, height }) => (
                      <MetricLine
                        width={width}
                        height={height}
                        best={bestK}
                        domainX={[clusters.candidates[0].k, clusters.candidates[clusters.candidates.length - 1].k]}
                        format={(value) => value.toFixed(2)}
                        points={clusters.candidates.map((candidate) => [candidate.k, candidate[key]] as [number, number])}
                      />
                    )}
                  </ChartBox>
                </div>
              ))}
            </div>
          </Panel>

          <Panel
            eyebrow="Дерево слияний"
            title="Ward: в каком порядке центры объединяются"
            subtitle="Высота перекладины — расстояние слияния. Чем выше, тем непохожее объединяемое"
            footnote="Разрез отмечен там, где дерево даёт пять ветвей — то же разбиение, что и k-средние."
          >
            <ChartBox height={360}>
              {({ width, height }) => (
                <Dendrogram
                  width={width}
                  height={height}
                  icoord={clusters.dendrogram.icoord}
                  dcoord={clusters.dendrogram.dcoord}
                  labels={clusters.dendrogram.ivl.map((id) => derived.nameOf(id))}
                  cutHeight={cutHeight}
                  colorOf={(label) => {
                    const org = organizations.find((item) => item.short_name === label)
                    return org ? clusterColor(org.cluster) : 'var(--rule-2)'
                  }}
                />
              )}
            </ChartBox>
          </Panel>
        </div>
      </Band>

      {/* ── матрицы ──────────────────────────────────────────────────────── */}
      <Band title="Под капотом: признаки и совместные попадания">
        <Panel
          eyebrow="Матрица"
          title={matrix === 'co' ? 'Как часто два центра оказываются вместе' : 'Что вносит вклад в главные компоненты'}
          subtitle={
            matrix === 'co'
              ? 'Доля бутстрап-прогонов, в которых пара центров попала в один кластер. Блоки по диагонали — устойчивые группы'
              : 'Модуль нагрузки признака на компоненту: чем темнее, тем сильнее признак определяет ось'
          }
          actions={
            <div className="flex flex-wrap items-center gap-2">
              <Segmented
                ariaLabel="Матрица"
                size="sm"
                value={matrix}
                onChange={setMatrix}
                options={[
                  { value: 'co', label: 'Совместные попадания' },
                  { value: 'loadings', label: 'Нагрузки признаков' },
                ]}
              />
              {/* Табличный двойник: на тепловой карте значение несёт только цвет,
                  а такое кодирование обязано иметь текстовую замену. */}
              <Segmented
                ariaLabel="Представление"
                size="sm"
                value={asTable ? 'table' : 'map'}
                onChange={(value) => setAsTable(value === 'table')}
                options={[
                  { value: 'map', label: 'Карта' },
                  { value: 'table', label: 'Таблица' },
                ]}
              />
            </div>
          }
          footnote={asTable ? (
            'Те же значения, что и на карте: цвет здесь не используется.'
          ) : (
            <SeqLegend
              from={matrix === 'co' ? 'никогда' : 'нет вклада'}
              to={matrix === 'co' ? 'всегда вместе' : 'определяет ось'}
              caption="значение дублируется в подсказке и в табличном виде"
            />
          )}
        >
          {matrix === 'co' ? (
            coRows.length ? (
              <Heatmap
                rows={coRows}
                columns={coRows}
                value={coValue}
                format={(value) => pct(value)}
                title="Совместное попадание"
                rowLabelWidth={150}
                cellMin={20}
                cellMax={34}
                asTable={asTable}
              />
            ) : (
              <Empty text="Матрица недоступна" />
            )
          ) : (
            <Heatmap
              rows={loadingRows}
              columns={pcColumns}
              value={loadingValue}
              format={(value) => dec(value * 0.7, 3)}
              title="Нагрузка признака"
              rowLabelWidth={230}
              cellMin={56}
              cellMax={110}
              asTable={asTable}
            />
          )}
        </Panel>

        <div className="stagger mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {Object.entries(clusters.feature_blocks).map(([block, features]) => (
            <Panel key={block} eyebrow={`Блок «${block}»`} title={`${features.length} ${plural(features.length, ['признак', 'признака', 'признаков'])}`}>
              <ul className="space-y-1.5">
                {features.map((feature) => (
                  <li key={feature} className="text-[11.5px] leading-snug text-ink-2">
                    {clusters.feature_descriptions[feature] ?? feature}
                  </li>
                ))}
              </ul>
            </Panel>
          ))}
        </div>

        <p className="mt-4 max-w-[86ch] text-[11.5px] leading-relaxed text-ink-3">
          Доли каналов — композиционные данные: они лежат на симплексе, сумма всегда равна единице,
          поэтому признаки линейно зависимы, а евклидово расстояние искажает близость. К ним применено
          центрированное логарифмическое преобразование с мультипликативной заменой нулей — стандартная
          практика для составов. Всего {num(clusters.loadings.length)} признаков на {num(organizations.length)} наблюдений,
          поэтому пространство сжато до {clusters.components} компонент.
        </p>
      </Band>

      <OrgSheet orgId={selected} onClose={() => setSelected(null)} />
    </Page>
  )
}

/**
 * Распределение силуэта на перемешанных данных против наблюдаемого.
 * Нормальная кривая по среднему и стандартному отклонению нулевого распределения —
 * форма нужна, чтобы показать, насколько далеко стоит фактическое значение.
 */
function PermutationPlot({ observed, mean, std }: { observed: number; mean: number; std: number }) {
  return (
    <ChartBox height={122}>
      {({ width, height }) => {
        const padding = { left: 6, right: 6, top: 10, bottom: 20 }
        const innerWidth = Math.max(10, width - padding.left - padding.right)
        const innerHeight = height - padding.top - padding.bottom
        const min = Math.min(mean - 4 * std, observed - 0.05)
        const max = Math.max(mean + 4 * std, observed + 0.05)
        const scale = (value: number) => ((value - min) / (max - min)) * innerWidth
        const samples = Array.from({ length: 90 }, (_, index) => {
          const value = min + ((max - min) * index) / 89
          const density = Math.exp(-0.5 * ((value - mean) / std) ** 2)
          return `${scale(value)},${innerHeight - density * innerHeight * 0.86}`
        }).join(' ')

        return (
          <svg width={width} height={height} role="img" aria-label="Нулевое распределение силуэта и наблюдаемое значение">
            <g transform={`translate(${padding.left},${padding.top})`}>
              <polygon points={`0,${innerHeight} ${samples} ${innerWidth},${innerHeight}`} fill="var(--panel-3)" />
              <polyline points={samples} fill="none" stroke="var(--rule-strong)" strokeWidth={1.5} />
              <line x1={0} x2={innerWidth} y1={innerHeight} y2={innerHeight} stroke="var(--rule-2)" />
              <line x1={scale(mean)} x2={scale(mean)} y1={innerHeight} y2={innerHeight * 0.14} stroke="var(--ink-3)" strokeWidth={1} />
              <text x={scale(mean)} y={innerHeight + 14} textAnchor="middle" className="fill-ink-3 text-[9.5px]">шум</text>
              <line x1={scale(observed)} x2={scale(observed)} y1={innerHeight + 4} y2={2} stroke="var(--st-good)" strokeWidth={2} />
              <circle cx={scale(observed)} cy={2} r={4} fill="var(--st-good)" stroke="var(--panel)" strokeWidth={2} />
              <text
                x={scale(observed)}
                y={innerHeight + 14}
                textAnchor={scale(observed) > innerWidth - 40 ? 'end' : 'middle'}
                className="text-[9.5px] font-medium"
                fill="var(--st-good)"
              >
                факт {observed.toFixed(2)}
              </text>
            </g>
          </svg>
        )
      }}
    </ChartBox>
  )
}
