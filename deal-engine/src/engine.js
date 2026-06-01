require('dotenv').config({ path: require('path').join(__dirname, '..', '.env') });

const Logger                             = require('./logger');
const { scanDormantContacts, createDraft } = require('./gmail');
const { findPILawyers }                  = require('./apollo');
const { findPIAdvertisers }              = require('./semrush');
const { findNewProspects }               = require('./search');
const { writeReengagementEmail, writeColdEmail } = require('./emailWriter');

const DRAFTS_PER_RUN = 2;

async function runEngine() {
  const logger  = new Logger();
  let drafts    = 0;
  let errors    = 0;
  const targets = [];

  // ── Phase 1: Gmail scan — dormant contacts (PATH A, warm) ─────────────────
  logger.info('Phase 1: Gmail dormant contact scan');
  try {
    const dormant = await scanDormantContacts(logger);
    targets.push(...dormant);
  } catch (err) {
    logger.warn('Gmail scan skipped (no refresh token?)', { message: err.message });
  }

  // ── Phase 2: Apollo.io — PI lawyers in Ontario/GTA (PATH B, verified emails)
  if (targets.length < DRAFTS_PER_RUN) {
    logger.info('Phase 2: Apollo PI lawyer search');
    try {
      const found = await findPILawyers(DRAFTS_PER_RUN - targets.length + 5, logger);
      targets.push(...found);
    } catch (err) {
      logger.warn('Apollo search error', { message: err.message });
    }
  }

  // ── Phase 3: SEMrush — firms actively spending on Google Ads ──────────────
  if (targets.length < DRAFTS_PER_RUN) {
    logger.info('Phase 3: SEMrush PI advertiser discovery');
    try {
      const found = await findPIAdvertisers(logger);
      targets.push(...found.slice(0, DRAFTS_PER_RUN - targets.length + 5));
    } catch (err) {
      logger.warn('SEMrush unavailable', { message: err.message });
    }
  }

  // ── Phase 4: Claude fallback — curated Ontario PI firms ───────────────────
  if (targets.length < DRAFTS_PER_RUN) {
    logger.info('Phase 4: Claude fallback prospect research');
    try {
      const found = await findNewProspects(DRAFTS_PER_RUN - targets.length + 3, logger);
      targets.push(...found);
    } catch (err) {
      logger.error('Claude prospect research failed', { message: err.message });
      errors++;
    }
  }

  if (targets.length === 0) {
    logger.warn('No prospects found in this run — check API keys');
    logger.summary(0, errors);
    return { drafts: 0, errors };
  }

  logger.info(`Total prospects: ${targets.length} — generating ${DRAFTS_PER_RUN} drafts`);

  // ── Draft generation ───────────────────────────────────────────────────────
  const used = new Set();

  for (const prospect of targets) {
    if (drafts >= DRAFTS_PER_RUN) break;
    if (used.has(prospect.email))  continue;
    used.add(prospect.email);

    logger.prospect(prospect);

    let email = null;
    try {
      email = prospect.path === 'A'
        ? await writeReengagementEmail(prospect, logger)
        : await writeColdEmail(prospect, logger);
    } catch (err) {
      logger.error('Email generation failed', { email: prospect.email, message: err.message });
      errors++;
      continue;
    }

    if (!email?.subject || !email?.body) {
      logger.warn('Claude returned invalid email', { prospect: prospect.email });
      errors++;
      continue;
    }

    try {
      const draftId = await createDraft(prospect.email, email.subject, email.body, logger);
      logger.draft(draftId, prospect.email, email.subject);
      drafts++;
    } catch (err) {
      logger.error('Draft creation failed', { email: prospect.email, message: err.message });
      errors++;
    }

    await sleep(500);
  }

  logger.summary(drafts, errors);
  return { drafts, errors };
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

module.exports = { runEngine };
