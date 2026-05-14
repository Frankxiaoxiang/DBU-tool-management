<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { listBatches, getBatchById, createBatch, updateBatch, cancelBatch } from '../../api/batch'
import { listProjects } from '../../api/project'
import { formatBackendTime } from '../../utils/datetime'
import { batchTypeTag, batchTypeLabel } from '../../utils/status'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const mode     = computed(() => route.meta.mode)
const isCreate = computed(() => mode.value === 'create')
const isEdit   = computed(() => mode.value === 'edit')
const isDetail = computed(() => mode.value === 'detail')
const batchId  = computed(() => route.params.id ? Number(route.params.id) : null)

const prefilledProjectId = computed(() =>
  route.query.projectId ? Number(route.query.projectId) : null
)

const form = reactive({
  project_id:      null,
  batch_type:      '',
  parent_batch_id: null,
  flow_path:       'full',
  expected_date:   '',
  remark:          '',
  version:         null,
})

const batchNoDisplay     = ref('')
const projectCodeDisplay = ref('')
const batchStatus        = ref('')
const loading            = ref(false)
const submitting         = ref(false)
const formRef            = ref(null)

// Create mode: prefill project_id from route query
if (isCreate.value && prefilledProjectId.value) {
  form.project_id = prefilledProjectId.value
}

// ── addon 联动 ──────────────────────────────────────────────
const isAddon = computed(() =>
  form.batch_type === 'addon_quantity' || form.batch_type === 'addon_optimize'
)

watch(() => form.batch_type, (newType) => {
  if (newType !== 'addon_quantity' && newType !== 'addon_optimize') {
    form.parent_batch_id = null
    form.flow_path = 'full'
  }
})

const parentBatchOptions = ref([])

async function loadParentBatchOptions() {
  if (!isAddon.value || !form.project_id) return
  try {
    const res = await listBatches({ project_id: form.project_id, per_page: 200 })
    parentBatchOptions.value = (res.data.data.items ?? []).filter(b =>
      b.status !== 'cancelled' && b.id !== batchId.value
    )
  } catch {
    parentBatchOptions.value = []
  }
}

watch([() => form.project_id, isAddon], ([, addon]) => {
  if (addon) loadParentBatchOptions()
  else parentBatchOptions.value = []
})

// ── 项目下拉（create 模式）──────────────────────────────────
const projectOptions = ref([])

async function loadProjectOptions() {
  if (!isCreate.value) return
  try {
    const res = await listProjects({ page: 1, per_page: 200 })
    projectOptions.value = res.data.data.items ?? []
  } catch {
    projectOptions.value = []
  }
}

// ── 加载已有批次（edit / detail 模式）──────────────────────
async function loadBatch() {
  if (!batchId.value) return
  loading.value = true
  try {
    const res = await getBatchById(batchId.value)
    const data = res.data.data
    form.project_id      = data.project_id
    form.batch_type      = data.batch_type
    form.parent_batch_id = data.parent_batch_id ?? null
    form.flow_path       = data.flow_path ?? 'full'
    form.expected_date   = data.expected_date ?? ''
    form.remark          = data.remark ?? ''
    form.version         = data.version
    batchNoDisplay.value     = data.batch_no ?? ''
    projectCodeDisplay.value = data.project_code ?? ''
    batchStatus.value        = data.status ?? ''
  } catch (err) {
    ElMessage.error(err?.response?.data?.message || '加载批次失败')
    router.back()
  } finally {
    loading.value = false
  }
}

// ── 表单校验 ───────────────────────────────────────────────
const rules = {
  project_id: [{ required: true, message: '请选择项目',    trigger: 'change' }],
  batch_type:  [{ required: true, message: '请选择批次类型', trigger: 'change' }],
  parent_batch_id: [
    {
      validator: (rule, value, callback) => {
        if (isAddon.value && !value) {
          callback(new Error('addon 类型批次必须选择父批次'))
        } else {
          callback()
        }
      },
      trigger: 'change',
    },
  ],
}

// ── 提交 ───────────────────────────────────────────────────
async function onSubmit() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  const payload = {
    project_id:      form.project_id,
    batch_type:      form.batch_type,
    parent_batch_id: isAddon.value ? form.parent_batch_id : null,
    flow_path:       form.flow_path,
    expected_date:   form.expected_date || null,
    remark:          form.remark || null,
  }

  if (isEdit.value) {
    if (form.version === null || form.version === undefined) {
      ElMessage.error('版本号缺失，请刷新后重试')
      return
    }
    payload.version = form.version
  }

  submitting.value = true
  try {
    if (isCreate.value) {
      await createBatch(payload)
      ElMessage.success('批次创建成功')
    } else {
      await updateBatch(batchId.value, payload)
      ElMessage.success('批次更新成功')
    }
    router.back()
  } catch (err) {
    // 409 由 axios 拦截器处理，此处跳过
    if (err?.response?.status !== 409) {
      ElMessage.error(err?.response?.data?.message || '操作失败')
    }
  } finally {
    submitting.value = false
  }
}

// ── 作废（detail 模式）────────────────────────────────────
async function onCancelBatch() {
  let reason = ''
  try {
    const { value } = await ElMessageBox.prompt('请输入作废原因', '确认作废批次', {
      confirmButtonText: '确认',
      cancelButtonText:  '取消',
      inputType:         'textarea',
      inputValidator:    (v) => v?.trim() ? true : '作废原因不能为空',
      type:              'warning',
    })
    reason = value
  } catch {
    return
  }
  try {
    await cancelBatch(batchId.value, { reason, version: form.version })
    ElMessage.success('批次已作废')
    router.back()
  } catch (err) {
    if (err?.response?.status !== 409) {
      ElMessage.error(err?.response?.data?.message || '作废失败')
    }
  }
}

function flowPathLabel(val) {
  return val === 'simplified' ? '简化流程' : '完整流程'
}

onMounted(async () => {
  await loadProjectOptions()
  if (!isCreate.value) {
    await loadBatch()
    if (isAddon.value) await loadParentBatchOptions()
  }
})
</script>

<template>
  <div class="batch-form" v-loading="loading">
    <el-form
      ref="formRef"
      :model="form"
      :rules="isCreate || isEdit ? rules : {}"
      label-width="100px"
      style="max-width: 600px"
    >
      <!-- batch_no: hidden in create, readonly in edit/detail -->
      <el-form-item v-if="!isCreate" label="批次号">
        <span class="readonly-text">{{ batchNoDisplay }}</span>
      </el-form-item>

      <!-- project_id: editable dropdown in create, readonly in edit/detail -->
      <el-form-item label="所属项目" prop="project_id">
        <el-select
          v-if="isCreate"
          v-model="form.project_id"
          :disabled="!!prefilledProjectId"
          placeholder="请选择项目"
          style="width: 100%"
        >
          <el-option
            v-for="p in projectOptions"
            :key="p.id"
            :label="`${p.project_code} ${p.project_name}`"
            :value="p.id"
          />
        </el-select>
        <span v-else class="readonly-text">{{ projectCodeDisplay }}</span>
      </el-form-item>

      <!-- batch_type: editable in create, readonly tag in edit/detail -->
      <el-form-item label="批次类型" prop="batch_type">
        <el-select
          v-if="isCreate"
          v-model="form.batch_type"
          placeholder="请选择批次类型"
          style="width: 100%"
        >
          <el-option label="手动初版"  value="manual_init" />
          <el-option label="量产"      value="mass_prod" />
          <el-option label="加开-加量" value="addon_quantity" />
          <el-option label="加开-优化" value="addon_optimize" />
        </el-select>
        <el-tag v-else :type="batchTypeTag(form.batch_type)">
          {{ batchTypeLabel(form.batch_type) }}
        </el-tag>
      </el-form-item>

      <!-- parent_batch_id: only for addon types -->
      <el-form-item v-if="isAddon" label="父批次" prop="parent_batch_id">
        <el-select
          v-if="isCreate || isEdit"
          v-model="form.parent_batch_id"
          placeholder="请选择父批次"
          style="width: 100%"
        >
          <el-option
            v-for="b in parentBatchOptions"
            :key="b.id"
            :label="b.batch_no"
            :value="b.id"
          />
        </el-select>
        <span v-else class="readonly-text">{{ form.parent_batch_id ?? '—' }}</span>
      </el-form-item>

      <!-- flow_path: hidden for non-addon in create/edit; always shown in detail -->
      <el-form-item v-if="isAddon || isDetail" label="流程路径">
        <el-select
          v-if="(isCreate || isEdit) && isAddon"
          v-model="form.flow_path"
          style="width: 100%"
        >
          <el-option label="完整流程" value="full" />
          <el-option label="简化流程" value="simplified" />
        </el-select>
        <span v-else class="readonly-text">{{ flowPathLabel(form.flow_path) }}</span>
      </el-form-item>

      <!-- expected_date: date picker in create/edit, readonly text in detail -->
      <el-form-item label="期望日期">
        <el-date-picker
          v-if="isCreate || isEdit"
          v-model="form.expected_date"
          type="date"
          placeholder="请选择日期"
          value-format="YYYY-MM-DD"
          style="width: 100%"
        />
        <span v-else class="readonly-text">
          {{ form.expected_date ? formatBackendTime(form.expected_date, 'YYYY-MM-DD') : '—' }}
        </span>
      </el-form-item>

      <!-- remark: textarea in create/edit, readonly in detail -->
      <el-form-item label="备注">
        <el-input
          v-if="isCreate || isEdit"
          v-model="form.remark"
          type="textarea"
          :rows="3"
          placeholder="可选备注"
        />
        <span v-else class="readonly-text">{{ form.remark || '—' }}</span>
      </el-form-item>

      <!-- action buttons -->
      <el-form-item>
        <template v-if="isCreate || isEdit">
          <el-button type="primary" :loading="submitting" @click="onSubmit">提交</el-button>
          <el-button @click="router.back()">取消</el-button>
        </template>
        <template v-if="isDetail">
          <el-button
            v-if="auth.hasPermission('batch.edit')"
            type="primary"
            @click="router.push(`/batches/${batchId}/edit`)"
          >
            编辑
          </el-button>
          <el-button
            v-if="auth.hasPermission('batch.cancel')"
            type="danger"
            :disabled="batchStatus === 'cancelled'"
            @click="onCancelBatch"
          >
            作废
          </el-button>
          <el-button @click="router.back()">返回</el-button>
        </template>
      </el-form-item>
    </el-form>
  </div>
</template>

<style scoped>
.batch-form {
  padding: 24px;
}
.readonly-text {
  line-height: 32px;
  color: #606266;
}
</style>
