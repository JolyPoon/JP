// 导出电子名片图片（发微信 / 朋友圈 / 邮件签名用）。
// 用法：node Market/scripts/export.cjs   （需要 playwright：npm i -D playwright）
// Logo 的 SVG / PDF / EPS / PNG 由 scripts/build_logo.py 生成。
const path = require("path");
const { pathToFileURL } = require("url");
const { chromium } = require("playwright");

const ROOT = path.resolve(__dirname, "..");
const OUT = path.join(ROOT, "export");
const PAGE = pathToFileURL(path.join(ROOT, "ecard.html")).href;

(async () => {
  const browser = await chromium.launch();
  // 手机尺寸（390×844，iPhone 14/15），3 倍图；关闭动画，截取最终状态
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, reducedMotion: "reduce" });
  await page.goto(PAGE);
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(300);

  // 1) 首屏：手机一屏（含底部操作栏）
  await page.screenshot({ path: path.join(OUT, "ibitpay-ecard-screen.png") });

  // 2) 长图：完整名片。长图里按钮无法点击，所以隐藏底部操作栏
  await page.addStyleTag({ content: ".dock{display:none} .page{padding-bottom:28px}" });
  await page.waitForTimeout(100);
  await page.screenshot({ path: path.join(OUT, "ibitpay-ecard-long.png"), fullPage: true });

  await browser.close();
  console.log("exported to", OUT);
})();
