import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { TOKEN_KEY, REFRESH_KEY, readSafeToken } from '../utils/storage'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    component: () => import('../views/Layout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Home',
        component: () => import('../views/Home.vue'),
      },
      {
        path: 'projects',
        name: 'ProjectList',
        component: () => import('../views/project/ProjectList.vue'),
      },
      {
        // 注意：/projects/new 必须在 /projects/:id 之前，
        // 否则字符串 'new' 会被匹配为 :id 参数值导致详情页 404
        path: 'projects/new',
        name: 'ProjectCreate',
        component: () => import('../views/project/ProjectForm.vue'),
        meta: { mode: 'create' },
      },
      {
        path: 'projects/:id/edit',
        name: 'ProjectEdit',
        component: () => import('../views/project/ProjectForm.vue'),
        meta: { mode: 'edit' },
      },
      {
        path: 'projects/:id',
        name: 'ProjectDetail',
        component: () => import('../views/project/ProjectForm.vue'),
        meta: { mode: 'detail' },
      },
      // ── 批次模块 ──────────────────────────────────────
      {
        // 场景 A：从项目详情进入，project_id 由 projectId 参数传入，隐藏项目下拉
        path: 'projects/:projectId/batches',
        name: 'ProjectBatchList',
        component: () => import('../views/batch/BatchList.vue'),
      },
      {
        // 场景 B：独立访问，搜索栏显示项目下拉
        path: 'batches',
        name: 'BatchList',
        component: () => import('../views/batch/BatchList.vue'),
      },
      {
        // 注意：batches/new 必须在 batches/:id 之前，防止 'new' 被动态参数捕获
        path: 'batches/new',
        name: 'BatchCreate',
        component: () => import('../views/batch/BatchForm.vue'),
        meta: { mode: 'create' },
      },
      {
        path: 'batches/:id',
        name: 'BatchDetail',
        component: () => import('../views/batch/BatchForm.vue'),
        meta: { mode: 'detail' },
      },
      {
        path: 'batches/:id/edit',
        name: 'BatchEdit',
        component: () => import('../views/batch/BatchForm.vue'),
        meta: { mode: 'edit' },
      },
      // ── 治具模块 ──────────────────────────────────────
      {
        // 场景 A：从批次下钻，project_id / batch_id 由路由参数自动预填
        path: 'projects/:projectId/batches/:batchId/fixtures',
        name: 'FixtureListInBatch',
        component: () => import('../views/fixture/FixtureList.vue'),
      },
      {
        // 场景 B：全局治具列表，搜索栏 project_id / batch_id 手动填写
        path: 'fixtures',
        name: 'FixtureList',
        component: () => import('../views/fixture/FixtureList.vue'),
      },
      {
        // 注意：fixtures/new 如需新建入口，须在 fixtures/:id 之前注册（防止 'new' 被动态参数捕获）
        // 详情页：Step 2-3-3 完成后替换为 FixtureForm.vue
        path: 'fixtures/:id',
        name: 'FixtureDetail',
        component: () => import('../views/fixture/FixtureList.vue'),
        meta: { mode: 'detail' },
      },
      {
        // 编辑页：Step 2-3-3 完成后替换为 FixtureForm.vue
        path: 'fixtures/:id/edit',
        name: 'FixtureEdit',
        component: () => import('../views/fixture/FixtureList.vue'),
        meta: { mode: 'edit' },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('../views/NotFound.vue'),
    meta: { requiresAuth: false },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, from, next) => {
  if (to.meta.requiresAuth === false) return next()

  const token = readSafeToken(TOKEN_KEY)
  if (!token) {
    return next({ path: '/login', query: { redirect: to.fullPath } })
  }

  const auth = useAuthStore()
  if (!auth.user) {
    try {
      await auth.fetchMe()
    } catch {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(REFRESH_KEY)
      return next({ path: '/login', query: { redirect: to.fullPath } })
    }
  }
  next()
})

export default router
