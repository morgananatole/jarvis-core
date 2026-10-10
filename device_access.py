"""One-use enrollment and revocable, request-signed device access."""
import base64
import hashlib
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def public_key(jwk):
    if not isinstance(jwk, dict) or jwk.get('kty') != 'EC' or jwk.get('crv') != 'P-256' or 'd' in jwk:
        raise ValueError('invalid_public_key')
    def number(s):
        if not isinstance(s, str) or len(s) != 43: raise ValueError('invalid_public_key')
        return int.from_bytes(base64.urlsafe_b64decode(s + '='), 'big')
    return ec.EllipticCurvePublicNumbers(number(jwk['x']), number(jwk['y']), ec.SECP256R1()).public_key()

class DeviceAccess:
    def __init__(self, db): self.db = db

    async def initialize(self):
        await self.db.device_codes.create_index('expires_at', expireAfterSeconds=0)
        await self.db.device_nonces.create_index('expires_at', expireAfterSeconds=0)

    async def issue(self, label, license_id=None):
        if not isinstance(label, str) or not label.strip() or len(label) > 80:
            raise HTTPException(400, 'invalid_device_name')
        if license_id is not None:
            from commercial_licenses import Licenses
            await Licenses(self.db).active(license_id)
        code = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        await self.db.device_codes.insert_one({'_id': digest(code), 'label': label.strip(),
            'created_at': now, 'expires_at': now + timedelta(minutes=10), 'used': False, 'license_id': license_id})
        return {'code': code, 'expires_in_seconds': 600}

    async def enroll(self, code, jwk, license_key=None):
        try: public_key(jwk)
        except (ValueError, KeyError, TypeError): raise HTTPException(400, 'invalid_public_key')
        if not isinstance(code, str) or not 40 <= len(code) <= 60:
            raise HTTPException(401, 'invalid_or_used_code')
        now = datetime.now(timezone.utc)
        record = await self.db.device_codes.find_one_and_update({'_id': digest(code),
            'used': False, 'expires_at': {'$gt': now}}, {'$set': {'used': True}}, return_document=True)
        if not record: raise HTTPException(401, 'invalid_or_used_code')
        identity = secrets.token_hex(16)
        license_id = record.get('license_id')
        if license_id:
            from commercial_licenses import Licenses
            await Licenses(self.db).reserve(license_id, license_key, identity)
        try:
            await self.db.authorized_devices.insert_one({'_id': identity, 'label': record['label'],
                'public_key': {k: jwk[k] for k in ('kty', 'crv', 'x', 'y')},
                'created_at': now, 'revoked': False, 'license_id': license_id})
        except Exception:
            if license_id: await Licenses(self.db).release(license_id, identity)
            raise
        return {'device_id': identity}

    async def verify(self, request, allow_expired=False):
        identity = request.headers.get('x-jarvis-device', '')
        stamp = request.headers.get('x-jarvis-time', '')
        nonce = request.headers.get('x-jarvis-nonce', '')
        sig = request.headers.get('x-jarvis-signature', '')
        try:
            if not re.fullmatch(r'[0-9a-f]{32}', identity) or not re.fullmatch(r'[0-9]{10}', stamp): raise ValueError()
            if abs(time.time() - int(stamp)) > 90 or not re.fullmatch(r'[A-Za-z0-9_-]{16,80}', nonce): raise ValueError()
            if len(sig) > 100: raise ValueError()
            device = await self.db.authorized_devices.find_one({'_id': identity, 'revoked': False})
            if not device: raise ValueError()
            body = await request.body()
            if len(body) > 8 * 1024 * 1024: raise HTTPException(413, 'Payload too large')
            target = request.url.path + ('?' + request.url.query if request.url.query else '')
            payload = '\n'.join([request.method, target, stamp, nonce, hashlib.sha256(body).hexdigest(), request.headers.get('idempotency-key', '')]).encode()
            raw = base64.urlsafe_b64decode(sig + '=' * (-len(sig) % 4))
            if len(raw) != 64: raise ValueError()
            signature = utils.encode_dss_signature(int.from_bytes(raw[:32], 'big'), int.from_bytes(raw[32:], 'big'))
            public_key(device['public_key']).verify(signature, payload, ec.ECDSA(hashes.SHA256()))
            await self.db.device_nonces.insert_one({'_id': identity + ':' + nonce,
                'expires_at': datetime.now(timezone.utc) + timedelta(minutes=5)})
        except (ValueError, TypeError, KeyError, InvalidSignature, DuplicateKeyError):
            raise HTTPException(401, 'device_authentication_failed') from None
        if device.get('license_id'):
            from commercial_licenses import Licenses
            license = await Licenses(self.db).active(device['license_id'], allow_expired=allow_expired)
            if identity not in license['devices']: raise HTTPException(403, 'license_device_not_authorized')
        return identity
