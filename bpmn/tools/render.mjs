// Validate + render the BudgetGuard BPMN files with bpmn-js (the library behind demo.bpmn.io).
// Usage: node render.mjs   (from bpmn/tools) -> ../png/<name>.png and .svg
// Uses an installed Chrome/Edge via puppeteer-core (no browser download).
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer-core';

const here = path.dirname(fileURLToPath(import.meta.url));
const bpmnDir = path.resolve(here, '..');
const outDir = path.join(bpmnDir, 'png');
const viewerJs = path.join(here, 'node_modules/bpmn-js/dist/bpmn-viewer.production.min.js');

const browsers = [
  process.env.CHROME_PATH,
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
].filter(Boolean);
const executablePath = browsers.find((p) => fs.existsSync(p));
if (!executablePath) throw new Error('No Chrome/Edge found; set CHROME_PATH');

const files = fs.readdirSync(bpmnDir).filter((f) => f.endsWith('.bpmn'));
const browser = await puppeteer.launch({ executablePath, headless: true });
let failed = false;

for (const file of files) {
  const xml = fs.readFileSync(path.join(bpmnDir, file), 'utf8');
  const page = await browser.newPage();
  await page.setViewport({ width: 1200, height: 800, deviceScaleFactor: 1 });
  await page.setContent('<html><body style="margin:0;background:#fff"><div id="c" style="width:100vw;height:100vh"></div></body></html>');
  await page.addScriptTag({ path: viewerJs });

  const res = await page.evaluate(async (xml) => {
    const viewer = new window.BpmnJS({ container: '#c' });
    try {
      const { warnings } = await viewer.importXML(xml);
      const canvas = viewer.get('canvas');
      const box = canvas.getActiveLayer().getBBox();
      const { svg } = await viewer.saveSVG();
      const reg = viewer.get('elementRegistry');
      return {
        ok: true,
        warnings: warnings.map((w) => w.message),
        box: { x: box.x, y: box.y, w: box.width, h: box.height },
        svg,
        count: reg.getAll().length,
      };
    } catch (e) {
      return { ok: false, error: String(e), warnings: (e.warnings || []).map((w) => w.message) };
    }
  }, xml);

  const base = file.replace(/\.bpmn$/, '');
  if (!res.ok) {
    failed = true;
    console.log(`✗ ${file}: ${res.error}`);
    res.warnings.forEach((w) => console.log('   warning:', w));
    await page.close();
    continue;
  }
  console.log(`✓ ${file}: ${res.count} elements, ${res.warnings.length} warnings`);
  res.warnings.forEach((w) => console.log('   warning:', w));
  if (res.warnings.length) failed = true;

  fs.writeFileSync(path.join(outDir, `${base}.svg`), res.svg);
  // Render the exported SVG at native size for a crisp PNG.
  const pad = 20;
  const w = Math.ceil(res.box.w + 2 * pad);
  const h = Math.ceil(res.box.h + 2 * pad);
  await page.setViewport({ width: w, height: h, deviceScaleFactor: 1.5 });
  await page.setContent(`<html><body style="margin:0;background:#fff">${res.svg}</body></html>`);
  await page.evaluate((w, h) => {
    const s = document.querySelector('svg');
    s.setAttribute('width', w);
    s.setAttribute('height', h);
  }, w, h);
  await page.screenshot({ path: path.join(outDir, `${base}.png`), clip: { x: 0, y: 0, width: w, height: h } });
  await page.close();
}

await browser.close();
process.exit(failed ? 1 : 0);
