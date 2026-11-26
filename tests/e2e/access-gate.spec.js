import { expect, test } from '@playwright/test'

const guestSession = {
  access_control_enabled: true,
  authenticated: false,
  source: 'none',
  role: 'guest',
  username: '',
  display_name: '',
  email: '',
  is_admin: false,
  admin_email: 'wangcheng308@bupt.edu.cn',
  client_ip: '198.51.100.24',
}

test('uninvited visitor is redirected to account request page', async ({ page }) => {
  await page.setViewportSize({ width: 1536, height: 1024 })
  await page.route('**/auth/session', (route) => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(guestSession),
  }))

  await page.goto('/analysis', { waitUntil: 'commit' })
  await expect(page).toHaveURL(/\/access\?redirect=/, { timeout: 60_000 })
  await expect(page.getByRole('heading', { name: '睿析实验', exact: true })).toBeVisible()
  await expect(page.getByText('wangcheng308@bupt.edu.cn')).toBeVisible()
  await expect(page.getByRole('link', { name: '发送申请邮件' })).toHaveAttribute('href', /^mailto:wangcheng308@bupt\.edu\.cn/)
  await expect(page.getByText('当前 IP：198.51.100.24')).toBeVisible()
  await page.screenshot({ path: 'test-results/guidelab-access-login.png', fullPage: true })

  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByRole('heading', { name: '请登录', exact: true })).toBeVisible()
  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth
  )
  expect(hasHorizontalOverflow).toBe(false)
  await page.screenshot({ path: 'test-results/guidelab-access-login-mobile.png', fullPage: true })
})

test('invited account logs in and returns to requested page', async ({ page }) => {
  let loggedIn = false
  await page.route('**/auth/session', (route) => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(loggedIn ? {
      ...guestSession,
      authenticated: true,
      source: 'account',
      role: 'student',
      username: 'student-01',
      display_name: '测试学生',
    } : guestSession),
  }))
  await page.route('**/auth/login', (route) => {
    loggedIn = true
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true, username: 'student-01', role: 'student' }),
    })
  })

  await page.goto('/access?redirect=/analysis')
  await page.getByLabel('账号或邮箱').fill('student-01')
  await page.getByLabel('密码', { exact: true }).fill('Student-Password-2026!')
  await page.getByRole('button', { name: '进入教学平台' }).click()
  await expect(page).toHaveURL('/analysis')
  await expect(page.getByRole('heading', { name: '实验分析工作台' })).toBeVisible()
})

test('administrator can open browser account management', async ({ page }) => {
  await page.route('**/auth/admin/classes', (route) => route.fulfill({
    contentType: 'application/json', body: JSON.stringify({ classes: [] }),
  }))
  await page.route('**/auth/session', (route) => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      ...guestSession,
      authenticated: true,
      source: 'account',
      role: 'admin',
      username: 'teacher-admin',
      display_name: '教学管理员',
      is_admin: true,
    }),
  }))
  await page.route('**/auth/admin/accounts', (route) => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      accounts: [{
        username: 'teacher-admin',
        display_name: '教学管理员',
        email: 'wangcheng308@bupt.edu.cn',
        is_admin: true,
        enabled: true,
        last_login_at: null,
      }],
    }),
  }))

  await page.goto('/admin/access')
  await expect(page.getByRole('heading', { name: '邀请账号' })).toBeVisible()
  await expect(page.getByText('teacher-admin')).toBeVisible()
  await page.getByRole('button', { name: '创建账号' }).click()
  await expect(page.getByRole('dialog', { name: '创建邀请账号' })).toBeVisible()
  await page.screenshot({ path: 'test-results/guidelab-access-admin.png', fullPage: true })
})
