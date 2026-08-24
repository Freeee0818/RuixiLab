export async function allowAccess(page, { admin = false } = {}) {
  await page.route('**/auth/session', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        access_control_enabled: true,
        authenticated: true,
        source: 'account',
        role: admin ? 'admin' : 'student',
        username: admin ? 'teacher-admin' : 'student-01',
        display_name: admin ? '教学管理员' : '测试学生',
        email: admin ? 'wangcheng308@bupt.edu.cn' : 'student@bupt.edu.cn',
        is_admin: admin,
        admin_email: 'wangcheng308@bupt.edu.cn',
        client_ip: '203.0.113.10',
      }),
    })
  })
}
