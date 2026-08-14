<template>
  <div class="recycle-page">
    <h2>🗑️ 回收站</h2>

    <div class="recycle-toolbar">
      <el-button type="danger" @click="clearBin" :loading="clearing">清空回收站</el-button>
      <el-button @click="loadAll" :loading="loading">刷新</el-button>
      <span class="recycle-hint">删除的患者/病历/报告先进回收站，支持级联恢复；彻底删除才物理清行与文件。</span>
    </div>

    <el-tabs v-model="activeTab" class="recycle-tabs">
      <!-- ═══ Tab 1: 患者 ═══ -->
      <el-tab-pane label="👤 患者" name="patients">
        <el-table :data="patients" border v-loading="loading" style="width:100%">
          <el-table-column label="ID" prop="id" width="70"/>
          <el-table-column label="姓名" prop="name" width="140"/>
          <el-table-column label="年龄" prop="age" width="80"/>
          <el-table-column label="性别" prop="gender" width="80"/>
          <el-table-column label="手机号" prop="phone" min-width="150"/>
          <el-table-column label="删除时间" width="170">
            <template #default="scope">{{ fmtTime(scope.row.deleted_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="scope">
              <el-button size="small" type="primary" @click="restore('patient', scope.row.id)">恢复</el-button>
              <el-button size="small" type="danger" @click="purge('patient', scope.row.id)">彻底删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- ═══ Tab 2: 病历 ═══ -->
      <el-tab-pane label="📋 病历" name="records">
        <el-table :data="records" border v-loading="loading" style="width:100%">
          <el-table-column label="ID" prop="id" width="70"/>
          <el-table-column label="患者ID" prop="patient_id" width="90"/>
          <el-table-column label="病历原文" prop="raw_text" min-width="260" show-overflow-tooltip/>
          <el-table-column label="创建时间" width="170">
            <template #default="scope">{{ fmtTime(scope.row.create_time) }}</template>
          </el-table-column>
          <el-table-column label="删除时间" width="170">
            <template #default="scope">{{ fmtTime(scope.row.deleted_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="scope">
              <el-button size="small" type="primary" @click="restore('record', scope.row.id)">恢复</el-button>
              <el-button size="small" type="danger" @click="purge('record', scope.row.id)">彻底删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- ═══ Tab 3: 报告 ═══ -->
      <el-tab-pane label="📄 报告" name="reports">
        <el-table :data="reports" border v-loading="loading" style="width:100%">
          <el-table-column label="ID" prop="id" width="70"/>
          <el-table-column label="病历ID" prop="record_id" width="90"/>
          <el-table-column label="诊断建议" prop="diagnosis_suggest" min-width="260" show-overflow-tooltip/>
          <el-table-column label="PDF" width="90">
            <template #default="scope">{{ scope.row.pdf_path ? '有' : '无' }}</template>
          </el-table-column>
          <el-table-column label="创建时间" width="170">
            <template #default="scope">{{ fmtTime(scope.row.create_time) }}</template>
          </el-table-column>
          <el-table-column label="删除时间" width="170">
            <template #default="scope">{{ fmtTime(scope.row.deleted_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="scope">
              <el-button size="small" type="primary" @click="restore('report', scope.row.id)">恢复</el-button>
              <el-button size="small" type="danger" @click="purge('report', scope.row.id)">彻底删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../utils/request'

const activeTab = ref('patients')
const patients = ref([])
const records = ref([])
const reports = ref([])
const loading = ref(false)
const clearing = ref(false)

// ISO 时间串 → YYYY-MM-DD HH:MM
const fmtTime = (v) => (v ? String(v).slice(0, 19).replace('T', ' ') : '')

const loadAll = async () => {
  loading.value = true
  try {
    const [p, r, rp] = await Promise.all([
      request.get('/recycle/patients', { params: { limit: 100 } }),
      request.get('/recycle/records', { params: { limit: 100 } }),
      request.get('/recycle/reports', { params: { limit: 100 } })
    ])
    if (p.code === 200) patients.value = p.data
    if (r.code === 200) records.value = r.data
    if (rp.code === 200) reports.value = rp.data
  } catch (e) {
    ElMessage.error('加载回收站失败')
  } finally {
    loading.value = false
  }
}

const restore = async (type, id) => {
  try {
    const res = await request.post(`/recycle/${type}/${id}/restore`)
    ElMessage.success(res.msg || '已恢复')
    loadAll()
  } catch (e) {
    ElMessage.error('恢复失败')
  }
}

const purge = async (type, id) => {
  try {
    await ElMessageBox.confirm('彻底删除后不可恢复（清行并删除关联文件），确定继续吗？', '彻底删除确认', {
      type: 'warning',
      confirmButtonText: '彻底删除',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }
  try {
    const res = await request.delete(`/recycle/${type}/${id}/purge`)
    ElMessage.success(res.msg || '已彻底删除')
    loadAll()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

const clearBin = async () => {
  try {
    await ElMessageBox.confirm('将清空回收站中全部患者/病历/报告（不可恢复），确定继续吗？', '清空回收站确认', {
      type: 'warning',
      confirmButtonText: '清空',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }
  clearing.value = true
  try {
    const res = await request.delete('/recycle/clear')
    ElMessage.success(res.msg || '回收站已清空')
    loadAll()
  } catch (e) {
    ElMessage.error('清空失败')
  } finally {
    clearing.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.recycle-page {
  max-width: 1100px;
  margin: 0 auto;
}

.recycle-page h2 {
  margin: 0 0 20px;
  font-size: 20px;
}

.recycle-toolbar {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.recycle-hint {
  font-size: 12px;
  color: var(--text-muted);
}

.recycle-tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
}
</style>
