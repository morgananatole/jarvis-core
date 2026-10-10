import os
import unittest
from unittest.mock import patch
import httpx
from fastapi import HTTPException
from whatsapp_connection import diagnostic

class Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        p=patch.dict(os.environ,{'WHATSAPP_ACCESS_TOKEN':'private-test-token','WHATSAPP_PHONE_NUMBER_ID':'123','META_GRAPH_VERSION':'v23.0'});p.start();self.addCleanup(p.stop)
    async def probe(self,handler):
        original=httpx.AsyncClient
        with patch('whatsapp_connection.httpx.AsyncClient',side_effect=lambda **kw:original(transport=httpx.MockTransport(handler),**kw)):
            return await diagnostic()
    async def test_extended_probe_is_read_only_and_masks_number(self):
        requests=[]
        def response(request):
            requests.append(request)
            return httpx.Response(200,json={'display_phone_number':'+55 81 99999-1234','is_on_biz_app':True,'platform_type':'CLOUD_API'})
        result=await self.probe(response)
        self.assertEqual(result['phone_ending'],'1234');self.assertTrue(result['business_app_connected'])
        self.assertFalse(result['registration_changed']);self.assertEqual(requests[0].method,'GET')
        self.assertNotIn('private-test-token',str(result))
    async def test_unsupported_fields_fall_back_without_claiming_coexistence(self):
        requests=[]
        def response(request):
            requests.append(request)
            return httpx.Response(400,json={}) if len(requests)==1 else httpx.Response(200,json={'display_phone_number':'1234'})
        result=await self.probe(response)
        self.assertEqual(result['coexistence_status'],'not_confirmed')
        self.assertEqual(len(requests),2);self.assertTrue(all(r.method=='GET' for r in requests))
    async def test_meta_read_rejection_does_not_change_registration(self):
        with self.assertRaises(HTTPException):await self.probe(lambda request:httpx.Response(401,json={}))
