import request from './request'

export function listFixtures(params) {
  return request.get('/fixtures/', { params })
}

export function getFixtureById(id) {
  return request.get(`/fixtures/${id}`)
}

export function createFixture(payload) {
  return request.post('/fixtures/', payload)
}

export function updateFixture(id, payload) {
  return request.put(`/fixtures/${id}`, payload)
}

export function bumpFixtureVersion(id, payload) {
  // payload: { version: <int> }
  // 命名路由，无尾部斜杠（CLAUDE.md §h）；无 /api 前缀（baseURL 已含）
  return request.post(`/fixtures/${id}/version-bump`, payload)
}

export function copyFixtureToBatch(id, payload) {
  // payload: { target_batch_id: <int> }
  // 命名路由，无尾部斜杠（CLAUDE.md §h）；无 /api 前缀（baseURL 已含）
  return request.post(`/fixtures/${id}/copy-to-batch`, payload)
}
