import api from './api';

export const fileService = {
  async upload(file, onProgress) {
    const form = new FormData();
    form.append('file', file);
    const { data } = await api.post('/api/files/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded * 100) / e.total));
        }
      },
    });
    return data;
  },

  async list(skip = 0, limit = 50) {
    const { data } = await api.get('/api/files/', { params: { skip, limit } });
    return data;
  },

  async shared() {
    const { data } = await api.get('/api/files/shared');
    return data;
  },

  async search(q, fileType, dateFrom, dateTo) {
    const { data } = await api.get('/api/files/search', {
      params: { q, file_type: fileType, date_from: dateFrom, date_to: dateTo },
    });
    return data;
  },

  async getById(id) {
    const { data } = await api.get(`/api/files/${id}`);
    return data;
  },

  async download(id, filename) {
    const response = await api.get(`/api/files/${id}/download`, {
      responseType: 'blob',
    });
    const url = URL.createObjectURL(response.data);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  },

  async delete(id) {
    await api.delete(`/api/files/${id}`);
  },

  // Sharing
  async shareFile(fileId, email, permission = 'VIEW') {
    const { data } = await api.post(`/api/files/${fileId}/share`, {
      shared_with_email: email,
      permission,
    });
    return data;
  },

  async listPermissions(fileId) {
    const { data } = await api.get(`/api/files/${fileId}/permissions`);
    return data;
  },

  async revokePermission(fileId, permId) {
    await api.delete(`/api/files/${fileId}/permissions/${permId}`);
  },

  // Versions
  async getVersions(fileId) {
    const { data } = await api.get(`/api/files/${fileId}/versions`);
    return data;
  },

  async restoreVersion(fileId, versionId) {
    const { data } = await api.post(`/api/files/${fileId}/restore/${versionId}`);
    return data;
  },

  async downloadVersion(fileId, versionId, filename) {
    const response = await api.get(`/api/files/${fileId}/versions/${versionId}/download`, { responseType: 'blob' });
    const url = URL.createObjectURL(response.data);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  },

  // Activity + replicas
  async getActivity(fileId) {
    const { data } = await api.get(`/api/files/${fileId}/activity`);
    return data;
  },

  async getReplicas(fileId) {
    const { data } = await api.get(`/api/files/${fileId}/replicas`);
    return data;
  },

  // Extended search
  async searchAdvanced(params) {
    const { data } = await api.get('/api/files/search', { params });
    return data;
  },

  formatSize(bytes) {
    if (!bytes) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(i ? 1 : 0)} ${units[i]}`;
  },

  fileIcon(mimeType) {
    if (!mimeType) return 'other';
    if (mimeType === 'application/pdf') return 'pdf';
    if (mimeType.startsWith('image/')) return 'img';
    if (mimeType.includes('word') || mimeType.includes('document')) return 'doc';
    if (mimeType.includes('sheet') || mimeType.includes('excel')) return 'sheet';
    if (mimeType.includes('zip') || mimeType.includes('tar') || mimeType.includes('gzip')) return 'zip';
    if (mimeType.startsWith('text/')) return 'code';
    return 'other';
  },
};

