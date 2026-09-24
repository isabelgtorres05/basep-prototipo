import os
os.environ['SUPABASE_URL']=''
os.environ['SUPABASE_KEY']=''
import unittest
from unittest.mock import patch,MagicMock
from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from services.supabase_store import MAP,changes,decode,ConflictError,commit
from services.seed import seed

def snapshot():
    names=[n for n,_ in MAP.values()]+['eventos_orden','evidencias','satisfaccion_cliente']
    return dict(revision=0,tables={name:[] for name in names})

class AdapterTests(unittest.TestCase):
    def test_roundtrip_and_atomic_payload(self):
        snap=snapshot();empty=decode(snap);demo=seed()
        patchset=changes(empty,demo)
        for entry in patchset:
            snap['tables'][entry['table']].append(dict(entry['row'],created_at='2026-09-24T12:00:00+00:00'))
        reloaded=decode(snap)
        self.assertEqual(len(reloaded['clients']),5)
        self.assertEqual(reloaded['orders'][0]['tech_id'],demo['orders'][0]['tech_id'])
        self.assertEqual(reloaded['orders'][0]['time'],'09:00')
        for a,b in zip(demo['orders'],reloaded['orders']):
            self.assertEqual([e['state'] for e in a['timeline']],[e['state'] for e in b['timeline']])
            self.assertEqual(a['closure'],b['closure'])
        self.assertEqual(changes(reloaded,deepcopy(reloaded)),[])
        modified=deepcopy(reloaded);modified['orders'][0]['published']=True
        p=changes(reloaded,modified)
        self.assertTrue(any(x['table']=='ordenes_servicio' for x in p))
        self.assertFalse(any(x['table']=='clientes' for x in p))

    def test_conflict_does_not_write_json(self):
        before=decode(snapshot());after=deepcopy(before)
        after['clients'].append(dict(id='C-TEST',name='Test',nit='X'))
        fake=MagicMock();fake.rpc.return_value.execute.side_effect=Exception('BASEP_CONFLICT')
        with patch('services.supabase_store.client',return_value=fake):
            with self.assertRaises(ConflictError):commit(before,after)
        self.assertEqual(before['clients'],[])

    def test_private_file_metadata(self):
        empty=decode(snapshot());demo=seed()
        demo['orders'][0]['photos']=[dict(name='test.png',path='orders/test/photo.png',bucket='basep-evidencias',kind='Fotografía',at='2026-09-24T10:00:00',authorized=False)]
        entries=changes(empty,demo)
        evidence=next(x['row'] for x in entries if x['table']=='evidencias')
        self.assertEqual(evidence['bucket'],'basep-evidencias')
        self.assertIn('orden_id',evidence)
        self.assertNotIn('https://',evidence['ruta_storage'])

    def test_empty_database_navigation(self):
        from streamlit.testing.v1 import AppTest
        empty=decode(snapshot())
        with patch('services.store.load',return_value=empty):
            at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20).run()
            self.assertFalse(at.exception)
            for name in ['Clientes','Equipos','Técnicos','Órdenes de servicio','Solicitudes / Tickets','Inventario','Indicadores','Portal Cliente']:
                at.radio(key='nav').set_value(name).run()
                self.assertFalse(at.exception,name+': '+str(at.exception))

    def test_login_stops_before_loading_private_data(self):
        from streamlit.testing.v1 import AppTest
        config={'SUPABASE_URL':'https://test.supabase.co','SUPABASE_KEY':'sb_secret_test_only','BASEP_ACCESS_PASSWORD':'test-password-not-a-real-secret'}
        with patch('services.supabase_client.setting',side_effect=lambda k:config.get(k,'')), patch('services.store.load') as read:
            at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20).run()
            self.assertFalse(at.exception)
            read.assert_not_called()
            self.assertTrue(any(x.label=='Contraseña del piloto' for x in at.text_input))

    def test_remote_failure_never_falls_back_to_demo(self):
        from services.store import load
        with patch('services.store.configured',return_value=True), patch('services.supabase_store.load',side_effect=ValueError('unavailable')), patch('services.store.seed') as demo:
            with self.assertRaises(ValueError):load()
            demo.assert_not_called()

if __name__=='__main__':unittest.main()

