<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { listBatches, cancelBatch } from '../../api/batch'
import { listProjects } from '../../api/project'
import { formatBackendTime } from '../../utils/datetime'
import {
  batchStatusTag, batchStatusLabel,
  batchTypeTag, batchTypeLabel,
} from '../../utils/status'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const loading = ref(false)
const list = ref([])
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

const projectIdFromRoute = computed(() =>
  route.params.projectId ? Number(route.params.projectId) : null
)
const isProjectScoped = computed(() => !!projectIdFromRoute.value)

const filters = reactive({
  project_id: projectIdFromRoute.value ?? null,
  batch_type: '',
  status: '',
  // TODO(Phase 1 Step 1-3-3后续): 后端 list_batches_with_filter 尚未实现 keyword 过滤，
  // 当前发送该参数会被静默忽略，不产生实际过滤效果
  keyword: '',
})

// 场景 B：独立访问时加载项目下拉选项
const projectOptions = ref([])

async function loadProjectOptions() {
  if (isProjectScoped.value) return
  try {
    const res = await listProjects({ page: 1, per_page: 200 })
    projectOptions.value = res.data.data.items ?? []
  } catch { /* 静默失败，下拉为空 */ }
}

async function load() {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      per_page: pagination.pageSize,
      ...(filters.project_id && { project_id: filters.project_id }),
      ...(filters.batch_type && { batch_type: filters.batch_type }),
      ...(filters.status     && { status: filters.status }),
      ...(filters.keyword    && { keyword: filters.keyword }),
    }
    const res = await listBatches(params)
    list.value = res.data.data.items ?? []
    pagination.total = res.data.data.total ?? 0
  } catch (err) {
    ElMessage.error(err?.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function onSearch() {
  pagination.page = 1
  await load()
}

async function onReset() {
  filters.batch_type = ''
  filters.status = ''
  filters.keyword = ''
  if (!isProjectScoped.value) filters.project_id = null
  await onSearch()
}

async function onPageChange(page) {
  pagination.page = page
  await load()
}

async function onCancel(row) {
  let reason
  try {
    const { value } = await ElMessageBox.prompt('请输入作废原因', '确认作废批次', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      inputType: 'textarea',
      inputValidator: v => !!v?.trim() || '作废原因不能为空',
      type: 'warning',
    })
    reason = value
  } catch { return }

  try {
    await cancelBatch(row.id, { reason, version: row.version })
    ElMessage.success('批次已作废')
    await load()
  } catch (err) {
    ElMessage.error(err?.response?.data?.message || '操作失败')
  }
}

function flowPathLabel(val) {
  return val === 'simplified' ? '简化流程' : '完整流程'
}

onMounted(async () => {
  await loadProjectOptions()
  await load()
})
</script>

<template>
  <div class="batch-list">
    <!-- 搜索栏 -->
    <el-form :inline="true" class="search-form">
      <el-form-item label="批次类型">
        <el-select v-model="filters.batch_type" clearable placeholder="全部" style="width: 130px">
          <el-option label="手动初版"  value="manual_init" />
          <el-option label="量产"      value="mass_prod" />
          <el-option label="加开-加量" value="addon_quantity" />
          <el-option label="加开-优化" value="addon_optimize" />
        </el-select>
      </el-form-item>

      <el-form-item label="状态">
        <el-select v-model="filters.status" clearable placeholder="全部" style="width: 110px">
          <el-option label="草稿"  value="draft" />
          <el-option label="进行中" value="in_progress" />
          <el-option label="已完成" value="completed" />
          <el-option label="已作废" value="cancelled" />
        </el-select>
      </el-form-item>

      <!-- 场景 B：独立访问时显示项目下拉 -->
      <el-form-item v-if="!isProjectScoped" label="所属项目">
        <el-select
          v-model="filters.project_id"
          clearable
          placeholder="全部项目"
          style="width: 180px"
        >
          <el-option
            v-for="p in projectOptions"
            :key="p.id"
            :label="`${p.project_code} ${p.project_name}`"
            :value="p.id"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="关键词">
        <!-- TODO(Phase 1 Step 1-3-3后续): keyword 参数后端暂未实现，输入后查询无过滤效果 -->
        <el-input
          v-model="filters.keyword"
          placeholder="批次号"
          clearable
          style="width: 160px"
          @keyup.enter="onSearch"
        />
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="onSearch">查询</el-button>
        <el-button @click="onReset">重置</el-button>
      </el-form-item>
    </el-form>

    <!-- 表格 -->
    <el-table :data="list" v-loading="loading" border stripe>
      <el-table-column label="批次号" min-width="150">
        <template #default="{ row }">
          <el-button type="primary" link @click="router.push('/batches/' + row.id)">
            {{ row.batch_no }}
          </el-button>
        </template>
      </el-table-column>

      <el-table-column label="批次类型" width="110">
        <template #default="{ row }">
          <el-tag :type="batchTypeTag(row.batch_type)">
            {{ batchTypeLabel(row.batch_type) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="流程路径" width="100">
        <template #default="{ row }">
          {{ flowPathLabel(row.flow_path) }}
        </template>
      </el-table-column>

      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="batchStatusTag(row.status)">
            {{ batchStatusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="期望日期" width="110">
        <template #default="{ row }">
          {{ row.expected_date ? formatBackendTime(row.expected_date, 'YYYY-MM-DD') : '—' }}
        </template>
      </el-table-column>

      <el-table-column label="创建时间" width="150">
        <template #default="{ row }">
          {{ formatBackendTime(row.created_at, 'YYYY-MM-DD HH:mm') }}
        </template>
      </el-table-column>

      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="router.push('/batches/' + row.id)">
            查看详情
          </el-button>
          <el-button
            v-if="auth.hasPermission('batch.edit')"
            type="primary"
            link
            :disabled="row.status === 'cancelled'"
            @click="router.push('/batches/' + row.id + '/edit')"
          >
            编辑
          </el-button>
          <el-button
            v-if="auth.hasPermission('batch.cancel')"
            type="danger"
            link
            :disabled="row.status === 'cancelled'"
            @click="onCancel(row)"
          >
            作废
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-bar">
      <el-pagination
        :current-page="pagination.page"
        :page-size="pagination.pageSize"
        :total="pagination.total"
        layout="total, prev, pager, next"
        @current-change="onPageChange"
      />
    </div>
  </div>
</template>

<style scoped>
.batch-list {
  padding: 16px;
}
.search-form {
  margin-bottom: 12px;
}
.pagination-bar {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
