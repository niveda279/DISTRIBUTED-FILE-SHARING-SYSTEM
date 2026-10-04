import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { X, Upload, CheckCircle, AlertCircle, CloudUpload } from 'lucide-react';
import { fileService } from '../services/fileService';
import toast from 'react-hot-toast';

export default function UploadModal({ onClose, onUploadComplete }) {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [results, setResults] = useState([]);

  const onDrop = useCallback((accepted) => {
    setFiles(prev => [...prev, ...accepted.map(f => ({
      file: f,
      name: f.name,
      size: f.size,
      progress: 0,
      status: 'pending', // pending | uploading | done | error
      error: null,
    }))]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true,
    maxSize: 100 * 1024 * 1024,
  });

  const removeFile = (idx) => setFiles(f => f.filter((_, i) => i !== idx));

  const handleUpload = async () => {
    if (!files.length) return;
    setUploading(true);
    const newResults = [];

    for (let i = 0; i < files.length; i++) {
      const item = files[i];
      setFiles(prev => prev.map((f, idx) => idx === i ? { ...f, status: 'uploading' } : f));
      try {
        const result = await fileService.upload(item.file, (progress) => {
          setFiles(prev => prev.map((f, idx) => idx === i ? { ...f, progress } : f));
        });
        setFiles(prev => prev.map((f, idx) => idx === i ? { ...f, status: 'done', progress: 100 } : f));
        newResults.push({ name: item.name, success: true, result });
      } catch (err) {
        const msg = err.response?.data?.detail || 'Upload failed';
        setFiles(prev => prev.map((f, idx) => idx === i ? { ...f, status: 'error', error: msg } : f));
        newResults.push({ name: item.name, success: false, error: msg });
      }
    }

    setResults(newResults);
    setUploading(false);
    const successCount = newResults.filter(r => r.success).length;
    if (successCount > 0) {
      toast.success(`${successCount} file${successCount > 1 ? 's' : ''} uploaded successfully!`);
      onUploadComplete?.();
    }
  };

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal" style={{ maxWidth: 600 }}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 36, height: 36, borderRadius: 8, background: 'rgba(99,120,255,0.15)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--clr-primary)',
            }}>
              <CloudUpload size={18} />
            </div>
            <span className="modal-title">Upload Files</span>
          </div>
          <button className="btn-icon btn-ghost" onClick={onClose} disabled={uploading}>
            <X size={18} />
          </button>
        </div>

        {/* Dropzone */}
        <div {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''}`}>
          <input {...getInputProps()} />
          <Upload size={40} className="dropzone-icon" />
          <p className="dropzone-label">
            {isDragActive ? 'Drop files here …' : 'Drag & drop files, or click to browse'}
          </p>
          <p className="dropzone-hint">Any file type • Max 100 MB per file</p>
        </div>

        {/* File list */}
        {files.length > 0 && (
          <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 240, overflowY: 'auto' }}>
            {files.map((item, idx) => (
              <div key={idx} style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '10px 12px', borderRadius: 8,
                background: 'var(--clr-surface2)',
                border: '1px solid var(--clr-border)',
              }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {item.name}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--clr-muted)', marginTop: 2 }}>
                    {fileService.formatSize(item.size)}
                  </div>
                  {item.status === 'uploading' && (
                    <div className="progress-bar" style={{ marginTop: 6 }}>
                      <div className="progress-fill" style={{ width: `${item.progress}%` }} />
                    </div>
                  )}
                  {item.status === 'error' && (
                    <div style={{ fontSize: 11, color: 'var(--clr-danger)', marginTop: 4 }}>
                      {item.error}
                    </div>
                  )}
                </div>
                {item.status === 'done' && <CheckCircle size={18} color="var(--clr-success)" />}
                {item.status === 'error' && <AlertCircle size={18} color="var(--clr-danger)" />}
                {item.status === 'pending' && (
                  <button className="btn-icon btn-ghost btn-sm" onClick={() => removeFile(idx)}>
                    <X size={14} />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Actions */}
        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 24 }}>
          <button className="btn btn-ghost" onClick={onClose} disabled={uploading}>Cancel</button>
          <button
            className="btn btn-primary"
            onClick={handleUpload}
            disabled={uploading || !files.length || files.every(f => f.status === 'done')}
          >
            {uploading ? (
              <><span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />Uploading…</>
            ) : (
              <><Upload size={14} />Upload {files.length} File{files.length !== 1 ? 's' : ''}</>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
