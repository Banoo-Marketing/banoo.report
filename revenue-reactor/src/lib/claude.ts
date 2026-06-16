import Anthropic from '@anthropic-ai/sdk'

const MODEL = 'claude-sonnet-4-6'
let _client: Anthropic | null = null

function client(): Anthropic {
  if (!_client) _client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })
  return _client
}

type CreateParams = Parameters<Anthropic['messages']['create']>[0]

export async function callClaude(system: string, user: string, maxTokens = 2048): Promise<string> {
  const systemBlock = { type: 'text' as const, text: system, cache_control: { type: 'ephemeral' as const } }

  const res = await client().messages.create({
    model: MODEL,
    max_tokens: maxTokens,
    system: [systemBlock] as CreateParams['system'],
    messages: [{ role: 'user', content: user }],
  })

  const c = res.content[0]
  if (c.type !== 'text') throw new Error('Unexpected Claude response type')
  return c.text
}

export async function callClaudeJSON<T>(system: string, user: string, maxTokens = 2048): Promise<T> {
  const text = await callClaude(system, user, maxTokens)
  const match = text.match(/```json\n?([\s\S]*?)\n?```/) ?? text.match(/(\{[\s\S]*\}|\[[\s\S]*\])/)
  const jsonStr = match ? (match[1] ?? match[0]) : text
  return JSON.parse(jsonStr) as T
}
