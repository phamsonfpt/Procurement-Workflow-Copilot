import React, { useState, useEffect } from 'react';
import { LogOut, Globe, AlertTriangle } from 'lucide-react';
import type { UserProfile, ThreadMeta } from '../types';
import ChatInterface from '../components/ChatInterface';
import { useNavigate } from 'react-router-dom';

export default function OpsPage() {
  const navigate = useNavigate();
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(() => {
    const saved = localStorage.getItem('current_user');
    return saved ? JSON.parse(saved) : null;
  });

  const [activeThreadId, setActiveThreadId] = useState<string>('');
  const [allRequests, setAllRequests] = useState<ThreadMeta[]>([]);
  const [loading, setLoading] = useState(true);

  if (!currentUser) {
    navigate('/login');
    return null;
  }

  const fetchRequests = async () => {
    try {
      const res = await fetch(`http://localhost:8000/api/requests?role=${currentUser.role}&email=${currentUser.email}`);
      const data = await res.json();
      setAllRequests(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
    const interval = setInterval(fetchRequests, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('current_user');
    navigate('/login');
  };

  const handleOverride = async (threadId: string) => {
    if (!window.confirm("Are you sure you want to OVERRIDE and force-approve this request?")) return;
    try {
      await fetch(`http://localhost:8000/api/requests/${threadId}/override`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_status: 'APPROVED', admin_email: currentUser.email })
      });
      fetchRequests();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar - Global View */}
      <div className="glass-panel sidebar" style={{ minWidth: '350px' }}>
        <div style={{ padding: '1rem', fontWeight: 'bold', color: '#a78bfa', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Globe size={20} /> Global Operations
        </div>
        <div className="thread-list" style={{ padding: '0 1rem' }}>
          {loading && <div className="no-threads">Loading...</div>}
          {allRequests.map(t => (
            <div 
              key={t.thread_id} 
              className={`glass-panel`}
              style={{ marginBottom: '1rem', padding: '1rem', cursor: 'pointer', border: t.thread_id === activeThreadId ? '1px solid #a78bfa' : '1px solid rgba(255,255,255,0.1)' }}
              onClick={() => setActiveThreadId(t.thread_id)}
            >
              <div style={{ fontWeight: 'bold', marginBottom: '0.5rem' }}>{t.title}</div>
              <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.2rem' }}>Requester: {t.requester_email}</div>
              <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.5rem' }}>Cost: ${t.total_cost}</div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className={`badge ${t.status === 'PENDING' ? 'pending' : (t.status === 'APPROVED' ? 'success' : '')}`}>
                  {t.status}
                </span>
                <span style={{ fontSize: '0.75rem', color: '#60a5fa' }}>Wait: {t.required_role}</span>
              </div>
              
              {t.status === 'PENDING' && (
                <button 
                  onClick={(e) => { e.stopPropagation(); handleOverride(t.thread_id); }}
                  style={{ marginTop: '1rem', width: '100%', padding: '0.5rem', background: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', border: '1px solid #ef4444', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
                >
                  <AlertTriangle size={14} /> Force Override
                </button>
              )}
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
        />
      ) : (
        <div className="glass-panel main-chat" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <div style={{ textAlign: 'center', color: '#94a3b8' }}>
            <Globe size={48} style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
            <h2>Procurement Operations</h2>
            <p>Monitor all corporate spend workflows across departments.</p>
          </div>
        </div>
      )}
    </div>
  );
}
