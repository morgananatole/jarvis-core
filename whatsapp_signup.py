"""Opt-in Meta v4 preview, independent of CRM credentials and registration APIs."""
import os
import re
import secrets
from pathlib import Path
from fastapi.responses import HTMLResponse


def preview():
    app_id = os.getenv('WHATSAPP_SIGNUP_APP_ID', '')
    config_id = os.getenv('WHATSAPP_SIGNUP_CONFIG_ID', '')
    valid = bool(re.fullmatch(r'[0-9]{5,30}', app_id)
                 and re.fullmatch(r'[0-9]{5,30}', config_id))
    enabled = os.getenv('WHATSAPP_SIGNUP_PREVIEW_ENABLED', 'false') == 'true' and valid
    nonce = secrets.token_urlsafe(24)
    html = Path(__file__).with_name('whatsapp_signup.html').read_text(encoding='utf-8')
    html = html.replace('__NONCE__', nonce).replace('__ENABLED__', 'true' if enabled else 'false')
    html = html.replace('__APP_ID__', app_id if valid else '').replace('__CONFIG_ID__', config_id if valid else '')
    # The CRM panel retains its original CSP. This page accepts no CRM credential,
    # sends no API requests to our backend, and never persists OAuth codes/tokens.
    sdk = ' https://connect.facebook.net' if enabled else ''
    frames = 'https://www.facebook.com https://web.facebook.com https://business.facebook.com' if enabled else "'none'"
    return HTMLResponse(html, headers={
        'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
        'Referrer-Policy': 'no-referrer', 'Cross-Origin-Opener-Policy': 'same-origin-allow-popups',
        'Content-Security-Policy': (
            "default-src 'none'; script-src 'nonce-" + nonce + "'" + sdk + "; "
            "style-src 'nonce-" + nonce + "'; connect-src " + frames + "; "
            "frame-src " + frames + "; img-src data:; frame-ancestors 'none'; "
            "base-uri 'none'; form-action 'none'; object-src 'none'"),
        'Permissions-Policy': 'camera=(), microphone=(), geolocation=()'})
