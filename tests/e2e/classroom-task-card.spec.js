import { expect, test } from '@playwright/test'
import { allowAccess } from './helpers/access.js'

test('Agent-created PySR task stays on its chat page and refreshes to completion', async ({ page }) => {
  await allowAccess(page)
  let polls = 0
  const taskId = '11111111-2222-4333-8444-555555555555'
  const browserErrors = []
  page.on('console', (message) => {
    if (message.type() === 'error') browserErrors.push(message.text())
  })
  page.on('pageerror', (error) => browserErrors.push(error.message))

  await page.route('**/analyze_experiment', async (route) => {
    const body = [
      'data: {"type":"agent","phase":"started","run_id":"agent-e2e","model":"fake-model","skill":"symbolic_regression","sequence":1}',
      '',
      'data: {"type":"tool","phase":"started","tool":"start_symbolic_regression","call_id":"call-e2e","run_id":"agent-e2e","round":1,"arguments":{"niterations":100},"model":"fake-model","skill":"symbolic_regression","sequence":2}',
      '',
      `data: {"type":"tool","phase":"finished","tool":"start_symbolic_regression","call_id":"call-e2e","run_id":"agent-e2e","round":1,"arguments":{"niterations":100},"ok":true,"duration_ms":8,"task_id":"${taskId}","status":"submitted","model":"fake-model","skill":"symbolic_regression","sequence":3}`,
      '',
      'data: {"content":"拟合任务已经提交，页面会自动跟踪计算结果。"}',
      '',
    ].join('\n')
    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream; charset=utf-8',
      headers: { 'cache-control': 'no-cache' },
      body,
    })
  })

  await page.route(`**/tasks/${taskId}`, async (route) => {
    polls += 1
    const completed = polls >= 2
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        task_id: taskId,
        status: completed ? 'completed' : 'running',
        status_message: completed ? '分析完成' : 'PySR worker 已启动',
        progress: completed ? 100 : 50,
        result: completed ? {
          equations: [{ equation: 'y = 2.0 * x', score: 0.99, complexity: 3 }],
          individual_plots: [],
        } : null,
      }),
    })
  })

  // A first root GET lets Vite finish its cold dependency transform before the
  // SPA history route is opened (not needed against the production dist).
  await page.request.get('/', { timeout: 60_000 })
  await page.goto('/analysis', { waitUntil: 'domcontentloaded', timeout: 60_000 })
  await page.getByPlaceholder('询问实验现象、公式，或让 Agent 调用工具…').fill('请用当前数据开始 PySR 拟合')
  await page.getByRole('button', { name: '发送' }).click()

  const card = page.locator('.task-card').filter({ hasText: taskId })
  await expect(page.getByText('Agent 工具活动')).toBeVisible()
  await expect(page.getByText('提交 PySR 拟合任务', { exact: true })).toBeVisible()
  await expect(page.getByText('第 1 轮')).toBeVisible()
  await page.getByText('查看审计信息').click()
  await expect(page.getByText('agent-e2e')).toBeVisible()
  await expect(page.getByText(/"niterations": 100/)).toBeVisible()
  await expect(card).toBeVisible()
  await expect(card).toContainText('已完成', { timeout: 10_000 })
  await expect(card).toContainText('y = 2.0 * x')
  expect(browserErrors).toEqual([])
  await page.screenshot({ path: 'test-results/classroom-task-card.png', fullPage: true })
})
