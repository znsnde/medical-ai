<template>
  <div>
    <h2>我的病历</h2>
    <p style="color:var(--text-secondary);margin:4px 0 20px;">查看自己的病历和诊断记录</p>

    <el-table :data="records" border v-loading="loading" style="width:100%">
      <el-table-column label="病历ID" prop="id" width="80"/>
      <el-table-column label="病历内容" min-width="300">
        <template #default="scope">
          <span v-if="scope.row.raw_text" style="font-size:13px;">{{ scope.row.raw_text.slice(0, 100) }}...</span>
          <span v-else style="color:var(--text-muted);">无内容</span>
        </template>
      </el-table-column>
      <el-table-column label="诊断" min-width="200">
        <template #default="scope">
          <el-tag v-if="scope.row.structured_data?.diagnosis?.length" type="success" size="small">
            {{ scope.row.structured_data.diagnosis.join('、') }}
          </el-tag>
          <span v-else style="color:var(--text-muted);">待诊断</span>
        </template>
      </el-table-column>
      <el-table-column label="日期" prop="create_time" width="170"/>
    </el-table>

    <el-empty v-if="!loading && records.length === 0" description="暂无病历记录" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../utils/request'

const records = ref([])
const loading = ref(false)

const loadRecords = async () => {
  loading.value = true
  try {
    const res = await request.get('/patient/my-records')
    if (res.code === 200) records.value = res.data || []
  } catch (e) {
    ElMessage.error('获取病历失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadRecords)
</script>
