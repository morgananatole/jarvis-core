"""Import a Google Contacts CSV privately. Does not authorize or send outreach."""
import argparse
import asyncio
import csv
import os
import re
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient
from contact_memory import ContactMemory, canonical_phone


BRAZIL_DDDS = {11,12,13,14,15,16,17,18,19,21,22,24,27,28,31,32,33,34,35,37,38,41,42,43,44,45,46,47,48,49,51,53,54,55,61,62,63,64,65,66,67,68,69,71,73,74,75,77,79,81,82,83,84,85,86,87,88,89,91,92,93,94,95,96,97,98,99}
def import_phone(value, default_country=None):
    value=value.strip()
    if value.startswith('+'): return canonical_phone(value)
    if default_country != 'BR': raise ValueError('explicit_country_required')
    if re.search(r'[^0-9 ()\-.]',value): raise ValueError('invalid_phone')
    digits=re.sub(r'\D','',value)
    if digits.startswith('0055'): digits=digits[2:]
    if len(digits) in (12,13) and digits.startswith('55'): digits=digits[2:]
    elif len(digits) in (13,14) and digits.startswith('0'): digits=digits[3:]
    if len(digits) not in (10,11) or int(digits[:2]) not in BRAZIL_DDDS: raise ValueError('ambiguous_phone')
    if len(digits)==11 and digits[2]!='9': raise ValueError('invalid_mobile')
    if len(digits)==10 and digits[2] not in '23456789': raise ValueError('invalid_subscriber')
    return canonical_phone('+55'+digits)


def rows_to_contacts(rows, default_country=None):
    for row in rows:
        name = (row.get('Name') or ' '.join(filter(None, [row.get('First Name') or row.get('Given Name'),
                row.get('Last Name') or row.get('Family Name')]))).strip()
        for field, value in row.items():
            if field and field.startswith('Phone ') and field.endswith(' - Value') and value:
                for phone in value.split(':::'):
                    try:
                        yield import_phone(phone, default_country), name[:150]
                    except ValueError:
                        continue


async def run(path):
    if not os.getenv('MONGODB_URI'):
        raise SystemExit('MONGODB_URI must be configured privately')
    client = AsyncIOMotorClient(os.environ['MONGODB_URI'], serverSelectionTimeoutMS=5000)
    db = client[os.getenv('MONGODB_DATABASE', os.getenv('DB_NAME', 'jarvis'))]
    memory = ContactMemory(db)
    try:
        await memory.initialize()
        count = 0
        with open(path, newline='', encoding='utf-8-sig') as source:
            for phone, name in rows_to_contacts(csv.DictReader(source)):
                profile = await memory.ensure(phone)
                if name and not profile.get('facts', {}).get('contact_name'):
                    await db.contacts.update_one({'_id': profile['_id']}, {'$set': {
                        'facts.contact_name': {'value': name, 'status': 'address_book',
                            'source': 'google_contacts_csv', 'reported_at': datetime.now(timezone.utc)}}})
                await memory.plan(profile['_id'], 'google_contacts_import')
                count += 1
        print('Import complete; phone entries processed:', count, '; no messages sent')
    finally:
        client.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('csv_path')
    args = parser.parse_args()
    asyncio.run(run(args.csv_path))
