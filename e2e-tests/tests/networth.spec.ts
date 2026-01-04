import { test, expect } from '@playwright/test';

test.describe('Net Worth Feature - Critical User Journeys', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/networth');
  });

  test('complete workflow: create asset account, set balance, view net worth', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Net Worth Tracker');

    const accountName = `Assets:Bank:Checking${Date.now()}`;

    await page.getByRole('button', { name: 'Add Account' }).click();
    await page.getByPlaceholder(/e.g., Assets:Bank:Savings/).fill(accountName);
    await page.locator('select').first().selectOption('USD');
    await page.getByPlaceholder('Add notes about this account...').fill('My checking account');
    await page.getByRole('button', { name: 'Create Account' }).click();

    await page.waitForTimeout(1000);

    await expect(page.getByText(accountName)).toBeVisible();

    const row = page.locator('tr').filter({ hasText: accountName });
    await row.getByRole('button', { name: 'Set Balance' }).click();

    await page.locator('input[type="number"]').fill('10000');
    await page.getByRole('button', { name: 'Update Balance' }).click();

    await page.waitForTimeout(1500);

    const updatedRow = page.locator('tr').filter({ hasText: accountName });
    await expect(updatedRow.locator('td').nth(3)).toContainText('10,000');

    const summarySection = page.locator('.bg-white').filter({ hasText: 'Net Worth Summary' });
    const usdSummary = summarySection.locator('.border.rounded-lg').filter({ hasText: 'USD' });

    await expect(usdSummary).toBeVisible();
    await expect(usdSummary.getByText(/Assets:/)).toBeVisible();
    await expect(usdSummary.getByText(/Net Worth:/)).toBeVisible();
  });

  test('complete workflow: create liability account and view negative impact on net worth', async ({ page }) => {
    const accountName = `Liabilities:CreditCard:Visa${Date.now()}`;

    await page.getByRole('button', { name: 'Add Account' }).click();
    await page.getByPlaceholder(/e.g., Assets:Bank:Savings/).fill(accountName);
    await page.locator('select').first().selectOption('USD');
    await page.getByRole('button', { name: 'Create Account' }).click();

    await page.waitForTimeout(1000);

    await expect(page.getByText(accountName)).toBeVisible();
    const row = page.locator('tr').filter({ hasText: accountName });
    await expect(row.locator('.bg-red-100')).toContainText('Liabilities');

    await row.getByRole('button', { name: 'Set Balance' }).click();
    await page.locator('input[type="number"]').fill('5000');
    await page.getByRole('button', { name: 'Update Balance' }).click();

    await page.waitForTimeout(1500);

    const summarySection = page.locator('.bg-white').filter({ hasText: 'Net Worth Summary' });
    const usdSummary = summarySection.locator('.border.rounded-lg').filter({ hasText: 'USD' });

    await expect(usdSummary).toBeVisible();
    await expect(usdSummary.getByText(/Liabilities:/)).toBeVisible();
  });

  test('multi-currency workflow: create accounts in different currencies', async ({ page }) => {
    const timestamp = Date.now();

    await page.getByRole('button', { name: 'Add Account' }).click();
    await page.getByPlaceholder(/e.g., Assets:Bank:Savings/).fill(`Assets:Bank:USD${timestamp}`);
    await page.locator('select').first().selectOption('USD');
    await page.getByRole('button', { name: 'Create Account' }).click();
    await page.waitForTimeout(1000);

    await page.getByRole('button', { name: 'Add Account' }).click();
    await page.getByPlaceholder(/e.g., Assets:Bank:Savings/).fill(`Assets:Bank:INR${timestamp}`);
    await page.locator('select').first().selectOption('INR');
    await page.getByRole('button', { name: 'Create Account' }).click();
    await page.waitForTimeout(1000);

    await expect(page.getByText(`Assets:Bank:USD${timestamp}`)).toBeVisible();
    await expect(page.getByText(`Assets:Bank:INR${timestamp}`)).toBeVisible();

    const row1 = page.locator('tr').filter({ hasText: `Assets:Bank:USD${timestamp}` });
    await row1.getByRole('button', { name: 'Set Balance' }).click();
    await page.locator('input[type="number"]').fill('1000');
    await page.getByRole('button', { name: 'Update Balance' }).click();
    await page.waitForTimeout(1000);

    const row2 = page.locator('tr').filter({ hasText: `Assets:Bank:INR${timestamp}` });
    await row2.getByRole('button', { name: 'Set Balance' }).click();
    await page.locator('input[type="number"]').fill('50000');
    await page.getByRole('button', { name: 'Update Balance' }).click();
    await page.waitForTimeout(1500);

    const summarySection = page.locator('.bg-white').filter({ hasText: 'Net Worth Summary' });
    await expect(summarySection.locator('.border.rounded-lg').filter({ hasText: 'USD' })).toBeVisible();
    await expect(summarySection.locator('.border.rounded-lg').filter({ hasText: 'INR' })).toBeVisible();
  });

  test('navigation and page load', async ({ page }) => {
    await page.goto('/');

    const networthLink = page.getByRole('link', { name: /Net Worth/i });
    if (await networthLink.isVisible()) {
      await networthLink.click();
      await expect(page).toHaveURL(/.*networth/);
    } else {
      await page.goto('/networth');
    }

    await expect(page.locator('h1')).toContainText('Net Worth Tracker');
    await expect(page.getByRole('button', { name: 'Add Account' })).toBeVisible();
    await expect(page.getByText('Net Worth Summary')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Accounts' })).toBeVisible();
  });
});
