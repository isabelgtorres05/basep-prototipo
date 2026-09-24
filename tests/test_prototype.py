import os
import tempfile
from pathlib import Path
TEST_ROOT=Path(os.environ.get('BASEP_TEST_ROOT',str(Path(__file__).resolve().parents[1]/'work')))
TEST_ROOT.mkdir(exist_ok=True)
tempfile.tempdir=str(TEST_ROOT)
import unittest
from datetime import date
import uuid
test_data=TEST_ROOT/('basep_test_'+uuid.uuid4().hex)
test_data.mkdir(parents=True)
os.environ['BASEP_DATA_DIR']=str(test_data)
from services.store import load,scoped,get,update
from services.workflow import create_order,transition,stock_move
from services.reports import report_html
from streamlit.testing.v1 import AppTest

class WorkflowTest(unittest.TestCase):
    def test_end_to_end(self):
        db=load();ticket=db['tickets'][0];e=get(db,'equipment',ticket['equipment_id'])
        oid=create_order(dict(client_id=e['client_id'],equipment_id=e['id'],tech_id='T001',type='Calibración',date=str(date.today()),time='09:00',duration=120,priority='Alta',address='Dirección de prueba',description='Calibración de prueba'),ticket['id'])
        with self.assertRaises(ValueError): create_order(dict(),ticket['id'])
        for state in ['Enviada','Recibida','Vista','Aceptada','En desplazamiento','Check-in','En ejecución']:
            transition(oid,state,'Prueba')
        with self.assertRaises(ValueError): transition(oid,'Check-out','Prueba')
        update('orders',oid,{'form':{'condition':'Operativo','work':'Calibración','result':'Dentro de tolerancia'},'closure':{'receiver':'Prueba','signature':'Prueba','quality':5,'punctuality':4,'attention':5}})
        transition(oid,'Check-out','Prueba');transition(oid,'Finalizada','Prueba')
        db=load();o=get(db,'orders',oid)
        self.assertEqual(get(db,'tickets',ticket['id'])['status'],'Finalizado')
        self.assertEqual(o['status'],'Finalizada');self.assertFalse(o['published'])
        self.assertIn(oid,report_html(db,o));self.assertEqual(get(db,'equipment',e['id'])['last_calibration'],str(date.today()))
        for c in db['clients']:
            view=scoped(db,c['id'])
            self.assertTrue(all(x['client_id']==c['id'] for key in ['equipment','orders','tickets','sites'] for x in view[key]))
        stock=get(db,'inventory','R001')['stock']
        with self.assertRaises(ValueError): stock_move('R001','Salida',stock+1)
        stock_move('R001','Consumo en servicio',1,oid)
        self.assertEqual(get(load(),'inventory','R001')['stock'],stock-1)

class PagesTest(unittest.TestCase):
    def test_pages(self):
        at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
        self.assertFalse(at.exception, str(at.exception))
        menu=['Programación','Órdenes de servicio','Solicitudes / Tickets','Clientes','Equipos','Técnicos','Ubicación / Mapa','Inventario','Informes','Indicadores','Portal Cliente','Configuración']
        for page in menu:
            at.sidebar.radio[0].set_value(page).run()
            self.assertFalse(at.exception, f'{page}: {at.exception}')
        at.sidebar.selectbox[0].set_value('Cliente').run()
        for page in ['Inicio','Mis equipos','Mis solicitudes','Servicios programados','Historial','Informes','Documentos','Solicitar servicio']:
            at.sidebar.radio[0].set_value(page).run()
            self.assertFalse(at.exception, f'Cliente {page}: {at.exception}')
        at.sidebar.selectbox[0].set_value('Técnico').run()
        self.assertFalse(at.exception,str(at.exception))
        at.sidebar.radio[0].set_value('Mi agenda').run()
        self.assertFalse(at.exception,str(at.exception))

class InterfaceFlowTest(unittest.TestCase):
    def test_customer_to_report(self):
        at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
        def widget(kind,label): return next(w for w in getattr(at,kind) if w.label==label)
        def click(label):
            widget('button',label).click().run()
            self.assertFalse(at.exception,str(at.exception))
        at.sidebar.selectbox[0].set_value('Cliente').run()
        at.sidebar.radio[0].set_value('Solicitar servicio').run()
        widget('text_area','Descripción').input('Prueba integral de interfaz').run()
        click('Enviar solicitud')
        ticket=next(t for t in load()['tickets'] if t['description']=='Prueba integral de interfaz')
        at.sidebar.selectbox[0].set_value('Marcela / Administradora').run()
        at.sidebar.radio[0].set_value('Solicitudes / Tickets').run()
        widget('selectbox','Consultar solicitud').set_value(ticket['id']).run()
        click('Crear orden de servicio')
        oid=get(load(),'tickets',ticket['id'])['order_id']
        self.assertEqual(widget('selectbox','Detalle de la orden').value,oid)
        click('Enviar tarea')
        at.sidebar.selectbox[0].set_value('Técnico').run()
        widget('selectbox','Detalle de la orden').set_value(oid).run()
        for button in ['Recibir tarea','Registrar visualización','Aceptar tarea','Iniciar desplazamiento','Check-in','Iniciar servicio']:
            click(button)
        widget('text_input','Condición inicial').input('Operativo')
        widget('text_area','Trabajos realizados').input('Verificación de balanza con patrón de prueba')
        widget('text_input','Condición final').input('Operativo')
        widget('number_input','Valor medido').set_value(100.5)
        click('Guardar formulario')
        self.assertEqual(get(load(),'orders',oid)['form']['result'],'Fuera de tolerancia')
        widget('text_input','Persona que recibe').input('Cliente de prueba')
        widget('text_input','Cargo').input('Coordinador')
        widget('text_input','Nombre escrito como firma simulada').input('Cliente de prueba')
        widget('checkbox','Confirmo la recepción del servicio (simulación)').check()
        click('Guardar recepción y firma');click('Check-out');click('Finalizar servicio')
        self.assertEqual(get(load(),'orders',oid)['status'],'Finalizada')
        at.sidebar.selectbox[0].set_value('Marcela / Administradora').run()
        at.sidebar.radio[0].set_value('Informes').run()
        widget('selectbox','Abrir informe').set_value(oid).run()
        click('Autorizar informe en portal cliente')
        at.sidebar.selectbox[0].set_value('Cliente').run()
        at.sidebar.radio[0].set_value('Informes').run()
        self.assertIn(oid,widget('selectbox','Abrir informe').options)
        widget('selectbox','Empresa de demostración').set_value('C002').run()
        self.assertNotIn(oid,widget('selectbox','Abrir informe').options)

if __name__=='__main__': unittest.main(verbosity=2)

