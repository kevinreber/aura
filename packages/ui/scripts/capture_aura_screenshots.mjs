#!/usr/bin/env node
/**
 * Capture screenshots of the Aura redesign for PR documentation + README.
 *
 * Drives http://localhost:5173 with playwright/chromium. Requires the UI dev
 * server + agent (:8001) + MCP server (:8000) + a valid logged-in session.
 *
 * The aura_session cookie is read from the AURA_LOCAL_COOKIE environment
 * variable. Grab yours from DevTools → Application → Cookies → localhost:5173.
 *
 *   AURA_LOCAL_COOKIE="<value>" node scripts/capture_aura_screenshots.mjs
 *
 * Outputs to docs/screenshots/aura-redesign/.
 */
import { chromium, devices } from "playwright";
import { mkdirSync } from "fs";
import { dirname, resolve } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(__dirname, "..", "..", "..", "docs", "screenshots", "aura-redesign");
mkdirSync(OUT, { recursive: true });

const UI_URL = "http://localhost:5173";
const COOKIE = process.env.AURA_LOCAL_COOKIE;
if (!COOKIE) {
  console.error("Missing AURA_LOCAL_COOKIE env var. Aborting.");
  process.exit(1);
}

const sessionCookie = {
  name: "aura_session",
  value: COOKIE,
  domain: "localhost",
  path: "/",
  httpOnly: false,
  sameSite: "Lax",
};

async function shoot(page, name, opts = {}) {
  const path = `${OUT}/${name}.png`;
  await page.screenshot({ path, fullPage: opts.fullPage ?? false });
  console.log(`  📸 ${name}.png`);
}

async function settle(page, ms = 1200) {
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(ms);
}

// Scroll inside the .main element (which is the actual scroll container on
// mobile, not the document body — see aura.css grid-template-rows: minmax(0,1fr)).
async function scrollMain(page, top) {
  await page.evaluate((y) => {
    const el = document.querySelector(".main");
    if (el) el.scrollTop = y;
  }, top);
}

async function clickNav(page, label) {
  await page.locator(`.nav-item:has-text("${label}")`).first().click();
  await settle(page, 800);
}

async function clickMobileTab(page, label) {
  await page.locator(`.shell-tabbar .m-tab:has-text("${label}")`).first().click();
  await settle(page, 600);
}

async function desktopFlow(browser) {
  console.log("\n── Desktop (1440×900) ──────────────────────────────────");
  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    colorScheme: "dark",
  });
  await ctx.addCookies([sessionCookie]);
  const page = await ctx.newPage();

  await page.goto(UI_URL, { waitUntil: "networkidle" });
  await settle(page, 2000);

  await shoot(page, "desktop-01-today");

  await clickNav(page, "Calendar");
  await shoot(page, "desktop-02-calendar");

  await clickNav(page, "Tasks");
  await shoot(page, "desktop-03-tasks");

  await clickNav(page, "Markets");
  await shoot(page, "desktop-04-markets");

  await clickNav(page, "Commute");
  await shoot(page, "desktop-05-commute");

  await ctx.close();
}

async function mobileFlow(browser) {
  console.log("\n── Mobile (iPhone 14 Pro, 393×852) ─────────────────────");
  const ctx = await browser.newContext({
    ...devices["iPhone 14 Pro"],
    colorScheme: "dark",
  });
  await ctx.addCookies([sessionCookie]);
  const page = await ctx.newPage();

  await page.goto(UI_URL, { waitUntil: "networkidle" });
  await settle(page, 2000);

  // 1. Today, initial state — sticky header, tabbed schedule, commute.
  await shoot(page, "mobile-01-today-top");

  // 2. Today scrolled — confirms sticky header pins, weather/markets/habits visible.
  await scrollMain(page, 700);
  await settle(page, 400);
  await shoot(page, "mobile-02-today-scrolled");

  // 3. Tabbed schedule on Tomorrow tab.
  await scrollMain(page, 0);
  await settle(page, 400);
  await page.locator(".schedule-tabs .tab:has-text('Tomorrow')").first().click();
  await settle(page, 400);
  await shoot(page, "mobile-03-schedule-tabs-tomorrow");

  // 4. Slide-up copilot sheet.
  await page.locator(".shell-fab").click();
  await settle(page, 600);
  await shoot(page, "mobile-04-copilot-sheet");
  // Close the sheet so subsequent shots aren't behind it.
  await page.locator(".cp-sheet-close").click();
  await settle(page, 400);

  // 5. Tasks view via bottom tab bar.
  await clickMobileTab(page, "Tasks");
  await shoot(page, "mobile-05-tasks");

  // 6. Markets via bottom tab bar.
  await clickMobileTab(page, "Markets");
  await shoot(page, "mobile-06-markets");

  // 7. Weekend planner via bottom tab bar.
  await clickMobileTab(page, "Weekend");
  await shoot(page, "mobile-07-weekend");

  await ctx.close();
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  try {
    await desktopFlow(browser);
    await mobileFlow(browser);
    console.log(`\n✅ All screenshots saved to ${OUT}`);
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
