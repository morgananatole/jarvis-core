'use strict';
// Local pilot only: no production URL, campaign loop or imported address book.
const {spawn} = require('node:child_process');
const readline = require('node:readline');
const path = require('node:path');
const {randomUUID,createHash} = require('node:crypto');
const {mkdirSync,chmodSync} = require('node:fs');
const {config,event,Journal,handle,deliver,phone} = require('./core.cjs');

async function start() {
  const cfg = config(process.env);
  const root = path.resolve(__dirname,'../..');
  const directory = path.resolve(process.env.PULSE_WEB_DATA_DIR || path.join(root,'.pulse-web-pilot'));
  mkdirSync(directory,{recursive:true,mode:0o700}); chmodSync(directory,0o700);
  const journal = new Journal(directory);
  const child = spawn(process.env.PULSE_PYTHON || 'python3',['-u','local_web_pilot.py'],{
    cwd:root,env:process.env,stdio:['pipe','pipe','ignore']});
  const lines = readline.createInterface({input:child.stdout})[Symbol.asyncIterator]();
  async function answer() {
    let timer;
    try {
      const next = await Promise.race([lines.next(),new Promise((_,reject)=>{
        timer=setTimeout(()=>reject(Error('bridge_timeout')),60000);
      })]);
      if (next.done) throw Error('bridge_closed');
      return JSON.parse(next.value);
    } finally {clearTimeout(timer);}
  }
  if ((await answer()).state!=='ready') {child.kill(); throw Error('bridge_not_ready');}
  async function bridge(payload) {
    try {
      child.stdin.write(JSON.stringify(payload)+'\n');
      const result = await answer();
      if (result.state==='review_required') throw Error('bridge_review_required');
      return result;
    } catch {child.kill();throw Error('bridge_unavailable');}
  }
  const {Client,LocalAuth} = require('whatsapp-web.js');
  const qr = require('qrcode-terminal');
  const client = new Client({authStrategy:new LocalAuth({clientId:'pulse-pilot',dataPath:path.join(directory,'auth')}),
    puppeteer:{headless:true}, webVersionCache:{type:'local',path:path.join(directory,'cache')}});
  let ready=false, running=false, stopped=false;
  function halt() {if(stopped)return;ready=false; stopped=true; child.kill(); void client.destroy(); journal.close();}
  process.once('SIGINT',halt); process.once('SIGTERM',halt);
  client.on('qr',code=>{console.log('Pareie somente o número de teste. QR privado, não compartilhar.');qr.generate(code,{small:true});});
  client.on('auth_failure',()=>{console.log('autenticacao_falhou');halt();});
  client.on('disconnected',()=>{console.log('desconectado_revisao_necessaria');halt();});
  client.on('ready',async()=>{
    if (client.info?.wid?.user!==cfg.own) {console.log('numero_pareado_incorreto');halt();return;}
    ready=true; console.log('piloto_conectado');
    const [command,destination,...words]=process.argv.slice(2);
    if (command==='send') {
      try {
        const number=phone(destination), text=words.join(' ');
        if (!cfg.allowed.has(number)||!text.trim()||text.length>4000) throw Error('invalid_send');
        const id='manual:'+randomUUID(); journal.claim(id);
        console.log(await deliver(id,number+'@c.us',text,journal,(to,body)=>client.sendMessage(to,body),
          (sent,body)=>bridge({action:'receipt',phone:number,id:'webout:'+createHash('sha256').update(sent.id._serialized).digest('hex'),text:body})));
      } catch {console.log('envio_nao_concluido_revisar');}
      halt();
    } else if (command) {console.log('comando_invalido');halt();}
  });
  client.on('message',async message=>{
    if (!ready || stopped) return;
    const input=event(message,cfg.allowed); if (!input) return;
    if (running) {console.log('piloto_ocupado_mensagem_nao_processada');return;}
    running=true;
    try {console.log(await handle(input,journal,bridge,(to,body)=>client.sendMessage(to,body),
      (sent,body)=>bridge({action:'receipt',phone:input.phone,id:'webout:'+createHash('sha256').update(sent.id._serialized).digest('hex'),text:body})));}
    finally {running=false;}
  });
  await client.initialize();
}
start().catch(()=>{console.error('piloto_indisponivel_verifique_configuracao');process.exit(1);});
