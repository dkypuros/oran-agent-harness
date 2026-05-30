const { test, expect } = require('@playwright/test');

test('Start button triggers visible demo flow', async ({ page }) => {
  await page.goto('http://127.0.0.1:3000', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: 'Start' }).click();
  await expect(page.getByText('Running')).toBeVisible();
  await expect(page.getByText('Procedure Analysis Mode')).toBeVisible();
  await expect(page.getByText('Start pressed: switched to Procedure Analysis and running demo flow')).toBeVisible();
  await expect(page.getByText('AI Factory Playbook')).toBeVisible();
});
