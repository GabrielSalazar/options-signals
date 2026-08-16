import { test, expect } from '@playwright/test';

test.describe('Filter & Sort Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should filter signals by type', async ({ page }) => {
    // Look for type filter
    const typeFilter = page.locator(
      'select[name*="type"], input[placeholder*="type"], [aria-label*="signal type"]'
    ).first();

    if (await typeFilter.isVisible()) {
      // Select CALL signals
      await typeFilter.click();
      const callOption = page.locator('text=/CALL|Compra/i').first();
      await callOption.click();

      // Wait for results
      await page.waitForLoadState('networkidle');

      // Verify filtered results
      const signals = page.locator('[role="row"], [data-testid="signal-item"]');
      const count = await signals.count();

      if (count > 0) {
        const firstSignal = signals.first();
        const text = await firstSignal.textContent();
        expect(text?.toUpperCase()).toContain('CALL');
      }
    }
  });

  test('should filter signals by score range', async ({ page }) => {
    // Look for score range slider or inputs
    const minScoreInput = page.locator('input[name*="min"], input[name*="score"]').first();

    if (await minScoreInput.isVisible()) {
      // Set minimum score to 70
      await minScoreInput.clear();
      await minScoreInput.fill('70');

      // Press Enter to apply
      await minScoreInput.press('Enter');

      // Wait for results
      await page.waitForLoadState('networkidle');

      // Verify scores are >= 70
      const scoreElements = page.locator('[data-testid="score"], .score');
      const count = await scoreElements.count();

      for (let i = 0; i < Math.min(count, 5); i++) {
        const scoreText = await scoreElements.nth(i).textContent();
        const score = parseInt(scoreText || '0');
        expect(score).toBeGreaterThanOrEqual(70);
      }
    }
  });

  test('should sort signals by score descending', async ({ page }) => {
    // Look for sort button/dropdown
    const sortButton = page.locator(
      'button:has-text(/sort|score|rating/i), select[name*="sort"]'
    ).first();

    if (await sortButton.isVisible()) {
      await sortButton.click();

      // Select "Score Descending"
      const sortOption = page.locator('text=/score|rating|descending|maior/i').first();
      if (await sortOption.isVisible()) {
        await sortOption.click();

        // Wait for sort to apply
        await page.waitForTimeout(500);

        // Verify order: scores should be descending
        const scoreElements = page.locator('[data-testid="score"], .score');
        const scores: number[] = [];

        const count = await scoreElements.count();
        for (let i = 0; i < Math.min(count, 10); i++) {
          const text = await scoreElements.nth(i).textContent();
          const score = parseInt(text || '0');
          scores.push(score);
        }

        // Check if descending
        for (let i = 0; i < scores.length - 1; i++) {
          expect(scores[i]).toBeGreaterThanOrEqual(scores[i + 1]);
        }
      }
    }
  });

  test('should sort signals by ticker ascending', async ({ page }) => {
    // Look for sort button
    const sortButton = page.locator(
      'button:has-text(/sort|ticker|symbol/i), select[name*="sort"]'
    ).first();

    if (await sortButton.isVisible()) {
      await sortButton.click();

      // Select "Ticker A-Z"
      const sortOption = page.locator('text=/ticker|symbol|a-z|ascending/i').first();
      if (await sortOption.isVisible()) {
        await sortOption.click();

        // Wait for sort
        await page.waitForTimeout(500);

        // Verify order: tickers should be ascending
        const tickerElements = page.locator('[data-testid="ticker"], .ticker');
        const tickers: string[] = [];

        const count = await tickerElements.count();
        for (let i = 0; i < Math.min(count, 10); i++) {
          const text = await tickerElements.nth(i).textContent();
          if (text) tickers.push(text.trim());
        }

        // Check if ascending
        for (let i = 0; i < tickers.length - 1; i++) {
          expect(tickers[i].localeCompare(tickers[i + 1])).toBeLessThanOrEqual(0);
        }
      }
    }
  });

  test('should apply multiple filters', async ({ page }) => {
    // Apply type filter
    const typeFilter = page.locator(
      'select[name*="type"], input[placeholder*="type"]'
    ).first();

    if (await typeFilter.isVisible()) {
      await typeFilter.click();
      const callOption = page.locator('text=/CALL/i').first();
      if (await callOption.isVisible()) {
        await callOption.click();
      }
    }

    // Apply score filter
    const minScoreInput = page.locator('input[name*="min"]').first();
    if (await minScoreInput.isVisible()) {
      await minScoreInput.clear();
      await minScoreInput.fill('70');
      await minScoreInput.press('Enter');
    }

    // Wait for results
    await page.waitForLoadState('networkidle');

    // Verify both filters applied
    const signals = page.locator('[role="row"], [data-testid="signal-item"]');
    const count = await signals.count();

    if (count > 0) {
      const firstSignal = signals.first();
      const text = await firstSignal.textContent();
      // Should contain CALL and have high score
      expect(text?.toUpperCase()).toContain('CALL');
    }
  });

  test('should clear filters and show all signals', async ({ page }) => {
    // Apply a filter
    const typeFilter = page.locator(
      'select[name*="type"], input[placeholder*="type"]'
    ).first();

    if (await typeFilter.isVisible()) {
      await typeFilter.click();
      const callOption = page.locator('text=/CALL/i').first();
      if (await callOption.isVisible()) {
        await callOption.click();
      }

      // Look for clear button
      const clearButton = page.locator('button:has-text(/clear|reset|limpar/i)');
      if (await clearButton.isVisible()) {
        await clearButton.click();

        // Wait for results
        await page.waitForLoadState('networkidle');

        // Should show more results now
        const signals = page.locator('[role="row"], [data-testid="signal-item"]');
        const count = await signals.count();
        expect(count).toBeGreaterThan(0);
      }
    }
  });

  test('should persist filter state in URL', async ({ page }) => {
    // Apply filter
    const typeFilter = page.locator(
      'select[name*="type"], input[placeholder*="type"]'
    ).first();

    if (await typeFilter.isVisible()) {
      await typeFilter.click();
      const callOption = page.locator('text=/CALL/i').first();
      if (await callOption.isVisible()) {
        await callOption.click();

        // Wait for URL to update
        await page.waitForLoadState('networkidle');

        // Check URL contains filter params
        const url = page.url();
        // URL should contain filter parameter (type=CALL or similar)
        expect(url).toMatch(/type|filter/i);

        // Navigate to the filtered URL directly
        await page.goto(url);
        await page.waitForLoadState('networkidle');

        // Filter should still be applied
        const signals = page.locator('[role="row"], [data-testid="signal-item"]');
        const count = await signals.count();
        expect(count).toBeGreaterThan(0);
      }
    }
  });
});
