<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { accessState, createAccessAccount, listAccessAccounts, listAccessClasses, updateAccessAccount } from '@/utils/access'

const accounts = ref([])
const classes = ref([])
const route = useRoute()
const classFilter = ref(String(route.query.class_id || 'all'))
const membershipVisible = ref(false)
const membershipSaving = ref(false)
const membership = reactive({ username: '', class_id: null })
const loading = ref(false)
const dialogVisible = ref(false)
const saving = ref(false)
const revealPassword = ref('')
const form = reactive({ username: '', display_name: '', email: '', password: '', is_admin: false, class_id: null })
const enabledCount = computed(() => accounts.value.filter((item) => item.enabled).length)
const filteredAccounts = computed(() => accounts.value.filter((item) => {
  if (classFilter.value === 'all') return true
  if (classFilter.value === 'unassigned') return !item.is_admin && item.class_id == null
  return item.class_id === Number(classFilter.value)
}))
watch(() => route.query.class_id, (value) => { classFilter.value = String(value || 'all') })
watch(() => form.is_admin, (value) => { if (value) form.class_id = null })

function className(classId) {
  return classes.value.find((item) => item.id === classId)?.name || '未分班'
}

function validPassword(value) {
  const length = Array.from(value || '').length
  return length >= 8 && length <= 256
}

function generatePassword() {
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#%'
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  return Array.from(bytes, (value) => alphabet[value % alphabet.length]).join('')
}

function formatTimestamp(_row, _column, value) {
  if (!value) return '尚未登录'
  return new Date(value * 1000).toLocaleString('zh-CN', { hour12: false })
}

async function loadAccounts() {
  loading.value = true
  try {
    const [payload, classPayload] = await Promise.all([listAccessAccounts(), listAccessClasses()])
    accounts.value = payload.accounts || []
    classes.value = classPayload.classes || []
  } catch (error) {
    ElMessage.error(error.message || '账号列表加载失败')
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  Object.assign(form, { username: '', display_name: '', email: '', password: generatePassword(), is_admin: false, class_id: null })
  dialogVisible.value = true
}

async function createAccount() {
  if (!form.username.trim() || !validPassword(form.password)) {
    ElMessage.warning('请填写账号，且临时密码为 8–256 个字符')
    return
  }
  saving.value = true
  try {
    await createAccessAccount({ ...form, username: form.username.trim(), class_id: form.is_admin ? null : (form.class_id ?? null) })
    revealPassword.value = form.password
    dialogVisible.value = false
    await loadAccounts()
    ElMessage.success('账号已创建，请安全发送临时密码')
  } catch (error) {
    ElMessage.error(error.message || '创建失败')
  } finally {
    saving.value = false
  }
}

async function toggleEnabled(account) {
  try {
    await updateAccessAccount(account.username, { enabled: !account.enabled })
    await loadAccounts()
    ElMessage.success(account.enabled ? '账号已停用' : '账号已启用')
  } catch (error) {
    ElMessage.error(error.message || '操作失败')
  }
}

async function resetPassword(account) {
  try {
    const { value } = await ElMessageBox.prompt(
      '新密码会立即生效，请通过安全渠道发送给用户。',
      `重置 ${account.username} 的密码`,
      {
        inputValue: generatePassword(),
        inputType: 'password',
        inputValidator: (value) => validPassword(value) || '密码需为 8–256 个字符',
        confirmButtonText: '确认重置',
        cancelButtonText: '取消',
      },
    )
    await updateAccessAccount(account.username, { password: value })
    revealPassword.value = value
    ElMessage.success('密码已重置')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(error.message || '重置失败')
  }
}

function openMembership(account) {
  Object.assign(membership, { username: account.username, class_id: account.class_id ?? null })
  membershipVisible.value = true
}

async function saveMembership() {
  membershipSaving.value = true
  try {
    await updateAccessAccount(membership.username, { class_id: membership.class_id ?? null })
    membershipVisible.value = false
    await loadAccounts()
    ElMessage.success('班级归属已更新')
  } catch (error) {
    ElMessage.error(error.message || '班级归属更新失败')
  } finally {
    membershipSaving.value = false
  }
}

onMounted(loadAccounts)
</script>

<template>
  <div class="admin-page">
    <header class="admin-heading">
      <div>
        <div class="eyebrow">教学平台·访问管理</div>
        <h1>邀请账号</h1>
        <p>审核邮件申请后，在这里为师生创建或停用账号。</p>
      </div>
      <el-button type="primary" size="large" @click="openCreateDialog">创建账号</el-button>
    </header>

    <section class="summary-grid">
      <article><strong>{{ accounts.length }}</strong><span>全部账号</span></article>
      <article><strong>{{ enabledCount }}</strong><span>已启用</span></article>
      <article><strong>{{ accounts.filter((item) => item.is_admin).length }}</strong><span>管理员</span></article>
      <article class="mail-summary"><strong>申请邮箱</strong><span>{{ accessState.adminEmail }}</span></article>
    </section>

    <el-alert v-if="revealPassword" class="password-alert" type="warning" :closable="true" show-icon @close="revealPassword = ''">
      <template #title>本次临时密码：<code>{{ revealPassword }}</code></template>
    </el-alert>

    <section class="accounts-panel">
      <div class="panel-heading">
        <div><h2>账号列表</h2><p>停用账号会阻止新的登录会话。</p></div>
        <div class="list-tools">
          <el-select v-model="classFilter" aria-label="按班级筛选" style="width: 220px">
            <el-option label="全部账号" value="all" />
            <el-option label="未分班学生" value="unassigned" />
            <el-option v-for="item in classes" :key="item.id" :label="item.name" :value="String(item.id)" />
          </el-select>
          <el-button @click="loadAccounts">刷新</el-button>
        </div>
      </div>
      <el-table v-loading="loading" :data="filteredAccounts" stripe empty-text="暂无账号">
        <el-table-column prop="username" label="账号" min-width="130" />
        <el-table-column label="用户" min-width="170">
          <template #default="{ row }"><div class="identity"><strong>{{ row.display_name || '未填写姓名' }}</strong><span>{{ row.email || '未填写邮箱' }}</span></div></template>
        </el-table-column>
        <el-table-column label="角色" width="105">
          <template #default="{ row }"><el-tag :type="row.is_admin ? 'danger' : 'info'">{{ row.is_admin ? '管理员' : '学生' }}</el-tag></template>
        </el-table-column>
        <el-table-column label="状态" width="95">
          <template #default="{ row }"><el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '启用' : '停用' }}</el-tag></template>
        </el-table-column>
        <el-table-column label="班级" min-width="210">
          <template #default="{ row }">{{ row.is_admin ? '—' : className(row.class_id) }}</template>
        </el-table-column>
        <el-table-column prop="last_login_at" label="最后登录" min-width="165" :formatter="formatTimestamp" />
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button v-if="!row.is_admin" link type="primary" @click="openMembership(row)">设置班级</el-button>
            <el-button link type="primary" @click="resetPassword(row)">重置密码</el-button>
            <el-button link :type="row.enabled ? 'danger' : 'success'" @click="toggleEnabled(row)">{{ row.enabled ? '停用' : '启用' }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog v-model="dialogVisible" title="创建邀请账号" width="min(92vw, 560px)" destroy-on-close>
      <el-form label-position="top">
        <div class="form-grid">
          <el-form-item label="账号"><el-input v-model="form.username" placeholder="学号、工号或英文名" /></el-form-item>
          <el-form-item label="姓名"><el-input v-model="form.display_name" placeholder="用于页面显示" /></el-form-item>
        </div>
        <el-form-item label="邮箱"><el-input v-model="form.email" type="email" placeholder="name@bupt.edu.cn" /></el-form-item>
        <el-form-item label="临时密码">
          <el-input v-model="form.password" show-password placeholder="8–256 个字符，保留原始空格与大小写" />
          <el-button class="generate-button" link type="primary" @click="form.password = generatePassword()">重新生成</el-button>
        </el-form-item>
        <el-form-item v-if="!form.is_admin" label="班级">
          <el-select v-model="form.class_id" clearable :value-on-clear="null" placeholder="暂不分班" style="width: 100%">
            <el-option v-for="item in classes" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-checkbox v-model="form.is_admin">设为管理员（可创建其他账号）</el-checkbox>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="createAccount">创建并启用</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="membershipVisible" title="设置班级归属" width="min(92vw, 480px)" destroy-on-close>
      <el-form label-position="top">
        <p>{{ membership.username }}</p>
        <el-form-item label="学生班级">
          <el-select v-model="membership.class_id" clearable :value-on-clear="null" placeholder="未分班（清空可移出班级）" style="width: 100%">
            <el-option v-for="item in classes" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="membershipVisible = false">取消</el-button>
        <el-button type="primary" :loading="membershipSaving" @click="saveMembership">保存归属</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.admin-page { width: min(1240px, calc(100% - 48px)); margin: 0 auto; padding: 54px 0 80px; }
.admin-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 32px; }
.eyebrow { margin-bottom: 8px; color: var(--gl-primary); font-size: 13px; font-weight: 750; letter-spacing: .1em; }
h1 { margin: 0; font-size: 38px; letter-spacing: -.04em; }
.admin-heading p, .panel-heading p { margin: 10px 0 0; color: var(--gl-text-secondary); }
.summary-grid { display: grid; grid-template-columns: repeat(3, 1fr) minmax(270px, 1.5fr); gap: 14px; margin: 32px 0 20px; }
.summary-grid article { display: flex; min-height: 100px; padding: 20px 22px; flex-direction: column; justify-content: center; border: 1px solid var(--gl-border); border-radius: 12px; background: #fff; box-shadow: var(--gl-shadow); }
.summary-grid strong { font-size: 27px; }
.summary-grid span { margin-top: 5px; color: var(--gl-text-muted); font-size: 13px; }
.mail-summary strong { font-size: 14px; }
.mail-summary span { color: var(--gl-primary); font-weight: 650; }
.password-alert { margin-bottom: 20px; }
.password-alert code { margin-left: 7px; padding: 3px 7px; border-radius: 5px; background: rgba(140,90,0,.1); user-select: all; }
.accounts-panel { overflow: hidden; border: 1px solid var(--gl-border); border-radius: 14px; background: #fff; box-shadow: var(--gl-shadow); }
.panel-heading { display: flex; align-items: center; justify-content: space-between; padding: 22px 24px; border-bottom: 1px solid var(--gl-border); }
.panel-heading h2 { margin: 0; font-size: 20px; }
.panel-heading p { font-size: 13px; }
.identity { display: flex; flex-direction: column; gap: 3px; }
.identity span { color: var(--gl-text-muted); font-size: 12px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.generate-button { margin-top: 5px; }
.list-tools { display: flex; align-items: center; gap: 12px; }
@media (max-width: 650px) { .panel-heading { align-items: flex-start; flex-direction: column; gap: 14px; } .list-tools { width: 100%; flex-wrap: wrap; } }
@media (max-width: 850px) { .admin-page { width: min(100% - 28px, 1240px); padding-top: 34px; } .admin-heading { align-items: flex-start; flex-direction: column; } .summary-grid { grid-template-columns: 1fr 1fr; } }
@media (max-width: 520px) { .summary-grid, .form-grid { grid-template-columns: 1fr; } }
</style>
