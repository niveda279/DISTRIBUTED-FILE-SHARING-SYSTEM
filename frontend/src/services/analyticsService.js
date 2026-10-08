import api from './api';

export const analyticsService = {
  async getExtendedStats() {
    const { data } = await api.get('/api/admin/stats/extended');
    return data;
  },

  async getNodeMetrics(nodeId) {
    const { data } = await api.get(`/api/nodes/${nodeId}/metrics`);
    return data;
  },

  async getReliability() {
    const { data } = await api.get('/api/cluster/reliability');
    return data;
  },

  async getDedupSavings() {
    const { data } = await api.get('/api/admin/stats/dedup-savings');
    return data;
  },
};
