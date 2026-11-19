#!/usr/bin/env node
/* usage: node run_apkscan.js <file>...  -> one JSON report per line (same schema as linkguard/apk.py) */
'use strict';
const fs = require('fs'), path = require('path');
const A = require(path.join(__dirname, '..', 'shared', 'dmsg-apkscan.js'));
(async () => {
  for (const f of process.argv.slice(2)) {
    const r = await A.inspect(new Uint8Array(fs.readFileSync(f)), path.basename(f));
    process.stdout.write(JSON.stringify({ file: path.basename(f), report: r }) + '\n');
  }
})().catch(e => { console.error(e); process.exit(2); });
