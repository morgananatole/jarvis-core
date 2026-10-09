"""Import a Google Contacts CSV privately. Does not authorize or send outreach."""
import argparse
import asyncio
import csv
import os
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient
from contact_memory import ContactMemory, canonical_phone


def rows_to_contacts(rows):
    for row in rows:
        name = (row.get('Name') or ' '.join(filter(None, [row.get('First Name') or row.get('Given Name'),
                row.get('Last Name') or row.get('Family Name')]))).strip()
        for field, value in row.items():
            if field and field.startswith('Phone ') and field.endswith(' - Value') and value:
                for phone in value.split(':::'):
                    try:
                        # Require explicit country code; avoid assigning the wrong country.
                        if not phone.strip().startswith('+'):
                            continue
                        yield canonical_phone(phone), name[:150]
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
