<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getFixtureById, createFixture, updateFixture, bumpFixtureVersion } from '../../api/fixture'
import { listBatches } from '../../api/batch'
import { formatBackendTime } from '../../utils/datetime'
import { FIXTURE_STATUS_MAP } from '../../utils/status'
import { useAuthStore } from '../../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const mode = computed(() => route.meta?.mode || 'create')
const isCreate = computed(() => mode.value === 'create')
const readOnly = computed(() => mode.value === 'detail')

const loading = ref(false)
const submitting = ref(false)
const formRef = ref(null)

const form = reactive({
  batch_id:             null,
  fixture_type_code:    '',
  quantity:             1,           // create 专属，其余模式不显示不提交
  supplier_id:          null,
  planned_arrival_date: null,
  lead_time_days:       null,
  version:              null,        // 乐观锁，edit 模式从 GET 响应继承（§e.5）
  // 以下字段 edit/detail 只读展示，前端不拼接、不提交（§e.7）
  fixture_code:         '',
  current_version_code: '',
  current_status:       '',
})

// create 模式：批次下拉数据源
const batches = ref([])

async function loadBatches() {
  try {
    const res = await listBatches({ per_page: 200 })
    batches.value = (res.data.data.items ?? []).filter(b => b.status !== 'cancelled')
  } catch {
    // 静默失败，下拉为空
  }
}

const rules = {
  batch_id: [
    { required: true, message: '请选择所属批次', trigger: 'change' },
  ],
  fixture_type_code: [
    { required: true, message: '请输入治具型号代号', trigger: 'blur' },
  ],
}

onMounted(async () => {
  if (isCreate.value) {
    await loadBatches()
    return
  }
  // edit / detail：拉取治具详情回填
  loading.value = true
  try {
    const res = await getFixtureById(route.params.id)
    const d = res.data.data
    form.batch_id             = d.batch_id
    form.fixture_type_code    = d.fixture_type_code
    form.supplier_id          = d.supplier_id
    // 时间回显：formatBackendTime 返回 'YYYY-MM-DD' 字符串，与 el-date-picker value-format 一致（§e.10）
    form.planned_arrival_date = d.planned_arrival_date
      ? formatBackendTime(d.planned_arrival_date, 'YYYY-MM-DD')
      : null
    form.lead_time_days       = d.lead_time_days
    form.fixture_code         = d.fixture_code          // 只读展示，前端不拼接（§e.7）
    form.current_version_code = d.current_version_code  // 只读展示
    form.current_status       = d.current_status        // 只读展示
    form.version              = d.version               // 乐观锁必须继承（§e.5）
  } catch (err) {
    if (err?.response?.status !== 409) {
      ElMessage.error(err?.response?.data?.message || '加载失败')
    }
  } finally {
    loading.value = false
  }
})

async function onSubmit() {
  // el-form 校验（仅 create 模式有必填校验规则）
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  // 二段 try/catch（§d Rule 9）
  try {
    await ElMessageBox.confirm(
      isCreate.value ? '确认新建治具？' : '确认保存修改？',
      '提示',
      { type: 'warning' }
    )
  } catch { return }  // 用户取消，静默退出

  submitting.value = true
  try {
    if (isCreate.value) {
      const payload = {
        batch_id:          form.batch_id,
        fixture_type_code: form.fixture_type_code.trim(),
      }
      if (form.supplier_id)          payload.supplier_id          = Number(form.supplier_id)
      if (form.planned_arrival_date) payload.planned_arrival_date = form.planned_arrival_date
      if (form.lead_time_days)       payload.lead_time_days       = form.lead_time_days

      // 逐套创建：后端 generate_fixture_code 每次自动递增套号，无需传 set_no
      for (let i = 0; i < form.quantity; i++) {
        await createFixture(payload)
      }
      ElMessage.success(`治具创建成功，共 ${form.quantity} 套，编码由系统自动生成`)
    } else {
      // edit 模式：payload 只含可编辑字段 + version（§d Rule 5 + §e.5）
      const payload = {
        supplier_id:          form.supplier_id ? Number(form.supplier_id) : null,
        planned_arrival_date: form.planned_arrival_date || null,
        lead_time_days:       form.lead_time_days || null,
        version:              form.version,
      }
      await updateFixture(route.params.id, payload)
      ElMessage.success('已保存')
    }
    router.push('/fixtures')
  } catch (err) {
    // 409 由 api/request.js 全局拦截器处理，此处只处理其他错误
    if (err?.response?.status !== 409) {
      ElMessage.error(err?.response?.data?.message || '操作失败')
    }
  } finally {
    submitting.value = false
  }
}

async function onVersionBump() {
  const currentVer = form.current_version_code || '当前版本'

  // 二段 try/catch（CLAUDE.md §d Rule 9）
  try {
    await ElMessageBox.confirm(
      `确认将图纸版本从「${currentVer}」升级到下一版本？此操作不可撤销。`,
      '图纸版本升级',
      { type: 'warning', confirmButtonText: '确认升级', cancelButtonText: '取消' }
    )
  } catch { return }  // 用户取消，静默退出

  try {
    const res = await bumpFixtureVersion(route.params.id, { version: form.version })
    // 后端返回更新后的 fixture 全字段（含新 current_version_code 和递增后 version）
    const updated = res.data.data
    form.current_version_code = updated.current_version_code
    form.version = updated.version
    ElMessage.success(`版本已升级为 ${updated.current_version_code}`)
  } catch (err) {
    // 409 由 api/request.js 全局拦截器处理，此处只处理其他错误
    if (err?.response?.status !== 409) {
      ElMessage.error(err?.response?.data?.message || '版本升级失败，请重试')
    }
  }
}

function fixtureStatusType(code) {
  return FIXTURE_STATUS_MAP[code]?.type || 'info'
}

function fixtureStatusLabel(code) {
  return FIXTURE_STATUS_MAP[code]?.label || code
}
</script>

<template>
  <div class="fixture-form-page" v-loading="loading">
    <h2>{{ isCreate ? '新建治具' : readOnly ? '治具详情' : '编辑治具' }}</h2>

    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      :disabled="readOnly"
      label-width="130px"
      style="max-width: 620px"
    >
      <!-- ── create：所属批次下拉 ──────────────────────────── -->
      <el-form-item v-if="isCreate" label="所属批次" prop="batch_id">
        <el-select v-model="form.batch_id" placeholder="请选择批次" filterable style="width: 100%">
          <el-option
            v-for="b in batches"
            :key="b.id"
            :value="b.id"
            :label="b.batch_no"
          />
        </el-select>
      </el-form-item>

      <!-- ── edit / detail：批次 ID 只读 ─────────────────── -->
      <el-form-item v-else label="所属批次">
        <el-input :model-value="`批次 ID: ${form.batch_id}`" readonly />
      </el-form-item>

      <!-- ── create：治具型号代号文本输入 ─────────────────── -->
      <el-form-item v-if="isCreate" label="治具型号代号" prop="fixture_type_code">
        <el-input
          v-model="form.fixture_type_code"
          placeholder="如 FB-YN、CC-SJ（参见《编码规则》型号代号清单）"
          style="width: 100%"
        />
        <!-- TODO: 待 GET /api/projects/:id/template-snapshots 端点就绪后改为下拉 -->
      </el-form-item>

      <!-- ── edit / detail：型号代号只读 ─────────────────── -->
      <el-form-item v-else label="治具型号代号">
        <el-input :model-value="form.fixture_type_code" readonly />
      </el-form-item>

      <!-- ── create 专属：套数 ─────────────────────────────── -->
      <el-form-item v-if="isCreate" label="套数">
        <el-input-number v-model="form.quantity" :min="1" :max="99" />
        <span class="form-tip">逐套独立创建，系统自动递增套号</span>
      </el-form-item>

      <!-- ── 供应商 ID（可空，create / edit 可填） ─────────── -->
      <el-form-item label="供应商 ID">
        <el-input
          v-model="form.supplier_id"
          type="number"
          placeholder="可空，输入供应商 ID"
          clearable
          style="width: 100%"
        />
        <!-- TODO: 待供应商列表 API 就绪后改为下拉选择 -->
      </el-form-item>

      <!-- ── 计划到货日 ──────────────────────────────────────── -->
      <el-form-item label="计划到货日">
        <el-date-picker
          v-model="form.planned_arrival_date"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="选择日期（可空）"
          style="width: 100%"
        />
      </el-form-item>

      <!-- ── LT 天数 ────────────────────────────────────────── -->
      <el-form-item label="LT（天）">
        <el-input-number v-model="form.lead_time_days" :min="1" />
      </el-form-item>

      <!-- ── edit / detail 只读字段区 ─────────────────────── -->
      <template v-if="!isCreate">
        <el-form-item label="治具编码">
          <!-- fixture_code 仅只读展示，前端严禁拼接（§e.7） -->
          <el-input :model-value="form.fixture_code" readonly />
        </el-form-item>

        <el-form-item label="当前图纸版本">
          <el-input :model-value="form.current_version_code" readonly />
        </el-form-item>

        <el-form-item label="当前状态">
          <!-- el-tag :type 兜底 'info'（§d Rule 8） -->
          <el-tag :type="fixtureStatusType(form.current_status)">
            {{ fixtureStatusLabel(form.current_status) }}
          </el-tag>
        </el-form-item>
      </template>
    </el-form>

    <!-- ── 操作区 ─────────────────────────────────────────── -->
    <div class="form-actions">
      <template v-if="!readOnly">
        <el-button type="primary" :loading="submitting" @click="onSubmit">
          {{ isCreate ? '创建治具' : '保存修改' }}
        </el-button>
        <el-button @click="router.back()">取消</el-button>
      </template>
      <template v-else>
        <el-button
          v-if="auth.hasPermission('fixture.edit')"
          type="primary"
          @click="router.push(`/fixtures/${route.params.id}/edit`)"
        >
          编辑
        </el-button>
        <!-- 图纸版本升级按钮：仅 detail 模式 + 有权限时显示 -->
        <el-button
          v-if="auth.hasPermission('fixture.version_bump')"
          type="warning"
          @click="onVersionBump"
        >
          图纸版本升级
        </el-button>
        <el-button @click="router.back()">返回</el-button>
      </template>
    </div>
  </div>
</template>

<style scoped>
.fixture-form-page {
  padding: 16px;
  max-width: 700px;
}
.form-actions {
  margin-top: 24px;
  display: flex;
  gap: 12px;
}
.form-tip {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
}
</style>
