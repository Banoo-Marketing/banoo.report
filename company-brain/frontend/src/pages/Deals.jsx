import React, { useEffect, useState } from 'react';
import DealCard from '../components/DealCard';
import { api } from '../App';

const STAGES = ['all', 'prospecting', 'qualification', 'proposal', 'negotiation', 'closed_won', 'closed_lost'];

export default function Deals() {
  const [deals, setDeals] = useState([]);
  const [stage, setStage] = useState('all');
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [analysing, setAnalysing] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [nurture, setNurture] = useState(null);

  useEffect(() => {
    setLoading(true);
    const url = stage === 'all' ? '/deals' : `/deals?stage=${stage}`;
    api.get(url).then(d => { setDeals(d.deals || []); setLoading(false); });
  }, [stage]);

  const openDeal = async (deal) => {
    const full = await api.get(`/deals/${deal.id}`);
    setSelected(full);
    setAnalysis(null);
    setNurture(null);
  };

  const analyse = async () => {
    if (!selected) return;
    setAnalysing(true);
    const result = await api.post(`/deals/${selected.id}/analyse`);
    setAnalysis(result);
    setAnalysing(false);
  };

  const getNurture = async () => {
    if (!selected?.contact_id) return;
    const result = await api.get(`/contacts/${selected.contact_id}/nurture`);
    setNurture(result.suggestion);
  };

  return (
    <div style={{ display: 'flex', gap: 24 }}>
      {/* Left: deal list */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h1 style={{ color: '#e2e8f0', fontSize: 20, fontWeight: 700 }}>Deals</h1>
          <span style={{ color: '#64748b', fontSize: 13 }}>{deals.length} deals</span>
        </div>

        {/* Stage filter */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
          {STAGES.map(s => (
            <button
              key={s}
              onClick={() => setStage(s)}
              style={{
                padding: '5px 12px', borderRadius: 6, fontSize: 12,
                border: `1px solid ${stage === s ? '#38bdf8' : '#334155'}`,
                background: stage === s ? '#38bdf822' : 'transparent',
                color: stage === s ? '#38bdf8' : '#64748b',
                cursor: 'pointer', textTransform: 'capitalize',
              }}
            >
              {s.replace('_', ' ')}
            </button>
          ))}
        </div>

        {loading
          ? <p style={{ color: '#64748b' }}>Loading…</p>
          : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {deals.map(deal => (
                <DealCard key={deal.id} deal={deal} onClick={() => openDeal(deal)} />
              ))}
            </div>
          )
        }
      </div>

      {/* Right: deal detail panel */}
      {selected && (
        <div style={{
          width: 360, flexShrink: 0, background: '#1e293b',
          border: '1px solid #334155', borderRadius: 12, padding: 20,
          height: 'fit-content', position: 'sticky', top: 20,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
            <h2 style={{ color: '#e2e8f0', fontSize: 16 }}>{selected.company}</h2>
            <button onClick={() => setSelected(null)} style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: 18 }}>×</button>
          </div>

          <InfoRow label="Deal" value={selected.name} />
          <InfoRow label="Value" value={`$${Number(selected.amount).toLocaleString()}`} />
          <InfoRow label="Stage" value={selected.stage?.replace('_', ' ')} />
          <InfoRow label="Contact" value={selected.contact_name} />
          <InfoRow label="CLV Tier" value={selected.clv_tier} />
          <InfoRow label="Renewal" value={selected.renewal_date ? new Date(selected.renewal_date).toLocaleDateString() : '—'} />
          <InfoRow label="Last activity" value={selected.days_since_activity != null ? `${selected.days_since_activity}d ago` : '—'} />

          <div style={{ borderTop: '1px solid #334155', margin: '16px 0' }} />

          {/* AI actions */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
            <button
              onClick={analyse}
              disabled={analysing}
              style={{ flex: 1, padding: '9px', background: '#0ea5e9', border: 'none', borderRadius: 8, color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}
            >
              {analysing ? '⏳ Analysing…' : '🤖 AI Analyse'}
            </button>
            <button
              onClick={getNurture}
              style={{ flex: 1, padding: '9px', background: 'transparent', border: '1px solid #334155', borderRadius: 8, color: '#94a3b8', cursor: 'pointer', fontSize: 13 }}
            >
              💡 Nurture tip
            </button>
          </div>

          {analysis && (
            <div style={{ background: '#0f172a', borderRadius: 8, padding: 14, marginBottom: 12 }}>
              <div style={{ fontSize: 12, color: '#64748b', marginBottom: 6 }}>AI DECISION</div>
              <div style={{ color: '#38bdf8', fontWeight: 600, fontSize: 14 }}>
                {analysis.action?.replace('_', ' ')}
                {analysis.urgency && (
                  <span style={{ marginLeft: 8, fontSize: 11, color: '#f59e0b' }}>{analysis.urgency}</span>
                )}
              </div>
              <p style={{ color: '#94a3b8', fontSize: 13, marginTop: 8, lineHeight: 1.5 }}>{analysis.reason}</p>
              {analysis.suggested_message && (
                <p style={{ color: '#64748b', fontSize: 12, marginTop: 6, fontStyle: 'italic' }}>{analysis.suggested_message}</p>
              )}
            </div>
          )}

          {nurture && (
            <div style={{ background: '#0f172a', borderRadius: 8, padding: 14 }}>
              <div style={{ fontSize: 12, color: '#64748b', marginBottom: 6 }}>NURTURE SUGGESTION</div>
              <p style={{ color: '#94a3b8', fontSize: 13, lineHeight: 1.5 }}>{nurture}</p>
            </div>
          )}

          {/* Pending actions for this deal */}
          {selected.pending_actions?.length > 0 && (
            <>
              <div style={{ borderTop: '1px solid #334155', margin: '16px 0' }} />
              <div style={{ fontSize: 12, color: '#64748b', marginBottom: 8 }}>QUEUED ACTIONS</div>
              {selected.pending_actions.map(a => (
                <div key={a.id} style={{ fontSize: 12, color: '#94a3b8', padding: '6px 0', borderBottom: '1px solid #1e293b' }}>
                  {a.action_type} — <span style={{ color: '#f59e0b' }}>{a.status}</span>
                </div>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}

function InfoRow({ label, value }) {
  if (!value) return null;
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid #0f172a' }}>
      <span style={{ fontSize: 12, color: '#475569' }}>{label}</span>
      <span style={{ fontSize: 13, color: '#e2e8f0', textTransform: 'capitalize' }}>{value}</span>
    </div>
  );
}
