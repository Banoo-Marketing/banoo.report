import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../App';
import ApprovalModal from './ApprovalModal';

const URGENCY_COLOR = { HIGH: '#ef4444', MEDIUM: '#f59e0b', LOW: '#22c55e' };
const ACTION_ICON = {
  renewal_email: '📧',
  remind: '🔔',
  assign_task: '✅',
  escalate: '🚨',
  draft_email: '📝',
};

export default function AlertInbox({ onCountChange }) {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    const data = await api.get('/alerts?status=PENDING_APPROVAL');
    setAlerts(data.alerts || []);
    onCountChange?.(data.count || 0);
    setLoading(false);
  }, [onCountChange]);

  useEffect(() => { load(); }, [load]);

  const handleApprove = async (id) => {
    await api.post(`/alerts/${id}/approve`, { user_id: 'dashboard_user' });
    setSelected(null);
    load();
  };

  const handleReject = async (id, reason) => {
    await api.post(`/alerts/${id}/reject`, { user_id: 'dashboard_user', reason });
    setSelected(null);
    load();
  };

  if (loading) return <p style={{ color: '#64748b' }}>Loading alerts…</p>;
  if (!alerts.length) return (
    <div style={{ textAlign: 'center', padding: 48, color: '#475569' }}>
      <div style={{ fontSize: 48 }}>✅</div>
      <p style={{ marginTop: 12 }}>No pending alerts</p>
      <p style={{ fontSize: 13, marginTop: 4 }}>All caught up! Brain is watching your deals.</p>
    </div>
  );

  return (
    <>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {alerts.map(alert => {
          const payload = typeof alert.payload === 'string' ? JSON.parse(alert.payload) : alert.payload;
          return (
            <div
              key={alert.id}
              onClick={() => setSelected({ ...alert, payload })}
              style={{
                background: '#1e293b',
                border: `1px solid ${URGENCY_COLOR[alert.urgency] || '#334155'}33`,
                borderLeft: `4px solid ${URGENCY_COLOR[alert.urgency] || '#334155'}`,
                borderRadius: 10,
                padding: '14px 18px',
                cursor: 'pointer',
                transition: 'background 0.15s',
              }}
              onMouseEnter={e => e.currentTarget.style.background = '#263147'}
              onMouseLeave={e => e.currentTarget.style.background = '#1e293b'}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <span style={{ fontSize: 18, marginRight: 8 }}>{ACTION_ICON[alert.action_type] || '⚡'}</span>
                  <strong style={{ color: '#e2e8f0' }}>{alert.company || alert.deal_name}</strong>
                  {alert.clv_tier && (
                    <span style={{
                      fontSize: 11, marginLeft: 8, padding: '2px 7px', borderRadius: 6,
                      background: alert.clv_tier === 'PLATINUM' ? '#7c3aed22' : '#0ea5e922',
                      color: alert.clv_tier === 'PLATINUM' ? '#a78bfa' : '#38bdf8',
                    }}>
                      {alert.clv_tier}
                    </span>
                  )}
                </div>
                <span style={{
                  fontSize: 11, padding: '3px 8px', borderRadius: 6,
                  background: `${URGENCY_COLOR[alert.urgency] || '#64748b'}22`,
                  color: URGENCY_COLOR[alert.urgency] || '#94a3b8',
                  fontWeight: 600,
                }}>
                  {alert.urgency}
                </span>
              </div>
              <p style={{ fontSize: 13, color: '#94a3b8', marginTop: 6 }}>{alert.reason}</p>
              {payload?.subject && (
                <p style={{ fontSize: 12, color: '#64748b', marginTop: 4, fontStyle: 'italic' }}>
                  "{payload.subject}"
                </p>
              )}
              <div style={{ display: 'flex', gap: 16, marginTop: 10 }}>
                <button
                  onClick={e => { e.stopPropagation(); handleApprove(alert.id); }}
                  style={{ padding: '5px 14px', background: '#16a34a', border: 'none', borderRadius: 6, color: '#fff', cursor: 'pointer', fontSize: 13 }}
                >
                  ✓ Approve
                </button>
                <button
                  onClick={e => { e.stopPropagation(); handleReject(alert.id, 'Declined'); }}
                  style={{ padding: '5px 14px', background: 'transparent', border: '1px solid #475569', borderRadius: 6, color: '#94a3b8', cursor: 'pointer', fontSize: 13 }}
                >
                  ✗ Reject
                </button>
                <span style={{ fontSize: 12, color: '#475569', alignSelf: 'center', marginLeft: 'auto' }}>
                  Click to review →
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {selected && (
        <ApprovalModal
          alert={selected}
          onApprove={() => handleApprove(selected.id)}
          onReject={(reason) => handleReject(selected.id, reason)}
          onClose={() => setSelected(null)}
        />
      )}
    </>
  );
}
