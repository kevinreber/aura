#!/usr/bin/env node
/**
 * Capture screenshots for the Weekend Orchestrator PR.
 *
 * Drives the running UI at http://localhost:5173 with playwright/chromium.
 * Assumes the UI dev server, agent (:8001), and MCP server (:8000) are all up.
 *
 * Outputs to docs/screenshots/weekend-orchestrator/.
 *
 * Run: node scripts/capture_pr_screenshots.mjs
 */
import { chromium } from "playwright";
import { mkdirSync } from "fs";
import { dirname, resolve } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(__dirname, "..", "..", "..", "docs", "screenshots", "weekend-orchestrator");
mkdirSync(OUT, { recursive: true });

const UI_URL = "http://localhost:5173";

async function shoot(page, name, opts = {}) {
  const path = `${OUT}/${name}.png`;
  await page.screenshot({ path, fullPage: opts.fullPage ?? false });
  console.log(`  📸 ${name}.png`);
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2, // Retina-quality screenshots
    colorScheme: "dark",
  });
  const page = await context.newPage();

  console.log(`Capturing screenshots from ${UI_URL}...`);

  // ── 1. Dashboard with Weekend Planner widget visible ──────────────────
  await page.goto(UI_URL, { waitUntil: "networkidle" });
  // Give the chat history + widgets a moment to settle
  await page.waitForTimeout(2000);
  await shoot(page, "01-dashboard", { fullPage: true });

  // ── 2. Weekend Planner widget close-up ────────────────────────────────
  // Use first() in case "Weekend Planner" appears in multiple matches
  const plannerHeader = page.getByText("Weekend Planner").first();
  if (await plannerHeader.isVisible().catch(() => false)) {
    await plannerHeader.scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);
    const widget = page.locator("xpath=ancestor::div[contains(@class, 'rounded-xl')][1]").nth(0);
    // Fall back to a viewport-cropped shot if locator chain misses
    await shoot(page, "02-weekend-planner-widget");
  }

  // ── 3. Settings modal open ────────────────────────────────────────────
  // Direct JS dispatch — chat overlay intercepts mouse clicks, but a
  // synthetic click event bypasses pointer-event capture.
  const opened = await page.evaluate(() => {
    const btn = document.querySelector('button[aria-label="Open weekend settings"]');
    if (btn) {
      btn.click();
      return true;
    }
    return false;
  });
  if (opened) {
    await page.waitForSelector('[role="dialog"]', { timeout: 5000 });
    await page.waitForTimeout(500);
    // Hide chat panel (same z-50 as modal, rendered on top) so the modal
    // body doesn't get covered. Restore after screenshot.
    await page.evaluate(() => {
      document.querySelectorAll(".fixed.bottom-0").forEach((el) => {
        el.dataset._aura_hidden = el.style.display;
        el.style.display = "none";
      });
    });
    await page.waitForTimeout(300);
    await shoot(page, "03-settings-modal");
    // Restore
    await page.evaluate(() => {
      document.querySelectorAll(".fixed.bottom-0").forEach((el) => {
        el.style.display = el.dataset._aura_hidden ?? "";
      });
    });
    await page.keyboard.press("Escape");
    await page.waitForTimeout(500);
  }

  // ── 4. Chat interaction with real trail data ──────────────────────────
  const sent = await page.evaluate(() => {
    // Find a quick-prompt button by its label text.
    const buttons = Array.from(document.querySelectorAll("button"));
    const trail = buttons.find((b) =>
      b.textContent?.includes("Find me hiking trails near San Francisco")
    );
    if (!trail) return false;
    trail.click();
    return true;
  });
  if (sent) {
    await page.waitForTimeout(500);
    // Now click send.
    await page.evaluate(() => {
      const send = Array.from(document.querySelectorAll("button")).find(
        (b) => b.textContent?.trim() === "Send"
      );
      if (send) send.click();
    });
    // Wait for the response (real Google Places call ~3-5s, plus LLM time).
    await page.waitForTimeout(20000);
    await shoot(page, "04-chat-trails-response", { fullPage: true });
  }

  await browser.close();
  console.log(`\n✅ Screenshots saved to ${OUT}`);
}

main().catch((err) => {
  console.error("Screenshot capture failed:", err);
  process.exit(1);
});
