import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, CheckCircle, ShieldAlert, Cpu } from 'lucide-react';

type Message = {
  id: string;
  sender: 'user' | 'Researcher' | 'Reviewer' | 'System';
  content: string;
  timestamp: Date;
};

type AgentStatus = 'idle' | 'researching' | 'reviewing' | 'error';

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [status, setStatus] = useState<AgentStatus>('idle');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, status]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      sender: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setStatus('researching');

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userMsg.content, department_name: 'Engineering' }),
      });

      if (!response.body) throw new Error("No readable stream");

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');

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
              if (data.type === 'status') {
                setStatus(data.node === 'researcher' ? 'researching' : 'reviewing');
              } else if (data.type === 'message') {
                setMessages((prev) => [
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
              } else if (data.type === 'error') {
                setStatus('error');
                setMessages((prev) => [
                  ...prev,
                  {
                    id: Date.now().toString(),
                    sender: 'System',
                    content: `Error: ${data.content}`,
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
    } catch (error) {
      console.error(error);
      setStatus('error');
    }
  };

  return (
    <div className="app-container">
      <div className="glass-panel main-chat">
        
        {/* Header */}
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

        {/* Chat History */}
        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="empty-state">
              <Bot size={48} className="empty-icon" />
              <h2>How can I assist your procurement today?</h2>
              <p>Try asking: "I need to buy a high-end Laptop for $2500"</p>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className={`message-wrapper ${msg.sender === 'user' ? 'user-wrapper' : 'bot-wrapper'}`}>
              <div className={`message-avatar ${msg.sender}`}>
                {msg.sender === 'user' ? <User size={20} /> : (msg.sender === 'Researcher' ? <ShieldAlert size={20} /> : <CheckCircle size={20} />)}
              </div>
              <div className={`message-bubble ${msg.sender}`}>
                <div className="message-sender">{msg.sender}</div>
                <div className="message-content">{msg.content}</div>
                <div className="message-time">{msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
              </div>
            </div>
          ))}

          {/* Typing Indicator */}
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

        {/* Input Area */}
        <div className="chat-input-container">
          <form onSubmit={handleSubmit} className="chat-form">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask for a product or budget reservation..."
              className="chat-input"
              disabled={status !== 'idle' && status !== 'error'}
            />
            <button type="submit" className="send-btn" disabled={!input.trim() || (status !== 'idle' && status !== 'error')}>
              <Send size={20} />
            </button>
          </form>
        </div>
        
      </div>
    </div>
  );
}
