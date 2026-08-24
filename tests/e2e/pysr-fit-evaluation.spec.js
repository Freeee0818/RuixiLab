import { expect, test } from '@playwright/test'
import { allowAccess } from './helpers/access.js'


const pixel = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M/wHwAF/gL+XK1LAAAAAElFTkSuQmCC'

test('PySR result explains numerical evidence and physical-review boundary', async ({ page }) => {
  await allowAccess(page)
  const browserErrors = []
  page.on('console', (message) => {
    if (message.type() === 'error') browserErrors.push(message.text())
  })
  page.on('pageerror', (error) => browserErrors.push(error.message))

  await page.route('**/tasks', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback()
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true, task_id: 'fit-evaluation-e2e' }),
    })
  })
  await page.route('**/tasks/fit-evaluation-e2e', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        task_id: 'fit-evaluation-e2e',
        status: 'completed',
        status_message: '分析完成',
        progress: 100,
        result: {
          equations: [{
            equation: '位移 = 2.01 * 时间 + 0.03',
            complexity: 5,
            score: 0.98,
            loss: 0.0025,
            is_best: true,
            rationality: {
              method: 'in_sample_diagnostics_v1',
              status: 'strong',
              label: '样本内拟合较强',
              metrics: { r2: 0.992, nrmse: 0.031, mae: 0.045, coverage: 1 },
              evidence: ['样本内 R²=0.992，解释度较高', '归一化 RMSE=0.031，相对观测范围较小'],
              risks: ['样本量仅 12，结论稳定性有限'],
              boundary: '仅评价观测样本内的数值拟合；量纲一致性、外推稳定性、因果关系与物理机制仍需人工核验。',
            },
          }],
          fitting_plot: pixel,
          individual_plots: [{ model_index: 1, plot: pixel }],
        },
      }),
    })
  })

  await page.setViewportSize({ width: 1536, height: 1100 })
  await page.request.get('/', { timeout: 60_000 })
  await page.goto('/analysis', { waitUntil: 'domcontentloaded', timeout: 60_000 })
  await page.getByRole('button', { name: '加载示例' }).click()
  await page.getByRole('button', { name: '使用为当前数据' }).click()
  await page.getByRole('button', { name: '开始分析' }).click()
  await expect(page.getByText('样本内拟合较强').first()).toBeVisible()
  await page.getByText('方程 1', { exact: true }).click()

  await expect(page.getByRole('heading', { name: '拟合合理性评价' })).toBeVisible()
  await expect(page.getByText('0.992', { exact: true })).toBeVisible()
  await expect(page.getByText('100.0%', { exact: true })).toBeVisible()
  await expect(page.getByText(/量纲一致性、外推稳定性/)).toBeVisible()
  expect(browserErrors).toEqual([])
  await page.screenshot({ path: 'test-results/pysr-fit-evaluation-desktop.png', fullPage: true })

  await page.setViewportSize({ width: 390, height: 844 })
  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth
  )
  expect(hasHorizontalOverflow).toBe(false)
  await expect(page.getByRole('heading', { name: '拟合合理性评价' })).toBeVisible()
  await page.screenshot({ path: 'test-results/pysr-fit-evaluation-mobile.png', fullPage: true })
})
