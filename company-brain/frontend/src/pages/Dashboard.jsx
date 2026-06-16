import React, { useEffect, useState } from 'react';
import AlertInbox from '../components/AlertInbox';
import { api } from '../App';

function StatCard({ label, value, sub, color = '#38bdf8' }) {
  return (
    <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 10, padding: '16px 20px', flex: 1, minWidth: 140 }}>
      <div style={{ fontSize: 28, fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: 14, color: '#e2e8f0', marginTop: 4 }}>{label}</div>
      {sub && <div style={{ fontSize: 12, color: '#475569', marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

export default function Dashboard({ onAlertClear }) {
  const [stats, setStats] = useState({});
  const [alertCount, setAlertCount] = useState(0);
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState(null);

  useEffect(() => {
    api.get('/alerts/stats').then(setStats);
  }, [alertCount]);

  const handleScan = async (endpoint) => {
    setScanning(true);
    setScanResult(null);
    try {
      const result = await api.post(endpoint);
      setScanResult(result);
      // Refresh alert count
      const data = await api.get('/alerts?status=PENDING_APPROVAL');
      setAlertCount(data.count || 0);
    } catch (e) {
      setScanResult({ error: 'Scan failed – check API logs' });
    }
    setScanning(false);
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ color: '#e2e8f0', fontSize: 22, fontWeight: 700 }}>🧠 Company Brain</h1>
          <p style={{ color: '#64748b', fontSize: 14, marginTop: 4 }}>AI co-pilot for your sales team</p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <ScanButton
            label="🔍 Scan Renewals"
            onClick={() => handleScan('/scan/renewals')}
            loading={scanning}
          />
          <ScanButton
            label="🤖 Run AI Scan"
            onClick={() => handleScan('/scan/agent')}
            loading={scanning}
            primary
          />
        </div>
      </div>

      {/* Stat cards */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 28, flexWrap: 'wrap' }}>
        <StatCard
          label="Pending Approvals"
          value={stats.PENDING_APPROVAL || 0}
          sub="Waiting for your review"
          color="#f59e0b"
        />
        <StatCard
          label="Approved Today"
          value={stats.APPROVED || 0}
          sub="Ready to execute"
          color="#22c55e"
        />
        <StatCard
          label="Executed"
          value={stats.EXECUTED || 0}
          sub="Actions completed"
          color="#38bdf8"
        />
        <StatCard
          label="Rejected"
          value={stats.REJECTED || 0}
          sub="Declined by team"
          color="#64748b"
        />
      </div>

      {/* Scan result banner */}
      {scanResult && (
        <div style={{
          background: scanResult.error ? '#7f1d1d22' : '#14532d22',
          border: `1px solid ${scanResult.error ? '#dc2626' : '#16a34a'}44`,
          borderRadius: 8, padding: '12px 16px', marginBottom: 20, fontSize: 14,
          color: scanResult.error ? '#fca5a5' : '#86efac',
        }}>
          {scanResult.error
            ? `❌ ${scanResult.error}`
            : `✅ Scan complete — ${scanResult.queued ?? scanResult.actions_queued ?? 0} new action(s) queued for review`
          }
        </div>
      )}

      {/* Alert inbox */}
      <div style={{ marginBottom: 12 }}>
        <h2 style={{ color: '#94a3b8', fontSize: 16, fontWeight: 600, marginBottom: 16 }}>
          📥 Pending Approvals
        </h2>
        <AlertInbox onCountChange={count => { setAlertCount(count); if (count === 0) onAlertClear?.(); }} />
      </div>
    </div>
  );
}

function ScanButton({ label, onClick, loading, primary }) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      style={{
        padding: '9px 16px',
        background: primary ? '#0ea5e9' : 'transparent',
        border: `1px solid ${primary ? '#0ea5e9' : '#334155'}`,
        borderRadius: 8,
        color: primary ? '#fff' : '#94a3b8',
        cursor: loading ? 'not-allowed' : 'pointer',
        fontSize: 13,
        fontWeight: 500,
        opacity: loading ? 0.6 : 1,
      }}
    >
      {loading ? '⏳ Scanning…' : label}
    </button>
  );
}
