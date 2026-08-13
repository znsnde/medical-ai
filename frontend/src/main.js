import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import './style.css'
import { createI18n } from 'vue-i18n'
import zh from './locales/zh-CN.js'
import en from './locales/en-US.js'
import request from './utils/request'

const i18n = createI18n({
  locale: localStorage.getItem('language') || 'zh-CN',
  fallbackLocale: 'zh-CN',
  messages: { 'zh-CN': zh, 'en-US': en },
})

const app = createApp(App)

app.config.globalProperties.$api = request

app.use(router)
app.use(ElementPlus)
app.use(i18n)
app.mount('#app')