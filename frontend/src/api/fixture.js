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
