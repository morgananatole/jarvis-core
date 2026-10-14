"""Owner-side API client shared by CLI and MCP bridge."""
import json
import os
import re
from urllib.parse import urlparse
from urllib.request import Request,build_opener,HTTPRedirectHandler

class OwnerClient:
    def __init__(self):
        self.server=os.environ['JARVIS_SERVER'].rstrip('/')
        p=urlparse(self.server)
        if p.scheme!='https' or not p.netloc or p.path or p.username or p.password or p.query or p.fragment: raise ValueError('https_origin_required')
        self.token=os.environ['JARVIS_OWNER_TOKEN']
        if len(self.token)<32: raise ValueError('owner_token_missing')
    def call(self,path,body=None,key=None):
        headers={'Authorization':'Bearer '+self.token,'Content-Type':'application/json'}
        if key:headers['Idempotency-Key']=key
        class NoRedirect(HTTPRedirectHandler):
            def redirect_request(self,*a,**kw):return None
        data=json.dumps(body).encode() if body is not None else None
        with build_opener(NoRedirect()).open(Request(self.server+path,data=data,headers=headers),timeout=40) as r:raw=r.read(2_000_001)
        if len(raw)>2_000_000:raise ValueError('response_too_large')
        return json.loads(raw)
    def devices(self):return self.call('/execution/devices')
    def submit(self,device_id,capability,args,idempotency_key):
        return self.call('/execution/tasks',{'device_id':device_id,'capability':capability,'args':args},idempotency_key)
    def status(self,task_id):
        if not re.fullmatch(r'[0-9a-f]{32}',task_id):raise ValueError('invalid_task_id')
        return self.call('/execution/tasks/'+task_id)
