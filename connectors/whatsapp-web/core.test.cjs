const {test}=require('node:test');
const assert=require('node:assert/strict');
const {mkdtempSync,rmSync}=require('node:fs');
const {tmpdir}=require('node:os');
const path=require('node:path');
const {config,event,Journal,handle}=require('./core.cjs');
const number='5511999999999';
function input(){return {id:'web:test',phone:number,text:'oi'};}
function journal(t){const dir=mkdtempSync(path.join(tmpdir(),'pulse-pilot-'));const j=new Journal(dir);
 t.after(()=>{j.close();rmSync(dir,{recursive:true,force:true});});return j;}
test('disabled and empty/oversized/self allowlists fail closed',()=>{
 assert.throws(()=>config({}));
 assert.throws(()=>config({PULSE_WEB_PILOT:'true',PULSE_WEB_OWN_NUMBER:number,PULSE_WEB_ALLOWED:number}));
 assert.throws(()=>config({PULSE_WEB_PILOT:'true',PULSE_WEB_OWN_NUMBER:number}));
});
test('only fresh allowlisted direct text, no own/media/group/history',()=>{
 const msg={from:number+'@c.us',body:'oi',type:'chat',timestamp:1000,id:{_serialized:'test'}};
 const allowed=new Set([number]);assert.ok(event(msg,allowed,1001));
 for(const change of [{fromMe:true},{hasMedia:true},{type:'image'},{from:number+'@g.us'},{timestamp:0},{body:''}])
   assert.equal(event({...msg,...change},allowed,1001),null);
 assert.equal(event(msg,new Set(),1001),null);
});
test('duplicate events cannot send twice, including concurrent calls',async t=>{
 const j=journal(t);let sends=0;
 const call=()=>handle(input(),j,async()=>({state:'prepared',reply:'teste'}),async()=>{sends++;return {};},async()=>{});
 await Promise.all([call(),call()]);assert.equal(sends,1);assert.equal(j.state(input().id),'accepted');
});
test('uncertain transport is held, never automatically retried',async t=>{
 const j=journal(t);let sends=0;
 const call=()=>handle(input(),j,async()=>({state:'prepared',reply:'teste'}),async()=>{sends++;throw Error();},async()=>{});
 assert.equal(await call(),'review_required');assert.equal(await call(),'duplicate_held');assert.equal(sends,1);
});
test('human/opt-out and provider failures do not send',async t=>{
 const j=journal(t);let sends=0;
 assert.equal(await handle(input(),j,async()=>({state:'human_or_suppressed'}),async()=>sends++,async()=>{}),'suppressed');
 assert.equal(await handle({...input(),id:'other'},j,async()=>{throw Error();},async()=>sends++,async()=>{}),'review_required');
 assert.equal(sends,0);
});
test('persistent journal prevents resend after restart',async t=>{
 const dir=mkdtempSync(path.join(tmpdir(),'pulse-restart-'));t.after(()=>rmSync(dir,{recursive:true,force:true}));
 let j=new Journal(dir);assert.equal(j.claim('uncertain'),true);j.set('uncertain','sending');j.close();
 j=new Journal(dir);assert.equal(j.claim('uncertain'),false);assert.equal(j.state('uncertain'),'sending');j.close();
});
