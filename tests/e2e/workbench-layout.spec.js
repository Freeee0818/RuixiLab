import { expect, test } from '@playwright/test'

async function openWorkbench(page) {
  await page.request.get('/', { timeout: 60_000 })
  await page.goto('/analysis', { waitUntil: 'domcontentloaded', timeout: 60_000 })
  await expect(page.getByRole('heading', { name: '实验分析工作台' })).toBeVisible()
}

test('desktop workbench gives analysis and Agent equal width', async ({ page }) => {
  const browserErrors = []
  page.on('console', (message) => {
    if (message.type() === 'error') browserErrors.push(message.text())
  })
  page.on('pageerror', (error) => browserErrors.push(error.message))

  await page.setViewportSize({ width: 1536, height: 1024 })
  await openWorkbench(page)

  const analysisBox = await page.locator('.analyzer-panel').boundingBox()
  const agentBox = await page.locator('.assistant-panel').boundingBox()
  expect(analysisBox).not.toBeNull()
  expect(agentBox).not.toBeNull()
  expect(Math.abs(analysisBox.width - agentBox.width)).toBeLessThanOrEqual(2)
  await expect(page.getByRole('heading', { name: '实验分析', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Agent 助教', exact: true })).toBeVisible()
  expect(browserErrors).toEqual([])

  await page.screenshot({ path: 'test-results/guidelab-workbench-desktop.png', fullPage: false })
})

test('mobile workbench switches between two equal tabs without overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await openWorkbench(page)

  await expect(page.locator('.analyzer-panel')).toBeVisible()
  await expect(page.locator('.assistant-panel')).toBeHidden()
  await page.getByRole('button', { name: 'Agent 助教', exact: true }).click()
  await expect(page.locator('.assistant-panel')).toBeVisible()
  await expect(page.locator('.analyzer-panel')).toBeHidden()

  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth
  )
  expect(hasHorizontalOverflow).toBe(false)
  await page.screenshot({ path: 'test-results/guidelab-workbench-mobile.png', fullPage: false })
})
