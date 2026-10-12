"""Signup isolation and click-only v4 launch; no live Meta requests."""
import os
import re
import json
import subprocess
import unittest
from unittest.mock import patch
from whatsapp_signup import preview
from crm_admin import panel


class SignupTests(unittest.TestCase):
    def render(self, **values):
        with patch.dict(os.environ, values, clear=True):
            return preview()

    def test_default_has_no_external_script_permission(self):
        response = self.render()
        self.assertIn('signupEnabled=false', response.body.decode())
        self.assertNotIn('https://connect.facebook.net', response.headers['content-security-policy'])
        self.assertIn("connect-src 'none'", response.headers['content-security-policy'])
        self.assertEqual(response.headers['cache-control'], 'no-store')

    def test_flag_alone_and_invalid_ids_cannot_enable_sdk(self):
        for app, config in [('', ''), ("12345';alert(1)//", '99999'), ('12345', 'not-an-id')]:
            response = self.render(WHATSAPP_SIGNUP_PREVIEW_ENABLED='true',
                WHATSAPP_SIGNUP_APP_ID=app, WHATSAPP_SIGNUP_CONFIG_ID=config)
            self.assertIn('signupEnabled=false', response.body.decode())
            self.assertNotIn('alert(1)', response.body.decode())
            self.assertNotIn('https://connect.facebook.net', response.headers['content-security-policy'])

    def test_enabled_scope_does_not_weaken_panel_or_expose_secrets(self):
        response = self.render(WHATSAPP_SIGNUP_PREVIEW_ENABLED='true',
            WHATSAPP_SIGNUP_APP_ID='12345', WHATSAPP_SIGNUP_CONFIG_ID='99999',
            CRM_ADMIN_TOKEN='secret-admin-value', WHATSAPP_ACCESS_TOKEN='secret-meta-value')
        html = response.body.decode()
        self.assertIn('signupEnabled=true', html)
        self.assertNotIn('secret-admin-value', html)
        self.assertNotIn('secret-meta-value', html)
        self.assertNotIn("connect-src 'self'", response.headers['content-security-policy'])
        self.assertIn("frame-ancestors 'none'", response.headers['content-security-policy'])
        self.assertNotIn('facebook', panel().headers['content-security-policy'])

    def test_sdk_load_and_login_require_separate_clicks_and_use_v4(self):
        html = self.render(WHATSAPP_SIGNUP_PREVIEW_ENABLED='true',
            WHATSAPP_SIGNUP_APP_ID='12345', WHATSAPP_SIGNUP_CONFIG_ID='99999').body.decode()
        script = re.search(r'<script nonce="[^"]+">(.*?)</script>', html, re.S).group(1)
        harness = r'''
const vm=require('node:vm'),assert=require('node:assert/strict');
let nodes={status:{textContent:''},start:{disabled:true}},scripts=[],login=[];
let listeners={};const window={addEventListener:(name,fn)=>listeners[name]=fn};
const FB={init:options=>{assert.equal(options.autoLogAppEvents,false)},login:(cb,options)=>login.push({cb,options})};
const document={getElementById:id=>nodes[id],createElement:()=>({}),head:{append:s=>scripts.push(s)}};
const context={window,document,FB};vm.createContext(context);vm.runInContext(SOURCE,context);
assert.equal(scripts.length,0);assert.equal(login.length,0);
nodes.start.onclick();assert.equal(scripts.length,1);assert.equal(login.length,0);
window.fbAsyncInit();assert.equal(login.length,0);
nodes.start.onclick();assert.equal(login.length,1);
const options=login[0].options;
assert.equal(options.config_id,'99999');assert.equal(options.response_type,'code');
assert.equal(options.extras.version,'v4');assert.equal(options.extras.featureType,'whatsapp_business_app_onboarding');
const before=nodes.status.textContent;
listeners.message({origin:'https://evil.facebook.com',data:{type:'WHATSAPP_EMBEDDED_SIGNUP',event:'FINISH'}});
assert.equal(nodes.status.textContent,before);
listeners.message({origin:'https://www.facebook.com',data:{type:'WHATSAPP_EMBEDDED_SIGNUP',event:'FINISH'}});
assert.ok(nodes.status.textContent.includes('verificação da API'));
assert.ok(nodes.status.textContent.includes('Não considere a conexão pronta'));
login[0].cb({authResponse:{code:'PRIVATE_OAUTH_CODE'}});
assert.ok(!nodes.status.textContent.includes('PRIVATE_OAUTH_CODE'));
assert.equal(scripts.length,1);
'''.replace('SOURCE', json.dumps(script))
        result = subprocess.run(['node', '-e', harness], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
