const Anthropic = require('@anthropic-ai/sdk');

/**
 * Use Claude to identify new PI law firms in Ontario that are actively growing.
 * Returns a list of prospect objects for cold outreach.
 */
async function findGrowingPIFirms(limit = 3) {
  const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

  const prompt = `You are a research assistant helping find outreach prospects for Banoo Marketing.

Find ${limit} personal injury law firms in Ontario, Canada (Toronto, Mississauga, Brampton, Hamilton, or Ottawa) that show signs of growth or active hiring. These should be small firms (1–20 lawyers).

For each firm, provide:
- Firm name
- City
- A contact name and title if you know it (Managing Partner preferred)
- A specific detail that signals growth (e.g., recently opened, hiring, expanded practice, new location)
- Why they'd be a good fit for PPC/lead gen/intake automation services

Respond ONLY with a JSON array, no markdown, no explanation. Format:
[
  {
    "firmName": "...",
    "city": "...",
    "contactName": "...",
    "title": "...",
    "email": "",
    "growthSignal": "...",
    "fitReason": "..."
  }
]`;

  let content;
  try {
    const msg = await client.messages.create({
      model: 'claude-sonnet-4-6',
      max_tokens: 1024,
      messages: [{ role: 'user', content: prompt }],
    });
    content = msg.content[0]?.text || '[]';
  } catch (err) {
    console.error('Claude search error:', err.message);
    return [];
  }

  let firms = [];
  try {
    const jsonMatch = content.match(/\[[\s\S]*\]/);
    if (jsonMatch) firms = JSON.parse(jsonMatch[0]);
  } catch {
    console.error('Failed to parse Claude search response');
    return [];
  }

  return firms.slice(0, limit).map((f) => ({
    source: 'web_research',
    path: 'B',
    name: f.contactName || `Team at ${f.firmName}`,
    email: f.email || '',
    title: f.title || 'Managing Partner',
    firmName: f.firmName,
    city: f.city,
    growthSignal: f.growthSignal,
    fitReason: f.fitReason,
  }));
}

module.exports = { findGrowingPIFirms };
