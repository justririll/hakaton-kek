/**
 * Разметка ответа языковой модели.
 *
 * Модель отдаёт короткий набор конструкций — заголовки, списки, жирный текст.
 * Полноценный парсер Markdown тут лишний: он тянет зависимость ради пяти правил
 * и открывает путь произвольному HTML в текст, который пришёл извне.
 */

import { Fragment } from 'react'
import type { ReactNode } from 'react'

function inline(text: string, keyPrefix: string): ReactNode[] {
  const parts: ReactNode[] = []
  const pattern = /\*\*(.+?)\*\*|«([^»]+)»|(\d[\d  \s]*(?:[.,]\d+)?\s*(?:₽|%|чел\.|шт\.|ед\.|раб\.))/g
  let cursor = 0
  let match: RegExpExecArray | null
  let index = 0

  while ((match = pattern.exec(text))) {
    if (match.index > cursor) parts.push(text.slice(cursor, match.index))
    if (match[1] !== undefined) {
      parts.push(<strong key={`${keyPrefix}-b${index}`} className="font-semibold text-ink">{match[1]}</strong>)
    } else if (match[2] !== undefined) {
      parts.push(<em key={`${keyPrefix}-q${index}`} className="not-italic text-ink">«{match[2]}»</em>)
    } else {
      parts.push(<span key={`${keyPrefix}-n${index}`} className="tnum font-medium text-ink">{match[3]}</span>)
    }
    cursor = match.index + match[0].length
    index += 1
  }
  if (cursor < text.length) parts.push(text.slice(cursor))
  return parts
}

export function Markdown({ text, className = '' }: { text: string; className?: string }) {
  const lines = text.split('\n')
  const blocks: ReactNode[] = []
  let list: Array<{ marker: string; body: string }> = []

  const flush = (key: string) => {
    if (!list.length) return
    const ordered = /^\d+\.$/.test(list[0].marker)
    blocks.push(
      <ol key={key} className={`my-2.5 space-y-2 ${ordered ? '' : 'list-none'}`}>
        {list.map((item, index) => (
          <li key={index} className="flex gap-2.5">
            <span className="eyebrow mt-[3px] shrink-0 tabular-nums" style={{ minWidth: ordered ? 16 : 10 }}>
              {ordered ? item.marker.replace('.', '') : '—'}
            </span>
            <span className="min-w-0 flex-1">{inline(item.body, `${key}-${index}`)}</span>
          </li>
        ))}
      </ol>,
    )
    list = []
  }

  lines.forEach((raw, index) => {
    const line = raw.trim()
    if (!line) { flush(`l${index}`); return }

    const heading = line.match(/^#{1,6}\s+(.*)$/)
    if (heading) {
      flush(`l${index}`)
      blocks.push(
        <h4 key={`h${index}`} className="mt-5 mb-1.5 font-serif text-[14.5px] font-semibold text-ink first:mt-0">
          {inline(heading[1], `h${index}`)}
        </h4>,
      )
      return
    }

    const bullet = line.match(/^[-*•]\s+(.*)$/)
    if (bullet) { list.push({ marker: '—', body: bullet[1] }); return }

    const numbered = line.match(/^(\d+\.)\s+(.*)$/)
    if (numbered) { list.push({ marker: numbered[1], body: numbered[2] }); return }

    flush(`l${index}`)
    blocks.push(
      <p key={`p${index}`} className="my-2 leading-relaxed">{inline(line, `p${index}`)}</p>,
    )
  })
  flush('tail')

  return <div className={`text-[13px] text-ink-2 ${className}`}>{blocks.map((block, index) => <Fragment key={index}>{block}</Fragment>)}</div>
}
