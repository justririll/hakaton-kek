/** Шапка раздела: надзаголовок, заголовок, подзаголовок и место под действия. */

import type { ReactNode } from 'react'

export function Page({
  eyebrow, title, lede, actions, children,
}: {
  eyebrow: string
  title: string
  lede?: ReactNode
  actions?: ReactNode
  children: ReactNode
}) {
  return (
    <div className="mx-auto w-full max-w-[1500px] px-4 pb-16 sm:px-6 lg:px-8">
      <header className="rise flex flex-wrap items-end justify-between gap-x-8 gap-y-4 border-b border-rule py-6 lg:py-8">
        <div className="min-w-0 max-w-[62ch]">
          <div className="eyebrow">{eyebrow}</div>
          <h1 className="mt-2 font-serif text-[26px] leading-[1.15] font-semibold tracking-[-0.02em] text-ink sm:text-[31px]">
            {title}
          </h1>
          {lede && <p className="mt-2.5 text-[13.5px] leading-relaxed text-ink-2">{lede}</p>}
        </div>
        {actions && <div className="flex min-w-0 max-w-full flex-wrap items-center gap-2">{actions}</div>}
      </header>
      <div className="pt-6">{children}</div>
    </div>
  )
}

/** Заголовок группы панелей внутри раздела. */
export function Band({ title, note, children }: { title: string; note?: ReactNode; children: ReactNode }) {
  return (
    <section className="mt-8 first:mt-0">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
        <h2 className="font-serif text-[17px] font-semibold tracking-[-0.01em] text-ink">{title}</h2>
        {note && <p className="text-[12px] text-ink-3">{note}</p>}
      </div>
      {children}
    </section>
  )
}
