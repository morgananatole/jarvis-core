#!/usr/bin/env python3
"""Owner-only license CLI. Secrets are read from the environment, never arguments."""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from urllib.parse import urlsplit

parser = argparse.ArgumentParser()
parser.add_argument('action', choices=['list', 'issue', 'renew', 'revoke', 'device-code'])
parser.add_argument('--label')
parser.add_argument('--kind', choices=['subscription', 'permanent'], default='subscription')
parser.add_argument('--expires-at', help='ISO 8601 with timezone; e.g. 2026-11-10T18:00:00-03:00')
parser.add_argument('--devices', type=int, default=1)
parser.add_argument('--license-id')
parser.add_argument('--payment-reference')
args = parser.parse_args()
base = os.environ.get('JARVIS_BASE_URL', '').rstrip('/')
token = os.environ.get('CRM_ADMIN_TOKEN', '')
if urlsplit(base).scheme != 'https' or len(token) < 32:
    parser.error('Set JARVIS_BASE_URL to HTTPS and CRM_ADMIN_TOKEN to the owner credential.')
path, body, method = '/crm/licenses', None, 'GET'
if args.action == 'issue':
    body = {'label':args.label, 'kind':args.kind, 'expires_at':args.expires_at, 'max_devices':args.devices}
if args.action in ('renew','revoke'):
    if not args.license_id: parser.error('--license-id is required')
    path += '/' + args.license_id + '/' + args.action
    body = {'expires_at':args.expires_at, 'payment_reference':args.payment_reference} if args.action == 'renew' else {}
if args.action == 'device-code':
    if not args.license_id: parser.error('--license-id is required for a commercial device')
    path, body = '/crm/devices/code', {'label':args.label, 'license_id':args.license_id}
if body is not None: method = 'POST'
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs): return None
request = urllib.request.Request(base+path, data=json.dumps(body).encode() if body is not None else None,
    headers={'Authorization':'Bearer '+token, 'Content-Type':'application/json'}, method=method)
try:
    with urllib.request.build_opener(NoRedirect).open(request, timeout=20) as response:
        print(response.read().decode())
except urllib.error.HTTPError as error:
    print('HTTP '+str(error.code)+': '+error.read(4096).decode(), file=sys.stderr);sys.exit(1)
except urllib.error.URLError:
    print('Connection failed; no automatic retry of license issuance.', file=sys.stderr);sys.exit(1)
