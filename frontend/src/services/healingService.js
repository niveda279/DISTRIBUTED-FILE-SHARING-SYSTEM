import api from './api';

export const healingService = {
  async getEvents(limit = 50) {
    const { data } = await api.get('/api/admin/self-healing/events', { params: { limit } });
    return data;
  },

  async getStatus() {
    const { data } = await api.get('/api/admin/self-healing/status');
    return data;
  },

  async triggerRepair() {
    const { data } = await api.post('/api/admin/self-healing/repair');
    return data;
  },
};
