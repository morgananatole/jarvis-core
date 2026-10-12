"""Tests for bounded, opt-in WhatsApp typing activity."""
import asyncio
import os
import unittest
from unittest.mock import patch
from whatsapp_typing import send_typing_indicator

class TypingTests(unittest.IsolatedAsyncioTestCase):
    async def test_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(await send_typing_indicator("wamid.valid"))
    async def test_rejects_invalid_id(self):
        with patch.dict(os.environ, {"WHATSAPP_TYPING_INDICATOR_ENABLED":"true"}):
            self.assertFalse(await send_typing_indicator("bad-id"))
    async def test_requires_credentials(self):
        with patch.dict(os.environ, {"WHATSAPP_TYPING_INDICATOR_ENABLED":"true"}, clear=True):
            self.assertFalse(await send_typing_indicator("wamid.valid"))
