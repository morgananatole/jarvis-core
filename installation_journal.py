"""Repeatable installation plans and private, structured evidence without secrets."""
import json
import os
import re
import stat
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError

STEPS = {'deployment', 'storage', 'panel', 'manifest', 'sdk_preview', 'device',
         'license', 'company_profile', 'isolation', 'meta_review', 'meta_access',
         'business_app', 'meta_signup', 'webhook', 'inbound', 'delivery',
         'human_pause', 'resume', 'followup', 'pix', 'trial_hour', 'migration_plan'}
RESULTS = {'passed', 'failed', 'blocked', 'pending'}
EVIDENCE = {'configured', 'storage_available', 'contact_memory_ready', 'http_status',
            'meta_error_code', 'verified', 'sdk_enabled', 'domain_allowed',
            'app_review_approved', 'access_verified', 'business_app_connected'}
ROUTES = [('deployment', '/health'), ('storage', '/ready'), ('panel', '/painel'),
          ('manifest', '/app.webmanifest'), ('sdk_preview', '/whatsapp/conectar')]


def base_url(value):
    parsed = urlsplit(value)
    host = parsed.hostname or ''
    if (parsed.scheme != 'https' or parsed.username or parsed.password or parsed.query
            or parsed.fragment or parsed.path not in {'', '/'} or parsed.port not in {None, 443}
            or not re.fullmatch(r'[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+', host)):
        raise ValueError('use_public_https_origin_without_credentials_or_query')
    return 'https://' + host.lower()


def plan(case, number_state, goal):
    if case not in {'new_device', 'new_company', 'current_number'}:
        raise ValueError('invalid_installation_case')
    if number_state not in {'cloud_api', 'business_app', 'new', 'unknown'} or goal not in {'pulse', 'coexistence'}:
        raise ValueError('invalid_installation_path')
    if case == 'new_device':
        return {'path': 'reuse_company_device_access', 'meta_setup_required': False,
                'steps': ['deployment', 'storage', 'panel', 'manifest', 'license', 'device'],
                'blocker': None, 'next_action': 'Autorizar o novo navegador no ambiente existente; não refazer Meta.'}
    steps = ['deployment', 'storage', 'isolation', 'company_profile'] if case == 'new_company' else ['deployment', 'storage']
    if goal == 'pulse' and number_state == 'cloud_api':
        return {'path': 'reuse_existing_cloud_api', 'meta_setup_required': case == 'new_company',
                'steps': steps + ['webhook', 'inbound', 'delivery', 'human_pause', 'resume', 'device'],
                'blocker': None, 'next_action': 'Conferir canal existente e atendimento pelo PULSE.'}
    if goal == 'coexistence' and number_state == 'cloud_api':
        return {'path': 'controlled_migration_review', 'meta_setup_required': True,
                'steps': steps + ['migration_plan', 'meta_review', 'meta_access', 'business_app', 'meta_signup', 'webhook', 'delivery'],
                'blocker': 'api_only_to_business_app_path_not_verified',
                'next_action': 'Definir sequência oficial e recuperação antes de remover o número; não repetir signup bloqueado.'}
    if goal == 'coexistence':
        return {'path': 'business_app_eligibility_first', 'meta_setup_required': True,
                'steps': steps + ['meta_review', 'meta_access', 'business_app', 'sdk_preview', 'meta_signup', 'webhook', 'inbound', 'delivery', 'human_pause', 'resume', 'device'],
                'blocker': None if number_state == 'business_app' else 'business_app_eligibility_not_verified',
                'next_action': 'Confirmar Business App existente/elegível e provedor aprovado antes do cadastro de coexistência.'}
    return {'path': 'cloud_api_onboarding', 'meta_setup_required': True,
            'steps': steps + ['meta_signup', 'webhook', 'inbound', 'delivery', 'human_pause', 'resume', 'device'],
            'blocker': 'number_state_unknown' if number_state == 'unknown' else None,
            'next_action': 'Conectar número autorizado pela rota Cloud API e testar envio/recibo.'}


def evidence_fields(values):
    if not isinstance(values, dict) or set(values) - EVIDENCE:
        raise ValueError('unsupported_evidence_field')
    for key, value in values.items():
        if key in {'http_status', 'meta_error_code'}:
            if type(value) is not int or not 0 <= value <= 9999999:
                raise ValueError('invalid_evidence_value')
        elif type(value) is not bool:
            raise ValueError('boolean_evidence_required')
    return values


def append(path, run_id, step, result, evidence=None, duration=0, source='operator_report'):
    if not re.fullmatch(r'[a-f0-9]{32}', run_id) or step not in STEPS or result not in RESULTS:
        raise ValueError('invalid_checkpoint')
    if source not in {'public_http_probe', 'operator_report'} or not isinstance(duration, (int, float)) or not 0 <= duration <= 86400:
        raise ValueError('invalid_checkpoint_metadata')
    if not str(path).endswith('.jsonl'):
        raise ValueError('journal_must_be_jsonl')
    record = {'version': 1, 'run_id': run_id, 'at_utc': datetime.now(timezone.utc).isoformat(),
              'step': step, 'result': result, 'source': source,
              'duration_seconds': round(duration, 3), 'evidence': evidence_fields(evidence or {})}
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0), 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError('journal_must_be_regular_file')
        os.fchmod(fd, 0o600)
        os.write(fd, (json.dumps(record, ensure_ascii=False) + '\n').encode())
        os.fsync(fd)
    finally:
        os.close(fd)
    return record


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def probe(origin, route):
    request = Request(base_url(origin) + route, headers={'User-Agent': 'PULSE-Installation-Check/1'}, method='GET')
    try:
        with build_opener(NoRedirect).open(request, timeout=10) as response:
            status = response.status
            body = response.read(65537) if route in {'/ready', '/app.webmanifest'} else b''
        if len(body) > 65536:
            return 'failed', {'http_status': status}
        values = {'http_status': status}
        if route == '/ready':
            data = json.loads(body)
            for key in ('configured', 'storage_available', 'contact_memory_ready'):
                values[key] = data.get(key) is True
            return ('passed' if all(values[k] for k in ('configured', 'storage_available', 'contact_memory_ready')) else 'blocked'), values
        if route == '/app.webmanifest':
            data = json.loads(body)
            return ('passed' if data.get('start_url') == '/painel' and data.get('display') == 'standalone' else 'failed'), values
        # HTTP availability is not proof of SDK activation, Meta access or delivery.
        return ('passed' if status == 200 else 'failed'), values
    except HTTPError as error:
        return 'failed', {'http_status': error.code}
    except Exception:
        return 'failed', {}  # Never serialize exception strings, URL queries or remote bodies.


def audit(origin, case, number_state, goal, output, run_id=None):
    origin = base_url(origin)
    selected = plan(case, number_state, goal)
    identity = run_id or uuid.uuid4().hex
    started = time.monotonic()
    records = []
    for step, route in ROUTES:
        tick = time.monotonic()
        result, evidence = probe(origin, route)
        records.append(append(output, identity, step, result, evidence,
                              time.monotonic() - tick, 'public_http_probe'))
    checked = {row['step'] for row in records if row['result'] == 'passed' and row['step'] != 'sdk_preview'}
    return {'run_id': identity, 'base_url': origin, 'case': case, 'number_state': number_state,
            'goal': goal, 'plan': selected, 'http_checks': records,
            'still_requires_real_evidence': [step for step in selected['steps'] if step not in checked],
            'duration_seconds': round(time.monotonic() - started, 3),
            'ready_to_sell_verified': False, 'registration_changed': False}
