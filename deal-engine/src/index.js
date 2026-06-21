require('dotenv').config();
const cron = require('node-cron');
const { findDormantPIContacts, findCalendarFollowUps, createDraft } = require('./gmail');
const { searchPILawyers } = require('./apollo');
const { findGrowingPIFirms } = require('./search');
const { generateEmail } = require('./emailWriter');
const { createLogger } = require('./logger');

const TARGET_DRAFTS = 2;
const IS_TEST = process.argv.includes('--test');

async function runDealEngine() {
  const log = createLogger();
  log.write('=== Deal Engine run started ===');

  const prospects = [];

  // Priority 1: Gmail dormant PI contacts
  log.write('Scanning Gmail for dormant PI contacts...');
  try {
    const gmailProspects = await findDormantPIContacts(TARGET_DRAFTS);
    log.write(`Gmail: found ${gmailProspects.length} dormant contacts`);
    prospects.push(...gmailProspects);
  } catch (err) {
    log.write(`Gmail error: ${err.message}`);
  }

  // Priority 2: Google Calendar follow-ups
  if (prospects.length < TARGET_DRAFTS) {
    log.write('Scanning Calendar for uncontacted meeting attendees...');
    try {
      const calProspects = await findCalendarFollowUps(TARGET_DRAFTS - prospects.length);
      log.write(`Calendar: found ${calProspects.length} follow-up candidates`);
      prospects.push(...calProspects);
    } catch (err) {
      log.write(`Calendar error: ${err.message}`);
    }
  }

  // Priority 3: Apollo.io PI lawyers
  if (prospects.length < TARGET_DRAFTS) {
    log.write('Searching Apollo for PI lawyers in BC and Calgary...');
    try {
      const apolloProspects = await searchPILawyers(TARGET_DRAFTS - prospects.length + 2);
      log.write(`Apollo: found ${apolloProspects.length} prospects`);
      prospects.push(...apolloProspects);
    } catch (err) {
      log.write(`Apollo error: ${err.message}`);
    }
  }

  // Priority 4: Claude web research
  if (prospects.length < TARGET_DRAFTS) {
    log.write('Running Claude web research for growing PI firms...');
    try {
      const webProspects = await findGrowingPIFirms(TARGET_DRAFTS - prospects.length);
      log.write(`Web research: found ${webProspects.length} firms`);
      prospects.push(...webProspects);
    } catch (err) {
      log.write(`Web research error: ${err.message}`);
    }
  }

  log.write(`Total prospects gathered: ${prospects.length}`);

  // Generate emails and create drafts for top 2
  const topProspects = prospects.slice(0, TARGET_DRAFTS);
  let draftsCreated = 0;

  for (const prospect of topProspects) {
    try {
      log.write(`Generating email for ${prospect.name} <${prospect.email}> (PATH ${prospect.path}, source: ${prospect.source})`);
      const email = await generateEmail(prospect);
      log.write(`  Subject: ${email.subject}`);

      if (!email.to || email.to.trim() === '') {
        log.write(`  Skipped — no email address`);
        continue;
      }

      const draftId = await createDraft(email);
      log.write(`  Draft created: ${draftId}`);
      draftsCreated++;
    } catch (err) {
      log.write(`  Error for ${prospect.name}: ${err.message}`);
    }
  }

  log.write(`=== Run complete: ${draftsCreated}/${TARGET_DRAFTS} drafts created ===`);
  log.save();
}

if (IS_TEST) {
  console.log('Running in TEST mode (single run)...');
  runDealEngine().catch(console.error);
} else {
  console.log("Emod's Deal Engine started. Cron: every 3 hours.");
  runDealEngine(); // run once immediately on start
  cron.schedule('0 */3 * * *', () => {
    runDealEngine().catch(console.error);
  });
}
