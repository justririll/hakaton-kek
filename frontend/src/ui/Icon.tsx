/**
 * Иконки — свой набор из 24-сеточных штрихов в едином весе.
 * Эмодзи в интерфейсе не используются: они ломают строку и тянут за собой
 * чужую типографику.
 */

export type IconName =
  | 'overview' | 'dynamics' | 'clusters' | 'orgs' | 'recs' | 'quality'
  | 'arrow-up' | 'arrow-down' | 'arrow-right' | 'chevron' | 'close' | 'search'
  | 'sun' | 'moon' | 'check' | 'alert' | 'info' | 'sparkle' | 'refresh'
  | 'sort' | 'external' | 'minus' | 'flag' | 'target' | 'people' | 'ruble' | 'doc'

const PATHS: Record<IconName, string> = {
  overview: 'M3 13h5V4H3zM10 20h5V4h-5zM17 20h4v-9h-4z',
  dynamics: 'M3 18l5-6 4 3 5-8M17 7h4v4',
  clusters: 'M7 7.5a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0M22 8.5a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0M11 17.5a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0M20 18.5a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0M6.6 9.4l2 6M17 10l-2.6 6.2M7 7.5h10',
  orgs: 'M3 21h18M5 21V7l7-4 7 4v14M9 21v-4h6v4M9 11h2M13 11h2M9 14h2M13 14h2',
  recs: 'M9 21h6M10 18h4M12 3a6 6 0 0 1 4 10.5V16H8v-2.5A6 6 0 0 1 12 3',
  quality: 'M12 3l8 4v6c0 4.2-3.2 7.3-8 8-4.8-.7-8-3.8-8-8V7zM9 12l2.2 2.2L15.5 10',
  'arrow-up': 'M12 19V5M6 11l6-6 6 6',
  'arrow-down': 'M12 5v14M6 13l6 6 6-6',
  'arrow-right': 'M5 12h14M13 6l6 6-6 6',
  chevron: 'M9 5l7 7-7 7',
  close: 'M6 6l12 12M18 6L6 18',
  search: 'M11 18a7 7 0 1 1 0-14 7 7 0 0 1 0 14M20 20l-4-4',
  sun: 'M12 4V2M12 22v-2M4 12H2M22 12h-2M6 6L4.5 4.5M19.5 19.5L18 18M18 6l1.5-1.5M4.5 19.5L6 18M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0',
  moon: 'M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5',
  check: 'M4 12.5l5 5L20 6.5',
  alert: 'M12 8v5M12 17h.01M10.3 3.9L2.6 17.2A2 2 0 0 0 4.3 20h15.4a2 2 0 0 0 1.7-2.8L13.7 3.9a2 2 0 0 0-3.4 0',
  info: 'M12 11v6M12 7.5h.01M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0',
  sparkle: 'M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z',
  refresh: 'M20 11a8 8 0 1 0-.7 4.3M20 5v6h-6',
  sort: 'M8 4v16M8 20l-3-3M8 20l3-3M16 20V4M16 4l-3 3M16 4l3 3',
  external: 'M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5',
  minus: 'M5 12h14',
  flag: 'M5 21V4M5 5h13l-2.5 4L18 13H5',
  target: 'M12 3v3M12 18v3M3 12h3M18 12h3M17 12a5 5 0 1 1-10 0 5 5 0 0 1 10 0M13.5 12a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0',
  people: 'M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7M2.5 20a6.5 6.5 0 0 1 13 0M16 5.2a3.5 3.5 0 0 1 0 6.6M18 13.6a6.5 6.5 0 0 1 3.5 5.8',
  ruble: 'M9 20V5h4.5a4 4 0 0 1 0 8H6M6 17h7',
  doc: 'M14 3H7a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V7zM14 3v4h4M9 13h6M9 17h4',
}

interface Props {
  name: IconName
  size?: number
  className?: string
  strokeWidth?: number
}

export function Icon({ name, size = 16, className = '', strokeWidth = 1.6 }: Props) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      <path d={PATHS[name]} />
    </svg>
  )
}
