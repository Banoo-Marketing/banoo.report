import Anthropic from '@anthropic-ai/sdk'
import type { TextBlockParam } from '@anthropic-ai/sdk/resources/messages'

const MODEL = 'claude-sonnet-4-6'

let client: Anthropic | null = null

function getClient(): Anthropic {
  if (!client) {
    client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })
  }
  return client
}

export async function callClaude(
  systemPrompt: string,
  userMessage: string,
  options: { maxTokens?: number; temperature?: number } = {}
): Promise<string> {
  const anthropic = getClient()

  const systemBlock: TextBlockParam & { cache_control?: { type: 'ephemeral' } } = {
    type: 'text',
    text: systemPrompt,
    cache_control: { type: 'ephemeral' },
  }

  const response = await anthropic.messages.create({
    model: MODEL,
    max_tokens: options.maxTokens ?? 2048,
    system: [systemBlock] as Parameters<typeof anthropic.messages.create>[0]['system'],
    messages: [
      {
        role: 'user',
        content: userMessage,
      },
    ],
  })

  const content = response.content[0]
  if (content.type !== 'text') throw new Error('Unexpected response type from Claude')
  return content.text
}

export async function callClaudeJSON<T>(
  systemPrompt: string,
  userMessage: string,
  options: { maxTokens?: number } = {}
): Promise<T> {
  const text = await callClaude(systemPrompt, userMessage, { maxTokens: options.maxTokens ?? 2048 })

  const jsonMatch = text.match(/```json\n?([\s\S]*?)\n?```/) ?? text.match(/(\{[\s\S]*\}|\[[\s\S]*\])/)
  const jsonStr = jsonMatch ? jsonMatch[1] ?? jsonMatch[0] : text

  try {
    return JSON.parse(jsonStr) as T
  } catch {
    throw new Error(`Failed to parse Claude response as JSON: ${text.slice(0, 200)}`)
  }
}
