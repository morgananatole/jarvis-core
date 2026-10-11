"""Public viewer isolation and truthful guided installation states."""
import json
from pathlib import Path
import subprocess
import unittest

class GuidedOnboardingTests(unittest.TestCase):
    def test_public_viewer_never_calls_private_services(self):
        html=Path('panel.html').read_text()
        code=html[html.index('function entryMode('):html.index('function installationAdvice(')]
        script=r'''
const vm=require('node:vm'),assert=require('node:assert/strict');
let nodes={},calls=[],demo=0;const el=id=>nodes[id]||(nodes[id]={hidden:false,setAttribute:(k,v)=>{nodes[id][k]=v},scrollIntoView:()=>{}});
el('demoStart').onclick=()=>demo++;
const context={el,businessConfigured:false,token:'',api:()=>{throw Error('viewer requested private data')},fetch:()=>{throw Error('viewer requested network')},switchView:x=>calls.push(x),say:x=>calls.push(x)};
vm.runInNewContext(CODE,context);
el('viewProduct').onclick();assert.equal(demo,1);assert.equal(el('demo').hidden,false);assert.equal(el('login').hidden,true);assert.equal(el('installation').hidden,true);
el('backWelcome').onclick();assert.equal(el('welcome').hidden,false);assert.equal(el('demo').hidden,true);
el('useKey').onclick();assert.equal(el('login').hidden,false);assert.equal(el('demo').hidden,true);
context.refreshJourney();assert.equal(el('journeyStart').hidden,true);el('journeyStart').onclick();assert.equal(calls.includes('human'),false);
context.businessConfigured=true;context.refreshJourney();assert.equal(el('journeyStart').hidden,false);el('journeyStart').onclick();assert.equal(calls.includes('human'),true);
(async()=>{await el('journeyPhone').onclick();assert.match(el('guidedStatus').textContent,/proprietário/);await el('journeyReview').onclick();assert.match(el('guidedStatus').textContent,/comprovação real/);})().catch(e=>{console.error(e);process.exitCode=1});
'''.replace('CODE',json.dumps(code))
        result=subprocess.run(['node','-e',script],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_install_help_is_visible_from_welcome_and_viewer(self):
        html=Path('panel.html').read_text()
        code=html[html.index("el('installApp').onclick="):html.index("window.addEventListener('appinstalled'")]
        script=r"""
const vm=require('node:vm'),assert=require('node:assert/strict');let els={installApp:{},installation:{hidden:true,scrollIntoView:()=>{}},installGuide:{},installStatus:{}};
vm.runInNewContext(CODE,{el:id=>els[id],installPrompt:null,refreshInstallation:()=>{}});
(async()=>{await els.installApp.onclick();assert.equal(els.installation.hidden,false);assert.equal(els.installGuide.open,true);assert.match(els.installStatus.textContent,/orientação/);})().catch(e=>{console.error(e);process.exitCode=1});
""".replace('CODE',json.dumps(code))
        result=subprocess.run(['node','-e',script],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
