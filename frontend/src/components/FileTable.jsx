import {
  FileText, Image, FileCode, Archive, Table, Music, Video, File,
  Download, Share2, Trash2, MoreVertical,
} from 'lucide-react';
import { useState } from 'react';
import { fileService } from '../services/fileService';
import toast from 'react-hot-toast';

function FileIcon({ mimeType, size = 18 }) {
  const type = fileService.fileIcon(mimeType);
  const map = {
    pdf:   [FileText, 'file-icon-pdf'],
    img:   [Image,    'file-icon-img'],
    doc:   [FileText, 'file-icon-doc'],
    sheet: [Table,    'file-icon-sheet'],
    zip:   [Archive,  'file-icon-zip'],
    code:  [FileCode, 'file-icon-code'],
    other: [File,     'file-icon-other'],
  };
  const [Icon, cls] = map[type] || map.other;
  return <Icon size={size} className={cls} />;
}

export { FileIcon };

export default function FileTable({ files, onShare, onDelete, showOwner = false, readOnly = false }) {
  const [deleting, setDeleting] = useState(null);

  const handleDownload = async (file) => {
    try {
      await fileService.download(file.id, file.original_filename);
    } catch {
      toast.error('Download failed');
    }
  };

  const handleDelete = async (file) => {
    if (deleting === file.id) return;
    if (!confirm(`Delete "${file.original_filename}"? This cannot be undone.`)) return;
    setDeleting(file.id);
    try {
      await fileService.delete(file.id);
      toast.success('File deleted');
      onDelete?.(file.id);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Delete failed');
    } finally {
      setDeleting(null);
    }
  };

  if (!files?.length) return null;

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Name</th>
            {showOwner && <th>Owner</th>}
            <th>Size</th>
            <th>Type</th>
            <th>Node</th>
            <th>Uploaded</th>
            <th style={{ textAlign: 'right' }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {files.map(file => (
            <tr key={file.id}>
              <td>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <FileIcon mimeType={file.mime_type} />
                  <div>
                    <div style={{ fontWeight: 500, maxWidth: 260 }} className="truncate">
                      {file.original_filename}
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--clr-subtle)', fontFamily: 'monospace' }}>
                      SHA: {file.checksum?.slice(0, 12)}…
                    </div>
                  </div>
                </div>
              </td>
              {showOwner && (
                <td>
                  <div style={{ fontSize: 12 }}>{file.owner_name}</div>
                  <div style={{ fontSize: 11, color: 'var(--clr-muted)' }}>{file.user_permission}</div>
                </td>
              )}
              <td style={{ color: 'var(--clr-muted)', fontSize: 12 }}>
                {fileService.formatSize(file.size)}
              </td>
              <td>
                <span style={{ fontSize: 11, color: 'var(--clr-muted)', fontFamily: 'monospace' }}>
                  {file.mime_type?.split('/')[1] || '—'}
                </span>
              </td>
              <td>
                {file.primary_node_id
                  ? <span className="badge badge-online" style={{ fontSize: 10 }}>{file.primary_node_id}</span>
                  : <span style={{ color: 'var(--clr-subtle)', fontSize: 12 }}>—</span>
                }
              </td>
              <td style={{ color: 'var(--clr-muted)', fontSize: 12, whiteSpace: 'nowrap' }}>
                {new Date(file.created_at).toLocaleDateString()}
              </td>
              <td>
                <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}>
                  <button
                    className="btn btn-ghost btn-sm btn-icon"
                    onClick={() => handleDownload(file)}
                    title="Download"
                  >
                    <Download size={14} />
                  </button>
                  {!readOnly && (
                    <>
                      <button
                        className="btn btn-ghost btn-sm btn-icon"
                        onClick={() => onShare?.(file)}
                        title="Share"
                      >
                        <Share2 size={14} />
                      </button>
                      <button
                        className="btn btn-ghost btn-sm btn-icon"
                        onClick={() => handleDelete(file)}
                        disabled={deleting === file.id}
                        title="Delete"
                        style={{ color: 'var(--clr-danger)' }}
                      >
                        <Trash2 size={14} />
                      </button>
                    </>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
