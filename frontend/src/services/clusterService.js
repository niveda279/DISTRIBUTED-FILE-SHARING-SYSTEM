import api from './api';

export const clusterService = {
  async getTopology() {
    const { data } = await api.get('/api/cluster/topology');
    return data;
  },

  async getMetrics() {
    const { data } = await api.get('/api/cluster/metrics');
    return data;
  },

  async getReliability() {
    const { data } = await api.get('/api/cluster/reliability');
    return data;
  },

  async getEvents(limit = 50) {
    const { data } = await api.get('/api/cluster/events/recent', { params: { limit } });
    return data;
  },

  getEventsStreamUrl() {
    const base = api.defaults.baseURL || '';
    return `${base}/api/cluster/events/stream`;
  },
};
