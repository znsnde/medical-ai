<template>
  <div class="app-root">
    <!-- 登录页 + 首页 — 不使用侧边栏布局 -->
    <template v-if="isFullPage">
      <router-view />
    </template>

    <!-- 主界面 — 侧边栏 + 内容区 -->
    <template v-else>
      <el-container style="height: 100vh;">
        <el-aside width="220px" style="background-color: #0A0F1A;">
          <!-- 用户信息区 -->
          <div class="sidebar-user">
            <div class="user-avatar">{{ avatarText }}</div>
            <div class="user-info">
              <div class="user-name">{{ userInfo.real_name || userInfo.username }}</div>
              <div class="user-role">{{ roleLabel }}</div>
            </div>
          </div>

          <el-menu
            :default-active="route.path"
            background-color="#001529"
            text-color="#fff"
            active-text-color="#409EFF"
            router
          >
            <!-- 医生/管理员菜单 -->
            <template v-if="userInfo.role !== 'patient'">
              <el-menu-item index="/dashboard">
                <el-icon><Monitor /></el-icon>
                <template #title>{{ $t('nav.dashboard') }}</template>
              </el-menu-item>
              <el-menu-item index="/patient">
                <el-icon><UserFilled /></el-icon>
                <template #title>{{ $t('nav.patient') }}</template>
              </el-menu-item>
              <el-menu-item index="/record">
                <el-icon><Document /></el-icon>
                <template #title>{{ $t('nav.record') }}</template>
              </el-menu-item>
              <el-menu-item index="/diagnosis">
                <el-icon><Aim /></el-icon>
                <template #title>{{ $t('nav.diagnosis') }}</template>
              </el-menu-item>
              <el-menu-item index="/paper">
                <el-icon><Upload /></el-icon>
                <template #title>{{ $t('nav.paper') }}</template>
              </el-menu-item>
              <el-menu-item index="/report">
                <el-icon><Printer /></el-icon>
                <template #title>{{ $t('nav.report') }}</template>
              </el-menu-item>
              <el-menu-item index="/knowledge-graph">
                <el-icon><Connection /></el-icon>
                <template #title>{{ $t('nav.knowledgeGraph') }}</template>
              </el-menu-item>
              <el-menu-item index="/chat">
                <el-icon><ChatLineSquare /></el-icon>
                <template #title>{{ $t('nav.chat') }}</template>
              </el-menu-item>
              <el-menu-item index="/settings" v-if="userInfo.role === 'admin'">
                <el-icon><Setting /></el-icon>
                <template #title>{{ $t('nav.settings') }}</template>
              </el-menu-item>
            </template>
            <!-- 患者菜单 -->
            <template v-else>
              <el-menu-item index="/my-records">
                <el-icon><Document /></el-icon>
                <template #title>{{ $t('nav.myRecords') }}</template>
              </el-menu-item>
              <el-menu-item index="/chat">
                <el-icon><ChatLineSquare /></el-icon>
                <template #title>{{ $t('nav.consultation') }}</template>
              </el-menu-item>
            </template>
          </el-menu>

          <!-- 底部退出按钮 + 语言切换 -->
          <div class="sidebar-footer">
            <div style="display:flex;align-items:center;gap:6px;padding:4px 16px 8px;">
              <el-dropdown size="small" @command="switchLang">
                <span style="color:rgba(255,255,255,0.5);font-size:12px;cursor:pointer;display:flex;align-items:center;gap:4px;">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
                  {{ currentLang === 'zh-CN' ? '中' : 'EN' }}
                </span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="zh-CN">中文</el-dropdown-item>
                    <el-dropdown-item command="en-US">English</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
            <el-button
              text
              style="color: rgba(255,255,255,0.65); width: 100%; justify-content: flex-start;"
              @click="handleLogout"
            >
              <el-icon><SwitchButton /></el-icon>
              <span style="margin-left: 8px;">{{ $t('nav.logout') }}</span>
            </el-button>
          </div>
        </el-aside>

        <el-main>
          <router-view />
        </el-main>
      </el-container>
    </template>
  </div>
</template>

<script setup>
import { computed, watch, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessageBox, ElMessage } from 'element-plus'
import {
  Monitor, UserFilled, Document, Aim,
  Upload, Printer, ChatLineSquare, SwitchButton, Setting, Connection
} from '@element-plus/icons-vue'
import { getUser, logout as clearAuth } from './utils/auth'

const { locale, t } = useI18n()
const currentLang = ref(locale.value)

const switchLang = (lang) => {
  locale.value = lang
  currentLang.value = lang
  localStorage.setItem('language', lang)
}

const route = useRoute()
const router = useRouter()

// ── 全屏页面判断（不显示侧边栏） ──
const isFullPage = computed(() => ['/login', '/'].includes(route.path))

// ── 用户信息 ──
const userInfo = computed(() => getUser())

const avatarText = computed(() => {
  const name = userInfo.value.real_name || userInfo.value.username
  return name ? name.charAt(0).toUpperCase() : '?'
})

const roleLabel = computed(() => {
  const map = { admin: 'role.admin', doctor: 'role.doctor', patient: 'role.patient' }
  const key = map[userInfo.value.role]
  return key ? t(key) : 'User'
})

// ── 时间主题 + 暗色模式 ──
const themeClasses = ['theme-dawn', 'theme-day', 'theme-dusk', 'theme-night']

const applyTimeTheme = () => {
  const h = new Date().getHours()
  let theme
  if (h >= 6 && h < 9) theme = 'theme-dawn'
  else if (h >= 9 && h < 17) theme = 'theme-day'
  else if (h >= 17 && h < 20) theme = 'theme-dusk'
  else theme = 'theme-night'

  document.documentElement.classList.remove(...themeClasses)
  document.documentElement.classList.add(theme)

  // 白天不用暗色模式，晚上用
  if (theme === 'theme-day' || theme === 'theme-dawn') {
    document.documentElement.classList.remove('dark')
  } else {
    document.documentElement.classList.add('dark')
  }
}

onMounted(() => {
  applyTimeTheme()
  setInterval(applyTimeTheme, 60000) // 每分钟检查
})

// ── 退出登录 ──
const handleLogout = async () => {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '退出确认', {
      type: 'warning',
      confirmButtonText: '确定退出',
      cancelButtonText: '取消'
    })
    clearAuth()
    ElMessage.success('已退出登录')
    router.push('/login')
  } catch {
    // 用户取消
  }
}

// 监听路由变化，更新页面标题
watch(() => route.path, () => {
  document.title = (route.meta?.title || '智慧医疗') + ' | 智慧医疗辅助诊断系统'
})
</script>

<style>
/* ── 全局基础 ── */
html, body {
  margin: 0; padding: 0; height: 100%;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  transition: background 1.5s ease, color 1.5s ease;
}

/* ── 时间主题：白天 ── */
html.theme-day, html.theme-dawn {
  background: #F0F4F8;
  color: #1E293B;
}
html.theme-day .el-main { background: #F0F4F8; }
html.theme-day .el-card { background: #FFFFFF !important; border-color: rgba(0,0,0,0.06) !important; color: #1E293B !important; }
html.theme-day .el-table th.el-table__cell { background: #F8FAFC !important; color: #64748B !important; }
html.theme-day .el-table td.el-table__cell { background: #FFFFFF !important; color: #1E293B !important; }
html.theme-day .el-descriptions__label { background: #F8FAFC !important; color: #64748B !important; }
html.theme-day .el-descriptions__content { background: #FFFFFF !important; color: #1E293B !important; }
html.theme-day h2, html.theme-day h3, html.theme-day h4 { color: #1E293B !important; }
html.theme-day .el-dialog { background: #FFFFFF !important; }
html.theme-day .el-dialog__title { color: #1E293B !important; }
html.theme-day .el-input__wrapper { background: #F1F5F9 !important; }
html.theme-day .el-input__inner { color: #1E293B !important; }
html.theme-day .el-select-dropdown { background: #FFFFFF !important; }
html.theme-day .el-select-dropdown__item { color: #1E293B !important; }
html.theme-day .el-empty__description p { color: #94A3B8 !important; }
html.theme-day .el-skeleton__item { background: #E2E8F0 !important; }

/* ── 时间主题：黄昏/夜晚 ── */
html.theme-dusk, html.theme-night {
  background: #0F172A;
  color: #E2E8F0;
}
html.theme-dusk .el-main, html.theme-night .el-main { background: #0F172A; }
html.theme-dusk .el-card, html.theme-night .el-card { background: #1E293B !important; border-color: rgba(255,255,255,0.06) !important; color: #E2E8F0 !important; }
html.theme-dusk .el-table th.el-table__cell, html.theme-night .el-table th.el-table__cell { background: #1E293B !important; color: #94A3B8 !important; }
html.theme-dusk .el-table td.el-table__cell, html.theme-night .el-table td.el-table__cell { background: #0F172A !important; color: #E2E8F0 !important; }
html.theme-dusk .el-descriptions__label, html.theme-night .el-descriptions__label { background: #1E293B !important; color: #94A3B8 !important; }
html.theme-dusk .el-descriptions__content, html.theme-night .el-descriptions__content { background: #0F172A !important; color: #E2E8F0 !important; }
html.theme-night h2, html.theme-dusk h2, html.theme-night h3, html.theme-dusk h3, html.theme-night h4, html.theme-dusk h4 { color: #E2E8F0 !important; }

/* ── 侧边栏 ── */
.el-aside {
  position: relative; overflow-y: auto; height: 100vh;
  display: flex; flex-direction: column;
  background: #0A0F1A !important;
  transition: background 1.5s ease;
}

.el-menu {
  border-right: none !important; flex: 1;
  background: transparent !important;
}

.el-menu-item {
  color: rgba(255,255,255,0.6) !important;
  transition: all 0.3s ease !important;
  border-radius: 8px !important;
  margin: 2px 8px !important;
  width: auto !important;
}

.el-menu-item.is-active {
  color: #007AFF !important;
  background: rgba(0, 122, 255, 0.12) !important;
}

.el-menu-item:hover {
  background: rgba(255,255,255,0.06) !important;
  color: #fff !important;
}

/* ── 侧边栏头部 ── */
.sidebar-user {
  padding: 20px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  display: flex; align-items: center; gap: 12px;
}
.user-avatar {
  width: 38px; height: 38px; border-radius: 50%;
  background: linear-gradient(135deg, #007AFF, #5856D6);
  color: #fff; display: flex; align-items: center; justify-content: center;
  font-size: 16px; font-weight: 600; flex-shrink: 0;
}
.user-info { overflow: hidden; }
.user-name { color: #E2E8F0; font-size: 14px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.user-role { color: #64748B; font-size: 12px; margin-top: 2px; }

/* ── 侧边栏底部 ── */
.sidebar-footer {
  position: absolute; bottom: 0; width: 220px;
  border-top: 1px solid rgba(255,255,255,0.06); padding: 8px 0;
}

/* ── 卡片 ── */
.el-card {
  border-radius: 12px !important;
  transition: all 1.5s ease;
}
.el-card :deep(.el-card__header) {
  border-bottom: 1px solid rgba(0,0,0,0.06) !important;
  padding: 14px 20px !important;
}
html.theme-day .el-card :deep(.el-card__header),
html.theme-dawn .el-card :deep(.el-card__header) {
  border-bottom-color: rgba(0,0,0,0.06) !important;
}
html.theme-night .el-card :deep(.el-card__header),
html.theme-dusk .el-card :deep(.el-card__header) {
  border-bottom-color: rgba(255,255,255,0.06) !important;
}

/* ── 表格 ── */
.el-table { background: transparent !important; transition: color 1.5s ease; }
.el-table th.el-table__cell { border-bottom: 1px solid rgba(0,0,0,0.06) !important; }
.el-table td.el-table__cell { border-bottom: 1px solid rgba(0,0,0,0.04) !important; }
.el-table--border { border: 1px solid rgba(0,0,0,0.06) !important; border-radius: 8px !important; overflow: hidden !important; }
html.theme-night .el-table th.el-table__cell,
html.theme-dusk .el-table th.el-table__cell { border-bottom-color: rgba(255,255,255,0.06) !important; }
html.theme-night .el-table td.el-table__cell,
html.theme-dusk .el-table td.el-table__cell { border-bottom-color: rgba(255,255,255,0.04) !important; }
html.theme-night .el-table--border,
html.theme-dusk .el-table--border { border-color: rgba(255,255,255,0.06) !important; }
.el-table__body tr:hover > td { background: rgba(0, 122, 255, 0.04) !important; }

/* ── 按钮美化 ── */
.el-button--primary {
  background: linear-gradient(135deg, #007AFF, #0060D0) !important;
  border: none !important;
  border-radius: 10px !important;
  font-weight: 500 !important;
  letter-spacing: 0.3px !important;
  transition: all 0.3s ease !important;
}
.el-button--primary:hover {
  transform: translateY(-1px) !important;
  box-shadow: 0 6px 20px rgba(0, 122, 255, 0.25) !important;
}
.el-button--primary:active {
  transform: translateY(0) !important;
}

.el-button--success {
  background: linear-gradient(135deg, #34C759, #28A745) !important;
  border: none !important;
  border-radius: 10px !important;
  font-weight: 500 !important;
  transition: all 0.3s ease !important;
}
.el-button--success:hover {
  transform: translateY(-1px) !important;
  box-shadow: 0 6px 20px rgba(52, 199, 89, 0.25) !important;
}

.el-button--danger {
  background: linear-gradient(135deg, #FF3B30, #DC3545) !important;
  border: none !important;
  border-radius: 10px !important;
  font-weight: 500 !important;
  transition: all 0.3s ease !important;
}
.el-button--danger:hover {
  transform: translateY(-1px) !important;
  box-shadow: 0 6px 20px rgba(255, 59, 48, 0.25) !important;
}

.el-button--default {
  border-radius: 10px !important;
  border: 1px solid rgba(0,0,0,0.1) !important;
  transition: all 0.3s ease !important;
}
html.theme-night .el-button--default,
html.theme-dusk .el-button--default {
  border-color: rgba(255,255,255,0.12) !important;
  background: rgba(255,255,255,0.06) !important;
  color: #E2E8F0 !important;
}
html.theme-night .el-button--default:hover,
html.theme-dusk .el-button--default:hover {
  background: rgba(255,255,255,0.12) !important;
}

/* ── 输入框 ── */
.el-input__wrapper {
  border-radius: 10px !important;
  box-shadow: none !important;
  transition: all 0.3s ease !important;
}
.el-input__wrapper:hover { border-color: #007AFF !important; }
.el-input__wrapper.is-focus { border-color: #007AFF !important; box-shadow: 0 0 0 3px rgba(0,122,255,0.12) !important; }

/* ── 弹窗 ── */
.el-dialog { border-radius: 16px !important; transition: background 1.5s ease; }
.el-dialog__header { padding: 20px 24px 0 !important; }
.el-dialog__body { padding: 20px 24px !important; }
.el-dialog__footer { padding: 0 24px 20px !important; }

/* ── 标签 ── */
.el-tag { border: none !important; border-radius: 6px !important; }

/* ── 描述列表 ── */
.el-descriptions { transition: color 1.5s ease; }
.el-descriptions__label, .el-descriptions__content {
  transition: all 1.5s ease !important;
}

/* ── 其他 ── */
h2, h3, h4 { transition: color 1.5s ease; }
.el-empty__description p { transition: color 1.5s ease; }
.el-skeleton__item { transition: background 1.5s ease; }
.el-select-dropdown { transition: all 1.5s ease; }
.el-slider__runway { background: #334155 !important; }
.el-slider__bar { background: #007AFF !important; }

/* ── 通用过渡 ── */
* { transition-property: none; }
.el-card, .el-table, .el-main, .el-aside, .el-dialog,
.el-input__wrapper, .el-descriptions__label, .el-descriptions__content {
  transition: background 1.5s ease, color 1.5s ease, border-color 1.5s ease !important;
}
</style>
