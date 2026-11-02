import { test, expect } from '@playwright/test';
import path from 'node:path';
import fs from 'node:fs';
import { setupMockApi } from './helpers/mockApi';

const repoRoot = path.resolve(import.meta.dirname, '../../..');
const screenshotsDir = path.resolve(repoRoot, 'docs/screenshots');

test.describe('Discovery Assistant Chatbot E2E & Visual Verification (P13.25)', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    if (!fs.existsSync(screenshotsDir)) {
      fs.mkdirSync(screenshotsDir, { recursive: true });
    }
  });

  test('desktop user journey: launch from header, query, candidate picks, and screenshot', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto('/');

    // 1. Launch assistant from AppHeader
    const askAiBtn = page.getByRole('button', { name: /open discovery assistant/i }).first();
    await expect(askAiBtn).toBeVisible();
    await askAiBtn.click();

    // 2. Verify dialog open and aria attributes
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await expect(dialog).toHaveAttribute('aria-modal', 'true');
    await expect(page.getByRole('heading', { name: /discovery assistant/i })).toBeVisible();

    // 3. Send a message
    const input = page.getByPlaceholder(/ask about/i);
    await expect(input).toBeVisible();
    await input.fill('Recommend classic sci-fi movies');
    await page.getByRole('button', { name: /send message/i }).click();

    // 4. Verify candidate picks and response
    await expect(dialog.getByText(/Here are two personalized recommendations/i)).toBeVisible();
    await expect(dialog.getByTestId('pick-card-1')).toBeVisible();

    // 5. Capture desktop screenshot
    const desktopScreenshotPath = path.join(screenshotsDir, 'chat-desktop.png');
    await page.screenshot({ path: desktopScreenshotPath, fullPage: false });
    expect(fs.existsSync(desktopScreenshotPath)).toBe(true);

    // 6. Test keyboard Escape dismiss
    await page.keyboard.press('Escape');
    await expect(dialog).not.toBeVisible();
  });

  test('mobile 360px viewport: floating launcher, responsive sheet, and screenshot', async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 740 });
    await page.goto('/');

    // 1. Floating launcher visible
    const launcher = page.getByRole('button', { name: /open discovery assistant/i }).last();
    await expect(launcher).toBeVisible();
    await launcher.click();

    // 2. Dialog visible as full-height mobile sheet
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();

    // 3. Capture mobile 360px screenshot
    const mobileScreenshotPath = path.join(screenshotsDir, 'chat-mobile.png');
    await page.screenshot({ path: mobileScreenshotPath, fullPage: false });
    expect(fs.existsSync(mobileScreenshotPath)).toBe(true);

    // 4. Close via X button
    await page.getByRole('button', { name: /close assistant panel/i }).click();
    await expect(dialog).not.toBeVisible();
  });
});
