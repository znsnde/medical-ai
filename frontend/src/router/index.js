import { createRouter, createWebHistory } from 'vue-router'
import { isLoggedIn, getUser } from '../utils/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { title: '登录', noAuth: true }
  },
  {
    path: '/',
    name: 'LandingPage',
    component: () => import('../views/LandingPage.vue'),
    meta: { title: '智慧医疗', noAuth: true }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { title: '工作台', roles: ['admin', 'doctor'] }
  },
  {
    path: '/patient',
    name: 'PatientManage',
    component: () => import('../views/PatientManage.vue'),
    meta: { title: '患者管理', roles: ['admin', 'doctor'] }
  },
  {
    path: '/record',
    name: 'RecordStruct',
    component: () => import('../views/RecordStruct.vue'),
    meta: { title: '病历结构化', roles: ['admin', 'doctor'] }
  },
  {
    path: '/diagnosis',
    name: 'AiDiagnosis',
    component: () => import('../views/AiDiagnosis.vue'),
    meta: { title: 'AI辅助诊断', roles: ['admin', 'doctor'] }
  },
  {
    path: '/paper',
    name: 'PaperUpload',
    component: () => import('../views/PaperUpload.vue'),
    meta: { title: '医学文献上传', roles: ['admin', 'doctor'] }
  },
  {
    path: '/report',
    name: 'ReportPdf',
    component: () => import('../views/ReportPdf.vue'),
    meta: { title: '诊断报告', roles: ['admin', 'doctor'] }
  },
  {
    path: '/knowledge-graph',
    name: 'KnowledgeGraph',
    component: () => import('../views/KnowledgeGraph.vue'),
    meta: { title: '知识图谱', roles: ['admin', 'doctor'] }
  },
  {
    path: '/chat',
    name: 'PatientChat',
    component: () => import('../views/PatientChat.vue'),
    meta: { title: '患者问答', roles: ['admin', 'doctor', 'patient'] }
  },
  {
    path: '/dicom/:record_id',
    name: 'DicomViewer',
    component: () => import('../views/DicomViewer.vue'),
    meta: { title: '影像查看', roles: ['admin', 'doctor'] }
  },
  {
    path: '/settings',
    name: 'SystemSettings',
    component: () => import('../views/SystemSettings.vue'),
    meta: { title: '系统设置', roles: ['admin'] }
  },
  {
    path: '/my-records',
    name: 'MyRecords',
    component: () => import('../views/MyRecords.vue'),
    meta: { title: '我的病历', roles: ['patient'] }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  document.title = (to.meta?.title || '智慧医疗') + ' | 智慧医疗辅助诊断系统'

  const loggedIn = isLoggedIn()
  const user = getUser()

  if (to.meta?.noAuth) {
    if (loggedIn) {
      next('/dashboard')
    } else {
      next()
    }
    return
  }

  // 未登录 → 登录页
  if (!loggedIn) {
    next(`/login?redirect=${to.path}`)
    return
  }

  // 角色检查
  const roles = to.meta?.roles
  if (roles && !roles.includes(user.role)) {
    // 患者跳转到我的病历，其他跳工作台
    if (user.role === 'patient') {
      next('/my-records')
    } else {
      next('/dashboard')
    }
    return
  }

  next()
})

export default router
