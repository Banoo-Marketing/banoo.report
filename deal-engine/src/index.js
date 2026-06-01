require('dotenv').config({ path: require('path').join(__dirname, '..', '.env') });

const cron          = require('node-cron');
const { runEngine } = require('./engine');

const TEST_MODE = process.argv.includes('--test');

function validateEnv() {
  const required = ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'GOOGLE_REFRESH_TOKEN', 'ANTHROPIC_API_KEY', 'SENDER_EMAIL'];
  const missing  = required.filter(k => !process.env[k]);
  if (missing.length) {
    console.error(`\n  Missing required env vars: ${missing.join(', ')}`);
    console.error('  Run `npm run setup` to complete OAuth setup, then fill in your .env\n');
    process.exit(1);
  }
}

validateEnv();

if (TEST_MODE) {
  console.log('\n  Deal Engine — TEST MODE (running once immediately)\n');
  runEngine()
    .then(r => {
      console.log(`\n  Done: ${r.drafts} drafts created, ${r.errors} errors`);
      process.exit(0);
    })
    .catch(err => {
      console.error('  Fatal error:', err.message);
      process.exit(1);
    });
} else {
  // Every 3 hours
  cron.schedule('0 */3 * * *', async () => {
    console.log(`\n[${new Date().toISOString()}] Cron triggered — running Deal Engine`);
    await runEngine().catch(err => console.error('Engine error:', err.message));
  });

  console.log('\n  ┌─────────────────────────────────────────┐');
  console.log('  │  Emod\'s Deal Engine — RUNNING           │');
  console.log('  │  Cron: every 3 hours (0 */3 * * *)      │');
  console.log(`  │  Sender: ${(process.env.SENDER_EMAIL || '').padEnd(30)}│`);
  console.log('  │  Press Ctrl+C to stop                   │');
  console.log('  └─────────────────────────────────────────┘\n');

  // Run immediately on start
  console.log('  Running first cycle now...\n');
  runEngine().catch(err => console.error('Initial run error:', err.message));
}
