import React, { useState, useEffect } from 'react';
import { LogOut, List, MessageSquare } from 'lucide-react';
import type { UserProfile, ThreadMeta } from '../types';
import ChatInterface from '../components/ChatInterface';
import { useNavigate } from 'react-router-dom';

export default function ManagerPage() {
  const navigate = useNavigate();
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(() => {
    const saved = localStorage.getItem('current_user');
    return saved ? JSON.parse(saved) : null;
  });

  const [activeThreadId, setActiveThreadId] = useState<string>('');
  const [pendingRequests, setPendingRequests] = useState<ThreadMeta[]>([]);
  const [loading, setLoading] = useState(true);

  if (!currentUser) {
    navigate('/login');
    return null;
  }

  const fetchRequests = async () => {
    try {
      const res = await fetch(`http://localhost:8000/api/requests?role=${currentUser.role}&email=${currentUser.email}`);
      const data = await res.json();
      setPendingRequests(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
    const interval = setInterval(fetchRequests, 5000); // Auto refresh
    return () => clearInterval(interval);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('current_user');
    navigate('/login');
  };

  const handleThreadUpdate = (id: string, status: string) => {
    // If approved, remove from pending
    if (status === 'APPROVED') {
      setPendingRequests(prev => prev.filter(r => r.thread_id !== id));
      setActiveThreadId('');
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <div className="glass-panel sidebar">
        <div style={{ padding: '1rem', fontWeight: 'bold', color: '#60a5fa', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <List size={20} /> Pending Approvals
        </div>
        <div className="thread-list">
          {loading && <div className="no-threads">Loading...</div>}
          {!loading && pendingRequests.length === 0 && <div className="no-threads">You're all caught up!</div>}
          {pendingRequests.map(t => (
            <div 
              key={t.thread_id} 
              className={`thread-item ${t.thread_id === activeThreadId ? 'active' : ''}`}
              onClick={() => setActiveThreadId(t.thread_id)}
            >
              <MessageSquare size={16} />
              <div className="thread-title">
                {t.title}
                <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                  By: {t.requester_email} • ${t.total_cost}
                </div>
              </div>
              <div className="badge pending"></div>
            </div>
          ))}
        </div>
        
        {/* User Profile */}
        <div className="user-profile-section">
          <div className="profile-info">
            <div className="profile-name">{currentUser.name}</div>
            <div className="profile-role">{currentUser.role}</div>
          </div>
          <button onClick={handleLogout} className="logout-btn" title="Sign Out">
            <LogOut size={16} />
          </button>
        </div>
      </div>

      {activeThreadId ? (
        <ChatInterface 
          currentUser={currentUser} 
          activeThreadId={activeThreadId}
          onThreadUpdate={handleThreadUpdate}
        />
      ) : (
        <div className="glass-panel main-chat" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <div style={{ textAlign: 'center', color: '#94a3b8' }}>
            <List size={48} style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
            <h2>Manager Dashboard</h2>
            <p>Select a pending request from the sidebar to review and approve.</p>
          </div>
        </div>
      )}
    </div>
  );
}
