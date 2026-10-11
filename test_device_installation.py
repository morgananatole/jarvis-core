"""Installation and enrollment recovery without consuming live codes or contacting Meta."""
import json
from pathlib import Path
import re
import subprocess
import unittest
from fastapi.testclient import TestClient
import main


class InstallationTests(unittest.TestCase):
    def test_manifest_and_worker_allow_online_app_without_caching_private_data(self):
        client = TestClient(main.app)
        manifest = client.get('/app.webmanifest')
        self.assertEqual(manifest.status_code, 200)
        self.assertEqual(manifest.json()['start_url'], '/painel')
        self.assertEqual(manifest.json()['display'], 'standalone')
        for icon in manifest.json()['icons']:
            self.assertEqual(client.get(icon['src']).status_code, 200)
        worker = client.get('/app-sw.js')
        self.assertEqual(worker.status_code, 200)
        self.assertNotIn('caches.', worker.text)
        self.assertNotIn("addEventListener('fetch'", worker.text)

    def test_device_enrollment_protects_existing_access_and_checks_storage_first(self):
        html = Path(__file__).with_name('panel.html').read_text()
        start = html.index('function deviceCapability(')
        end = html.index("el('deviceLogin').onclick=", start)
        activation = html[start:end]
        advice = html[html.index('function installationAdvice('):html.index('function installedWindow(')]
        script = r'''
const vm=require('node:vm'),assert=require('node:assert/strict');
const code=CODE,advice=ADVICE;
async function run(options={}){
 let calls=[],stored=options.existing,logins=0;
 const els={activate:{},activation:{value:'synthetic-code'},licenseKey:{value:'synthetic-license'},deviceLogin:{onclick:async()=>{logins++}}};
 const context={window:{isSecureContext:options.secure!==false},globalThis:{crypto:{subtle:{}},indexedDB:{}},
 el:id=>els[id],say:()=>{},keyStore:async value=>{calls.push(value?'save':'load');if(value&&options.storageFailure)throw Error('storage failed');if(value)stored=value;return stored},
 crypto:{subtle:{generateKey:async()=>({publicKey:{},privateKey:{synthetic:true}}),exportKey:async()=>({kty:'EC'})}},
 fetch:async(url,args)=>{calls.push('enroll');const body=JSON.parse(args.body);assert.equal(body.code,'synthetic-code');assert.equal(body.license_key,'synthetic-license');assert.equal(body.privateKey,undefined);return {ok:options.rejected!==true,json:async()=>({device_id:'new-device'})}}};
 vm.runInNewContext(code,context);await els.activate.onclick();return {calls,stored,logins,disabled:els.activate.disabled,context};
}
(async()=>{
 let x=await run({existing:{id:'existing-device',privateKey:{old:true}}});assert.equal(x.logins,1);assert.equal(x.stored.id,'existing-device');assert.deepEqual(x.calls,['load']);
 x=await run({secure:false});assert.deepEqual(x.calls,[]);assert.equal(x.logins,0);
 x=await run({storageFailure:true});assert.deepEqual(x.calls,['load','save']);assert.equal(x.logins,0);
 x=await run();assert.deepEqual(x.calls,['load','save','enroll','save']);assert.equal(x.logins,1);assert.equal(x.stored.id,'new-device');assert.equal(x.disabled,false);
 x=await run({rejected:true});assert.equal(x.logins,0);assert.equal(x.stored.pending,true);assert.equal(x.disabled,false);
 let ctx={};vm.runInNewContext(advice,ctx);
 assert.match(ctx.installationAdvice('iPhone',false),/Safari/);
 assert.match(ctx.installationAdvice('Android',false),/menu/);
 assert.match(ctx.installationAdvice('Windows',false),/notebook/);
 assert.match(ctx.installationAdvice('Linux',true),/aplicativo/);
 assert.match(ctx.installationAdvice('unknown',false),/nesta aba/);
 assert.match(x.context.deviceCapability({secure:true,crypto:false,storage:true}),/acesso seguro/);
 assert.equal(x.context.deviceCapability({secure:true,crypto:true,storage:true}),null);
})().catch(error=>{console.error(error);process.exitCode=1});
'''.replace('CODE', json.dumps(activation)).replace('ADVICE', json.dumps(advice))
        result = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_install_button_is_available_without_browser_install_event(self):
        html = Path(__file__).with_name('panel.html').read_text()
        button = re.search(r'<button[^>]*id="installApp"[^>]*>', html).group()
        self.assertNotIn('hidden', button)
        self.assertIn('id="installInstructions"', html)
        self.assertIn('id="whatsappPreparation"', html)
