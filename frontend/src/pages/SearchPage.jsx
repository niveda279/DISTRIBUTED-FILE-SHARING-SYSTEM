import { useState } from 'react';
import { Search, Filter } from 'lucide-react';
import Navbar from '../components/Navbar';
import FileTable from '../components/FileTable';
import ShareModal from '../components/ShareModal';
import { fileService } from '../services/fileService';
import toast from 'react-hot-toast';

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [fileType, setFileType] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [shareFile, setShareFile] = useState(null);

  const handleSearch = async (e) => {
    e?.preventDefault();
    if (!query.trim() && !fileType) return;
    setLoading(true);
    try {
      const data = await fileService.search(query || undefined, fileType || undefined);
      setResults(data);
    } catch {
      toast.error('Search failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Navbar title="Search" subtitle="Find files across your storage" />
      <div className="page-inner fade-in">
        <form onSubmit={handleSearch}>
          <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
            <div className="search-box" style={{ flex: 1, maxWidth: 500 }}>
              <Search size={16} color="var(--clr-muted)" />
              <input
                id="search-input"
                placeholder="Search by filename…"
                value={query}
                onChange={e => setQuery(e.target.value)}
                autoFocus
              />
            </div>
            <select
              className="form-input"
              style={{ width: 160 }}
              value={fileType}
              onChange={e => setFileType(e.target.value)}
            >
              <option value="">All types</option>
              <option value="application/pdf">PDF</option>
              <option value="image">Images</option>
              <option value="text">Text</option>
              <option value="application/zip">Archives</option>
            </select>
            <button
              id="search-btn"
              type="submit"
              className="btn btn-primary"
              disabled={loading}
            >
              {loading ? <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> : <Search size={14} />}
              Search
            </button>
          </div>
        </form>

        {results === null ? (
          <div className="card">
            <div className="empty-state">
              <Search size={48} />
              <h3>Search your files</h3>
              <p>Enter a filename or select a file type to get started.</p>
            </div>
          </div>
        ) : (
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--clr-border)' }}>
              <span style={{ fontWeight: 600, fontSize: 14 }}>
                {results.length} result{results.length !== 1 ? 's' : ''}
                {query ? ` for "${query}"` : ''}
              </span>
            </div>
            {results.length === 0 ? (
              <div className="empty-state">
                <Search size={32} />
                <h3>No results found</h3>
                <p>Try different keywords or file type.</p>
              </div>
            ) : (
              <FileTable
                files={results}
                showOwner
                onShare={setShareFile}
                onDelete={(id) => setResults(r => r.filter(x => x.id !== id))}
              />
            )}
          </div>
        )}
      </div>

      {shareFile && <ShareModal file={shareFile} onClose={() => setShareFile(null)} />}
    </>
  );
}
