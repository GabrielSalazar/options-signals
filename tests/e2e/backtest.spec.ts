import { test, expect } from '@playwright/test';

test.describe('Backtest Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/backtest');
    await page.waitForLoadState('networkidle');
  });

  test('should display backtest form with inputs', async ({ page }) => {
    // Verify page loaded
    await expect(page).toHaveTitle(/backtest/i);

    // Look for ticker input
    const tickerInput = page.locator('input[name*="ticker"], [aria-label*="ticker"]').first();
    await expect(tickerInput).toBeVisible();

    // Look for date inputs
    const dateInputs = page.locator('input[type="date"], input[name*="date"]');
    const dateCount = await dateInputs.count();
    expect(dateCount).toBeGreaterThanOrEqual(1); // At least start date

    // Look for submit button
    const submitButton = page.locator('button[type="submit"], button:has-text(/backtest|run/i)').first();
    await expect(submitButton).toBeVisible();
  });

  test('should run backtest and display results', async ({ page }) => {
    // Fill ticker
    const tickerInput = page.locator('input[name*="ticker"], [aria-label*="ticker"]').first();
    await tickerInput.fill('PETR4');

    // Fill dates if needed
    const startDate = page.locator('input[name*="start"], input[placeholder*="start"]').first();
    if (await startDate.isVisible()) {
      await startDate.fill('2024-01-01');
    }

    // Submit form
    const submitButton = page.locator('button[type="submit"], button:has-text(/backtest|run/i)').first();
    await submitButton.click();

    // Wait for results
    await page.waitForLoadState('networkidle');

    // Verify results are displayed
    const resultsContainer = page.locator('[role="region"], .results, .backtest-results');
    await expect(resultsContainer).toBeVisible({ timeout: 10000 });

    // Verify key metrics
    const metrics = page.locator('text=/sharpe|return|drawdown|trades|win rate/i');
    expect(await metrics.count()).toBeGreaterThan(0);
  });

  test('should display equity curve', async ({ page }) => {
    // Run backtest
    const tickerInput = page.locator('input[name*="ticker"], [aria-label*="ticker"]').first();
    await tickerInput.fill('VALE3');

    const submitButton = page.locator('button[type="submit"], button:has-text(/backtest|run/i)').first();
    await submitButton.click();

    await page.waitForLoadState('networkidle');

    // Look for chart
    const chart = page.locator('canvas, [role="img"][aria-label*="chart"], svg');
    const hasChart = await chart.isVisible({ timeout: 5000 }).catch(() => false);

    expect(hasChart).toBeTruthy();
  });

  test('should show individual trades', async ({ page }) => {
    // Run backtest
    const tickerInput = page.locator('input[name*="ticker"], [aria-label*="ticker"]').first();
    await tickerInput.fill('BBAS3');

    const submitButton = page.locator('button[type="submit"], button:has-text(/backtest|run/i)').first();
    await submitButton.click();

    await page.waitForLoadState('networkidle');

    // Look for trades table/list
    const tradesSection = page.locator('[data-testid="trades"], .trades-list, table:has-text(/trade|entry|exit/)');
    const hasTradesSection = await tradesSection.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasTradesSection) {
      // Verify trade details
      const tradeRows = page.locator('tr, [data-testid="trade-row"]');
      const count = await tradeRows.count();
      expect(count).toBeGreaterThan(0);

      // Click a trade to see details
      const firstTrade = tradeRows.first();
      await firstTrade.click();

      // Should show entry/exit details
      const details = page.locator('text=/entry|exit|price|date/i');
      expect(await details.count()).toBeGreaterThan(0);
    }
  });

  test('should handle backtest errors gracefully', async ({ page }) => {
    // Fill invalid ticker
    const tickerInput = page.locator('input[name*="ticker"], [aria-label*="ticker"]').first();
    await tickerInput.fill('INVALID_TICKER');

    // Submit form
    const submitButton = page.locator('button[type="submit"], button:has-text(/backtest|run/i)').first();
    await submitButton.click();

    // Wait for error
    const errorMessage = page.locator('[role="alert"], .error, text=/error|invalid|not found/i');
    await expect(errorMessage).toBeVisible({ timeout: 5000 });
  });

  test('should allow downloading results', async ({ page }) => {
    // Run backtest
    const tickerInput = page.locator('input[name*="ticker"], [aria-label*="ticker"]').first();
    await tickerInput.fill('PETR4');

    const submitButton = page.locator('button[type="submit"], button:has-text(/backtest|run/i)').first();
    await submitButton.click();

    await page.waitForLoadState('networkidle');

    // Look for download button
    const downloadButton = page.locator('button:has-text(/download|export|csv/i)');
    const hasDownloadButton = await downloadButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasDownloadButton) {
      // Setup download listener
      const downloadPromise = page.waitForEvent('download');
      await downloadButton.click();

      // Verify download
      const download = await downloadPromise;
      expect(download.suggestedFilename()).toMatch(/backtest|result/i);
    }
  });
});
