"""Outbound-only signed worker. Usage: python -m connectors.agent pair|run|doctor."""
import argparse
import base64
import hashlib
import json
import platform
import secrets
import sqlite3
import time
from getpass import getpass
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
from connectors.adapters import Adapters, AdapterError, private_write

class Client:
    def __init__(self,config):
        self.config=config
        url=config['server'];p=urlparse(url)
        if p.scheme!='https' or not p.netloc or p.path not in ('','/') or p.query or p.fragment or p.username or p.password: raise ValueError('https_origin_required')
        self.server=url.rstrip('/')
    def call(self,path,body=None,signed=True):
        data=json.dumps(body if body is not None else {}).encode()
        headers={'Content-Type':'application/json'}
        if signed:
            stamp,nonce=str(int(time.time())),secrets.token_urlsafe(24)
            key=serialization.load_pem_private_key(Path(self.config['key_file']).expanduser().read_bytes(),password=None)
            payload='\n'.join(['POST',path,stamp,nonce,hashlib.sha256(data).hexdigest(),'']).encode()
            r,s=utils.decode_dss_signature(key.sign(payload,ec.ECDSA(hashes.SHA256())))
            headers.update({'x-jarvis-device':self.config['device_id'],'x-jarvis-time':stamp,
                'x-jarvis-nonce':nonce,'x-jarvis-signature':base64.urlsafe_b64encode(r.to_bytes(32,'big')+s.to_bytes(32,'big')).decode().rstrip('=')})
        # Refuse redirects rather than forward credentials/key signatures to another host.
        from urllib.request import build_opener, HTTPRedirectHandler
        class NoRedirect(HTTPRedirectHandler):
            def redirect_request(self,*a,**kw): return None
        with build_opener(NoRedirect()).open(Request(self.server+path,data=data,headers=headers),timeout=40) as response:
            raw=response.read(2_000_001)
        if len(raw)>2_000_000: raise ValueError('response_too_large')
        return json.loads(raw)

def pair(config,path):
    if config.get('device_id'): raise ValueError('already_paired')
    keypath=Path(config['key_file']).expanduser()
    if keypath.exists(): raise ValueError('key_already_exists')
    key=ec.generate_private_key(ec.SECP256R1());pub=key.public_key().public_numbers()
    enc=lambda n:base64.urlsafe_b64encode(n.to_bytes(32,'big')).decode().rstrip('=')
    code=getpass('Código de pareamento do painel (não cole no chat): ')
    result=Client(config).call('/device/enroll',{'code':code,'public_key':{
        'kty':'EC','crv':'P-256','x':enc(pub.x),'y':enc(pub.y)}},signed=False)
    private_write(keypath,key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()).decode())
    config['device_id']=result['device_id'];private_write(path,json.dumps(config,indent=2))
    print('Pareado. Execute run para conectar; credenciais não exibidas.')

def run(config,once=False):
    adapter,client=Adapters(config),Client(config)
    state=Path(config['state_file']).expanduser();state.parent.mkdir(parents=True,exist_ok=True)
    if state.is_symlink(): raise ValueError('symlink_not_allowed')
    db=sqlite3.connect(state)
    if platform.system()!='Windows':state.chmod(0o600)
    db.execute('CREATE TABLE IF NOT EXISTS receipts(id TEXT PRIMARY KEY, payload TEXT)')
    client.call('/execution/agent/register',{'platform':platform.system(),'capabilities':adapter.capabilities()})
    while True:
        # Persist result before uploading; network failure resends result, never action.
        for identity,payload in db.execute('SELECT id,payload FROM receipts WHERE payload IS NOT NULL').fetchall():
            client.call('/execution/agent/tasks/'+identity+'/result',json.loads(payload))
            db.execute('DELETE FROM receipts WHERE id=?',(identity,));db.commit()
        task=client.call('/execution/agent/claim')
        if task:
            identity=task['_id'];old=db.execute('SELECT id FROM receipts WHERE id=?',(identity,)).fetchone()
            if old: state_name,output='uncertain',{'error':'previous_execution_unconfirmed'}
            else:
                db.execute('INSERT INTO receipts VALUES (?,NULL)',(identity,));db.commit()
                try:
                    output=adapter.execute(task['capability'],task['args'])
                    state_name='failed' if output.get('exit_code',0) else 'succeeded'
                except AdapterError as exc:
                    state_name='uncertain' if 'uncertain' in str(exc) else 'failed';output={'error':str(exc)}
                except Exception:
                    # A connector may have applied a click/write before failing.
                    state_name='uncertain';output={'error':'adapter_failed_check_target'}
            payload={'claim_token':task['claim_token'],'state':state_name,'output':output}
            db.execute('UPDATE receipts SET payload=? WHERE id=?',(json.dumps(payload),identity));db.commit()
            client.call('/execution/agent/tasks/'+identity+'/result',payload)
            db.execute('DELETE FROM receipts WHERE id=?',(identity,));db.commit()
        if once: break
        time.sleep(3)
    db.close()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['pair','run','doctor']);parser.add_argument('--config',default=str(Path.home()/'.jarvis-executor/config.json'));parser.add_argument('--once',action='store_true')
    args=parser.parse_args();config=json.loads(Path(args.config).read_text())
    if args.action=='pair':pair(config,args.config)
    elif args.action=='doctor':print(json.dumps({'paired':bool(config.get('device_id')),'platform':platform.system(),'enabled':Adapters(config).capabilities(),'system':Adapters(config).execute('system.info',{})},indent=2))
    else:
        from urllib.error import HTTPError
        while True:
            try:
                run(config,args.once);break
            except HTTPError as exc:
                if exc.code in (401,403):raise SystemExit('Dispositivo não autorizado. Execução interrompida.') from None
                if args.once:raise
                print('Servidor indisponível; resultados preservados. Nova conexão em 10s.',flush=True)
                time.sleep(10)
            except (OSError,ValueError):
                if args.once:raise
                print('Conexão interrompida; resultados preservados. Nova conexão em 10s.',flush=True)
                time.sleep(10)
if __name__=='__main__':main()
