<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { listProjects, cancelProject } from '../../api/project'
import { formatBackendTime } from '../../utils/datetime'
import { projectStatusTag, projectStatusLabel, productTypeLabel, PRODUCT_TYPE_MAP } from '../../utils/status'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const loading = ref(false)
const tableData = ref([])

const filters = reactive({
  product_type: '',
  status: 'active',
  keyword: '',
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})

async function load() {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      per_page: pagination.pageSize,
      ...(filters.product_type && { product_type: filters.product_type }),
      ...(filters.status        && { status: filters.status }),
      ...(filters.keyword       && { keyword: filters.keyword }),
    }
    const res = await listProjects(params)
    tableData.value = res.data.data.items
    pagination.total = res.data.data.total
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

function onReset() {
  filters.product_type = ''
  filters.status = 'active'
  filters.keyword = ''
  pagination.page = 1
  load()
}

async function onPageChange(page) {
  pagination.page = page
  await load()
}

async function onCancel(row) {
  let reason
  try {
    const { value } = await ElMessageBox.prompt('请输入作废原因', '确认作废', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      inputType: 'textarea',
      inputValidator: v => !!v?.trim() || '原因不能为空',
    })
    reason = value
  } catch { return }

  try {
    await cancelProject(row.id, { reason, version: row.version })
    ElMessage.success('已作废')
    await load()
  } catch (err) {
    ElMessage.error(err?.response?.data?.message || '作废失败')
  }
}

onMounted(load)
</script>

<template>
  <div class="project-list">
    <!-- 搜索栏 -->
    <el-form :inline="true" class="search-form">
      <el-form-item label="产品线">
        <el-select v-model="filters.product_type" clearable placeholder="全部" style="width: 120px">
          <el-option
            v-for="(label, code) in PRODUCT_TYPE_MAP"
            :key="code"
            :label="label"
            :value="code"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="状态">
        <el-select v-model="filters.status" clearable placeholder="全部" style="width: 120px">
          <el-option label="进行中" value="active" />
          <el-option label="已关闭" value="closed" />
          <el-option label="已作废" value="cancelled" />
        </el-select>
      </el-form-item>
      <el-form-item label="关键词">
        <el-input
          v-model="filters.keyword"
          placeholder="项目编号 / 名称"
          clearable
          style="width: 200px"
          @keyup.enter="onSearch"
        />
      </el-form-item>
      <!-- TODO(Phase 6): 补充 owner_id 下拉过滤，依赖 GET /api/users 接口上线 -->
      <el-form-item>
        <el-button type="primary" @click="onSearch">查询</el-button>
        <el-button @click="onReset">重置</el-button>
      </el-form-item>
    </el-form>

    <!-- 工具栏 -->
    <div class="toolbar">
      <el-button
        v-if="auth.hasPermission('project.create')"
        type="primary"
        @click="router.push('/projects/new')"
      >
        新建项目
      </el-button>
    </div>

    <!-- 表格 -->
    <el-table :data="tableData" v-loading="loading" border stripe>
      <el-table-column prop="project_code" label="项目编号" width="120" />
      <el-table-column label="项目名称" min-width="160">
        <template #default="{ row }">
          <el-button type="primary" link @click="router.push('/projects/' + row.id)">
            {{ row.project_name }}
          </el-button>
        </template>
      </el-table-column>
      <el-table-column label="产品线" width="100">
        <template #default="{ row }">
          {{ productTypeLabel(row.product_type) }}
        </template>
      </el-table-column>
      <el-table-column prop="owner_name" label="负责人" width="100" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="projectStatusTag(row.status)">
            {{ projectStatusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="160">
        <template #default="{ row }">
          {{ formatBackendTime(row.created_at, 'YYYY-MM-DD HH:mm') }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="router.push('/projects/' + row.id)">
            查看详情
          </el-button>
          <el-button
            v-if="auth.hasPermission('project.edit')"
            type="primary"
            link
            @click="router.push('/projects/' + row.id + '/edit')"
          >
            编辑
          </el-button>
          <el-button
            v-if="auth.hasPermission('project.cancel')"
            type="danger"
            link
            :disabled="row.status !== 'active'"
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
.project-list {
  padding: 16px;
}
.search-form {
  margin-bottom: 12px;
}
.toolbar {
  margin-bottom: 12px;
}
.pagination-bar {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
