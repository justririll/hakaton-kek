/**
 * Резюме от языковой модели.
 *
 * Текст генерируется по уже посчитанным числам и ничего не досчитывает сам,
 * поэтому он подписан моделью и временем и отделён от остальной витрины: это
 * пересказ, а не источник. Запрос уходит после открытия — на старте витрина
 * не должна ждать внешний сервис.
 */

import { useCallback, useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { AiSummary } from '../lib/types'
import { Icon } from './Icon'
import { Markdown } from './Markdown'
import { Button, Skeleton } from './primitives'

export function AiBrief({
  orgId, title = 'Исполнительское резюме', className = '', facts,
}: {
  orgId?: string
  title?: string
  className?: string
  /** Числа, на которых стоит текст: колонка справа держит его на проверяемой почве. */
  facts?: Array<{ label: string; value: string }>
}) {
  const [state, setState] = useState<{ phase: 'idle' | 'loading' | 'ready' | 'error'; data?: AiSummary; error?: string }>({
    phase: 'loading',
  })

  const load = useCallback(
    (refresh = false) => {
      setState({ phase: 'loading' })
      const request = orgId ? api.aiOrg(orgId, refresh) : api.aiSummary(refresh)
      request
        .then((data) => setState({ phase: 'ready', data }))
        .catch((error: Error) => setState({ phase: 'error', error: error.message }))
    },
    [orgId],
  )

  useEffect(() => { load() }, [load])

  const content = state.data?.content
  const failed = state.phase === 'error' || (state.phase === 'ready' && !content)

  return (
    <section className={`panel overflow-hidden shadow-card ${className}`}>
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-rule bg-panel-2 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <span className="text-ink-3"><Icon name="sparkle" size={14} /></span>
          <h3 className="text-[13px] font-medium text-ink">{title}</h3>
          {state.data?.model && (
            <span className="hidden font-mono text-[10.5px] text-ink-3 sm:inline">
              {state.data.model}
              {state.data.stale ? ' · последний удачный ответ' : ''}
            </span>
          )}
        </div>
        <Button icon="refresh" onClick={() => load(true)} disabled={state.phase === 'loading'}>
          Пересобрать
        </Button>
      </header>

      <div className={`gap-6 px-4 py-3.5 ${facts ? 'grid lg:grid-cols-[minmax(0,1fr)_212px]' : ''}`}>
        <div className="min-w-0">
        {state.phase === 'loading' && (
          <div className="space-y-2">
            <Skeleton className="h-3.5 w-1/3" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-[92%]" />
            <Skeleton className="h-3 w-[78%]" />
          </div>
        )}

        {failed && (
          <p className="text-[12.5px] leading-relaxed text-ink-3">
            Резюме сейчас недоступно: {state.error ?? state.data?.detail ?? 'модель не ответила'}.
            Все выводы витрины считаются на бэкенде и от этого текста не зависят.
          </p>
        )}

        {state.phase === 'ready' && content && (
          <>
            <Markdown text={content} className="max-w-[78ch]" />
            <p className="mt-4 border-t border-rule pt-2.5 text-[11px] text-ink-3">
              Текст собран моделью по уже рассчитанным показателям
              {state.data?.generated_at ? ` · ${state.data.generated_at}` : ''}
              {state.data?.elapsed_seconds ? ` · ${state.data.elapsed_seconds.toFixed(1)} с` : ''}
              . Числа берутся из конвейера, модель их не пересчитывает.
            </p>
          </>
        )}
        </div>

        {facts && (
          <aside className="min-w-0 border-t border-rule pt-3.5 lg:border-t-0 lg:border-l lg:pt-0 lg:pl-5">
            <div className="eyebrow mb-2.5">Из чего собран текст</div>
            <dl className="space-y-2.5">
              {facts.map((fact) => (
                <div key={fact.label} className="border-b border-rule pb-2 last:border-0 last:pb-0">
                  <dt className="text-[11px] leading-snug text-ink-3">{fact.label}</dt>
                  <dd className="tnum mt-0.5 text-[14px] font-medium text-ink">{fact.value}</dd>
                </div>
              ))}
            </dl>
          </aside>
        )}
      </div>
    </section>
  )
}
