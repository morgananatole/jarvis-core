"""Real Mongo concurrency test; CI supplies isolated localhost Mongo."""
import asyncio
import os
import secrets
import unittest
from motor.motor_asyncio import AsyncIOMotorClient
from execution_hub import ExecutionHub

@unittest.skipUnless(os.getenv('PULSE_TEST_MONGO_URI'), 'integration Mongo not configured')
class MongoExecutionTests(unittest.IsolatedAsyncioTestCase):
    async def test_durable_atomic_claim_and_result(self):
        client=AsyncIOMotorClient(os.environ['PULSE_TEST_MONGO_URI'])
        name='test_execution_'+secrets.token_hex(8);db=client[name]
        try:
            identity=secrets.token_hex(16)
            await db.authorized_devices.insert_one({'_id':identity,'revoked':False,'license_id':None})
            hub=ExecutionHub(db)
            await hub.register(identity,{'platform':'Linux','capabilities':['system.info']})
            task=await hub.submit({'device_id':identity,'capability':'system.info','args':{}},secrets.token_urlsafe(24))
            claims=await asyncio.gather(*(hub.claim(identity) for _ in range(8)))
            selected=[x for x in claims if x];self.assertEqual(len(selected),1)
            # New service instance cannot redispatch the claimed task.
            restored=ExecutionHub(db);self.assertIsNone(await restored.claim(identity))
            result={'claim_token':selected[0]['claim_token'],'state':'succeeded','output':{'probe':True}}
            await restored.result(identity,task['_id'],result)
            doc=await db.execution_tasks.find_one({'_id':task['_id']});self.assertEqual(doc['state'],'succeeded')
            self.assertTrue((await restored.result(identity,task['_id'],result))['duplicate'])
        finally:
            await client.drop_database(name);client.close()
