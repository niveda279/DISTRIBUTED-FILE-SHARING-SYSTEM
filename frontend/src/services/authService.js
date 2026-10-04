import api from './api';

export const authService = {
  async register(name, email, password) {
    const { data } = await api.post('/api/auth/register', { name, email, password });
    return data;
  },

  async login(email, password) {
    const { data } = await api.post('/api/auth/login', { email, password });
    localStorage.setItem('dfs_token', data.access_token);
    localStorage.setItem('dfs_user', JSON.stringify({
      id: data.user_id,
      name: data.name,
      email: data.email,
      role: data.role,
    }));
    return data;
  },

  async me() {
    const { data } = await api.get('/api/auth/me');
    return data;
  },

  logout() {
    localStorage.removeItem('dfs_token');
    localStorage.removeItem('dfs_user');
    window.location.href = '/login';
  },

  getUser() {
    const raw = localStorage.getItem('dfs_user');
    return raw ? JSON.parse(raw) : null;
  },

  isLoggedIn() {
    return !!localStorage.getItem('dfs_token');
  },
};
