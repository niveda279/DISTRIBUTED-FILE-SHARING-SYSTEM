import api from './api';

export const simulationService = {
  async getStatus() {
    const { data } = await api.get('/api/admin/simulation/status');
    return data;
  },

  async simulateFailure(nodeId) {
    const { data } = await api.post(`/api/admin/simulation/node-failure/${nodeId}`);
    return data;
  },

  async simulateRecovery(nodeId) {
    const { data } = await api.post(`/api/admin/simulation/node-recovery/${nodeId}`);
    return data;
  },

  async simulateNetworkDelay(nodeId, ms = 2000) {
    const { data } = await api.post(`/api/admin/simulation/network-delay/${nodeId}`, { latency_ms: ms });
    return data;
  },

  async simulateHighLoad(nodeId) {
    const { data } = await api.post(`/api/admin/simulation/high-load/${nodeId}`);
    return data;
  },

  async simulateStorageWarning(nodeId) {
    const { data } = await api.post(`/api/admin/simulation/storage-warning/${nodeId}`);
    return data;
  },

  async clearAll() {
    const { data } = await api.post('/api/admin/simulation/clear-all');
    return data;
  },
};
