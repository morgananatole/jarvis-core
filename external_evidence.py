"""Bounded retrieval of public primary sources; never sends customer data out."""
import os
import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
import httpx

SOURCES = {
    'alcohol': ('OMS — Álcool', 'https://www.who.int/news-room/fact-sheets/detail/alcohol'),
    'treatment': ('NIDA — Treatment and Recovery', 'https://nida.nih.gov/publications/drugs-brains-behavior-science-addiction/treatment-recovery'),
}

class PageText(HTMLParser):
    def __init__(self):
        super().__init__(); self.skip = 0; self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style', 'nav', 'footer', 'header'}: self.skip += 1
    def handle_endtag(self, tag):
        if tag in {'script', 'style', 'nav', 'footer', 'header'}: self.skip = max(0, self.skip - 1)
    def handle_data(self, data):
        if not self.skip and data.strip(): self.parts.append(data.strip())

def source_key(text):
    lower = text.casefold()
    if re.search(r'\b(álcool|alcool|alcoolismo|bebida)\b', lower): return 'alcohol'
    if re.search(r'\b(tratamento|dependência|dependencia|recuperação|recuperacao)\b', lower): return 'treatment'
    return None

async def context(db, text):
    if os.getenv('EXTERNAL_EVIDENCE_ENABLED', 'false') != 'true': return []
    key = source_key(text)
    if not key: return []
    now = datetime.now(timezone.utc)
    try:
        cached = await db.external_sources.find_one({'_id': key})
        if cached:
            at = cached['retrieved_at']
            if at.tzinfo is None: at = at.replace(tzinfo=timezone.utc)
            if now - at < timedelta(hours=24): return [cached]
        title, url = SOURCES[key]
        # No arbitrary URL, redirect, cookies, query or customer identifiers.
        async with httpx.AsyncClient(timeout=5, follow_redirects=False) as client:
            async with client.stream('GET', url, headers={'Accept': 'text/html'}) as response:
                if response.status_code != 200 or 'text/html' not in response.headers.get('content-type', ''): return []
                raw = bytearray()
                async for chunk in response.aiter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 1024 * 1024: return []
        parser = PageText(); parser.feed(raw.decode('utf-8', errors='replace'))
        content = ' '.join(parser.parts)
        # Keep the section most relevant to the selected source, not navigation.
        anchor = 'Key facts' if key == 'alcohol' else 'Can addiction be treated'
        pos = content.casefold().find(anchor.casefold())
        if pos < 0: return []
        doc = {'_id': key, 'title': title, 'url': url, 'retrieved_at': now,
               'text': content[pos:pos + 6500], 'origin': 'public_primary_source'}
        await db.external_sources.update_one({'_id': key}, {'$set': doc}, upsert=True)
        return [doc]
    except Exception:
        # Optional evidence must never stop the existing conversation.
        return []
