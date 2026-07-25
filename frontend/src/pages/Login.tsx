import React, { useState } from 'react';
import { Cpu, Mail } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { DIRECTORY } from '../types';

export default function Login() {
  const [loginEmail, setLoginEmail] = useState('');
  const [loginError, setLoginError] = useState('');
  const navigate = useNavigate();

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    const user = DIRECTORY[loginEmail.toLowerCase()];
    if (user) {
      localStorage.setItem('current_user', JSON.stringify(user));
      setLoginError('');
      
      // Route based on role
      if (user.role === 'Requester') navigate('/requester');
      else if (user.role === 'IT Admin') navigate('/admin');
      else if (user.role === 'Ops') navigate('/ops');
      else navigate('/manager');
      
    } else {
      setLoginError('Email not found in Active Directory. Try employee@acme.corp');
    }
  };

  return (
    <div className="login-container">
      <div className="glass-panel login-panel">
        <Cpu className="icon-glow login-icon" size={48} />
        <h2>Enterprise SSO Login</h2>
        <p>Sign in with your corporate email</p>
        <form onSubmit={handleLogin}>
          <div className="input-group">
            <Mail size={18} className="input-icon" />
            <input 
              type="email" 
              placeholder="email@acme.corp" 
              value={loginEmail}
              onChange={e => setLoginEmail(e.target.value)}
              required
            />
          </div>
          {loginError && <div className="error-text">{loginError}</div>}
          <button type="submit" className="login-btn">Sign In via SSO</button>
        </form>
        <div className="demo-accounts">
          <p>Demo Accounts:</p>
          <ul>
            <li><code>employee@acme.corp</code> (Requester)</li>
            <li><code>manager@acme.corp</code> (Line Manager)</li>
            <li><code>head@acme.corp</code> (Dept Head)</li>
            <li><code>cfo@acme.corp</code> (CFO)</li>
            <li><code>ops@acme.corp</code> (Procurement Ops)</li>
            <li><code>admin@acme.corp</code> (IT Admin)</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
