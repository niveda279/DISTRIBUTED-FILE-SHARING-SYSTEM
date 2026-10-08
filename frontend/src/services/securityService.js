import api from './api';

export const securityService = {
  async getEvents(params = {}) {
    const { data } = await api.get('/api/admin/security/events', { params });
    return data;
  },

  async getSummary() {
    const { data } = await api.get('/api/admin/security/summary');
    return data;
  },
};
