'use strict';
const {createHash} = require('node:crypto');
const {DatabaseSync} = require('node:sqlite');
const {mkdirSync, chmodSync} = require('node:fs');
const path = require('node:path');

function phone(value) {
  if (typeof value !== 'string' || !/^[0-9]{8,15}$/.test(value)) throw Error('invalid_phone');
  return value;
}
function config(env) {
  if (env.PULSE_WEB_PILOT !== 'true') throw Error('pilot_disabled');
  const own = phone(env.PULSE_WEB_OWN_NUMBER);
  const allowed = new Set((env.PULSE_WEB_ALLOWED || '').split(',').filter(Boolean).map(phone));
  if (!allowed.size || allowed.size > 5 || allowed.has(own)) throw Error('pilot_allowlist_required');
  return {own, allowed};
}
function event(message, allowed, now = Date.now()/1000) {
  if (message.fromMe || message.hasMedia || message.type !== 'chat'
      || !/^[0-9]{8,15}@c\.us$/.test(message.from || '')
      || !Number.isFinite(message.timestamp) || Math.abs(now-message.timestamp)>120
      || typeof message.body !== 'string' || !message.body.trim() || message.body.length>6000) return null;
  const sender = message.from.split('@')[0];
  if (!allowed.has(sender) || !message.id?._serialized) return null;
  return {action:'prepare', phone:sender, text:message.body,
    id:'web:'+createHash('sha256').update(message.id._serialized).digest('hex')};
}
class Journal {
  constructor(directory) {
    mkdirSync(directory, {recursive:true, mode:0o700});
    chmodSync(directory, 0o700);
    const file = path.join(directory, 'outbox.sqlite');
    this.db = new DatabaseSync(file); chmodSync(file,0o600);
    this.db.exec('PRAGMA synchronous=FULL; CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, state TEXT NOT NULL)');
  }
  claim(id) {
    return this.db.prepare('INSERT OR IGNORE INTO jobs VALUES (?, ?)').run(id,'processing').changes === 1;
  }
  set(id,state) { this.db.prepare('UPDATE jobs SET state=? WHERE id=?').run(state,id); }
  state(id) { return this.db.prepare('SELECT state FROM jobs WHERE id=?').get(id)?.state; }
  close() {this.db.close();}
}
async function deliver(id, target, text, journal, send, receipt) {
  journal.set(id,'sending');
  try {
    const sent = await send(target,text);
    // A transport acceptance is not a delivery/read receipt.
    journal.set(id,'accepted');
    await receipt(sent,text);
    return 'accepted';
  } catch {
    journal.set(id,'review_required');
    return 'review_required';
  }
}
async function handle(input, journal, prepare, send, receipt) {
  if (!journal.claim(input.id)) return 'duplicate_held';
  try {
    const result = await prepare(input);
    if (result.state !== 'prepared' || !result.reply) {
      journal.set(input.id, result.state === 'human_or_suppressed' ? 'suppressed' : 'review_required');
      return journal.state(input.id);
    }
    return await deliver(input.id,input.phone+'@c.us',result.reply,journal,send,receipt);
  } catch {journal.set(input.id,'review_required'); return 'review_required';}
}
module.exports={config,event,Journal,handle,deliver,phone};
