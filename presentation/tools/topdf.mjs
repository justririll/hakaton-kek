/** Печать HTML-колоды в PDF: запасной формат, если .pptx не откроется. */
import { spawn } from 'node:child_process'
import { writeFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const SRC = process.argv[2]
const OUT = process.argv[3]
const PORT = 9336
const PROFILE = join(tmpdir(), `vss-pdf-${process.pid}`)
const chrome = spawn('/usr/bin/google-chrome-stable', ['--headless=new', `--remote-debugging-port=${PORT}`,
  `--user-data-dir=${PROFILE}`, '--no-first-run', '--no-sandbox', '--disable-gpu', '--hide-scrollbars',
  '--font-render-hinting=none', 'about:blank'], { stdio: ['ignore', 'ignore', 'pipe'] })
chrome.stderr.on('data', () => {})
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
async function version() {
  for (let i = 0; i < 80; i += 1) {
    try { const r = await fetch(`http://127.0.0.1:${PORT}/json/version`); if (r.ok) return r.json() } catch {}
    await sleep(250)
  }
  throw new Error('нет CDP')
}
class S {
  constructor(ws) { this.ws = ws; this.id = 0; this.w = new Map() }
  static async open(u) {
    const ws = new WebSocket(u)
    await new Promise((a, b) => { ws.onopen = a; ws.onerror = b })
    const s = new S(ws)
    ws.onmessage = (e) => { const m = JSON.parse(e.data); const k = s.w.get(m.id)
      if (k) { s.w.delete(m.id); m.error ? k.rej(new Error(JSON.stringify(m.error))) : k.res(m.result) } }
    return s
  }
  send(m, p = {}) { const id = ++this.id; this.ws.send(JSON.stringify({ id, method: m, params: p }))
    return new Promise((res, rej) => this.w.set(id, { res, rej })) }
}
const info = await version()
const browser = await S.open(info.webSocketDebuggerUrl)
const { targetId } = await browser.send('Target.createTarget', { url: 'about:blank' })
const tab = await S.open(`ws://127.0.0.1:${PORT}/devtools/page/${targetId}`)
await tab.send('Page.enable')
await tab.send('Page.navigate', { url: 'file://' + SRC })
await sleep(3500)
const { data } = await tab.send('Page.printToPDF', {
  printBackground: true, preferCSSPageSize: true, marginTop: 0, marginBottom: 0, marginLeft: 0, marginRight: 0,
})
writeFileSync(OUT, Buffer.from(data, 'base64'))
console.log(OUT)
chrome.kill()
try { rmSync(PROFILE, { recursive: true, force: true }) } catch {}
