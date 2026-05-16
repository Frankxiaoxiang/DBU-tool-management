<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listFixtures } from '../../api/fixture'
import { formatBackendTime } from '../../utils/datetime'
import { useAuthStore } from '../../stores/auth'
import { FIXTURE_STATUS_MAP } from '../../utils/status'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

// 场景 A：路由带 batchId（从批次下钻）；场景 B：无路由参数（全局列表）
const isScenarioA = computed(() => !!route.params.batchId)

const loading = ref(false)
const list = ref([])
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

const filters = reactive({
  project_id:     route.params.projectId ? Number(route.params.projectId) : null,
  batch_id:       route.params.batchId   ? Number(route.params.batchId)   : null,
  current_status: null,
  fixture_code:   '',
})

// 状态下拉选项，从 status.js 动态派生，禁止组件内硬编码
const statusOptions = Object.entries(FIXTURE_STATUS_MAP).map(([code, val]) => ({
  value: code,
  label: val.label,
}))

function fixtureStatusType(code) {
  return FIXTURE_STATUS_MAP[code]?.type || 'info'
}

function fixtureStatusLabel(code) {
  return FIXTURE_STATUS_MAP[code]?.label || code
}

async function load() {
  loading.value = true
  try {
    const params = { page: pagination.page, per_page: pagination.pageSize }
    if (filters.project_id)     params.project_id     = filters.project_id
    if (filters.batch_id)       params.batch_id       = filters.batch_id
    if (filters.current_status) params.current_status = filters.current_status
    if (filters.fixture_code)   params.fixture_code   = filters.fixture_code
    const res = await listFixtures(params)
    list.value = res.data.data.items ?? []
    pagination.total = res.data.data.total ?? 0
  } catch (err) {
    // 409 由 request.js 拦截器统一处理，此处只处理其他错误
    if (err?.response?.status !== 409) {
      ElMessage.error(err?.response?.data?.message || '加载失败')
    }
  } finally {
    loading.value = false
  }
}

function onSearch() {
  pagination.page = 1
  load()
}

function onReset() {
  filters.current_status = null
  filters.fixture_code = ''
  // 场景 A：project_id / batch_id 锁定路由参数，不可清空
  if (!isScenarioA.value) {
    filters.project_id = null
    filters.batch_id = null
  }
  onSearch()
}

function goDetail(row) {
  router.push('/fixtures/' + row.id)
}

function goEdit(row) {
  router.push('/fixtures/' + row.id + '/edit')
}

// 占位 — 状态变更（Step 2-3-3 接入后替换处理函数）
function onChangeStatus(row) {
  console.warn('TODO: Step 2-3-3 status change', row.id)
  ElMessage.info('该功能开发中')
}

// 占位 — 版本升级（Step 2-4-1 接入后替换处理函数）
function onVersionBump(row) {
  console.warn('TODO: Step 2-4-1 version bump', row.id)
  ElMessage.info('该功能开发中')
}

onMounted(load)
</script>

<template>
  <div class="fixture-list">
    <!-- 搜索栏 -->
    <el-form :inline="true" class="search-form">
      <el-form-item label="项目 ID">
        <el-input
          v-model="filters.project_id"
          type="number"
          placeholder="输入项目 ID"
          clearable
          style="width: 120px"
          :disabled="isScenarioA"
          @keyup.enter="onSearch"
        />
      </el-form-item>

      <el-form-item label="批次 ID">
        <el-input
          v-model="filters.batch_id"
          type="number"
          placeholder="输入批次 ID"
          clearable
          style="width: 120px"
          :disabled="isScenarioA"
          @keyup.enter="onSearch"
        />
      </el-form-item>

      <el-form-item label="状态">
        <el-select v-model="filters.current_status" clearable placeholder="全部" style="width: 150px">
          <el-option
            v-for="opt in statusOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="治具编号">
        <el-input
          v-model="filters.fixture_code"
          placeholder="输入治具编号搜索"
          clearable
          style="width: 180px"
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
      <el-table-column label="治具编号" min-width="170">
        <template #default="{ row }">
          <el-button type="primary" link @click="goDetail(row)">
            {{ row.fixture_code }}
          </el-button>
        </template>
      </el-table-column>

      <el-table-column label="所属批次" width="90">
        <template #default="{ row }">{{ row.batch_id }}</template>
      </el-table-column>

      <el-table-column label="治具型号" width="110" prop="fixture_type_code" />

      <el-table-column label="套号" width="70">
        <template #default="{ row }">#{{ row.set_no }}</template>
      </el-table-column>

      <el-table-column label="当前版本" width="90" prop="current_version_code" />

      <el-table-column label="状态" width="130">
        <template #default="{ row }">
          <el-tag :type="fixtureStatusType(row.current_status)">
            {{ fixtureStatusLabel(row.current_status) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="供应商" width="80">
        <template #default="{ row }">{{ row.supplier_id ?? '—' }}</template>
      </el-table-column>

      <el-table-column label="计划到货日" width="120">
        <template #default="{ row }">
          {{ row.planned_arrival_date ? formatBackendTime(row.planned_arrival_date, 'YYYY-MM-DD') : '—' }}
        </template>
      </el-table-column>

      <el-table-column label="创建时间" width="150">
        <template #default="{ row }">
          {{ formatBackendTime(row.created_at, 'YYYY-MM-DD HH:mm') }}
        </template>
      </el-table-column>

      <el-table-column label="操作" width="230" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="goDetail(row)">查看详情</el-button>
          <el-button
            v-if="auth.hasPermission('fixture.edit')"
            type="primary"
            link
            @click="goEdit(row)"
          >
            编辑
          </el-button>
          <el-button
            v-if="auth.hasPermission('fixture.status.me')"
            type="warning"
            link
            @click="onChangeStatus(row)"
          >
            状态变更
          </el-button>
          <el-button
            v-if="auth.hasPermission('fixture.version_bump')"
            type="info"
            link
            @click="onVersionBump(row)"
          >
            版本升级
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-bar">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        layout="total, prev, pager, next"
        @current-change="load"
        @size-change="onSearch"
      />
    </div>
  </div>
</template>

<style scoped>
.fixture-list {
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
