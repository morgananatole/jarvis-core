"""One-hour use after owner validation and one explicit signed activation.

Validation is an owner attestation to real checks, not an automated claim that
WhatsApp or a payment worked. No message, payment, or credentials are changed.
"""
import os
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from commercial_licenses import Licenses, business


def release_version():
    return os.getenv('RENDER_GIT_COMMIT') or 'pulse-hour-trial-v1'


def clock():
    return datetime.now(timezone.utc)


def public(record):
    started = record.get('started_at')
    expires = record.get('expires_at')
    state = ('expired' if expires <= clock() else 'started') if started else (
        'validated' if record.get('validation') and record['validation']['version'] == release_version() else 'prepared')
    return {'kind': 'trial_hour', 'state': state, 'started_at': started,
        'expires_at': expires, 'duration_seconds': 3600, 'version': release_version(),
        'remaining_seconds': max(0, int((expires - clock()).total_seconds())) if started else 3600}


class HourTrials:
    def __init__(self, db): self.db = db

    async def record(self, identity):
        record = await Licenses(self.db).active(identity, allow_expired=True, allow_prepared=True)
        if record['kind'] != 'trial_hour': raise HTTPException(409, 'not_hour_trial')
        return record

    async def validate(self, identity, body):
        record = await self.record(identity)
        if record.get('started_at') is not None: raise HTTPException(409, 'trial_already_started')
        if not isinstance(body, dict) or body.get('functioning_verified') is not True:
            raise HTTPException(400, 'trial_functioning_confirmation_required')
        evidence, device = body.get('evidence'), body.get('device_id')
        if not isinstance(evidence, str) or not 8 <= len(evidence.strip()) <= 500:
            raise HTTPException(400, 'trial_validation_evidence_required')
        if body.get('version') != release_version(): raise HTTPException(409, 'trial_version_changed')
        if device not in record['devices']:
            raise HTTPException(403, 'license_device_not_authorized')
        enrolled = await self.db.authorized_devices.find_one({'_id': device, 'license_id': identity, 'revoked': False})
        if not enrolled: raise HTTPException(403, 'license_device_not_authorized')
        result = await self.db.commercial_licenses.update_one({'_id': identity, 'business_id': business(),
            'revoked': False, 'devices': record['devices'], 'started_at': None}, {'$set': {
                'trial_state': 'validated', 'validation': {'at': clock(), 'device_id': device,
                    'version': release_version(), 'evidence': evidence.strip(), 'actor': 'owner'}}})
        if not result.matched_count: raise HTTPException(409, 'trial_changed_reload')
        return public(await self.record(identity))

    async def for_device(self, device):
        enrolled = await self.db.authorized_devices.find_one({'_id': device, 'revoked': False})
        if not enrolled: raise HTTPException(403, 'license_device_not_authorized')
        identity = enrolled.get('license_id')
        if not identity: return None, {'kind': 'internal'}
        record = await Licenses(self.db).active(identity, allow_expired=True, allow_prepared=True)
        if device not in record['devices']: raise HTTPException(403, 'license_device_not_authorized')
        return record, public(record) if record['kind'] == 'trial_hour' else {'kind': record['kind']}

    async def start(self, device, body):
        record, status = await self.for_device(device)
        if status['kind'] != 'trial_hour': raise HTTPException(409, 'not_hour_trial')
        # Retries with a fresh signed nonce return the original deadline.
        if record.get('started_at') is not None: return status
        if not isinstance(body, dict) or body.get('activate') is not True:
            raise HTTPException(400, 'trial_activation_required')
        validation = record.get('validation')
        if not validation or validation['device_id'] != device:
            raise HTTPException(409, 'trial_validation_required')
        if validation['version'] != release_version() or body.get('version') != release_version():
            raise HTTPException(409, 'trial_version_changed')
        now = clock()
        updated = await self.db.commercial_licenses.find_one_and_update({'_id': record['_id'],
            'business_id': business(), 'revoked': False, 'devices': record['devices'],
            'started_at': None, 'validation': validation}, {'$set': {
                'trial_state': 'started', 'started_at': now, 'expires_at': now + timedelta(seconds=3600)}}, return_document=True)
        if updated: return public(updated)
        latest, status = await self.for_device(device)
        if latest.get('started_at') is not None: return status
        raise HTTPException(409, 'trial_changed_reload')
