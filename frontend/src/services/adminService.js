import api from './api';

export const adminService = {
  async getStats() {
    const { data } = await api.get('/api/admin/stats');
    return data;
  },

  async listUsers(skip = 0, limit = 50) {
    const { data } = await api.get('/api/admin/users', { params: { skip, limit } });
    return data;
  },

  async disableUser(userId) {
    const { data } = await api.post(`/api/admin/users/${userId}/disable`);
    return data;
  },

  async enableUser(userId) {
    const { data } = await api.post(`/api/admin/users/${userId}/enable`);
    return data;
  },

  async promoteUser(userId) {
    const { data } = await api.post(`/api/admin/users/${userId}/promote`);
    return data;
  },

  async auditLogs(skip = 0, limit = 100, action = '') {
    const { data } = await api.get('/api/admin/audit-logs', {
      params: { skip, limit, action: action || undefined },
    });
    return data;
  },
};
