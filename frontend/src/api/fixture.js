import request from './request'

export function listFixtures(params) {
  return request.get('/fixtures/', { params })
}

export function getFixtureById(id) {
  return request.get(`/fixtures/${id}`)
}
