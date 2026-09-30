// 导出名片：PNG（300 dpi 成品尺寸）、效果图、印刷 PDF（含 3 mm 出血）、Logo PNG。
// 用法：node Market/scripts/export.cjs   （需要 playwright：npm i -D playwright 或全局安装）
const path = require("path");
const { pathToFileURL } = require("url");
const { chromium } = require("playwright");

const ROOT = path.resolve(__dirname, "..");
const OUT = path.join(ROOT, "export");
const PAGE = pathToFileURL(path.join(ROOT, "business-card.html")).href;
const DPI = 300;

async function open(browser, opts) {
  const page = await browser.newPage(opts);
  // 离线导出：卡片字体都在本地，外部字体 CSS 只是编辑时的兜底
  await page.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
  await page.goto(PAGE, { waitUntil: "domcontentloaded" });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(300);
  return page;
}

(async () => {
  const browser = await chromium.launch();

  // 1) 单面 PNG：成品尺寸 90×54 mm @300dpi = 1063×638 px
  let page = await open(browser, { viewport: { width: 1400, height: 1000 }, deviceScaleFactor: DPI / 96 });
  await page.evaluate(() => document.body.classList.add("exporting"));
  // 按卡片边界向内取整裁切，避免亚像素边缘露出页面底色
  const clipOf = async el => {
    const b = await el.boundingBox(), s = DPI / 96;
    const x = Math.ceil(b.x * s) / s, y = Math.ceil(b.y * s) / s;
    return { x, y, width: Math.floor((b.x + b.width) * s) / s - x, height: Math.floor((b.y + b.height) * s) / s - y };
  };
  const cards = await page.$$(".card");
  await page.screenshot({ path: path.join(OUT, "ibitpay-card-front.png"), clip: await clipOf(cards[0]) });
  await page.screenshot({ path: path.join(OUT, "ibitpay-card-back.png"), clip: await clipOf(cards[1]) });
  await page.close();

  // 2) 效果图：页面中的双面预览
  page = await open(browser, { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
  const st = await (await page.$(".stage")).boundingBox();
  await page.screenshot({ path: path.join(OUT, "ibitpay-card-mockup.png"), clip: { x: st.x - 40, y: st.y - 36, width: st.width + 80, height: st.height - 12 } });
  await page.close();

  // 3) 印刷 PDF：每页 96×60 mm（含出血），正反两页
  page = await open(browser, {});
  await page.pdf({ path: path.join(OUT, "ibitpay-card-print.pdf"), preferCSSPageSize: true, printBackground: true });
  await page.close();

  // 4) Logo PNG（透明底）：直接打开 SVG 文件按倍率截图
  const shot = async (file, w, h, scale, out) => {
    const p = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: scale });
    await p.goto(pathToFileURL(path.join(ROOT, "logo", file)).href);
    await p.screenshot({ path: path.join(ROOT, "logo", out), omitBackground: true });
    await p.close();
  };
  await shot("ibitpay-mark.svg", 64, 64, 16, "ibitpay-mark-1024.png");
  await shot("ibitpay-logo.svg", 262, 64, 4, "ibitpay-logo.png");
  await shot("ibitpay-logo-reversed.svg", 262, 64, 4, "ibitpay-logo-reversed.png");

  await browser.close();
  console.log("exported to", OUT);
})();
