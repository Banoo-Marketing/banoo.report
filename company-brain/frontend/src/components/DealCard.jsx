import React from 'react';

const STAGE_COLOR = {
  prospecting: '#6366f1',
  qualification: '#8b5cf6',
  proposal: '#0ea5e9',
  negotiation: '#f59e0b',
  closed_won: '#22c55e',
  closed_lost: '#ef4444',
};

const TIER_COLOR = {
  PLATINUM: { bg: '#7c3aed22', text: '#a78bfa' },
  GOLD: { bg: '#d97706222', text: '#fbbf24' },
  SILVER: { bg: '#94a3b822', text: '#cbd5e1' },
  STANDARD: { bg: '#1e293b', text: '#64748b' },
};

export default function DealCard({ deal, onClick }) {
  const renewalDays = deal.renewal_date
    ? Math.ceil((new Date(deal.renewal_date) - new Date()) / 86400000)
    : null;

  const tier = deal.clv_tier || 'STANDARD';
  const tierStyle = TIER_COLOR[tier] || TIER_COLOR.STANDARD;

  return (
    <div
      onClick={onClick}
      style={{
        background: '#1e293b',
        border: '1px solid #334155',
        borderRadius: 10,
        padding: '16px 18px',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'border-color 0.15s',
      }}
      onMouseEnter={e => onClick && (e.currentTarget.style.borderColor = '#38bdf8')}
      onMouseLeave={e => (e.currentTarget.style.borderColor = '#334155')}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <strong style={{ color: '#e2e8f0', fontSize: 15 }}>{deal.company}</strong>
          <span style={{
            marginLeft: 8, fontSize: 11, padding: '2px 7px', borderRadius: 5,
            background: tierStyle.bg, color: tierStyle.text,
          }}>
            {tier}
          </span>
        </div>
        <span style={{
          fontSize: 13, fontWeight: 600, color: '#22c55e',
        }}>
          ${Number(deal.amount).toLocaleString()}
        </span>
      </div>

      <p style={{ fontSize: 13, color: '#64748b', marginTop: 4 }}>{deal.name}</p>

      <div style={{ display: 'flex', gap: 12, marginTop: 12, flexWrap: 'wrap' }}>
        <Tag
          label={deal.stage?.replace('_', ' ')}
          color={STAGE_COLOR[deal.stage] || '#64748b'}
        />
        {renewalDays !== null && (
          <Tag
            label={`Renews in ${renewalDays}d`}
            color={renewalDays <= 7 ? '#ef4444' : renewalDays <= 14 ? '#f59e0b' : '#38bdf8'}
          />
        )}
        {deal.days_since_activity > 7 && (
          <Tag label={`${deal.days_since_activity}d no activity`} color="#f59e0b" />
        )}
      </div>

      {deal.contact_name && (
        <p style={{ fontSize: 12, color: '#475569', marginTop: 10 }}>
          👤 {deal.contact_name} · {deal.industry || 'Unknown industry'}
        </p>
      )}
    </div>
  );
}

function Tag({ label, color }) {
  return (
    <span style={{
      fontSize: 11, padding: '3px 8px', borderRadius: 6,
      background: `${color}22`, color, fontWeight: 500, textTransform: 'capitalize',
    }}>
      {label}
    </span>
  );
}
