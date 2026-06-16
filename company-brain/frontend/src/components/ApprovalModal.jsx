import React, { useState } from 'react';

export default function ApprovalModal({ alert, onApprove, onReject, onClose }) {
  const [rejectReason, setRejectReason] = useState('');
  const [showReject, setShowReject] = useState(false);
  const payload = alert.payload || {};

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
    }} onClick={onClose}>
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: '#1e293b', border: '1px solid #334155', borderRadius: 14,
          padding: 28, maxWidth: 560, width: '95vw', maxHeight: '90vh', overflowY: 'auto',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
          <h2 style={{ color: '#e2e8f0', fontSize: 18 }}>
            Review Action
            <span style={{ fontSize: 13, color: '#64748b', fontWeight: 400, marginLeft: 10 }}>
              #{alert.id}
            </span>
          </h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: 20 }}>×</button>
        </div>

        {/* Deal info */}
        <div style={{ background: '#0f172a', borderRadius: 8, padding: '12px 16px', marginBottom: 18 }}>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            <Field label="Company" value={alert.company || payload.company} />
            <Field label="Contact" value={alert.contact_name || payload.contact_name} />
            <Field label="Deal" value={alert.deal_name} />
            <Field label="Value" value={alert.amount ? `$${Number(alert.amount).toLocaleString()}` : ''} />
            <Field label="Renewal" value={payload.renewal_date} />
          </div>
          <p style={{ fontSize: 13, color: '#94a3b8', marginTop: 10 }}>
            <strong>Reason:</strong> {alert.reason}
          </p>
        </div>

        {/* Email preview */}
        {payload.subject && (
          <div style={{ marginBottom: 18 }}>
            <label style={{ fontSize: 12, color: '#64748b', textTransform: 'uppercase', letterSpacing: 1 }}>
              Drafted Email
            </label>
            <div style={{ background: '#0f172a', borderRadius: 8, padding: '14px 16px', marginTop: 8 }}>
              <p style={{ color: '#38bdf8', fontSize: 14, marginBottom: 10 }}>
                <strong>Subject:</strong> {payload.subject}
              </p>
              <p style={{ color: '#94a3b8', fontSize: 14, whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                {payload.body}
              </p>
              {payload.to && (
                <p style={{ fontSize: 12, color: '#475569', marginTop: 10 }}>To: {payload.to}</p>
              )}
            </div>
          </div>
        )}

        {/* Actions */}
        {!showReject ? (
          <div style={{ display: 'flex', gap: 12 }}>
            <button
              onClick={onApprove}
              style={{
                flex: 1, padding: '12px', background: '#16a34a', border: 'none',
                borderRadius: 8, color: '#fff', cursor: 'pointer', fontWeight: 600, fontSize: 15,
              }}
            >
              ✓ Approve & Execute
            </button>
            <button
              onClick={() => setShowReject(true)}
              style={{
                flex: 1, padding: '12px', background: 'transparent',
                border: '1px solid #475569', borderRadius: 8,
                color: '#94a3b8', cursor: 'pointer', fontSize: 15,
              }}
            >
              ✗ Reject
            </button>
          </div>
        ) : (
          <div>
            <textarea
              placeholder="Reason for rejection (optional)"
              value={rejectReason}
              onChange={e => setRejectReason(e.target.value)}
              style={{
                width: '100%', minHeight: 80, background: '#0f172a',
                border: '1px solid #334155', borderRadius: 8,
                color: '#e2e8f0', padding: 12, fontSize: 14, resize: 'vertical',
              }}
            />
            <div style={{ display: 'flex', gap: 10, marginTop: 12 }}>
              <button
                onClick={() => onReject(rejectReason)}
                style={{ flex: 1, padding: '10px', background: '#dc2626', border: 'none', borderRadius: 8, color: '#fff', cursor: 'pointer' }}
              >
                Confirm Reject
              </button>
              <button
                onClick={() => setShowReject(false)}
                style={{ padding: '10px 20px', background: 'transparent', border: '1px solid #475569', borderRadius: 8, color: '#94a3b8', cursor: 'pointer' }}
              >
                Back
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Field({ label, value }) {
  if (!value) return null;
  return (
    <div>
      <div style={{ fontSize: 11, color: '#475569', textTransform: 'uppercase', letterSpacing: 0.8 }}>{label}</div>
      <div style={{ fontSize: 14, color: '#e2e8f0', marginTop: 2 }}>{value}</div>
    </div>
  );
}
