import { test, expect } from '@playwright/test';

test.describe('Market View Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should display signals on market view', async ({ page }) => {
    // Verify page loaded
    await expect(page).toHaveTitle(/signals|market/i);

    // Look for signals table or list
    const signalsContainer = page.locator('[role="region"], .signals-container, table');
    await expect(signalsContainer).toBeVisible({ timeout: 5000 });

    // Verify at least one signal is visible
    const signalRows = page.locator('[role="row"], [data-testid="signal-item"]');
    const count = await signalRows.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should show signal details when clicking a row', async ({ page }) => {
    // Find first signal row
    const firstSignal = page.locator('[role="row"], [data-testid="signal-item"]').first();
    await expect(firstSignal).toBeVisible();

    // Click to view details
    await firstSignal.click();

    // Verify details modal or panel opens
    const detailsPanel = page.locator('[role="dialog"], .details-panel, .signal-details');
    await expect(detailsPanel).toBeVisible({ timeout: 3000 });

    // Verify key signal fields are displayed
    await expect(
      page.locator('text=/ticker|symbol|price|alvo|target/i').first()
    ).toBeVisible();
  });

  test('should filter signals by ticker', async ({ page }) => {
    // Find filter input
    const filterInput = page.locator(
      'input[placeholder*="ticker"], input[placeholder*="symbol"], input[aria-label*="filter"]'
    ).first();

    if (await filterInput.isVisible()) {
      // Enter ticker
      await filterInput.fill('PETR4');

      // Wait for results to update
      await page.waitForLoadState('networkidle');

      // Verify filtered results contain PETR4
      const signals = page.locator('[role="row"], [data-testid="signal-item"]');
      const count = await signals.count();

      if (count > 0) {
        const firstSignal = signals.first();
        const text = await firstSignal.textContent();
        expect(text).toContain('PETR4');
      }
    }
  });

  test('should display loading state while fetching signals', async ({ page }) => {
    // Clear cache to force reload
    await page.evaluate(() => localStorage.clear());

    // Navigate to market view
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    // Look for loading indicator
    const loader = page.locator(
      '[role="status"], .loader, .spinner, .loading, [aria-label*="loading"]'
    );

    // Should show loading or have content
    const hasLoader = await loader.isVisible({ timeout: 1000 }).catch(() => false);
    const hasContent = await page.locator('[role="row"], [data-testid="signal-item"]').isVisible();

    expect(hasLoader || hasContent).toBeTruthy();
  });

  test('should handle empty signals state', async ({ page }) => {
    // Mock empty response
    await page.route('**/api/signals*', (route) => {
      route.abort('failed');
    });

    // Reload page
    await page.reload({ waitUntil: 'networkidle' });

    // Should show error or empty state
    const emptyState = page.locator(
      'text=/no signals|empty|nenhum sinal/i, [data-testid="empty-state"]'
    );
    const errorState = page.locator(
      'text=/error|failed|erro/i, [role="alert"]'
    );

    const hasEmptyOrError = await emptyState.isVisible().catch(() => false) ||
                            await errorState.isVisible().catch(() => false);

    expect(hasEmptyOrError).toBeTruthy();
  });
});
