<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createAccessClass, listAccessClasses, listAccessClassAccounts } from '@/utils/access'

const classes = ref([])
const members = ref([])
const selectedId = ref(null)
const loading = ref(false)
const membersLoading = ref(false)
const membersError = ref('')
const errorMessage = ref('')
const dialogVisible = ref(false)
const saving = ref(false)
const newName = ref('')
const selectedClass = computed(() => classes.value.find((item) => item.id === selectedId.value))
let memberRequest = 0

async function selectClass(classroom) {
  selectedId.value = classroom?.id ?? null
  members.value = []
  membersError.value = ''
  const request = ++memberRequest
  membersLoading.value = Boolean(classroom)
  if (!classroom) return
  try {
    const payload = await listAccessClassAccounts(classroom.id)
    if (request === memberRequest) members.value = payload.accounts || []
  } catch (error) {
    if (request === memberRequest) membersError.value = error.message || '学生名单加载失败'
  } finally {
    if (request === memberRequest) membersLoading.value = false
  }
}

async function loadClasses(preferredId = selectedId.value) {
  loading.value = true
  errorMessage.value = ''
  try {
    const payload = await listAccessClasses()
    classes.value = payload.classes || []
    await selectClass(classes.value.find((item) => item.id === preferredId) || classes.value[0])
  } catch (error) {
    errorMessage.value = error.message || '班级列表加载失败'
  } finally {
    loading.value = false
  }
}

function openCreate() {
  newName.value = ''
  dialogVisible.value = true
}

async function createClass() {
  const name = newName.value.trim()
  if (!name || Array.from(name).length > 128) {
    ElMessage.warning('班级名称需为 1–128 个字符')
    return
  }
  saving.value = true
  try {
    const payload = await createAccessClass(name)
    dialogVisible.value = false
    await loadClasses(payload.class.id)
    ElMessage.success('班级已创建，可前往账号管理添加学生')
  } catch (error) {
    ElMessage.error(error.message || '班级创建失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => loadClasses())
</script>

<template>
  <div class="class-page">
    <header class="page-heading">
      <div>
        <div class="eyebrow">教学平台·访问管理</div>
        <h1>班级管理</h1>
        <p>创建教学班级，查看学生名单与账号状态。</p>
      </div>
      <div class="actions">
        <el-button @click="loadClasses()">刷新</el-button>
        <el-button type="primary" size="large" @click="openCreate">创建班级</el-button>
      </div>
    </header>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" :closable="false" show-icon />

    <section class="panel" aria-label="教学班级">
      <div class="panel-heading"><h2>班级列表</h2><span>共 {{ classes.length }} 个班级</span></div>
      <el-table v-loading="loading" :data="classes" stripe empty-text="暂无班级，请先创建教学班级">
        <el-table-column prop="name" label="班级名称" min-width="240" />
        <el-table-column prop="student_count" label="学生人数" width="110" />
        <el-table-column prop="created_by" label="创建人" min-width="150" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }"><el-button link type="primary" @click="selectClass(row)">查看学生</el-button></template>
        </el-table-column>
      </el-table>
    </section>

    <section v-if="selectedClass" class="panel" aria-label="班级学生名单">
      <div class="panel-heading">
        <div><h2>{{ selectedClass.name }}</h2><p>共 {{ selectedClass.student_count }} 名学生，含已停用账号。</p></div>
        <router-link :to="{ path: '/admin/access', query: { class_id: selectedClass.id } }" class="manage-link">管理本班账号</router-link>
      </div>
      <el-alert v-if="membersError" :title="membersError" type="error" :closable="false" show-icon />
      <el-table v-loading="membersLoading" :data="members" stripe empty-text="暂无学生，可在账号管理中设置班级归属">
        <el-table-column prop="username" label="账号" min-width="150" />
        <el-table-column prop="display_name" label="姓名" min-width="140" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }"><el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '启用' : '停用' }}</el-tag></template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog v-model="dialogVisible" title="创建教学班级" width="min(92vw, 520px)" destroy-on-close>
      <el-form label-position="top" @submit.prevent="createClass">
        <el-form-item label="班级名称"><el-input v-model="newName" placeholder="例如：2025211119班物理实验" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="createClass">确认创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.class-page { width: min(1240px, calc(100% - 48px)); margin: 0 auto; padding: 54px 0 80px; }
.page-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; margin-bottom: 28px; }
.eyebrow { margin-bottom: 8px; color: var(--gl-primary); font-size: 13px; font-weight: 750; letter-spacing: .1em; }
h1 { margin: 0; font-size: 38px; letter-spacing: -.04em; }
.page-heading p, .panel-heading p { margin: 10px 0 0; color: var(--gl-text-secondary); }
.actions { display: flex; align-items: center; gap: 12px; }
.actions .el-button + .el-button { margin-left: 0; }
.panel { overflow: hidden; margin-top: 20px; border: 1px solid var(--gl-border); border-radius: 14px; background: #fff; box-shadow: var(--gl-shadow); }
.panel-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 22px 24px; border-bottom: 1px solid var(--gl-border); }
.panel-heading h2 { margin: 0; font-size: 20px; overflow-wrap: anywhere; }
.panel-heading p, .panel-heading > span { font-size: 13px; color: var(--gl-text-muted); }
.manage-link { color: var(--gl-primary); font-size: 14px; white-space: nowrap; }
@media (max-width: 850px) { .class-page { width: min(100% - 28px, 1240px); padding-top: 34px; } .page-heading { align-items: flex-start; flex-direction: column; } }
@media (max-width: 520px) { .panel-heading { align-items: flex-start; flex-direction: column; } }
</style>
