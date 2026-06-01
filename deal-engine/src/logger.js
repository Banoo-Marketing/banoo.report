const fs = require('fs');
const path = require('path');

function createLogger() {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const logDir = path.join(__dirname, '..', 'logs');
  if (!fs.existsSync(logDir)) fs.mkdirSync(logDir, { recursive: true });

  const logFile = path.join(logDir, `run_${timestamp}.txt`);
  const lines = [];

  function write(msg) {
    const line = `[${new Date().toISOString()}] ${msg}`;
    console.log(line);
    lines.push(line);
  }

  function save() {
    fs.writeFileSync(logFile, lines.join('\n') + '\n');
  }

  return { write, save, logFile };
}

module.exports = { createLogger };
