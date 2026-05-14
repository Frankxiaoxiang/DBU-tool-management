import request from './request'

export function listBatches(params) {
  return request.get('/batches/', { params })
}

export function getBatchById(id) {
  return request.get(`/batches/${id}`)
}

export function cancelBatch(id, payload) {
  return request.patch(`/batches/${id}/cancel`, payload)
}

export function createBatch(payload) {
  return request.post('/batches/', payload)
}

export function updateBatch(id, payload) {
  return request.put(`/batches/${id}`, payload)
}
