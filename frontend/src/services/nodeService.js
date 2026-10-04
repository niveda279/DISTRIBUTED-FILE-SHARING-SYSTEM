import api from './api';

export const nodeService = {
  async list() {
    const { data } = await api.get('/api/nodes/');
    return data;
  },

  async ping(nodeId) {
    const { data } = await api.post(`/api/nodes/${nodeId}/ping`);
    return data;
  },

  async disable(nodeId) {
    const { data } = await api.post(`/api/nodes/${nodeId}/disable`);
    return data;
  },

  async enable(nodeId) {
    const { data } = await api.post(`/api/nodes/${nodeId}/enable`);
    return data;
  },

  formatStorage(bytes) {
    if (!bytes) return '0 B';
    const gb = bytes / (1024 ** 3);
    if (gb >= 1) return `${gb.toFixed(1)} GB`;
    const mb = bytes / (1024 ** 2);
    if (mb >= 1) return `${mb.toFixed(0)} MB`;
    return `${(bytes / 1024).toFixed(0)} KB`;
  },

  usagePercent(total, available) {
    if (!total || !available) return 0;
    return Math.round(((total - available) / total) * 100);
  },
};
