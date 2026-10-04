import { useEffect, useState } from 'react';
import { Files, Share2, HardDrive, Server, TrendingUp, Clock } from 'lucide-react';
import Navbar from '../components/Navbar';
import NodeStatusCard from '../components/NodeStatusCard';
import UploadModal from '../components/UploadModal';
import FileTable from '../components/FileTable';
import ShareModal from '../components/ShareModal';
import { fileService } from '../services/fileService';
import { nodeService } from '../services/nodeService';
import { useAuth } from '../context/AuthContext';

export default function Dashboard() {
  const { user } = useAuth();
  const [files, setFiles] = useState([]);
  const [nodes, setNodes] = useState([]);
  const [sharedCount, setSharedCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showUpload, setShowUpload] = useState(false);
  const [shareFile, setShareFile] = useState(null);

  const load = async () => {
    try {
      const [myFiles, nodeList, sharedFiles] = await Promise.all([
        fileService.list(0, 5),
        nodeService.list(),
        fileService.shared(),
      ]);
      setFiles(myFiles);
      setNodes(nodeList);
      setSharedCount(sharedFiles.length);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const totalSize = files.reduce((s, f) => s + f.size, 0);
  const onlineNodes = nodes.filter(n => n.status === 'ONLINE').length;

  return (
    <>
      <Navbar
        title={`Welcome back, ${user?.name?.split(' ')[0] || 'User'} 👋`}
        subtitle="Here's what's happening with your files."
        onUpload={() => setShowUpload(true)}
      />
      <div className="page-inner fade-in">
        {/* Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px,1fr))', gap: 16, marginBottom: 28 }}>
          <div className="stat-card">
            <div className="stat-icon stat-icon-blue"><Files size={22} /></div>
            <div>
              <div className="stat-value">{files.length}</div>
              <div className="stat-label">My Files</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon stat-icon-green"><Share2 size={22} /></div>
            <div>
              <div className="stat-value">{sharedCount}</div>
              <div className="stat-label">Shared With Me</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon stat-icon-yellow"><HardDrive size={22} /></div>
            <div>
              <div className="stat-value">{fileService.formatSize(totalSize)}</div>
              <div className="stat-label">Storage Used</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon stat-icon-pink"><Server size={22} /></div>
            <div>
              <div className="stat-value">{onlineNodes}/{nodes.length}</div>
              <div className="stat-label">Nodes Online</div>
            </div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 20, alignItems: 'start' }}>
          {/* Recent Files */}
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ padding: '18px 24px', borderBottom: '1px solid var(--clr-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Clock size={16} color="var(--clr-muted)" />
                <span style={{ fontWeight: 700, fontSize: 15 }}>Recent Files</span>
              </div>
            </div>
            {loading ? (
              <div style={{ padding: 40, textAlign: 'center', color: 'var(--clr-muted)' }}>
                <div className="spinner" style={{ margin: '0 auto' }} />
              </div>
            ) : files.length === 0 ? (
              <div className="empty-state">
                <Files size={40} />
                <h3>No files yet</h3>
                <p>Upload your first file to get started.</p>
                <button className="btn btn-primary btn-sm" onClick={() => setShowUpload(true)}>Upload File</button>
              </div>
            ) : (
              <FileTable
                files={files}
                onShare={setShareFile}
                onDelete={(id) => setFiles(f => f.filter(x => x.id !== id))}
              />
            )}
          </div>

          {/* Node Status */}
          <div>
            <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Server size={16} color="var(--clr-muted)" />
              Storage Nodes
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {loading ? (
                <div style={{ color: 'var(--clr-muted)', fontSize: 13 }}>Loading…</div>
              ) : nodes.map(node => (
                <NodeStatusCard key={node.node_id} node={node} />
              ))}
            </div>
          </div>
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
