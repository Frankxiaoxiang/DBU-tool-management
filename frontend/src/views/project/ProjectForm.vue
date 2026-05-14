<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getProjectById, createProject, updateProject,
  transferOwner, cancelProject, syncProjectTemplates,
} from '../../api/project'
import { projectStatusTag, projectStatusLabel, productTypeLabel, PRODUCT_TYPE_MAP } from '../../utils/status'
import { useAuthStore } from '../../stores/auth'

const route  = useRoute()
const router = useRouter()
const auth   = useAuthStore()

const mode     = computed(() => route.meta.mode || 'detail')
const isCreate = computed(() => mode.value === 'create')
const isEdit   = computed(() => mode.value === 'edit')
const isDetail = computed(() => mode.value === 'detail')

const loading = ref(false)
const saving  = ref(false)
const formRef = ref(null)

const form = reactive({
  project_code:     '',
  project_name:     '',
  product_type:     '',
  project_owner_id: null,
  owner_name:       '',
  status:           '',
  version:          null,
})

const rules = {
  project_code: [
    { required: true, message: '请输入项目代号', trigger: 'blur' },
    { pattern: /^[A-Z]{2,6}$/, message: '须为 2–6 位大写字母', trigger: 'blur' },
  ],
  project_name: [
    { required: true, message: '请输入项目名称', trigger: 'blur' },
    { max: 128, message: '最多 128 个字符', trigger: 'blur' },
  ],
  product_type: [
    { required: true, message: '请选择产品线', trigger: 'change' },
  ],
}

const pageTitle = computed(() => {
  if (isCreate.value) return '新建项目'
  if (isEdit.value)   return '编辑项目'
  return '项目详情'
})

// create 模式：owner_id 默认填当前用户；其他模式从后端加载
// TODO(Phase 6): 替换为用户下拉，依赖 GET /api/users 接口
onMounted(async () => {
  if (isCreate.value) {
    form.project_owner_id = auth.user?.id ?? null
    return
  }
  loading.value = true
  try {
    const res = await getProjectById(route.params.id)
    Object.assign(form, res.data.data)
  } catch (err) {
    ElMessage.error(err?.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
})

async function onSubmit() {
  await formRef.value.validate()
  try {
    await ElMessageBox.confirm(
      isCreate.value ? '确认新建项目？' : '确认保存修改？',
      '提示',
      { type: 'warning' },
    )
  } catch { return }

  saving.value = true
  try {
    if (isCreate.value) {
      await createProject({
        project_code:     form.project_code,
        project_name:     form.project_name,
        product_type:     form.product_type,
        project_owner_id: form.project_owner_id,
      })
      ElMessage.success('项目创建成功')
    } else {
      // PUT 全量：project_name + product_type + version（乐观锁必带）
      await updateProject(route.params.id, {
        project_name: form.project_name,
        product_type: form.product_type,
        version:      form.version,
      })
      ElMessage.success('保存成功')
    }
    router.push('/projects')
  } catch (err) {
    // 409 由全局拦截器弹窗处理，此处只捕获其他错误
    ElMessage.error(err?.response?.data?.message || '操作失败')
  } finally {
    saving.value = false
  }
}

async function onTransferOwner() {
  let newOwnerId
  try {
    const { value } = await ElMessageBox.prompt(
      '请输入新负责人的用户 ID',
      '转移负责人',
      {
        confirmButtonText: '确认',
        cancelButtonText:  '取消',
        inputType:         'number',
        inputValidator:    v => (Number.isInteger(Number(v)) && Number(v) > 0) || '请输入有效的用户 ID',
        // TODO(Phase 6): 替换为用户下拉选择
      },
    )
    newOwnerId = Number(value)
  } catch { return }

  try {
    await transferOwner(route.params.id, { new_owner_id: newOwnerId, version: form.version })
    ElMessage.success('负责人已转移')
    const res = await getProjectById(route.params.id)
    Object.assign(form, res.data.data)
  } catch (err) {
    ElMessage.error(err?.response?.data?.message || '转移失败')
  }
}

async function onCancel() {
  let reason
  try {
    const { value } = await ElMessageBox.prompt('请输入作废原因', '确认作废', {
      confirmButtonText: '确认',
      cancelButtonText:  '取消',
      inputType:         'textarea',
      inputValidator:    v => !!v?.trim() || '原因不能为空',
    })
    reason = value
  } catch { return }

  try {
    await cancelProject(route.params.id, { reason, version: form.version })
    ElMessage.success('项目已作废')
    router.push('/projects')
  } catch (err) {
    ElMessage.error(err?.response?.data?.message || '作废失败')
  }
}

async function onSyncTemplates() {
  try {
    await ElMessageBox.confirm(
      '确认要把模板库中本项目产品线下新增的模板追加到本项目快照吗？已有快照不会被覆盖。',
      '追加同步模板库',
      { type: 'warning', confirmButtonText: '确认追加', cancelButtonText: '取消' },
    )
  } catch { return }

  try {
    const res = await syncProjectTemplates(route.params.id)
    const added = res.data.data.added_count
    ElMessage.success(`已追加 ${added} 条模板`)
  } catch (err) {
    ElMessage.error(err?.response?.data?.message || '同步失败')
  }
}
</script>

<template>
  <div v-loading="loading" class="project-form">
    <!-- 页头 -->
    <div class="page-header">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item style="cursor:pointer" @click="router.push('/projects')">
          项目管理
        </el-breadcrumb-item>
        <el-breadcrumb-item>{{ pageTitle }}</el-breadcrumb-item>
      </el-breadcrumb>
      <h2 class="page-title">{{ pageTitle }}</h2>
    </div>

    <!-- 表单 -->
    <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" class="form-body">

      <!-- project_code：create 模式可编辑，edit/detail 只读 -->
      <el-form-item v-if="isCreate" label="项目代号" prop="project_code">
        <el-input
          v-model="form.project_code"
          placeholder="2–6 位大写字母，如 SUSV"
          style="width: 240px"
        />
      </el-form-item>
      <el-form-item v-else label="项目代号">
        <span class="readonly-text">{{ form.project_code }}</span>
      </el-form-item>

      <!-- project_name -->
      <el-form-item label="项目名称" prop="project_name">
        <el-input
          v-model="form.project_name"
          :disabled="isDetail"
          maxlength="128"
          show-word-limit
          style="width: 360px"
        />
      </el-form-item>

      <!-- product_type -->
      <el-form-item label="产品线" prop="product_type">
        <el-select
          v-model="form.product_type"
          :disabled="isDetail"
          placeholder="请选择"
          style="width: 160px"
        >
          <el-option
            v-for="(label, code) in PRODUCT_TYPE_MAP"
            :key="code"
            :label="label"
            :value="code"
          />
        </el-select>
      </el-form-item>

      <!-- project_owner_id / owner_name -->
      <el-form-item label="负责人">
        <template v-if="isCreate">
          <span class="readonly-text">当前登录用户（ID: {{ form.project_owner_id }}）</span>
        </template>
        <template v-else-if="isDetail">
          <span class="readonly-text">{{ form.owner_name }}</span>
        </template>
        <!-- edit 模式：不展示，owner 变更走 detail 的"转移负责人"按钮 -->
      </el-form-item>

      <!-- status（仅 detail 模式） -->
      <el-form-item v-if="isDetail" label="状态">
        <el-tag :type="projectStatusTag(form.status)">
          {{ projectStatusLabel(form.status) }}
        </el-tag>
      </el-form-item>

    </el-form>

    <!-- 操作区：create / edit 模式 -->
    <div v-if="!isDetail" class="action-bar">
      <el-button type="primary" :loading="saving" @click="onSubmit">保存</el-button>
      <el-button @click="router.back()">取消</el-button>
    </div>

    <!-- 操作区：detail 模式 -->
    <div v-if="isDetail" class="action-bar">
      <el-button
        v-if="auth.hasPermission('project.edit') && form.status === 'active'"
        type="primary"
        @click="router.push('/projects/' + route.params.id + '/edit')"
      >
        编辑
      </el-button>
      <el-button
        v-if="auth.hasPermission('project.transfer_owner') && form.status === 'active'"
        @click="onTransferOwner"
      >
        转移负责人
      </el-button>
      <el-button
        v-if="auth.hasPermission('project.cancel') && form.status === 'active'"
        type="danger"
        plain
        @click="onCancel"
      >
        作废
      </el-button>
      <!-- 追加同步模板库：仅 super_admin / pm 可见，仅 active 项目可操作 -->
      <el-button
        v-if="auth.hasPermission('project.sync_templates') && form.status === 'active'"
        @click="onSyncTemplates"
      >追加同步模板库</el-button>
      <el-button @click="router.push('/projects')">返回列表</el-button>
    </div>
  </div>
</template>

<style scoped>
.project-form {
  padding: 24px;
  max-width: 720px;
}
.page-header {
  margin-bottom: 24px;
}
.page-title {
  margin: 12px 0 0;
  font-size: 20px;
  font-weight: 600;
}
.form-body {
  margin-bottom: 16px;
}
.readonly-text {
  color: #606266;
  line-height: 32px;
}
.action-bar {
  display: flex;
  gap: 8px;
  padding-left: 100px;
}
</style>
