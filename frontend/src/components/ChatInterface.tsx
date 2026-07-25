import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, CheckCircle, ShieldAlert, Cpu } from 'lucide-react';
import type { Message, AgentStatus, UserProfile } from '../types';

interface ChatInterfaceProps {
  currentUser: UserProfile;
  activeThreadId: string;
  onThreadCreated?: (threadId: string, title: string) => void;
  onThreadUpdate?: (threadId: string, status: string) => void;
}

export default function ChatInterface({ currentUser, activeThreadId, onThreadCreated, onThreadUpdate }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>(() => {
    const saved = localStorage.getItem(`messages_${activeThreadId}`);
    return saved ? JSON.parse(saved).map((m: any) => ({ ...m, timestamp: new Date(m.timestamp) })) : [];
  });
  
  const [input, setInput] = useState('');
  const [status, setStatus] = useState<AgentStatus>('idle');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    if (activeThreadId) {
      localStorage.setItem(`messages_${activeThreadId}`, JSON.stringify(messages));
    }
  }, [messages, status, activeThreadId]);

  useEffect(() => {
    const saved = localStorage.getItem(`messages_${activeThreadId}`);
    if (saved) {
      setMessages(JSON.parse(saved).map((m: any) => ({ ...m, timestamp: new Date(m.timestamp) })));
    } else {
      setMessages([]);
    }
    setStatus('idle');
  }, [activeThreadId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || status !== 'idle') return;

    const userMsg: Message = {
      id: Date.now().toString(),
      sender: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setStatus('researching');

    let currentThreadId = activeThreadId;

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query: userMsg.content, 
          department_name: 'Engineering',
          thread_id: currentThreadId || undefined,
          user_role: currentUser.role,
          email: currentUser.email
        }),
      });

      if (!response.body) throw new Error("No readable stream");

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let gotInterrupt = false;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.replace('data: ', '');
            if (!dataStr) continue;

            try {
              const data = JSON.parse(dataStr);
              if (data.type === 'thread_info') {
                if (!currentThreadId) {
                  currentThreadId = data.thread_id;
                  if (onThreadCreated) onThreadCreated(currentThreadId, userMsg.content.substring(0, 30) + '...');
                }
              } else if (data.type === 'status') {
                setStatus(data.node === 'researcher' ? 'researching' : 'reviewing');
              } else if (data.type === 'message') {
                setMessages(prev => [
                  ...prev,
                  {
                    id: Date.now().toString() + Math.random(),
                    sender: data.sender,
                    content: data.content,
                    timestamp: new Date(),
                  }
                ]);
              } else if (data.type === 'done') {
                setStatus('idle');
                if (currentThreadId && onThreadUpdate) onThreadUpdate(currentThreadId, 'APPROVED');
              } else if (data.type === 'interrupt') {
                setStatus('idle');
                gotInterrupt = true;
                if (currentThreadId && onThreadUpdate) onThreadUpdate(currentThreadId, 'PENDING');
                setMessages(prev => [
                  ...prev,
                  {
                    id: Date.now().toString() + Math.random(),
                    sender: 'System',
                    content: `[Attention] Workflow paused for human review. Please check the FLAG and output above to Approve or Reject manually.`,
                    timestamp: new Date(),
                  }
                ]);
              } else if (data.type === 'error') {
                setStatus('error');
                setMessages(prev => [
                  ...prev,
                  {
                    id: Date.now().toString(),
                    sender: 'Error',
                    content: data.content,
                    timestamp: new Date(),
                  }
                ]);
              }
            } catch (err) {
              console.error("Error parsing SSE JSON:", err);
            }
          }
        }
      }
      
      if (!gotInterrupt && currentThreadId && onThreadUpdate) {
        onThreadUpdate(currentThreadId, 'APPROVED');
      }

    } catch (error) {
      console.error(error);
      setStatus('error');
    }
  };

  return (
    <div className="glass-panel main-chat">
      <header className="chat-header">
        <div className="header-title">
          <Cpu className="icon-glow" />
          <h1>Procurement Copilot</h1>
        </div>
        <div className="header-status">
          <span className={`status-dot ${status !== 'idle' ? 'active' : ''}`}></span>
          {status === 'idle' && 'Ready'}
          {status === 'researching' && 'Researcher analyzing...'}
          {status === 'reviewing' && 'Reviewer checking budget...'}
          {status === 'error' && 'System Error'}
        </div>
      </header>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="empty-state">
            <Bot size={48} className="empty-icon" />
            <h2>Hello, {currentUser.name}!</h2>
            <p>Your role is <strong>{currentUser.role}</strong>.</p>
            <p>How can I assist your procurement today?</p>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`message-wrapper ${msg.sender === 'user' ? 'user-wrapper' : 'bot-wrapper'}`}>
            <div className={`message-avatar ${msg.sender}`}>
              {msg.sender === 'user' ? <User size={20} /> : (msg.sender === 'Researcher' ? <ShieldAlert size={20} /> : (msg.sender === 'Error' ? <ShieldAlert size={20} /> : <CheckCircle size={20} />))}
            </div>
            <div className={`message-bubble ${msg.sender}`}>
              <div className="message-sender">{msg.sender}</div>
              <div className="message-content">{msg.content}</div>
              <div className="message-time">{msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
            </div>
          </div>
        ))}

        {status !== 'idle' && status !== 'error' && (
          <div className="message-wrapper bot-wrapper">
            <div className="message-avatar bot">
              <Cpu size={20} className="spin-animation" />
            </div>
            <div className="message-bubble typing">
              <span className="dot"></span>
              <span className="dot"></span>
              <span className="dot"></span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        <form onSubmit={handleSubmit} className="chat-form">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask for a product or budget reservation..."
            className="chat-input"
            disabled={status !== 'idle'}
          />
          <button type="submit" className="send-btn" disabled={!input.trim() || status !== 'idle'}>
            <Send size={20} />
          </button>
        </form>
      </div>
    </div>
  );
}
