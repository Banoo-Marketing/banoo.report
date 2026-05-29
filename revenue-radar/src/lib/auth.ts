import { NextAuthOptions } from 'next-auth'
import GoogleProvider from 'next-auth/providers/google'
import { PrismaAdapter } from '@auth/prisma-adapter'
import { prisma } from './db'
import { encrypt } from './crypto'

export const authOptions: NextAuthOptions = {
  adapter: PrismaAdapter(prisma) as NextAuthOptions['adapter'],
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID ?? '',
      clientSecret: process.env.GOOGLE_CLIENT_SECRET ?? '',
      authorization: {
        params: {
          scope: [
            'openid',
            'email',
            'profile',
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.send',
          ].join(' '),
          access_type: 'offline',
          prompt: 'consent',
        },
      },
    }),
  ],
  callbacks: {
    async signIn({ user, account }) {
      if (account?.provider === 'google' && account.access_token && account.refresh_token) {
        try {
          const expiresAt = account.expires_at
            ? new Date(account.expires_at * 1000)
            : new Date(Date.now() + 3600 * 1000)

          await prisma.gmailToken.upsert({
            where: { userId: user.id! },
            update: {
              accessToken: encrypt(account.access_token),
              refreshToken: encrypt(account.refresh_token),
              expiresAt,
            },
            create: {
              userId: user.id!,
              accessToken: encrypt(account.access_token),
              refreshToken: encrypt(account.refresh_token),
              expiresAt,
            },
          })
        } catch (err) {
          console.error('Failed to store Gmail token:', err)
        }
      }
      return true
    },
    async session({ session, user }) {
      if (session.user) {
        session.user.id = user.id
      }
      return session
    },
  },
  pages: {
    signIn: '/login',
  },
  session: {
    strategy: 'database',
  },
}
