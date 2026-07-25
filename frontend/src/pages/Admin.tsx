import React, { useState } from 'react';
import { LogOut, Activity, Database, Server, Key } from 'lucide-react';
import type { UserProfile } from '../types';
import { useNavigate } from 'react-router-dom';

export default function AdminPage() {
  const navigate = useNavigate();
  const [currentUser] = useState<UserProfile | null>(() => {
    const saved = localStorage.getItem('current_user');
    return saved ? JSON.parse(saved) : null;
  });

  if (!currentUser) {
    navigate('/login');
    return null;
  }

  const handleLogout = () => {
    localStorage.removeItem('current_user');
    navigate('/login');
  };

  return (
    <div className="app-container" style={{ padding: '2rem' }}>
      <div className="glass-panel" style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
        
        <header className="chat-header" style={{ borderRadius: '16px 16px 0 0' }}>
          <div className="header-title">
            <Activity className="icon-glow" />
            <h1>IT Admin / System Monitor</h1>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span style={{ color: '#94a3b8' }}>{currentUser.name} ({currentUser.role})</span>
            <button onClick={handleLogout} className="logout-btn" title="Sign Out">
              <LogOut size={20} />
            </button>
          </div>
        </header>

        <div style={{ padding: '2rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem' }}>
          
          <div className="glass-panel" style={{ padding: '1.5rem', background: 'rgba(0,0,0,0.2)' }}>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', color: '#60a5fa' }}>
              <Server size={20} /> FastAPI Server
            </h3>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <span>Status</span> <span style={{ color: '#4ade80' }}>Online</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <span>Uptime</span> <span>14d 2h 45m</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Active Connections</span> <span>42</span>
            </div>
          </div>

          <div className="glass-panel" style={{ padding: '1.5rem', background: 'rgba(0,0,0,0.2)' }}>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', color: '#a78bfa' }}>
              <Database size={20} /> Supabase PostgreSQL
            </h3>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <span>Connection Pool</span> <span style={{ color: '#4ade80' }}>Healthy (8/10)</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <span>Checkpointer DB</span> <span>pg_vector ready</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Storage Used</span> <span>14.2 MB</span>
            </div>
          </div>

          <div className="glass-panel" style={{ padding: '1.5rem', background: 'rgba(0,0,0,0.2)' }}>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', color: '#fb923c' }}>
              <Key size={20} /> LLM API Quota
            </h3>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <span>Groq Provider</span> <span style={{ color: '#4ade80' }}>Active</span>
            </div>
            <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '4px', margin: '1rem 0' }}>
              <div style={{ width: '65%', height: '100%', background: '#fb923c', borderRadius: '4px' }}></div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: '#94a3b8' }}>
              <span>Token Usage</span> <span>6.5M / 10M Limit</span>
            </div>
          </div>

        </div>

        <div style={{ padding: '0 2rem 2rem 2rem', flex: 1 }}>
          <div className="glass-panel" style={{ height: '100%', padding: '1.5rem', background: 'rgba(0,0,0,0.4)', fontFamily: 'monospace', fontSize: '0.85rem', color: '#94a3b8', overflowY: 'auto' }}>
            <div style={{ color: '#60a5fa', marginBottom: '1rem' }}>&gt; System Trace Logs:</div>
            <div>[2026-07-25 14:02:11] INFO: Server started on port 8000</div>
            <div>[2026-07-25 14:05:32] INFO: Supabase connection established</div>
            <div>[2026-07-25 14:12:45] DEBUG: LangGraph workflow initialized for thread_id=98c4-1234</div>
            <div style={{ color: '#ef4444' }}>[2026-07-25 15:22:10] WARN: Smurfing detected by PolicyChecker (requester: employee@acme.corp)</div>
            <div>[2026-07-25 15:22:12] INFO: Escalated required_role to Department Head</div>
            <div>[2026-07-25 16:45:00] INFO: User cfo@acme.corp authenticated successfully.</div>
            <div><span className="spin-animation" style={{ display: 'inline-block' }}>_</span></div>
          </div>
        </div>

      </div>
    </div>
  );
}
