/**
 * Снимки витрины для колоды защиты.
 *
 * Кадрируем не страницу, а конкретную панель: так в кадр не попадают обрезанные
 * слова и половины осей. Где панель длиннее нужного, высота обрезается не по
 * произвольному пикселю, а по нижней границе последней целиком помещающейся
 * строки — тогда кадр выглядит как «список продолжается», а не как обрыв.
 *
 * node tools/shoot.mjs <базовый-url> <каталог>
 */
import { spawn } from 'node:child_process'
import { writeFileSync, mkdirSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const BASE = process.argv[2] ?? 'https://vitaliysoftware.duckdns.org'
const OUT = process.argv[3] ?? 'shots/pptx'
const PORT = 9333
const PROFILE = join(tmpdir(), `vss-shots-${process.pid}`)

const SHOTS = [
  // Обзор: шапка раздела и первый ряд панелей — то, что видно при открытии.
  { name: 'overview', path: '/', w: 1500,
    pick: { from: 'header', to: 'section.panel:nth-of-type(2)' }, pad: 0 },

  // Журнал противоречий: длинный список, режем по границе строки.
  { name: 'quality', path: '/quality', w: 1080,
    pick: { h3: 'Показатели, которые не сходятся', maxH: 780, snap: ':scope li, :scope > div > div' }, pad: 12 },

  // Карта кластеров целиком, с осями и легендой.
  { name: 'clusters', path: '/clusters', w: 1120, pick: { h3: 'Где центр находится' }, pad: 12 },

  // Очередь мер: карточки рекомендаций.
  { name: 'recs', path: '/recommendations', w: 1500,
    pick: { from: 'header', to: 'ul.stagger', maxH: 880, snap: 'ul.stagger > li' }, pad: 0 },

  // Ступени вовлечённости.
  { name: 'eng', path: '/engagement', w: 1080, pick: { h3: 'От участия к внешнему признанию' }, pad: 12 },

  // Панель «чего в данных нет» — ядро слайда о честности.
  { name: 'gaps', path: '/engagement', w: 900, pick: { h3: 'Контур настоящей обратной связи' }, pad: 12 },

  // Таблица центров.
  { name: 'orgs', path: '/organizations', w: 1900,
    pick: { sel: 'section.panel', maxH: 660, snap: 'tbody tr' }, pad: 12 },

  // Исполнение годового плана.
  { name: 'plan', path: '/dynamics', w: 1080, pick: { h3: 'Как читается год' }, pad: 12 },

  // Рейтинг центров по исполнению.
  { name: 'pace', path: '/dynamics', w: 1180,
    pick: { h3: 'Двадцать центров в порядке исполнения', maxH: 700, snap: ':scope li, tbody tr' }, pad: 12 },
]

const chrome = spawn('/usr/bin/google-chrome-stable', [
  '--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${PROFILE}`,
  '--no-first-run', '--no-default-browser-check', '--no-sandbox', '--disable-gpu',
  '--hide-scrollbars', '--force-device-scale-factor=1', 'about:blank',
], { stdio: ['ignore', 'ignore', 'pipe'] })
chrome.stderr.on('data', () => {})

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function version() {
  for (let i = 0; i < 80; i += 1) {
    try { const r = await fetch(`http://127.0.0.1:${PORT}/json/version`); if (r.ok) return r.json() } catch { /* поднимается */ }
    await sleep(250)
  }
  throw new Error('Chrome не ответил на CDP')
}

class Session {
  constructor(ws) { this.ws = ws; this.id = 0; this.waiting = new Map() }
  static async open(url) {
    const ws = new WebSocket(url)
    await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej })
    const s = new Session(ws)
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data)
      const slot = s.waiting.get(msg.id)
      if (slot) { s.waiting.delete(msg.id); msg.error ? slot.rej(new Error(JSON.stringify(msg.error))) : slot.res(msg.result) }
    }
    return s
  }
  send(method, params = {}) {
    const id = ++this.id
    this.ws.send(JSON.stringify({ id, method, params }))
    return new Promise((res, rej) => this.waiting.set(id, { res, rej }))
  }
  async evaluate(expression) {
    const r = await this.send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.text)
    return r.result.value
  }
}

const RESOLVE = `(spec) => {
  const norm = (s) => (s || '').replace(/\\s+/g, ' ').trim();
  const byHead = (text) => [...document.querySelectorAll('section.panel')]
    .find((p) => { const h = p.querySelector('h3'); return h && norm(h.textContent).includes(text) });
  const one = (s) => (s.h3 ? byHead(s.h3) : document.querySelector(s.sel));
  const box = (el) => { const r = el.getBoundingClientRect();
    return { x: r.x + scrollX, y: r.y + scrollY, w: r.width, h: r.height } };

  const trim = (r, el, spec) => {
    if (!spec.maxH || r.h <= spec.maxH) return r;
    // Срез по нижней границе последнего целиком уместившегося элемента списка.
    const limit = r.y + spec.maxH;
    let cut = 0;
    for (const child of el.querySelectorAll(spec.snap)) {
      const c = box(child);
      if (c.y + c.h <= limit && c.y + c.h > cut) cut = c.y + c.h;
    }
    r.h = (cut > r.y + 120 ? cut - r.y : spec.maxH);
    r.cropped = true;
    return r;
  };

  if (spec.from) {
    const a = document.querySelector(spec.from), b = document.querySelector(spec.to);
    if (!a || !b) return null;
    const ra = box(a), rb = box(b);
    const r = { x: Math.min(ra.x, rb.x), y: ra.y, w: Math.max(ra.w, rb.w), h: rb.y + rb.h - ra.y };
    return trim(r, a.parentElement ?? document.body, spec);
  }
  const el = one(spec);
  if (!el) return null;
  const r = box(el);
  if (spec.maxH && r.h > spec.maxH) {
    // Срез по нижней границе последнего целиком уместившегося элемента списка.
    const limit = r.y + spec.maxH;
    let cut = 0;
    for (const child of el.querySelectorAll(spec.snap)) {
      const c = box(child);
      if (c.y + c.h <= limit && c.y + c.h > cut) cut = c.y + c.h;
    }
    r.h = (cut > r.y + 120 ? cut - r.y : spec.maxH);
    r.cropped = true;
  }
  return r;
}`

async function main() {
  mkdirSync(OUT, { recursive: true })
  const info = await version()
  const browser = await Session.open(info.webSocketDebuggerUrl)
  const { targetId } = await browser.send('Target.createTarget', { url: 'about:blank' })
  const tab = await Session.open(`ws://127.0.0.1:${PORT}/devtools/page/${targetId}`)
  await tab.send('Page.enable')
  await tab.send('Runtime.enable')
  await tab.send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: 'light' }] })

  for (const shot of SHOTS) {
    await tab.send('Emulation.setDeviceMetricsOverride', { width: shot.w, height: 1100, deviceScaleFactor: 2, mobile: false })
    await tab.send('Page.navigate', { url: BASE + shot.path })
    for (let i = 0; i < 140; i += 1) {
      const ready = await tab.evaluate(`document.querySelectorAll('section.panel').length`).catch(() => 0)
      if (ready > 0) break
      await sleep(250)
    }
    await tab.evaluate(`document.documentElement.setAttribute('data-theme','light'); 1`)
    await sleep(1500)

    const rect = await tab.evaluate(`(${RESOLVE})(${JSON.stringify(shot.pick)})`)
    if (!rect) { console.log(`!! ${shot.name}: элемент не найден`); continue }

    const pad = shot.pad
    const below = rect.cropped ? 0 : pad
    const clip = { x: Math.max(0, rect.x - pad), y: Math.max(0, rect.y - pad),
                   width: rect.w + pad * 2, height: rect.h + pad + below, scale: 2 }
    const { data } = await tab.send('Page.captureScreenshot', { format: 'png', clip, captureBeyondViewport: true, fromSurface: true })
    writeFileSync(join(OUT, `${shot.name}.png`), Buffer.from(data, 'base64'))
    console.log(`${shot.name.padEnd(9)} ${Math.round(clip.width)}×${Math.round(clip.height)}   ratio ${(clip.width / clip.height).toFixed(2)}`)
  }

  chrome.kill()
  try { rmSync(PROFILE, { recursive: true, force: true }) } catch { /* профиль ещё пишется */ }
}

main().catch((e) => { console.error(e); chrome.kill(); process.exit(1) })
