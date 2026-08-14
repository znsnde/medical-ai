<template>
  <div class="settings-page">
    <h2>⚙️ 系统设置</h2>

    <el-tabs v-model="activeTab" class="settings-tabs">
      <!-- ═══ Tab 1: 用户管理 ═══ -->
      <el-tab-pane label="👥 用户管理" name="users">
        <div class="tab-toolbar">
          <el-button type="primary" @click="openAddDialog" :disabled="!isAdmin">新增用户</el-button>
          <span class="tab-hint" v-if="!isAdmin">仅管理员可管理用户</span>
        </div>

        <el-table :data="userList" border v-loading="loadingUsers" style="width:100%">
          <el-table-column label="ID" prop="id" width="60"/>
          <el-table-column label="用户名" prop="username" width="120"/>
          <el-table-column label="姓名" prop="real_name" width="120"/>
          <el-table-column label="角色" width="100">
            <template #default="scope">
              <el-tag :type="roleTagType(scope.row.role)" size="small">{{ roleLabel(scope.row.role) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="科室" prop="department" width="120"/>
          <el-table-column label="状态" width="80">
            <template #default="scope">
              <el-tag :type="scope.row.is_active ? 'success' : 'danger'" size="small">
                {{ scope.row.is_active ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" prop="create_time" width="170"/>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="scope">
              <el-button size="small" @click="openEditDialog(scope.row)" :disabled="!isAdmin">编辑</el-button>
              <el-button size="small" type="danger" @click="deleteUser(scope.row)" :disabled="!isAdmin || scope.row.username === 'admin'">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 新增/编辑用户弹窗 -->
        <el-dialog v-model="userDialogVisible" :title="isEditing ? '编辑用户' : '新增用户'" width="500px">
          <el-form :model="userForm" label-width="80px">
            <el-form-item label="用户名" v-if="!isEditing">
              <el-input v-model="userForm.username" placeholder="登录用户名"/>
            </el-form-item>
            <el-form-item label="密码" :required="!isEditing">
              <el-input v-model="userForm.password" type="password" show-password :placeholder="isEditing ? '留空则不修改' : '输入密码'"/>
            </el-form-item>
            <el-form-item label="姓名">
              <el-input v-model="userForm.real_name" placeholder="真实姓名"/>
            </el-form-item>
            <el-form-item label="角色">
              <el-select v-model="userForm.role" style="width:100%">
                <el-option label="管理员" value="admin"/>
                <el-option label="医生" value="doctor"/>
                <el-option label="患者" value="patient"/>
              </el-select>
            </el-form-item>
            <el-form-item label="科室">
              <el-input v-model="userForm.department" placeholder="所属科室"/>
            </el-form-item>
            <el-form-item label="状态" v-if="isEditing">
              <el-switch v-model="userForm.is_active" :active-value="1" :inactive-value="0"/>
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="userDialogVisible=false">取消</el-button>
            <el-button type="primary" @click="submitUser" :loading="savingUser">{{ isEditing ? '保存修改' : '创建用户' }}</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>

      <!-- ═══ Tab 2: 系统信息 ═══ -->
      <el-tab-pane label="📊 系统信息" name="system">
        <el-row :gutter="20">
          <el-col :span="8" v-for="card in statCards" :key="card.label">
            <el-card shadow="hover" class="stat-card" :style="{ borderTop: `3px solid ${card.color}` }">
              <div class="stat-value" :style="{ color: card.color }">{{ card.value }}</div>
              <div class="stat-label">{{ card.label }}</div>
            </el-card>
          </el-col>
        </el-row>

        <el-card style="margin-top:20px;">
          <template #header><span>系统信息</span></template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="系统名称">{{ sysInfo.system_name || '智慧医疗系统' }}</el-descriptions-item>
            <el-descriptions-item label="版本号">{{ sysInfo.version || '1.0.0' }}</el-descriptions-item>
            <el-descriptions-item label="后端框架">FastAPI + Python</el-descriptions-item>
            <el-descriptions-item label="前端框架">Vue 3 + Element Plus</el-descriptions-item>
            <el-descriptions-item label="数据库">MySQL</el-descriptions-item>
            <el-descriptions-item label="AI 模型">DeepSeek Chat</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-tab-pane>

      <!-- ═══ Tab 3: 关于 ═══ -->
      <el-tab-pane label="ℹ️ 关于" name="about">
        <el-card style="text-align:center;padding:40px;">
          <div style="font-size:48px;margin-bottom:16px;">🏥</div>
          <h2 style="margin:0 0 8px;">智慧医疗辅助诊断与电子病历结构化系统</h2>
          <p style="color:var(--text-secondary);margin:0 0 20px;">版本 1.0.0</p>
          <el-divider/>
          <div style="text-align:left;max-width:500px;margin:0 auto;">
            <h4>核心功能</h4>
            <ul style="line-height:2;">
              <li>📋 电子病历智能结构化（文本 + DICOM 多模态）</li>
              <li>🧠 AI 辅助诊断（基于 DeepSeek 大模型）</li>
              <li>👨‍⚕️ 患者管理与随访</li>
              <li>📄 诊断报告 PDF 生成</li>
              <li>📚 医学文献 AI 速读</li>
              <li>🗣️ 智能问诊多轮对话</li>
              <li>🩻 典型病例参考影像库</li>
            </ul>
            <el-divider/>
            <p style="font-size:12px;color:var(--text-muted);">
              项目展示用途 · 数据仅供演示
            </p>
          </div>
        </el-card>
      </el-tab-pane>

      <!-- ═══ Tab 4: 审计日志 ═══ -->
      <el-tab-pane label="🔍 审计日志" name="audit">
        <div class="tab-toolbar">
          <el-select v-model="auditLevel" placeholder="级别" clearable style="width:120px" @change="reloadAudit">
            <el-option label="INFO" value="INFO"/>
            <el-option label="WARNING" value="WARNING"/>
          </el-select>
          <el-input v-model="auditKeyword" placeholder="关键字（如：登录成功）" clearable style="width:240px"
                    @keyup.enter="reloadAudit" @clear="reloadAudit"/>
          <el-button type="primary" @click="reloadAudit">查询</el-button>
          <el-button @click="refreshAudit" :loading="loadingAudit">刷新</el-button>
        </div>

        <el-table :data="auditItems" border v-loading="loadingAudit" style="width:100%">
          <el-table-column label="时间" prop="time" width="190"/>
          <el-table-column label="级别" width="100">
            <template #default="scope">
              <el-tag :type="auditLevelType(scope.row.level)" size="small">{{ scope.row.level }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="审计事件" prop="message" min-width="300" show-overflow-tooltip/>
        </el-table>

        <div class="audit-pagination">
          <el-pagination background layout="total, prev, pager, next"
                         :total="auditTotal" :page-size="auditPageSize"
                         :current-page="auditPage" @current-change="onAuditPageChange"/>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../utils/request'
import { getUser } from '../utils/auth'

const activeTab = ref('users')

// ── 当前用户权限 ──
const currentUser = computed(() => getUser())
const isAdmin = computed(() => currentUser.value.role === 'admin')

// ── 用户管理 ──
const userList = ref([])
const loadingUsers = ref(false)
const userDialogVisible = ref(false)
const isEditing = ref(false)
const editingUserId = ref(null)
const savingUser = ref(false)

const userForm = ref({
  username: '',
  password: '',
  real_name: '',
  role: 'doctor',
  department: '',
  is_active: 1
})

const roleLabel = (role) => ({ admin: '管理员', doctor: '医生', patient: '患者' }[role] || role)
const roleTagType = (role) => ({ admin: 'danger', doctor: 'primary', patient: 'success' }[role] || 'info')

const loadUsers = async () => {
  loadingUsers.value = true
  try {
    const res = await request.get('/auth/users')
    if (res.code === 200) userList.value = res.data
  } catch (e) {
    // ignore
  } finally {
    loadingUsers.value = false
  }
}

const openAddDialog = () => {
  isEditing.value = false
  editingUserId.value = null
  userForm.value = { username: '', password: '', real_name: '', role: 'doctor', department: '', is_active: 1 }
  userDialogVisible.value = true
}

const openEditDialog = (row) => {
  isEditing.value = true
  editingUserId.value = row.id
  userForm.value = {
    username: row.username,
    password: '',
    real_name: row.real_name || '',
    role: row.role || 'doctor',
    department: row.department || '',
    is_active: row.is_active
  }
  userDialogVisible.value = true
}

const submitUser = async () => {
  if (!isEditing.value && !userForm.value.username) return ElMessage.warning('请输入用户名')
  savingUser.value = true
  try {
    if (isEditing.value) {
      const params = new URLSearchParams()
      if (userForm.value.real_name) params.append('real_name', userForm.value.real_name)
      if (userForm.value.role) params.append('role', userForm.value.role)
      if (userForm.value.department) params.append('department', userForm.value.department)
      if (userForm.value.password) params.append('password', userForm.value.password)
      params.append('is_active', userForm.value.is_active)
      await request.put(`/auth/users/${editingUserId.value}`, params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      })
      ElMessage.success('用户信息已更新')
    } else {
      const params = new URLSearchParams()
      params.append('username', userForm.value.username)
      params.append('password', userForm.value.password)
      params.append('real_name', userForm.value.real_name)
      params.append('role', userForm.value.role)
      params.append('department', userForm.value.department)
      await request.post('/auth/register', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      })
      ElMessage.success('用户创建成功')
    }
    userDialogVisible.value = false
    loadUsers()
  } catch (e) {
    const msg = e.response?.data?.msg || e.response?.data?.detail || '操作失败'
    ElMessage.error(msg)
  } finally {
    savingUser.value = false
  }
}

const deleteUser = async (row) => {
  if (row.username === 'admin') return ElMessage.warning('不能删除超级管理员')
  try {
    await ElMessageBox.confirm(`确定删除用户「${row.username}」吗？`, '删除确认', { type: 'warning' })
    await request.delete(`/auth/users/${row.id}`)
    ElMessage.success('用户已删除')
    loadUsers()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

// ── 系统信息 ──
const sysInfo = ref({})
const statCards = ref([])

const loadSystemInfo = async () => {
  try {
    const res = await request.get('/system/info')
    if (res.code === 200) {
      sysInfo.value = res.data
      const db = res.data.database || {}
      statCards.value = [
        { label: '用户总数', value: db.users || 0, color: '#409EFF' },
        { label: '患者总数', value: db.patients || 0, color: '#67C23A' },
        { label: '病历总数', value: db.records || 0, color: '#E6A23C' },
        { label: '诊断报告', value: db.reports || 0, color: '#F56C6C' },
      ]
    }
  } catch (e) {
    // not admin - ignore
  }
}

// ── 审计日志 ──
const auditItems = ref([])
const auditTotal = ref(0)
const auditPage = ref(1)
const auditPageSize = 20
const auditLevel = ref('')
const auditKeyword = ref('')
const loadingAudit = ref(false)

const auditLevelType = (level) => ({ ERROR: 'danger', WARNING: 'warning' }[level] || 'info')

const loadAudit = async () => {
  loadingAudit.value = true
  try {
    const res = await request.get('/system/audit', {
      params: {
        skip: (auditPage.value - 1) * auditPageSize,
        limit: auditPageSize,
        level: auditLevel.value || '',
        keyword: auditKeyword.value.trim()
      }
    })
    if (res.code === 200) {
      auditItems.value = res.data.items
      auditTotal.value = res.data.total
    }
  } catch (e) {
    // ignore
  } finally {
    loadingAudit.value = false
  }
}

const reloadAudit = () => {
  auditPage.value = 1
  loadAudit()
}

const onAuditPageChange = (page) => {
  auditPage.value = page
  loadAudit()
}

const refreshAudit = loadAudit

onMounted(() => {
  loadUsers()
  loadSystemInfo()
  loadAudit()
})
</script>

<style scoped>
.settings-page {
  max-width: 1000px;
  margin: 0 auto;
}

.settings-page h2 {
  margin: 0 0 20px;
  font-size: 20px;
}

.settings-tabs :deep(.el-tabs__header) {
  margin-bottom: 20px;
}

.tab-toolbar {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.tab-hint {
  font-size: 12px;
  color: var(--text-muted);
}

/* ── 统计卡片 ── */
.stat-card {
  text-align: center;
  border-radius: 10px;
  margin-bottom: 16px;
}

.stat-card :deep(.el-card__body) {
  padding: 24px;
}

.stat-value {
  font-size: 36px;
  font-weight: 700;
}

.stat-label {
  font-size: 14px;
  color: var(--text-secondary);
  margin-top: 8px;
}

/* ── 审计日志分页 ── */
.audit-pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
