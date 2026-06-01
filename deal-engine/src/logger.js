const fs   = require('fs');
const path = require('path');

const LOG_DIR = path.join(__dirname, '..', 'logs');

function timestamp() {
  return new Date().toISOString();
}

function runId() {
  return new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
}

class Logger {
  constructor() {
    this.runId   = runId();
    this.logFile = path.join(LOG_DIR, `run_${this.runId}.txt`);
    this.entries = [];

    if (!fs.existsSync(LOG_DIR)) fs.mkdirSync(LOG_DIR, { recursive: true });

    this._write(`\n${'='.repeat(60)}`);
    this._write(`DEAL ENGINE RUN — ${timestamp()}`);
    this._write('='.repeat(60));
  }

  info(msg, data)  { this._log('INFO',  msg, data); }
  warn(msg, data)  { this._log('WARN',  msg, data); }
  error(msg, data) { this._log('ERROR', msg, data); }

  prospect(p) {
    this._write('\n--- PROSPECT ---');
    this._write(`Name:    ${p.name}`);
    this._write(`Email:   ${p.email}`);
    this._write(`Firm:    ${p.firm || '—'}`);
    this._write(`Path:    ${p.path}`);
    this._write(`Source:  ${p.source}`);
    if (p.context) this._write(`Context: ${p.context}`);
  }

  draft(draftId, to, subject) {
    this._write(`\n✓ DRAFT CREATED`);
    this._write(`  To:      ${to}`);
    this._write(`  Subject: ${subject}`);
    this._write(`  ID:      ${draftId}`);
  }

  summary(draftsCreated, errors) {
    this._write(`\n${'─'.repeat(60)}`);
    this._write(`SUMMARY: ${draftsCreated} drafts created, ${errors} errors`);
    this._write(`Completed: ${timestamp()}`);
    this._write('='.repeat(60) + '\n');
    console.log(`[Deal Engine] Run complete — ${draftsCreated} drafts, ${errors} errors. Log: ${this.logFile}`);
  }

  _log(level, msg, data) {
    const line = `[${timestamp()}] ${level}: ${msg}${data ? ' — ' + JSON.stringify(data) : ''}`;
    this._write(line);
    console.log(line);
  }

  _write(line) {
    fs.appendFileSync(this.logFile, line + '\n');
  }
}

module.exports = Logger;
