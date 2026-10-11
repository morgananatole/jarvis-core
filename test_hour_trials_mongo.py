"""Opt-in integration checks against an isolated, loopback MongoDB server.

PULSE_TEST_MONGO_URI=mongodb://127.0.0.1:27029 python -m unittest test_hour_trials_mongo -v
Never reads MONGODB_URI or a production database. Each test owns a random DB.
"""
import asyncio
import json
import os
import re
import secrets
import unittest
from datetime import timedelta
from unittest.mock import patch

import httpx
from fastapi import FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from commercial_licenses import Licenses
from device_access import DeviceAccess
from pulse_trials import HourTrials, release_version
from crm_admin import router, enrollment_router
import test_device_access as device_helpers


@unittest.skipUnless(os.getenv('PULSE_TEST_MONGO_URI'), 'isolated MongoDB not configured')
class MongoTrials(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        uri = os.environ['PULSE_TEST_MONGO_URI']
        if not re.fullmatch(r'mongodb://127\.0\.0\.1:[0-9]{2,5}', uri):
            raise ValueError('Only an explicit loopback MongoDB test server is allowed')
        self.env = patch.dict(os.environ, {'BUSINESS_ID': 'integration_test',
            'RENDER_GIT_COMMIT': 'mongo-integration-release'})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.client = AsyncIOMotorClient(uri, tz_aware=True, serverSelectionTimeoutMS=3000)
        device_helpers.Tests.setUp(self)
        # The key/signature helpers above create a mock DB; replace it entirely.
        self.db = self.client['pulse_test_' + secrets.token_hex(12)]
        self.service = DeviceAccess(self.db)
        self.licenses, self.trials = Licenses(self.db), HourTrials(self.db)
        await self.client.admin.command('ping')
        await self.service.initialize()

    async def asyncTearDown(self):
        await self.client.drop_database(self.db.name)
        self.client.close()

    def request(self, identity, **kwargs):
        return device_helpers.Tests.request(self, identity, nonce=secrets.token_urlsafe(24), **kwargs)

    async def prepared(self):
        lic = await self.licenses.issue({'label': 'Disposable integration test', 'kind': 'trial_hour'})
        code = (await self.service.issue('Disposable device', lic['license_id']))['code']
        device = (await self.service.enroll(code, self.jwk, lic['activation_key']))['device_id']
        return lic, device

    async def validated(self):
        lic, device = await self.prepared()
        await self.trials.validate(lic['license_id'], {'device_id': device,
            'functioning_verified': True, 'version': release_version(),
            'evidence': 'Synthetic integration check; no external service attestation.'})
        return lic, device

    async def start(self, device):
        return await self.trials.start(device, {'activate': True, 'version': release_version()})

    async def test_validation_does_not_start_or_authorize_crm(self):
        lic, device = await self.validated()
        row = await self.db.commercial_licenses.find_one({'_id': lic['license_id']})
        self.assertIsNone(row['started_at'])
        self.assertIsNone(row['expires_at'])
        self.assertNotIn(lic['activation_key'], str(row))
        with self.assertRaises(HTTPException) as error:
            await self.service.verify(self.request(device))
        self.assertEqual(error.exception.detail, 'trial_not_started')

    async def test_concurrent_starts_fix_one_deadline_and_reconnect_preserves_it(self):
        lic, device = await self.validated()
        results = await asyncio.gather(*(self.start(device) for _ in range(32)))
        self.assertEqual(len({r['started_at'] for r in results}), 1)
        self.assertEqual(len({r['expires_at'] for r in results}), 1)
        self.assertEqual(results[0]['expires_at'] - results[0]['started_at'], timedelta(seconds=3600))
        another = AsyncIOMotorClient(os.environ['PULSE_TEST_MONGO_URI'], tz_aware=True)
        try:
            resumed = await HourTrials(another[self.db.name]).start(device, {'activate': True})
            self.assertEqual(resumed['expires_at'], results[0]['expires_at'])
        finally:
            another.close()
        await self.service.verify(self.request(device))

    async def test_real_unique_nonce_rejects_concurrent_replay(self):
        _, device = await self.validated()
        await self.start(device)
        request = self.request(device)
        results = await asyncio.gather(*(self.service.verify(request) for _ in range(16)), return_exceptions=True)
        self.assertEqual(sum(r == device for r in results), 1)
        self.assertTrue(all(r == device or isinstance(r, HTTPException) and r.status_code == 401 for r in results))

    async def test_concurrent_enrollment_enforces_single_seat(self):
        lic = await self.licenses.issue({'label': 'Seat race', 'kind': 'trial_hour'})
        codes = [(await self.service.issue('Disposable device', lic['license_id']))['code'] for _ in range(16)]
        results = await asyncio.gather(*(self.service.enroll(c, self.jwk, lic['activation_key']) for c in codes), return_exceptions=True)
        self.assertEqual(sum(isinstance(r, dict) for r in results), 1)
        row = await self.db.commercial_licenses.find_one({'_id': lic['license_id']})
        self.assertEqual(len(row['devices']), 1)
        self.assertEqual(await self.db.authorized_devices.count_documents({'license_id': lic['license_id']}), 1)

    async def test_exact_expiry_and_revocation_deny_access(self):
        lic, device = await self.validated()
        end = (await self.start(device))['expires_at']
        with patch('commercial_licenses.datetime') as dt, patch('pulse_trials.clock', return_value=end):
            dt.now.return_value = end
            with self.assertRaises(HTTPException) as error:
                await self.service.verify(self.request(device))
            self.assertEqual(error.exception.detail, 'trial_expired')
            self.assertEqual((await self.start(device))['expires_at'], end)
        await self.db.commercial_licenses.update_one({'_id': lic['license_id']}, {'$set': {'revoked': True}})
        with self.assertRaises(HTTPException):
            await self.service.verify(self.request(device), allow_expired=True, allow_prepared=True)

    async def test_replacement_invalidates_validation_and_business_is_checked(self):
        lic, device = await self.validated()
        with patch.dict(os.environ, {'BUSINESS_ID': 'another_business'}):
            with self.assertRaises(HTTPException):
                await self.start(device)
        await self.licenses.release(lic['license_id'], device)
        code = (await self.service.issue('Replacement', lic['license_id']))['code']
        replacement = (await self.service.enroll(code, self.jwk, lic['activation_key']))['device_id']
        with self.assertRaises(HTTPException) as error:
            await self.start(replacement)
        self.assertEqual(error.exception.detail, 'trial_validation_required')

    async def test_internal_and_permanent_access_remain_available(self):
        code = (await self.service.issue('Internal'))['code']
        device = (await self.service.enroll(code, self.jwk))['device_id']
        self.assertEqual(await self.service.verify(self.request(device)), device)
        self.assertEqual((await self.trials.for_device(device))[1], {'kind': 'internal'})
        lic = await self.licenses.issue({'label': 'Permanent', 'kind': 'permanent'})
        await self.licenses.active(lic['license_id'])

    async def test_http_owner_validation_signed_start_and_replay(self):
        lic, device = await self.prepared()
        app = FastAPI()
        app.include_router(router(lambda: self.db, lambda db: None))
        app.include_router(enrollment_router(lambda: self.db))
        owner_token = 'isolated-owner-' + secrets.token_hex(24)
        with patch.dict(os.environ, {'CRM_ADMIN_TOKEN': owner_token}):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                validate_path = '/crm/licenses/' + lic['license_id'] + '/validate-trial'
                device_request = self.request(device, body=b'{}', path=validate_path)
                denied = await client.post(validate_path, headers=dict(device_request.headers), content=b'{}')
                self.assertEqual(denied.status_code, 403)
                body = json.dumps({'activate': True, 'version': release_version()}).encode()
                request = self.request(device, body=body, path='/device/trial/start')
                before = await client.post('/device/trial/start', headers=dict(request.headers), content=body)
                self.assertEqual(before.status_code, 409)
                validated = await client.post(validate_path, headers={'Authorization': 'Bearer ' + owner_token},
                    json={'device_id': device, 'version': release_version(), 'functioning_verified': True,
                        'evidence': 'Synthetic HTTP integration check with isolated MongoDB.'})
                self.assertEqual(validated.status_code, 200)
                self.assertIsNone(validated.json()['started_at'])
                request = self.request(device, body=body, path='/device/trial/start')
                started = await client.post('/device/trial/start', headers=dict(request.headers), content=body)
                self.assertEqual(started.status_code, 200)
                replay = await client.post('/device/trial/start', headers=dict(request.headers), content=body)
                self.assertEqual(replay.status_code, 401)
                fresh = self.request(device, body=body, path='/device/trial/start')
                retry = await client.post('/device/trial/start', headers=dict(fresh.headers), content=body)
                self.assertEqual(retry.json()['expires_at'], started.json()['expires_at'])
