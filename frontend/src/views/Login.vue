<template>
  <div class="login-container" :class="themeClass">
    <!-- 装饰性背景元素 -->
    <div class="deco-circle deco-1"></div>
    <div class="deco-circle deco-2"></div>
    <div class="deco-circle deco-3"></div>
    <div class="deco-grid"></div>
    <div class="deco-dots"></div>

    <div class="login-card">
      <!-- Logo区 -->
      <div class="login-header">
        <svg class="login-logo" width="40" height="40" viewBox="0 0 24 24" fill="none">
          <path d="M3 12H6L9 3L12 21L15 9L18 15L21 12H22" stroke="#007AFF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        </svg>
        <h2>{{ $t('login.title') }}</h2>
        <p class="subtitle">{{ isRegister ? $t('login.registerSubtitle') : $t('login.subtitle') }}</p>
      </div>

      <!-- 登录表单 -->
      <el-form v-if="!isRegister" ref="formRef" :model="form" :rules="rules" label-width="0" class="login-form" @keyup.enter="handleLogin">
        <el-form-item prop="username">
          <el-input v-model="form.username" :placeholder="$t('login.usernamePlaceholder')" :prefix-icon="User" size="large" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" :placeholder="$t('login.passwordPlaceholder')" :prefix-icon="Lock" size="large" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" class="login-btn" :loading="loading" @click="handleLogin">
            {{ loading ? $t('login.loggingIn') : $t('login.loginBtn') }}
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 注册表单 -->
      <el-form v-else ref="regFormRef" :model="regForm" :rules="regRules" label-width="0" class="login-form" @keyup.enter="handleRegister">
        <el-form-item prop="username">
          <el-input v-model="regForm.username" :placeholder="$t('login.usernamePlaceholder')" :prefix-icon="User" size="large" />
        </el-form-item>
        <el-form-item prop="real_name">
          <el-input v-model="regForm.real_name" :placeholder="$t('login.realName')" size="large" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="regForm.password" type="password" :placeholder="$t('login.passwordPlaceholder')" :prefix-icon="Lock" size="large" show-password />
        </el-form-item>
        <el-form-item prop="confirm">
          <el-input v-model="regForm.confirm" type="password" :placeholder="$t('login.confirmPassword')" :prefix-icon="Lock" size="large" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" class="login-btn" :loading="regLoading" @click="handleRegister">
            {{ regLoading ? $t('login.registering') : $t('login.registerBtn') }}
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 切换登录/注册 -->
      <div class="switch-auth">
        <el-button text size="small" @click="toggleAuth">
          {{ isRegister ? $t('login.switchToLogin') : $t('login.switchToRegister') }}
        </el-button>
      </div>

      <!-- 语言切换 -->
      <div style="text-align:center;margin-top:12px;">
        <el-button text size="small" @click="switchLang('zh-CN')" :type="currentLang==='zh-CN'?'primary':'default'">中文</el-button>
        <span style="color:#475569;margin:0 4px;">|</span>
        <el-button text size="small" @click="switchLang('en-US')" :type="currentLang==='en-US'?'primary':'default'">EN</el-button>
      </div>

      <div class="login-footer">
        <p>{{ $t('login.version') }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import request from '../utils/request'
import { saveLoginInfo } from '../utils/auth'

const { locale } = useI18n()
const currentLang = ref(locale.value)

const switchLang = (lang) => {
  locale.value = lang
  currentLang.value = lang
  localStorage.setItem('language', lang)
}

const router = useRouter()
const route = useRoute()
const formRef = ref(null)
const regFormRef = ref(null)
const loading = ref(false)
const regLoading = ref(false)
const isRegister = ref(false)

// ── 时间主题 ──
const themeClass = computed(() => {
  const h = new Date().getHours()
  if (h >= 6 && h < 9) return 'theme-dawn'
  if (h >= 9 && h < 17) return 'theme-day'
  if (h >= 17 && h < 20) return 'theme-dusk'
  return 'theme-night'
})

// ── 登录 ──
const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const handleLogin = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    const params = new URLSearchParams()
    params.append('username', form.username)
    params.append('password', form.password)
    const res = await request.post('/auth/login', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
    if (res.code === 200) {
      saveLoginInfo(res.data.token, res.data.user)
      ElMessage.success(`欢迎回来，${res.data.user.real_name || res.data.user.username}`)
      const redirect = route.query.redirect || '/dashboard'
      router.push(redirect)
    } else {
      ElMessage.error(res.msg || '登录失败')
    }
  } catch (e) {} finally {
    loading.value = false
  }
}

// ── 注册 ──
const regForm = reactive({ username: '', real_name: '', password: '', confirm: '' })
const regRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }, { min: 4, message: '至少4个字符', trigger: 'blur' }],
  confirm: [{ required: true, message: '请确认密码', trigger: 'blur' }, {
    validator: (rule, value) => value === regForm.password ? Promise.resolve() : Promise.reject('密码不一致'),
    trigger: 'blur'
  }]
}

const handleRegister = async () => {
  const valid = await regFormRef.value?.validate().catch(() => false)
  if (!valid) return
  regLoading.value = true
  try {
    const params = new URLSearchParams()
    params.append('username', regForm.username)
    params.append('password', regForm.password)
    params.append('real_name', regForm.real_name)
    const res = await request.post('/auth/register/public', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
    if (res.code === 200) {
      ElMessage.success('注册成功，请登录')
      isRegister.value = false
      form.username = regForm.username
    } else {
      ElMessage.error(res.msg || '注册失败')
    }
  } catch (e) {} finally {
    regLoading.value = false
  }
}

const toggleAuth = () => {
  isRegister.value = !isRegister.value
}
</script>

<style scoped>
.login-container {
  height: 100vh; height: 100dvh;
  display: flex; align-items: center; justify-content: center;
  position: relative; overflow: hidden;
  transition: background 1.5s ease;
}

/* ── 时间主题色 ── */
.theme-dawn { background: linear-gradient(135deg, #F5E6D3 0%, #E8D5C4 50%, #D4C5B9 100%); }
.theme-day { background: linear-gradient(135deg, #E8F0FE 0%, #D6E4F0 50%, #C5D9E8 100%); }
.theme-dusk { background: linear-gradient(135deg, #2D1B4E 0%, #1E2A5E 50%, #0F172A 100%); }
.theme-night { background: #0F172A; }

.theme-dawn .login-card { background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(16px); }
.theme-dawn h2 { color: #4A3728; }
.theme-dawn .subtitle { color: #8B7355; }
.theme-dawn .login-footer p { color: #A89880; }
.theme-dawn .login-form :deep(.el-input__wrapper) { background: rgba(255,255,255,0.7); border-color: rgba(74, 55, 40, 0.12); }
.theme-dawn .login-form :deep(.el-input__inner) { color: #4A3728; }

.theme-day .login-card { background: rgba(255, 255, 255, 0.88); backdrop-filter: blur(16px); }
.theme-day h2 { color: #1E293B; }
.theme-day .subtitle { color: #64748B; }
.theme-day .login-footer p { color: #94A3B8; }
.theme-day .login-form :deep(.el-input__wrapper) { background: rgba(255,255,255,0.8); border-color: rgba(30, 41, 59, 0.12); }
.theme-day .login-form :deep(.el-input__inner) { color: #1E293B; }

.theme-dusk .login-card { background: rgba(30, 41, 59, 0.85); backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.08); }
.theme-dusk h2 { color: #E2E8F0; }
.theme-dusk .subtitle { color: #64748B; }

.theme-night .login-card { background: rgba(30, 41, 59, 0.8); backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.08); }
.theme-night h2 { color: #E2E8F0; }
.theme-night .subtitle { color: #64748B; }

/* ── 装饰元素 ── */
.deco-circle {
  position: absolute; border-radius: 50%;
  pointer-events: none;
  transition: all 1.5s ease;
}
.deco-1 {
  width: 500px; height: 500px;
  top: -120px; right: -100px;
  background: radial-gradient(circle, rgba(0,122,255,0.12) 0%, transparent 70%);
}
.theme-dawn .deco-1 { background: radial-gradient(circle, rgba(255,149,0,0.15) 0%, transparent 70%); }
.theme-day .deco-1 { background: radial-gradient(circle, rgba(0,122,255,0.1) 0%, transparent 70%); }
.theme-dusk .deco-1 { background: radial-gradient(circle, rgba(120,80,200,0.2) 0%, transparent 70%); }
.theme-night .deco-1 { background: radial-gradient(circle, rgba(0,122,255,0.08) 0%, transparent 70%); }

.deco-2 {
  width: 350px; height: 350px;
  bottom: -80px; left: -60px;
  background: radial-gradient(circle, rgba(0,122,255,0.08) 0%, transparent 70%);
}
.theme-dawn .deco-2 { background: radial-gradient(circle, rgba(255,200,50,0.12) 0%, transparent 70%); }
.theme-day .deco-2 { background: radial-gradient(circle, rgba(0,122,255,0.07) 0%, transparent 70%); }
.theme-dusk .deco-2 { background: radial-gradient(circle, rgba(200,100,150,0.15) 0%, transparent 70%); }

.deco-3 {
  width: 200px; height: 200px;
  top: 50%; left: 15%;
  background: radial-gradient(circle, rgba(0,122,255,0.06) 0%, transparent 70%);
}
.theme-dawn .deco-3 { background: radial-gradient(circle, rgba(255,100,50,0.08) 0%, transparent 70%); }

.deco-grid {
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(0,122,255,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,122,255,0.03) 1px, transparent 1px);
  background-size: 60px 60px;
  pointer-events: none;
}

.deco-dots {
  position: absolute; inset: 0;
  background-image: radial-gradient(circle, rgba(0,122,255,0.08) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
}

/* ── 登录卡片 ── */
.login-card {
  width: 420px; max-width: 90vw;
  border-radius: 20px;
  padding: 44px 36px 36px;
  box-shadow: 0 25px 60px rgba(0,0,0,0.12);
  position: relative; z-index: 1;
  transition: all 1.5s ease;
}

.login-header { text-align: center; margin-bottom: 32px; }
.login-logo { margin-bottom: 12px; }
.login-header h2 { margin: 0; font-size: 22px; font-weight: 600; font-family: 'Playfair Display', serif; font-style: italic; transition: color 1.5s ease; }
.subtitle { margin: 8px 0 0; font-size: 13px; transition: color 1.5s ease; }

.login-form { margin: 0 auto; }
.login-form :deep(.el-input__wrapper) {
  border-radius: 10px; padding: 4px 16px; box-shadow: none !important;
  transition: all 0.3s ease;
}
.login-form :deep(.el-input__wrapper:hover) { border-color: #007AFF !important; }
.login-form :deep(.el-input__wrapper.is-focus) { border-color: #007AFF !important; box-shadow: 0 0 0 3px rgba(0,122,255,0.12) !important; }
.login-form :deep(.el-input__prefix-inner) { color: #94A3B8; }

.login-btn {
  width: 100%; border-radius: 10px; font-size: 15px; height: 46px;
  letter-spacing: 1px; background: #007AFF; border: none; margin-top: 8px;
}
.login-btn:hover { background: #0060D0 !important; }

.switch-auth { text-align: center; margin-top: 16px; }
.switch-auth :deep(.el-button) { color: #007AFF; font-size: 13px; }

.login-footer { text-align: center; margin-top: 20px; }
.login-footer p { margin: 0; font-size: 11px; transition: color 1.5s ease; }
</style>
