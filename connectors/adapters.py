"""Executable Linux/Windows, screen, Android and Google adapters."""
import base64
import io
import json
import os
import platform
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

class AdapterError(Exception): pass

class Adapters:
    def __init__(self, config): self.config=config
    def capabilities(self): return sorted(self.config.get('enabled',['system.info','pulse.doctor','pulse.test']))
    def execute(self, capability, args):
        if capability not in self.capabilities(): raise AdapterError('capability_disabled')
        if not isinstance(args,dict): raise AdapterError('invalid_args')
        if capability=='system.info':
            return {'platform':platform.system(),'python':platform.python_version(),
                    'node_present':bool(shutil.which('node')),'adb_present':bool(shutil.which('adb'))}
        if capability in ('pulse.doctor','pulse.test'):
            root=Path(self.config['pulse_dir']).expanduser().resolve()
            node=self.config.get('node','node')
            argv=[node,'app.mjs','doctor'] if capability=='pulse.doctor' else [node,'--test','test.mjs','reliability.test.mjs','crm.test.mjs','identity.test.mjs','care.test.mjs','business_knowledge.test.mjs']
            return self.run(argv,root,120)
        if capability=='command.run':
            # Commands defined locally by the owner, never remote shell text.
            if set(args)!={'name'}: raise AdapterError('named_command_required')
            command=self.config.get('commands',{}).get(args['name'])
            if not command or not isinstance(command.get('argv'),list) or not all(isinstance(v,str) for v in command['argv']):
                raise AdapterError('unknown_command')
            return self.run(command['argv'],Path(command['cwd']).expanduser(),min(600,int(command.get('timeout',120))))
        if capability.startswith('screen.'):
            return self.screen(capability,args)
        if capability.startswith('android.'):
            return self.android(capability,args)
        if capability.startswith('google.'):
            return self.google(capability,args)
        raise AdapterError('unknown_capability')
    def run(self,argv,cwd=None,timeout=30,binary=False):
        # File-backed output prevents unbounded RAM use from verbose commands.
        with tempfile.TemporaryFile() as out:
            child=subprocess.Popen(argv,cwd=cwd,stdout=out,stderr=subprocess.STDOUT,
                start_new_session=os.name!='nt')
            try: code=child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                if os.name=='nt': subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                else:
                    import signal
                    os.killpg(child.pid,signal.SIGKILL)
                child.wait();raise AdapterError('timeout_execution_uncertain') from None
            out.seek(0);raw=out.read(1_000_001)
        if binary:
            if code or len(raw)>1_000_000: raise AdapterError('capture_failed_or_too_large')
            return raw
        # Output intentionally goes only to private server; credentials are never commands.
        return {'exit_code':code,'text':raw[:64000].decode('utf-8','replace'),'truncated':len(raw)>64000}
    def png(self,image):
        image.thumbnail((1600,1600));buf=io.BytesIO();image.save(buf,format='PNG')
        if buf.tell()>1_000_000: raise AdapterError('capture_too_large')
        return {'mime':'image/png','base64':base64.b64encode(buf.getvalue()).decode(),
                'width':image.width,'height':image.height}
    def coordinate(self,args):
        if set(args)!={'x','y'} or any(type(args[k]) is not int or not 0<=args[k]<=20000 for k in ('x','y')):
            raise AdapterError('invalid_coordinates')
        return args['x'],args['y']
    def screen(self,cap,args):
        import pyautogui as gui
        gui.FAILSAFE=True
        if cap=='screen.capture': return self.png(gui.screenshot())
        if cap=='screen.click':
            x,y=self.coordinate(args)
            if not gui.onScreen(x,y): raise AdapterError('outside_screen')
            gui.click(x,y)
        elif cap=='screen.type':
            text=args.get('text')
            if set(args)!={'text'} or not isinstance(text,str) or len(text)>2000 or not text.isascii() or any(ord(c)<32 for c in text): raise AdapterError('ascii_text_only')
            gui.write(text,interval=0.01)
        elif cap=='screen.key':
            key=args.get('key')
            if set(args)!={'key'} or key not in ('enter','tab','esc','backspace','up','down','left','right'): raise AdapterError('invalid_key')
            gui.press(key)
        else: raise AdapterError('unknown_screen_action')
        return {'performed':True}
    def android(self,cap,args):
        serial=self.config.get('android_serial')
        if not isinstance(serial,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,100}',serial): raise AdapterError('android_serial_required')
        adb=[self.config.get('adb','adb'),'-s',serial]
        if cap=='android.info': return self.run(adb+['get-state'])
        if cap=='android.capture':
            from PIL import Image
            return self.png(Image.open(io.BytesIO(self.run(adb+['exec-out','screencap','-p'],binary=True))))
        if cap=='android.tap':
            x,y=self.coordinate(args);return self.run(adb+['shell','input','tap',str(x),str(y)])
        if cap=='android.key':
            key=args.get('key')
            mapping={'home':'3','back':'4','enter':'66','recent':'187'}
            if set(args)!={'key'} or key not in mapping: raise AdapterError('invalid_key')
            return self.run(adb+['shell','input','keyevent',mapping[key]])
        raise AdapterError('unknown_android_action')
    def google(self,cap,args):
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google.auth.transport.requests import AuthorizedSession
        path=Path(self.config['google_token']).expanduser()
        creds=Credentials.from_authorized_user_file(str(path))
        if not creds.valid:
            creds.refresh(Request());private_write(path,creds.to_json())
        session=AuthorizedSession(creds)
        if cap=='google.drive.list':
            if set(args)-{'query'} or not isinstance(args.get('query','trashed = false'),str) or len(args.get('query',''))>1000: raise AdapterError('invalid_drive_query')
            response=session.get('https://www.googleapis.com/drive/v3/files',params={
                'q':args.get('query','trashed = false'),'pageSize':30,'fields':'files(id,name,mimeType,webViewLink),nextPageToken'},timeout=30)
        else:
            identity=args.get('document_id','')
            if not isinstance(identity,str) or not re.fullmatch(r'[A-Za-z0-9_-]{10,200}',identity): raise AdapterError('invalid_document_id')
            url='https://docs.googleapis.com/v1/documents/'+identity
            if cap=='google.docs.read':
                if set(args)!={'document_id'}: raise AdapterError('invalid_document_args')
                response=session.get(url,params={'includeTabsContent':'true'},timeout=30)
            elif cap=='google.docs.append':
                text,tab=args.get('text'),args.get('tab_id')
                if set(args)!={'document_id','text','tab_id'} or not isinstance(text,str) or len(text)>10000 or not isinstance(tab,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}',tab): raise AdapterError('invalid_document_args')
                response=session.post(url+':batchUpdate',json={'requests':[{'insertText':{
                    'endOfSegmentLocation':{'tabId':tab},'text':text}}]},timeout=30)
            else: raise AdapterError('unknown_google_action')
        if response.status_code>=400: raise AdapterError('google_http_'+str(response.status_code))
        if len(response.content)>1_000_000: raise AdapterError('google_result_too_large')
        return {'data':response.json()}

def private_write(path,text):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.is_symlink(): raise AdapterError('symlink_not_allowed')
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as f: f.write(text)
    if os.name!='nt': path.chmod(0o600)
