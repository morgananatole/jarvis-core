"""Deployment-bound commercial access; raw activation secrets are never persisted."""
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from device_access import digest


def business():
    return os.getenv('BUSINESS_ID', 'nova_vida')


def expiration(value):
    try:
        date = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if date.tzinfo is None or date <= datetime.now(timezone.utc): raise ValueError()
        return date.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(400, 'expiry_requires_future_date_with_timezone')


class Licenses:
    def __init__(self, db): self.db = db

    async def issue(self, body):
        if not isinstance(body, dict): raise HTTPException(400, 'invalid_license')
        kind, seats = body.get('kind'), body.get('max_devices', 1)
        if kind not in ('subscription', 'permanent') or type(seats) is not int or not 1 <= seats <= 100:
            raise HTTPException(400, 'invalid_license_kind_or_device_limit')
        label = body.get('label', '')
        if not isinstance(label, str) or not label.strip() or len(label) > 120:
            raise HTTPException(400, 'invalid_license_label')
        trial_days = body.get('trial_days')
        if trial_days is not None:
            if type(trial_days) is not int or trial_days != 30 or kind != 'subscription' or body.get('expires_at') is not None:
                raise HTTPException(400, 'invalid_30_day_trial')
        expires = (datetime.now(timezone.utc) + timedelta(days=30) if trial_days == 30
                   else expiration(body.get('expires_at')) if kind == 'subscription' else None)
        identity, key = secrets.token_hex(16), secrets.token_urlsafe(32)
        await self.db.commercial_licenses.insert_one({'_id': identity, 'business_id': business(),
            'label': label.strip(), 'kind': kind, 'expires_at': expires, 'key_hash': digest(key),
            'max_devices': seats, 'devices': [], 'revoked': False, 'trial_days': trial_days, 'created_at': datetime.now(timezone.utc)})
        return {'license_id': identity, 'activation_key': key, 'kind': kind, 'expires_at': expires,
            'max_devices': seats, 'trial_days': trial_days, 'note': 'Save this key now; it is displayed once.'}

    async def active(self, identity, allow_expired=False):
        if not isinstance(identity, str) or not re.fullmatch(r'[0-9a-f]{32}', identity):
            raise HTTPException(400, 'invalid_license_id')
        record = await self.db.commercial_licenses.find_one({'_id': identity, 'business_id': business(), 'revoked': False})
        if not record: raise HTTPException(403, 'license_revoked_or_missing')
        if not allow_expired and record['kind'] == 'subscription' and record['expires_at'] <= datetime.now(timezone.utc):
            raise HTTPException(403, 'license_expired')
        return record

    async def reserve(self, identity, key, device):
        record = await self.active(identity)
        if not isinstance(key, str) or len(key) > 100 or not secrets.compare_digest(digest(key), record['key_hash']):
            raise HTTPException(403, 'invalid_license_key')
        # One atomic update enforces the seat limit even with simultaneous enrollments.
        query = {'_id': identity, 'business_id': business(), 'revoked': False,
            '$expr': {'$lt': [{'$size': '$devices'}, '$max_devices']}}
        if record['kind'] == 'subscription': query['expires_at'] = {'$gt': datetime.now(timezone.utc)}
        reserved = await self.db.commercial_licenses.find_one_and_update(query, {'$push': {'devices': device}}, return_document=True)
        if not reserved: raise HTTPException(403, 'license_expired_revoked_or_device_limit')

    async def release(self, identity, device):
        await self.db.commercial_licenses.update_one({'_id': identity, 'business_id': business()}, {'$pull': {'devices': device}})

    async def renew(self, identity, body):
        record = await self.db.commercial_licenses.find_one({'_id': identity, 'business_id': business()})
        if not record: raise HTTPException(404, 'license_not_found')
        if record['kind'] != 'subscription': raise HTTPException(409, 'permanent_license_has_no_renewal')
        expires = expiration(body.get('expires_at'))
        if expires <= record['expires_at']: raise HTTPException(400, 'renewal_must_extend_validity')
        reference = body.get('payment_reference')
        if not isinstance(reference, str) or not reference.strip() or len(reference) > 160:
            raise HTTPException(400, 'payment_reference_required')
        result = await self.db.commercial_licenses.update_one({'_id': identity, 'business_id': business(),
            'expires_at': record['expires_at']}, {'$set': {'expires_at': expires}, '$push': {'renewals': {
                'expires_at': expires, 'payment_reference': reference.strip(), 'at': datetime.now(timezone.utc)}}})
        if not result.matched_count: raise HTTPException(409, 'license_changed_retry')
        return {'renewed': True, 'expires_at': expires}
