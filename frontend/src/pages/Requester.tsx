import React, { useState } from 'react';
import { LogOut, MessageSquare, Plus } from 'lucide-react';
import type { UserProfile } from '../types';
import ChatInterface from '../components/ChatInterface';
import { useNavigate } from 'react-router-dom';

export default function RequesterPage() {
  const navigate = useNavigate();
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(() => {
    const saved = localStorage.getItem('current_user');
    return saved ? JSON.parse(saved) : null;
  });

  const [activeThreadId, setActiveThreadId] = useState<string>(() => localStorage.getItem('active_thread_id') || '');

  // For Requester, we just rely on local state for the sidebar or just let them create new chats
  const [threads, setThreads] = useState<any[]>(() => {
    const saved = localStorage.getItem('chat_threads');
    return saved ? JSON.parse(saved) : [];
  });

  if (!currentUser) {
    navigate('/login');
    return null;
  }

  const handleLogout = () => {
    localStorage.removeItem('current_user');
    navigate('/login');
  };

  const handleThreadCreated = (id: string, title: string) => {
    setActiveThreadId(id);
    setThreads(prev => [{ id, title, status: 'active', lastUpdated: new Date() }, ...prev]);
    localStorage.setItem('chat_threads', JSON.stringify([{ id, title, status: 'active', lastUpdated: new Date() }, ...threads]));
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <div className="glass-panel sidebar">
        <button className="new-chat-btn" onClick={() => setActiveThreadId('')}>
          <Plus size={16} /> New Request
        </button>
        <div className="thread-list">
          {threads.length === 0 && <div className="no-threads">No recent requests</div>}
          {threads.map(t => (
            <div 
              key={t.id} 
              className={`thread-item ${t.id === activeThreadId ? 'active' : ''}`}
              onClick={() => setActiveThreadId(t.id)}
            >
              <MessageSquare size={16} />
              <div className="thread-title">{t.title}</div>
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

      <ChatInterface 
        currentUser={currentUser} 
        activeThreadId={activeThreadId} 
        onThreadCreated={handleThreadCreated}
      />
    </div>
  );
}
