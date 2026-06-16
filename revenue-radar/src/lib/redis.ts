let redis: { get: (key: string) => Promise<string | null>; set: (key: string, value: string, opts?: { ex?: number }) => Promise<void>; del: (key: string) => Promise<void> } | null = null

if (process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN) {
  const { Redis } = require('@upstash/redis')
  redis = new Redis({
    url: process.env.UPSTASH_REDIS_REST_URL,
    token: process.env.UPSTASH_REDIS_REST_TOKEN,
  })
}

export async function cacheGet(key: string): Promise<string | null> {
  if (!redis) return null
  return redis.get(key)
}

export async function cacheSet(key: string, value: string, ttlSeconds?: number): Promise<void> {
  if (!redis) return
  await redis.set(key, value, ttlSeconds ? { ex: ttlSeconds } : undefined)
}

export async function cacheDel(key: string): Promise<void> {
  if (!redis) return
  await redis.del(key)
}
