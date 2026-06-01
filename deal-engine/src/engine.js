require('dotenv').config({ path: require('path').join(__dirname, '..', '.env') });

const Logger               = require('./logger');
const { scanDormantContacts, createDraft } = require('./gmail');
const { findPIAdvertisers }                = require('./semrush');
const { findNewProspects }                 = require('./search');
const { writeReengagementEmail, writeColdEmail } = require('./emailWriter');

const DRAFTS_PER_RUN = 2;

async function runEngine() {
  const logger  = new Logger();
  let drafts    = 0;
  let errors    = 0;
  const targets = [];

  // ── 1. Gmail scan — dormant contacts (PATH A) ──────────────────────────────
  logger.info('Phase 1: Gmail dormant contact scan');
  try {
    const dormant = await scanDormantContacts(logger);
    targets.push(...dormant);
  } catch (err) {
    logger.error('Gmail scan error', { message: err.message });
    errors++;
  }

  // ── 2. SEMrush discovery — PI advertisers (PATH B) ─────────────────────────
  if (targets.length < DRAFTS_PER_RUN) {
    logger.info('Phase 2: SEMrush PI advertiser discovery');
    try {
      const found = await findPIAdvertisers(logger);
      targets.push(...found.slice(0, DRAFTS_PER_RUN - targets.length + 5));
    } catch (err) {
      logger.warn('SEMrush unavailable — falling back to Claude prospect research', { message: err.message });
    }
  }

  // ── 3. Claude fallback — curated Ontario PI firms ──────────────────────────
  if (targets.length < DRAFTS_PER_RUN) {
    logger.info('Phase 3: Claude fallback prospect research');
    try {
      const found = await findNewProspects(DRAFTS_PER_RUN - targets.length + 3, logger);
      targets.push(...found);
    } catch (err) {
      logger.error('Claude prospect research error', { message: err.message });
      errors++;
    }
  }

  if (targets.length === 0) {
    logger.warn('No prospects found in this run');
    logger.summary(0, errors);
    return { drafts: 0, errors };
  }

  logger.info(`Total prospects: ${targets.length} — generating ${DRAFTS_PER_RUN} drafts`);

  // ── 3. Write emails + create drafts ────────────────────────────────────────
  const used = new Set();

  for (const prospect of targets) {
    if (drafts >= DRAFTS_PER_RUN) break;
    if (used.has(prospect.email)) continue;
    used.add(prospect.email);

    logger.prospect(prospect);

    // Generate email via Claude
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

    if (!email || !email.subject || !email.body) {
      logger.warn('Claude returned invalid email', { prospect: prospect.email });
      errors++;
      continue;
    }

    // Create Gmail draft
    try {
      const draftId = await createDraft(prospect.email, email.subject, email.body, logger);
      logger.draft(draftId, prospect.email, email.subject);
      drafts++;
    } catch (err) {
      logger.error('Draft creation failed', { email: prospect.email, message: err.message });
      errors++;
    }

    // Small delay between Claude calls
    await sleep(500);
  }

  logger.summary(drafts, errors);
  return { drafts, errors };
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

module.exports = { runEngine };
