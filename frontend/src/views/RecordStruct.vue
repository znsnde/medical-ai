<template>
  <div>
    <h2>病历智能结构化录入（文本 + 影像多模态）</h2>
    <el-card style="margin:20px 0;">
      <el-form label-width="120px">
        <el-form-item label="患者选择">
          <el-select v-model="selectedPatientId" placeholder="请先选择患者" filterable style="width:300px;">
            <el-option
              v-for="p in patientList"
              :key="p.id"
              :label="`${p.name} (ID:${p.id})`"
              :value="p.id"
            />
          </el-select>
          <el-button size="small" @click="loadPatientList" style="margin-left:10px;">刷新患者列表</el-button>
        </el-form-item>

        <el-form-item label="原始病历文本">
          <el-input v-model="rawText" type="textarea" rows="8" placeholder="输入患者病历原始文本内容"></el-input>
        </el-form-item>

        <!-- 新增：影像文件上传 -->
        <el-form-item label="上传影像文件">
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
            <el-button type="primary" @click="imageInput?.click()">
              {{ selectedImage ? '重新选择' : '选择医学影像' }}
            </el-button>
            <span v-if="selectedImage" style="color:#67c23a;font-size:13px;">
              ✅ {{ selectedImage.name }} ({{ (selectedImage.size / 1024).toFixed(1) }}KB)
              <el-button text type="danger" size="small" @click="selectedImage=null">清除</el-button>
            </span>
            <span v-else style="color:var(--text-muted);font-size:12px;">
              支持 DICOM(.dcm)、JPG、PNG 格式
            </span>
          </div>
          <input
            ref="imageInput"
            type="file"
            accept=".dcm,.dicom,.jpg,.jpeg,.png"
            style="display:none"
            @change="handleImageChange"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="submitRecord" :loading="structuring" size="large">
            {{ structuring ? 'AI多模态解析中...' : '提交多模态结构化解析' }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 结构化结果展示（增强版） -->
    <el-card v-if="result" style="margin-top:20px;">
      <template #header>
        <span style="font-weight:bold;font-size:16px;">
          🧠 AI多模态结构化抽取结果
          <el-tag v-if="result.image_analysis" type="warning" style="margin-left:10px;">含影像分析</el-tag>
        </span>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="症状" :span="2">
          {{ result.structured_data?.symptom?.length ? result.structured_data.symptom.join('、') : '未检出' }}
        </el-descriptions-item>
        <el-descriptions-item label="既往史" :span="2">
          {{ result.structured_data?.past_history?.length ? result.structured_data.past_history.join('、') : '未检出' }}
        </el-descriptions-item>
        <el-descriptions-item label="诊断" :span="2">
          {{ result.structured_data?.diagnosis?.length ? result.structured_data.diagnosis.join('、') : '未检出' }}
        </el-descriptions-item>
        <el-descriptions-item label="用药" :span="2">
          {{ result.structured_data?.medicine?.length ? result.structured_data.medicine.join('、') : '未检出' }}
        </el-descriptions-item>
        <!-- 如果是多模态分析，显示影像分析 -->
        <el-descriptions-item v-if="result.image_analysis" label="影像分析" :span="2">
          <pre style="margin:0;white-space:pre-wrap;background:#fdf6ec;padding:8px;border-radius:4px;">{{ result.image_analysis }}</pre>
        </el-descriptions-item>
        <el-descriptions-item v-if="result.combined_diagnosis" label="综合诊断意见" :span="2">
          <pre style="margin:0;white-space:pre-wrap;background:#f0f9eb;padding:8px;border-radius:4px;">{{ result.combined_diagnosis }}</pre>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 历史病历列表 -->
    <h3 style="margin-top:30px;">历史病历记录</h3>
    <el-table :data="recordList" border v-loading="loading" style="width:100%">
      <el-table-column label="病历ID" prop="id" width="80"/>
      <el-table-column label="患者ID" prop="patient_id" width="80"/>
      <el-table-column label="结构化数据" min-width="180">
        <template #default="scope">
          <el-tag v-if="scope.row.structured_data?.symptom?.length">症状:{{ scope.row.structured_data.symptom.join('、') }}</el-tag>
          <span v-else>待解析</span>
        </template>
      </el-table-column>
      <el-table-column label="影像文件" width="120">
        <template #default>
          <el-tag type="success">参考影像</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" prop="create_time" width="170"/>
      <el-table-column label="操作" width="280">
        <template #default="scope">
          <el-button size="small" type="primary" @click="viewRecord(scope.row)">查看</el-button>
          <el-button size="small" type="success" @click="goAiDiagnosis(scope.row)">
            AI诊断
          </el-button>
          <el-button size="small" @click="viewDicom(scope.row)">
            影像
          </el-button>
          <el-button size="small" type="danger" @click="deleteRecord(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 查看详情弹窗 -->
    <el-dialog v-model="detailVisible" title="病历详情" width="700px">
      <p><strong>患者ID：</strong>{{ currentRecord?.patient_id }}</p>
      <p><strong>原始文本：</strong></p>
      <p style="background:#f5f7fa;padding:10px;border-radius:4px;">{{ currentRecord?.raw_text }}</p>
      <p v-if="currentRecord?.dicom_file_path">
        <strong>影像文件：</strong>{{ currentRecord.dicom_file_path }}
        <el-button size="small" style="margin-left:10px;" @click="viewDicom(currentRecord)">查看影像</el-button>
      </p>
      <p><strong>结构化数据：</strong></p>
      <pre style="background:#f5f7fa;padding:10px;border-radius:4px;">{{ JSON.stringify(currentRecord?.structured_data, null, 2) }}</pre>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../utils/request'

const router = useRouter()

const imageInput = ref(null)
const selectedPatientId = ref(null)
const rawText = ref('')
const selectedImage = ref(null)
const result = ref(null)
const structuring = ref(false)
const loading = ref(false)
const patientList = ref([])
const recordList = ref([])
const detailVisible = ref(false)
const currentRecord = ref(null)

// 加载患者列表
const loadPatientList = async () => {
  try {
    const res = await request.get('/patient/list/all')
    if (res.code === 200) patientList.value = res.data
  } catch (e) {
    ElMessage.error('获取患者列表失败')
  }
}

// 选择影像文件
const handleImageChange = (e) => {
  const files = e.target.files
  if (files && files.length > 0) {
    selectedImage.value = files[0]
  }
  e.target.value = ''
}

// 提交结构化解析（文本 + 可选影像）
const submitRecord = async () => {
  if (!selectedPatientId.value) return ElMessage.warning('请选择患者')
  if (!rawText.value) return ElMessage.warning('请输入病历文本')

  structuring.value = true
  try {
    const form = new FormData()
    form.append('patient_id', selectedPatientId.value)
    form.append('raw_text', rawText.value)
    if (selectedImage.value) {
      form.append('image_file', selectedImage.value)
    }
    const res = await request.post('/record/struct', form)
    if (res.code === 200) {
      result.value = res.data
      ElMessage.success(selectedImage.value ? '多模态结构化解析完成' : '结构化解析完成')
      rawText.value = ''
      selectedImage.value = null
      loadRecordList()
    } else {
      ElMessage.error(res.msg)
    }
  } catch (e) {
    const msg = e.response?.data?.detail || e.message || '请求失败'
    ElMessage.error(`解析失败：${msg}`)
  } finally {
    structuring.value = false
  }
}

// 加载病历列表
const loadRecordList = async () => {
  loading.value = true
  try {
    const pid = selectedPatientId.value
    const res = await request.get(`/record/patient/${pid}`, { params: { skip: 0, limit: 50 } })
    if (res.code === 200) recordList.value = res.data
  } finally {
    loading.value = false
  }
}

// 查看病历详情
const viewRecord = (record) => {
  currentRecord.value = record
  detailVisible.value = true
}

// 删除病历
const deleteRecord = async (record) => {
  try {
    await ElMessageBox.confirm(`确定删除病历 #${record.id} 吗？此操作不可恢复。`, '删除确认', {
      type: 'warning',
      confirmButtonText: '确定删除',
      cancelButtonText: '取消'
    })
    const res = await request.delete(`/record/${record.id}`)
    if (res.code === 200) {
      ElMessage.success('病历已删除')
      loadRecordList()
    } else {
      ElMessage.error(res.msg)
    }
  } catch (e) {
    if (e !== 'cancel') {
      const msg = e.response?.data?.detail || e.message || '删除失败'
      ElMessage.error(msg)
    }
  }
}

// 跳转到AI诊断（携带病历ID）
const goAiDiagnosis = (record) => {
  router.push({ path: '/diagnosis', query: { record_id: record.id } })
}

// 跳转到DICOM影像查看
const viewDicom = (record) => {
  router.push(`/dicom/${record.id}`)
}

onMounted(() => {
  loadPatientList()
})

// 切换患者时重新加载历史病历
watch(selectedPatientId, (newVal) => {
  if (newVal) {
    loadRecordList()
  } else {
    recordList.value = []
  }
})
</script>
