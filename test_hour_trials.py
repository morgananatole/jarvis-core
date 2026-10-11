import asyncio
import json
import os
import secrets
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import httpx
from fastapi import FastAPI, HTTPException
from crm_admin import router, enrollment_router
from commercial_licenses import Licenses
from pulse_trials import HourTrials, release_version
import test_device_access as dev
from test_commercial_licenses import Collection


class Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        dev.Tests.setUp(self)
        self.db.commercial_licenses = Collection()
        self.licenses = Licenses(self.db)
        self.trials = HourTrials(self.db)
        env = patch.dict(os.environ, {'BUSINESS_ID': 'nova_vida', 'RENDER_GIT_COMMIT': 'test-release-a',
            'CRM_ADMIN_TOKEN': 'owner-test-' + 'x' * 40})
        env.start(); self.addCleanup(env.stop)
        self.app = FastAPI()
        self.app.include_router(router(lambda: self.db, lambda db: None))
        self.app.include_router(enrollment_router(lambda: self.db))

    def request(self, identity, body=b'', path='/crm/human'):
        return dev.Tests.request(self, identity, body=body, path=path, nonce=secrets.token_urlsafe(24))

    async def prepared(self):
        lic = await self.licenses.issue({'label': 'Teste fictício', 'kind': 'trial_hour'})
        code = (await self.service.issue('Dispositivo fictício', lic['license_id']))['code']
        device = (await self.service.enroll(code, self.jwk, lic['activation_key']))['device_id']
        return lic, device

    async def validated(self):
        lic, device = await self.prepared()
        await self.trials.validate(lic['license_id'], {'device_id': device, 'version': release_version(),
            'functioning_verified': True, 'evidence': 'Referência fictícia para teste local.'})
        return lic, device

    async def start(self, device):
        return await self.trials.start(device, {'activate': True, 'version': release_version()})

    async def test_preparation_and_validation_do_not_start_clock_or_allow_crm(self):
        lic, device = await self.validated()
        row = self.db.commercial_licenses.docs[lic['license_id']]
        self.assertIsNone(row['started_at']); self.assertIsNone(row['expires_at'])
        self.assertNotIn(lic['activation_key'], str(self.db.commercial_licenses.docs))
        with self.assertRaises(HTTPException) as e:
            await self.service.verify(self.request(device))
        self.assertEqual(e.exception.detail, 'trial_not_started')
        self.assertEqual(await self.service.verify(self.request(device, path='/device/trial/start'),
            allow_prepared=True), device)

    async def test_requires_real_check_attestation_correct_device_and_explicit_activation(self):
        lic, device = await self.prepared()
        with self.assertRaises(HTTPException) as e: await self.start(device)
        self.assertEqual(e.exception.detail, 'trial_validation_required')
        valid = {'device_id': device, 'version': release_version(), 'functioning_verified': True,
            'evidence': 'Referência fictícia para teste local.'}
        for changes in ({'functioning_verified': False}, {'evidence': ''}, {'device_id': 'f'*32}, {'version': 'wrong'}):
            with self.assertRaises(HTTPException): await self.trials.validate(lic['license_id'], valid | changes)
        await self.trials.validate(lic['license_id'], valid)
        with self.assertRaises(HTTPException): await self.trials.start(device, {})
        self.assertIsNone(self.db.commercial_licenses.docs[lic['license_id']]['started_at'])

    async def test_concurrent_starts_and_service_restart_preserve_exact_deadline(self):
        lic, device = await self.validated()
        results = await asyncio.gather(*[self.start(device) for _ in range(8)])
        self.assertEqual(len({r['started_at'] for r in results}), 1)
        self.assertEqual(len({r['expires_at'] for r in results}), 1)
        self.assertEqual(results[0]['expires_at'] - results[0]['started_at'], timedelta(seconds=3600))
        restarted = await HourTrials(self.db).start(device, {'activate': True, 'version': release_version()})
        self.assertEqual(restarted['expires_at'], results[0]['expires_at'])
        await self.service.verify(self.request(device))

    async def test_version_change_requires_revalidation_before_start(self):
        lic, device = await self.validated()
        with patch.dict(os.environ, {'RENDER_GIT_COMMIT': 'test-release-b'}):
            with self.assertRaises(HTTPException) as e: await self.start(device)
            self.assertEqual(e.exception.detail, 'trial_version_changed')
            _, status = await self.trials.for_device(device)
            self.assertEqual(status['state'], 'prepared')
            await self.trials.validate(lic['license_id'], {'device_id': device, 'version': release_version(),
                'functioning_verified': True, 'evidence': 'Nova verificação fictícia da versão.'})
            await self.start(device)

    async def test_exact_expiry_blocks_crm_and_retry_cannot_restart(self):
        lic, device = await self.validated()
        started = await self.start(device)
        end = started['expires_at']
        with patch('commercial_licenses.datetime') as dt, patch('pulse_trials.clock', return_value=end):
            dt.now.return_value = end
            with self.assertRaises(HTTPException) as e: await self.service.verify(self.request(device))
            self.assertEqual(e.exception.detail, 'trial_expired')
            retry = await self.start(device)
            self.assertEqual(retry['state'], 'expired'); self.assertEqual(retry['expires_at'], end)
            self.assertEqual(retry['remaining_seconds'], 0)
        with self.assertRaises(HTTPException): await self.service.issue('Novo', lic['license_id'])
        with self.assertRaises(HTTPException): await self.licenses.renew(lic['license_id'], {})

    async def test_revocation_business_and_device_membership_always_apply(self):
        lic, device = await self.validated()
        with patch.dict(os.environ, {'BUSINESS_ID': 'other'}):
            with self.assertRaises(HTTPException): await self.start(device)
        row = self.db.commercial_licenses.docs[lic['license_id']]
        row['revoked'] = True
        with self.assertRaises(HTTPException): await self.start(device)
        with self.assertRaises(HTTPException):
            await self.service.verify(self.request(device), allow_prepared=True, allow_expired=True)
        row['revoked'] = False
        self.db.authorized_devices.docs[device]['revoked'] = True
        with self.assertRaises(HTTPException): await self.start(device)

    async def test_replacement_device_needs_validation_and_used_trial_cannot_be_reenrolled(self):
        lic, device = await self.validated()
        await self.licenses.release(lic['license_id'], device)
        self.assertIsNone(self.db.commercial_licenses.docs[lic['license_id']]['validation'])
        code = (await self.service.issue('Substituto', lic['license_id']))['code']
        replacement = (await self.service.enroll(code, self.jwk, lic['activation_key']))['device_id']
        with self.assertRaises(HTTPException): await self.start(replacement)
        await self.trials.validate(lic['license_id'], {'device_id': replacement, 'version': release_version(),
            'functioning_verified': True, 'evidence': 'Teste fictício do substituto verificado.'})
        await self.start(replacement)
        await self.licenses.release(lic['license_id'], replacement)
        with self.assertRaises(HTTPException): await self.service.issue('Outro', lic['license_id'])

    async def test_inflight_code_cannot_enroll_after_trial_started(self):
        lic, device = await self.validated()
        code = (await self.service.issue('Em trânsito', lic['license_id']))['code']
        await self.start(device)
        await self.licenses.release(lic['license_id'], device)
        with self.assertRaises(HTTPException): await self.service.enroll(code, self.jwk, lic['activation_key'])

    async def test_invalid_trial_parameters(self):
        for extra in ({'max_devices': 2}, {'max_devices': True}, {'trial_days': 30},
            {'expires_at': (datetime.now(timezone.utc)+timedelta(days=1)).isoformat()}):
            with self.assertRaises(HTTPException):
                await self.licenses.issue({'label': 'Inválida', 'kind': 'trial_hour'} | extra)
        self.assertEqual(self.db.commercial_licenses.docs, {})

    async def test_owner_internal_and_permanent_access_unchanged(self):
        code = (await self.service.issue('Interno'))['code']
        device = (await self.service.enroll(code, self.jwk))['device_id']
        await self.service.verify(self.request(device))
        _, status = await self.trials.for_device(device)
        self.assertEqual(status, {'kind': 'internal'})
        with self.assertRaises(HTTPException): await self.start(device)
        lic = await self.licenses.issue({'label': 'Permanente', 'kind': 'permanent'})
        await self.licenses.active(lic['license_id'])

    async def test_http_prepared_device_cannot_validate_or_read_crm_and_signed_replay_rejected(self):
        lic, device = await self.prepared()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url='http://test') as c:
            path = '/crm/licenses/' + lic['license_id'] + '/validate-trial'
            req = self.request(device, body=b'{}', path=path)
            r = await c.post(path, headers=dict(req.headers), content=b'{}')
            self.assertEqual(r.status_code, 403)
            body = json.dumps({'activate': True, 'version': release_version()}).encode()
            req = self.request(device, body=body, path='/device/trial/start')
            r = await c.post('/device/trial/start', headers=dict(req.headers), content=body)
            self.assertEqual(r.status_code, 409)
            repeated = await c.post('/device/trial/start', headers=dict(req.headers), content=body)
            self.assertEqual(repeated.status_code, 401)
            anonymous = await c.post('/device/trial/start', json={'activate': True, 'version': release_version()})
            self.assertEqual(anonymous.status_code, 401)
            owner = {'Authorization': 'Bearer ' + os.environ['CRM_ADMIN_TOKEN']}
            r = await c.post(path, headers=owner, json={'device_id': device, 'version': release_version(),
                'functioning_verified': True, 'evidence': 'Teste fictício pelo proprietário.'})
            self.assertEqual(r.status_code, 200)
            self.assertIsNone(r.json()['started_at'])
            body = json.dumps({'activate': True, 'version': release_version()}).encode()
            req = self.request(device, body=body, path='/device/trial/start')
            r = await c.post('/device/trial/start', headers=dict(req.headers), content=body)
            self.assertEqual(r.status_code, 200)
            # Even a running commercial device cannot attest to its own functioning.
            req = self.request(device, body=b'{}', path=path)
            r = await c.post(path, headers=dict(req.headers), content=b'{}')
            self.assertEqual(r.status_code, 401)
