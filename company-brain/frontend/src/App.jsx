import React, { useEffect, useRef, useState } from 'react';
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Deals from './pages/Deals';

const API = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const api = {
  get: (path) => fetch(`${API}${path}`).then(r => r.json()),
  post: (path, body = {}) => fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(r => r.json()),
};

export const WS_URL = API.replace('http', 'ws') + '/ws/alerts';

function Nav({ newAlerts }) {
  const active = ({ isActive }) => ({
    color: isActive ? '#38bdf8' : '#94a3b8',
    textDecoration: 'none',
    fontWeight: isActive ? '600' : '400',
    padding: '8px 16px',
    borderRadius: 8,
    background: isActive ? 'rgba(56,189,248,0.08)' : 'transparent',
  });

  return (
    <nav style={{ background: '#1e293b', borderBottom: '1px solid #334155', display: 'flex', alignItems: 'center', padding: '0 24px', height: 56 }}>
      <span style={{ fontWeight: 700, fontSize: 18, color: '#38bdf8', marginRight: 32 }}>
        🧠 Company Brain
      </span>
      <NavLink to="/" style={active}>
        Dashboard
        {newAlerts > 0 && (
          <span style={{ background: '#ef4444', color: '#fff', borderRadius: 10, fontSize: 11, padding: '1px 6px', marginLeft: 6 }}>
            {newAlerts}
          </span>
        )}
      </NavLink>
      <NavLink to="/deals" style={active}>Deals</NavLink>
    </nav>
  );
}

export default function App() {
  const [newAlerts, setNewAlerts] = useState(0);
  const wsRef = useRef(null);

  useEffect(() => {
    const connect = () => {
      try {
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;
        ws.onmessage = (e) => {
          const msg = JSON.parse(e.data);
          if (msg.type === 'new_alerts') setNewAlerts(n => n + (msg.count || 1));
          if (msg.type === 'alert_approved' || msg.type === 'alert_rejected') {
            setNewAlerts(n => Math.max(0, n - 1));
          }
        };
        ws.onclose = () => setTimeout(connect, 3000);
      } catch (_) {}
    };
    connect();
    return () => wsRef.current?.close();
  }, []);

  return (
    <BrowserRouter>
      <Nav newAlerts={newAlerts} />
      <main style={{ maxWidth: 1200, margin: '0 auto', padding: '24px 16px' }}>
        <Routes>
          <Route path="/" element={<Dashboard onAlertClear={() => setNewAlerts(0)} />} />
          <Route path="/deals" element={<Deals />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}
