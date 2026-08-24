<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { accessState, loginAccess, refreshAccessSession } from '@/utils/access'

const route = useRoute()
const router = useRouter()
const identifier = ref('')
const password = ref('')
const submitting = ref(false)

const requestMail = computed(() => {
  const subject = encodeURIComponent('睿析实验教学平台账号申请')
  const body = encodeURIComponent('王老师您好，\n\n我想申请“睿析实验”教学平台账号。\n姓名：\n学号/工号：\n用途/课程：\n\n谢谢。')
  return `mailto:${accessState.adminEmail}?subject=${subject}&body=${body}`
})

function safeRedirect() {
  const target = route.query.redirect
  return typeof target === 'string' && target.startsWith('/') && !target.startsWith('//')
    ? target
    : '/'
}

async function submitLogin() {
  if (!identifier.value.trim() || !password.value) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  submitting.value = true
  try {
    await loginAccess(identifier.value.trim(), password.value)
    ElMessage.success('登录成功')
    await router.replace(safeRedirect())
  } catch (error) {
    ElMessage.error(error.message || '登录失败')
  } finally {
    submitting.value = false
  }
}

refreshAccessSession({ force: true })
</script>

<template>
  <div class="access-page">
    <header class="access-header">
      <img
        class="school-logo"
        src="@/assets/BUPTPhyscis.jpg"
        alt="北京邮电大学物理科学与技术学院"
      />
    </header>

    <main class="access-main">
      <section class="brand-story" aria-labelledby="platform-title">
        <div>
          <h1 id="platform-title">睿析实验</h1>
          <p class="platform-subtitle">AI赋能的物理实验教学平台</p>
          <span class="brand-rule" aria-hidden="true"></span>
          <p class="platform-description">
            让实验教学更高效、更智能、更有趣。
          </p>
          <p class="platform-description">
            为教师提供丰富的实验资源和教学工具，为学生提供自主学习和实验操作的环境，助力物理实验教学的创新与发展。
          </p>
        </div>

        <svg class="physics-figure" viewBox="0 0 680 350" role="img" aria-label="波形与运动轨迹装饰图">
          <g class="figure-axis">
            <path d="M30 238H338M104 296V112" />
            <path d="m338 238-12-7v14Z" class="axis-arrow" />
            <path d="m104 112-7 12h14Z" class="axis-arrow" />
            <path d="M34 238c32-89 65 89 98 0s66 89 99 0 65 89 98 0" />
          </g>
          <g class="figure-orbit">
            <path d="M-64 187C168 104 398 149 588 338" />
            <path d="M-72 214C203 122 454 180 645 378" stroke-dasharray="7 10" />
            <circle cx="356" cy="176" r="12" />
            <circle cx="538" cy="296" r="6" class="figure-node" />
          </g>
        </svg>
      </section>

      <section class="login-section" aria-labelledby="login-title">
        <div class="login-content">
          <h2 id="login-title">请登录</h2>
          <form class="login-form" @submit.prevent="submitLogin">
            <label for="access-identifier">账号或邮箱</label>
            <el-input
              id="access-identifier"
              v-model="identifier"
              size="large"
              autocomplete="username"
              placeholder="请输入账号或邮箱"
            />
            <label for="access-password">密码</label>
            <el-input
              id="access-password"
              v-model="password"
              size="large"
              type="password"
              autocomplete="current-password"
              show-password
              placeholder="请输入密码"
            />
            <el-button
              class="login-button"
              type="primary"
              size="large"
              native-type="submit"
              :loading="submitting"
            >进入教学平台</el-button>
          </form>

          <div class="account-request">
            <div>
              <span>还没有账号？</span>
              <a :href="requestMail">发送申请邮件</a>
            </div>
            <a class="teacher-email" :href="requestMail">{{ accessState.adminEmail }}</a>
          </div>

          <router-link class="utility-row" :to="{ name: 'access-admin' }">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12 3 5 6v5c0 4.7 2.8 8.1 7 10 4.2-1.9 7-5.3 7-10V6l-7-3Z" />
            </svg>
            <span>管理员入口</span>
            <svg class="row-arrow" viewBox="0 0 24 24" aria-hidden="true"><path d="m9 5 7 7-7 7" /></svg>
          </router-link>

          <div class="network-row">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M4 20h16M6 17h12M7 17V9m5 8V9m5 8V9M5 9h14L12 4 5 9Z" />
            </svg>
            <div>
              <span>校内授权网络可免登录访问</span>
              <small>当前 IP：{{ accessState.clientIp || '正在检测' }}</small>
            </div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.access-page {
  min-height: 100vh;
  color: #0a2347;
  background: #ffffff;
}

.access-header {
  display: flex;
  width: min(100% - 72px, 1440px);
  height: 112px;
  margin: 0 auto;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #e5eaf2;
}

.platform-wordmark {
  color: #0a2347;
  font-size: 26px;
  font-weight: 760;
  letter-spacing: .04em;
  text-decoration: none;
}

.school-logo {
  width: min(430px, 42vw);
  height: 62px;
  object-fit: contain;
  object-position: right center;
}

.access-main {
  display: grid;
  width: min(100% - 72px, 1240px);
  min-height: calc(100vh - 112px);
  margin: 0 auto;
  grid-template-columns: minmax(0, 1fr) minmax(420px, .88fr);
  align-items: start;
  gap: clamp(72px, 8vw, 132px);
  padding: 84px 0 70px;
}

.brand-story {
  position: relative;
  display: flex;
  min-height: 610px;
  align-items: center;
  overflow: hidden;
}

.brand-story > div {
  position: relative;
  z-index: 1;
  align-self: flex-start;
  margin-top: 86px;
}

h1 {
  margin: 0;
  color: #08234a;
  font-size: clamp(56px, 5.2vw, 78px);
  font-weight: 760;
  line-height: 1.08;
  letter-spacing: -.06em;
}

.platform-subtitle {
  margin: 14px 0 0;
  color: #5d6879;
  font-size: clamp(20px, 1.7vw, 26px);
  letter-spacing: .02em;
}

.brand-rule {
  display: block;
  width: 42px;
  height: 3px;
  margin: 32px 0;
  background: #155eef;
}

.platform-description {
  max-width: 510px;
  margin: 0;
  color: #5f6b7d;
  font-size: 16px;
  line-height: 1.95;
}

.physics-figure {
  position: absolute;
  left: -34px;
  bottom: 2px;
  width: min(680px, 110%);
  color: #8eb5f5;
  pointer-events: none;
}

.physics-figure path,
.physics-figure circle {
  fill: none;
  stroke: currentColor;
  stroke-width: 1.25;
  vector-effect: non-scaling-stroke;
}

.figure-axis { opacity: .55; }
.figure-orbit { opacity: .3; }
.physics-figure .axis-arrow,
.physics-figure .figure-node { fill: currentColor; stroke: none; }

.login-section {
  display: flex;
  min-height: 610px;
  align-items: center;
  border-left: 1px solid #e6ebf3;
  padding-left: clamp(52px, 5vw, 82px);
}

.login-content {
  width: 100%;
  max-width: 500px;
}

h2 {
  margin: 0;
  color: #0a2347;
  font-size: clamp(30px, 2.5vw, 38px);
  font-weight: 730;
  line-height: 1.25;
  letter-spacing: -.035em;
}

.login-help {
  margin: 15px 0 35px;
  color: #7b8594;
  font-size: 16px;
}

.login-form {
  display: grid;
  gap: 12px;
}

.login-form label {
  margin-top: 5px;
  color: #263b58;
  font-size: 14px;
  font-weight: 650;
}

.login-form :deep(.el-input__wrapper) {
  min-height: 54px;
  padding: 0 16px;
  border-radius: 6px;
  box-shadow: 0 0 0 1px #cfd8e7 inset;
  transition: box-shadow .2s ease;
}

.login-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #9fb4d4 inset;
}

.login-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px rgba(21, 94, 239, .24) inset;
}

.login-form :deep(.el-input__inner) {
  color: #152b4d;
  font-size: 15px;
}

.login-button {
  width: 100%;
  height: 54px;
  margin-top: 17px;
  border-radius: 6px;
  background: #155eef;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: .04em;
  box-shadow: 0 10px 24px rgba(21, 94, 239, .16);
}

.account-request {
  display: flex;
  margin-top: 25px;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  color: #6f7989;
  font-size: 14px;
}

.account-request > div {
  display: flex;
  gap: 10px;
}

.account-request a {
  color: #155eef;
  font-weight: 650;
  text-decoration: none;
}

.teacher-email {
  color: #45566f !important;
  font-weight: 500 !important;
}

.utility-row,
.network-row {
  display: flex;
  min-height: 70px;
  align-items: center;
  gap: 15px;
  border-top: 1px solid #e7ebf2;
}

.utility-row {
  margin-top: 29px;
  color: #155eef;
  font-size: 15px;
  font-weight: 650;
  text-decoration: none;
}

.utility-row svg,
.network-row > svg {
  width: 23px;
  height: 23px;
  flex: 0 0 auto;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.6;
}

.utility-row .row-arrow {
  width: 17px;
  height: 17px;
  margin-left: auto;
}

.network-row {
  color: #7a8596;
}

.network-row > div {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.network-row span { font-size: 14px; }
.network-row small { color: #9aa3b1; font-size: 12px; }

@media (max-width: 980px) {
  .access-main {
    grid-template-columns: minmax(0, .8fr) minmax(400px, 1fr);
    gap: 42px;
  }

  .login-section { padding-left: 40px; }
  .physics-figure { opacity: .72; }
}

@media (max-width: 760px) {
  .access-header {
    width: min(100% - 36px, 720px);
    height: 86px;
  }

  .platform-wordmark { font-size: 19px; }
  .school-logo { width: min(245px, 58vw); height: 44px; }

  .access-main {
    width: min(100% - 40px, 560px);
    min-height: auto;
    grid-template-columns: 1fr;
    gap: 42px;
    padding: 52px 0 66px;
  }

  .brand-story {
    min-height: 270px;
    align-items: flex-start;
  }

  .brand-story > div { margin-top: 0; }
  h1 { font-size: clamp(46px, 13vw, 62px); }
  .platform-subtitle { max-width: 340px; font-size: 19px; line-height: 1.55; }
  .brand-rule { margin: 23px 0; }
  .platform-description { font-size: 14px; line-height: 1.8; }
  .physics-figure { display: none; }

  .login-section {
    min-height: auto;
    border-top: 1px solid #e6ebf3;
    border-left: 0;
    padding: 40px 0 0;
  }

  .account-request {
    align-items: flex-start;
    flex-direction: column;
    gap: 7px;
  }
}

@media (max-width: 430px) {
  .access-header { width: calc(100% - 28px); }
  .platform-wordmark { font-size: 17px; }
  .school-logo { width: 205px; }
  .access-main { width: calc(100% - 32px); padding-top: 42px; }
  .brand-story { min-height: 250px; }
  h2 { font-size: 28px; }
  .account-request > div { flex-wrap: wrap; }
}
</style>
