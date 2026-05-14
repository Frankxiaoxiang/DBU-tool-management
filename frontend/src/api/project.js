import request from './request'

// request.baseURL = '/api'，路径从 /projects/ 开始，不加 /api 前缀

export function listProjects(params) {
  return request.get('/projects/', { params })
}

export function cancelProject(id, payload) {
  // payload: { reason, version }
  return request.patch(`/projects/${id}/cancel`, payload)
}

export function getProjectById(id) {
  return request.get(`/projects/${id}`)
}

export function createProject(payload) {
  // payload: { project_code, project_name, product_type, project_owner_id }
  return request.post('/projects/', payload)
}

export function updateProject(id, payload) {
  // payload 必含 version + 全字段（乐观锁）
  return request.put(`/projects/${id}`, payload)
}

export function transferOwner(id, payload) {
  // payload: { new_owner_id, version }
  return request.put(`/projects/${id}/owner`, payload)
}

export function syncProjectTemplates(id) {
  // POST /api/projects/:id/sync-templates
  // 响应：{ added_count: number, added_codes: string[] }
  return request.post(`/projects/${id}/sync-templates`)
}
