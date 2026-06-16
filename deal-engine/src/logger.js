'use strict'
const fs = require('fs')
const path = require('path')

const LOGS_DIR = path.join(__dirname, '..', 'logs')

function ensureLogsDir() {
  if (!fs.existsSync(LOGS_DIR)) fs.mkdirSync(LOGS_DIR, { recursive: true })
}

function log(message, data = null) {
  ensureLogsDir()
  const ts = new Date().toISOString()
  const line = `[${ts}] ${message}${data ? '\n' + JSON.stringify(data, null, 2) : ''}`
  const filename = path.join(LOGS_DIR, `run_${new Date().toISOString().slice(0, 10)}.txt`)
  fs.appendFileSync(filename, line + '\n')
  console.log(line)
}

module.exports = { log }
