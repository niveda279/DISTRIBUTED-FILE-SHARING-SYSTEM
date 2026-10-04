import { useEffect, useState } from 'react';
import { Share2, RefreshCw } from 'lucide-react';
import Navbar from '../components/Navbar';
import FileTable from '../components/FileTable';
import { fileService } from '../services/fileService';
import toast from 'react-hot-toast';

export default function SharedFilesPage() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      const data = await fileService.shared();
      setFiles(data);
    } catch {
      toast.error('Failed to load shared files');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const filtered = files.filter(f =>
    f.original_filename.toLowerCase().includes(search.toLowerCase()) ||
    f.owner_name?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <>
      <Navbar
        title="Shared With Me"
        subtitle={`${files.length} file${files.length !== 1 ? 's' : ''} shared by others`}
      />
      <div className="page-inner fade-in">
        <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
          <div className="search-box" style={{ flex: 1 }}>
            <Share2 size={16} color="var(--clr-muted)" />
            <input
              placeholder="Filter by name or owner…"
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
              <Share2 size={40} />
              <h3>{search ? 'No matching files' : 'Nothing shared yet'}</h3>
              <p>{search ? 'Try a different term.' : 'Files shared with you will appear here.'}</p>
            </div>
          ) : (
            <FileTable
              files={filtered}
              showOwner
              readOnly
            />
          )}
        </div>
      </div>
    </>
  );
}
