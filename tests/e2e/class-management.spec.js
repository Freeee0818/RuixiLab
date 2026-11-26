import { expect, test } from '@playwright/test'
import { allowAccess } from './helpers/access'

async function adminApi(page) {
  await allowAccess(page, { admin: true })
  const state = {
    classes: [{ id: 1, name: '测试物理实验班', student_count: 1, created_by: 'teacher-admin' }],
    accounts: [
      { username: 'teacher-admin', display_name: '教学管理员', is_admin: true, enabled: true, class_id: null },
      { username: 'student-01', display_name: '测试学生甲', is_admin: false, enabled: true, class_id: 1 },
      { username: 'student-02', display_name: '测试学生乙', is_admin: false, enabled: true, class_id: null },
    ],
    writes: [],
  }
  await page.route('**/auth/admin/**', async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname
    const method = request.method()
    const body = method === 'GET' ? null : request.postDataJSON()
    let response
    let status = 200
    if (method !== 'GET') state.writes.push({ path, method, body })
    if (path.endsWith('/classes') && method === 'GET') {
      response = { classes: state.classes.map((item) => ({ ...item, student_count: state.accounts.filter((a) => a.class_id === item.id).length })) }
    } else if (path.endsWith('/classes') && method === 'POST') {
      const classroom = { id: state.classes.length + 1, name: body.name, student_count: 0, created_by: 'teacher-admin' }
      state.classes.push(classroom)
      response = { class: classroom }
      status = 201
    } else if (/\/classes\/\d+\/accounts$/.test(path)) {
      const id = Number(path.split('/').at(-2))
      response = { accounts: state.accounts.filter((item) => item.class_id === id) }
    } else if (path.endsWith('/accounts') && method === 'GET') {
      response = { accounts: state.accounts }
    } else if (path.endsWith('/accounts') && method === 'POST') {
      const { password: _password, ...account } = body
      state.accounts.push({ ...account, enabled: true })
      response = { account: state.accounts.at(-1) }
      status = 201
    } else if (method === 'PATCH') {
      const account = state.accounts.find((item) => item.username === decodeURIComponent(path.split('/').at(-1)))
      const { password: _password, ...publicFields } = body
      Object.assign(account, publicFields)
      response = { account }
    } else {
      return route.fulfill({ status: 404, contentType: 'application/json', body: '{}' })
    }
    return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(response) })
  })
  return state
}

test('administrator creates class and opens its filtered student accounts', async ({ page }) => {
  const state = await adminApi(page)
  await page.goto('/admin/classes')
  await expect(page.getByRole('heading', { name: '班级管理', exact: true })).toBeVisible()
  const roster = page.getByRole('region', { name: '班级学生名单' })
  await expect(roster.getByText('student-01', { exact: true })).toBeVisible()
  await expect(roster.getByText('student-02', { exact: true })).toHaveCount(0)
  await page.getByRole('link', { name: '管理本班账号' }).click()
  await expect(page).toHaveURL(/\/admin\/access\?class_id=1$/)
  await expect(page.getByText('student-01', { exact: true })).toBeVisible()
  await expect(page.getByText('student-02', { exact: true })).toHaveCount(0)
  await page.goto('/admin/classes')
  await page.getByRole('button', { name: '创建班级', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: '创建教学班级' })
  await dialog.getByLabel('班级名称').fill('新建测试班')
  await dialog.getByRole('button', { name: '确认创建' }).click()
  await expect(page.getByRole('heading', { name: '新建测试班', exact: true })).toBeVisible()
  expect(state.classes.at(-1).name).toBe('新建测试班')
})

test('create and reset accept eight characters verbatim and reject invalid lengths', async ({ page }) => {
  const state = await adminApi(page)
  await page.goto('/admin/access')
  await page.getByRole('button', { name: '创建账号', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: '创建邀请账号' })
  await dialog.getByLabel('账号', { exact: true }).fill('eight-char')
  await dialog.getByLabel('临时密码').fill('1234567')
  await dialog.getByRole('button', { name: '创建并启用' }).click()
  await expect(page.getByText('请填写账号，且临时密码为 8–256 个字符')).toBeVisible()
  expect(state.writes).toHaveLength(0)
  await dialog.getByLabel('临时密码').fill('x'.repeat(257))
  await dialog.getByRole('button', { name: '创建并启用' }).click()
  expect(state.writes).toHaveLength(0)
  await dialog.getByLabel('临时密码').fill(' 0Ab!xy ')
  await dialog.getByRole('button', { name: '创建并启用' }).click()
  await expect(dialog).toBeHidden()
  expect(state.writes[0].body.password).toBe(' 0Ab!xy ')
  const row = page.getByRole('row').filter({ hasText: 'eight-char' })
  await row.getByRole('button', { name: '重置密码' }).click()
  const reset = page.getByRole('dialog', { name: '重置 eight-char 的密码' })
  await reset.locator('input').fill('1234567')
  await reset.getByRole('button', { name: '确认重置' }).click()
  await expect(reset.getByText('密码需为 8–256 个字符')).toBeVisible()
  expect(state.writes).toHaveLength(1)
  await reset.locator('input').fill('😀'.repeat(8))
  await reset.getByRole('button', { name: '确认重置' }).click()
  await expect(reset).toBeHidden()
  expect(state.writes[1].body.password).toBe('😀'.repeat(8))
})

test('administrator assigns and clears class membership without resetting password', async ({ page }) => {
  const state = await adminApi(page)
  await page.goto('/admin/access')
  const row = page.getByRole('row').filter({ hasText: 'student-02' })
  await row.getByRole('button', { name: '设置班级' }).click()
  const dialog = page.getByRole('dialog', { name: '设置班级归属' })
  await dialog.locator('.el-select__wrapper').click()
  await page.getByRole('option', { name: '测试物理实验班' }).click()
  await dialog.getByRole('button', { name: '保存归属' }).click()
  await expect(dialog).toBeHidden()
  await expect(row.getByText('测试物理实验班')).toBeVisible()
  expect(state.writes[0].body).toEqual({ class_id: 1 })
  await row.getByRole('button', { name: '设置班级' }).click()
  await dialog.locator('.el-select__wrapper').hover()
  await dialog.locator('.el-select__clear').click()
  await dialog.getByRole('button', { name: '保存归属' }).click()
  await expect(dialog).toBeHidden()
  await expect(row.getByText('未分班')).toBeVisible()
  expect(state.writes[1].body).toEqual({ class_id: null })
})

test('class management fits mobile width', async ({ page }) => {
  await adminApi(page)
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/admin/classes')
  await expect(page.getByRole('heading', { name: '班级管理', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: '测试物理实验班', exact: true })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(false)
})

test('student cannot enter class management or see admin navigation', async ({ page }) => {
  await allowAccess(page)
  await page.goto('/admin/classes')
  await expect(page).toHaveURL('/')
  await expect(page.getByRole('link', { name: '班级管理', exact: true })).toHaveCount(0)
})
