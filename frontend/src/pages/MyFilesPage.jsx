import { useEffect, useState } from 'react';
import { Files, RefreshCw } from 'lucide-react';
import Navbar from '../components/Navbar';
import FileTable from '../components/FileTable';
import ShareModal from '../components/ShareModal';
import UploadModal from '../components/UploadModal';
import { fileService } from '../services/fileService';
import toast from 'react-hot-toast';

export default function MyFilesPage() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [shareFile, setShareFile] = useState(null);
  const [showUpload, setShowUpload] = useState(false);
  const [search, setSearch] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      const data = await fileService.list(0, 200);
      setFiles(data);
    } catch {
      toast.error('Failed to load files');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const filtered = files.filter(f =>
    f.original_filename.toLowerCase().includes(search.toLowerCase())
  );
  const totalSize = files.reduce((s, f) => s + f.size, 0);

  return (
    <>
      <Navbar
        title="My Files"
        subtitle={`${files.length} file${files.length !== 1 ? 's' : ''} · ${fileService.formatSize(totalSize)} total`}
        onUpload={() => setShowUpload(true)}
      />
      <div className="page-inner fade-in">
        {/* Search + refresh */}
        <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
          <div className="search-box" style={{ flex: 1 }}>
            <Files size={16} color="var(--clr-muted)" />
            <input
              placeholder="Filter files…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <button className="btn btn-ghost" onClick={load} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'spin' : ''} />
          </button>
        </div>

        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          {loading ? (
            <div style={{ padding: 60, display: 'flex', justifyContent: 'center' }}>
              <div className="spinner" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="empty-state">
              <Files size={40} />
              <h3>{search ? 'No matching files' : 'No files yet'}</h3>
              <p>{search ? 'Try a different search term.' : 'Click Upload to add your first file.'}</p>
              {!search && (
                <button className="btn btn-primary btn-sm" onClick={() => setShowUpload(true)}>
                  Upload File
                </button>
              )}
            </div>
          ) : (
            <FileTable
              files={filtered}
              onShare={setShareFile}
              onDelete={(id) => setFiles(f => f.filter(x => x.id !== id))}
            />
          )}
        </div>
      </div>

      {showUpload && (
        <UploadModal
          onClose={() => setShowUpload(false)}
          onUploadComplete={() => { setShowUpload(false); load(); }}
        />
      )}
      {shareFile && <ShareModal file={shareFile} onClose={() => setShareFile(null)} />}
    </>
  );
}
