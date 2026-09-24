from datetime import datetime
import streamlit as st
from services.store import add,get,update,now
from services.seed import TYPES
from services.files import upload,path_for
from components.ui import heading,pick,label,table
from views.orders import new_order

def new_ticket(db,cid):
    heading('Nueva solicitud','Cuéntanos qué necesita tu equipo. Marcela recibirá el requerimiento.')
    equipment=[e for e in db['equipment'] if e['client_id']==cid]
    if not equipment: st.info('No hay equipos registrados para esta empresa.');return
    with st.form('ticket_form',clear_on_submit=True):
        eid=pick(db,'equipment','Equipo',items=equipment)
        kind=st.selectbox('Tipo de necesidad',TYPES)
        priority=st.selectbox('Prioridad',['Baja','Media','Alta','Urgente'],index=1)
        desc=st.text_area('Descripción');contact=st.text_input('Persona de contacto',get(db,'clients',cid)['contact'])
        photo=st.file_uploader('Fotografía opcional',type=['png','jpg','jpeg'])
        if st.form_submit_button('Enviar solicitud',type='primary'):
            if not desc.strip() or not contact.strip(): st.error('Completa descripción y contacto.');return
            tid=add('tickets',dict(client_id=cid,equipment_id=eid,created=now(),type=kind,priority=priority,description=desc,contact=contact,status='Recibido',responsible='Marcela',photos=[],order_id=None,first_response=None,closed_at=None),'TK-')
            if photo:
                try: upload([photo],'tickets',tid)
                except (ValueError,OSError): st.warning('La solicitud se guardó, pero la fotografía no pudo adjuntarse.')
            st.success(f'{tid} recibida. Consulta su avance en Mis solicitudes.')

def tickets_page(db,client=False):
    heading('Mis solicitudes' if client else 'Solicitudes / Tickets','Desde el requerimiento hasta una solución trazable.')
    status=st.selectbox('Estado de solicitud',['Todos','Recibido','En revisión','Programado','En ejecución','Finalizado'])
    found=[t for t in db['tickets'] if status=='Todos' or t['status']==status]
    table([{'Número':t['id'],'Cliente':label(db,'clients',t['client_id']),'Equipo':label(db,'equipment',t['equipment_id']),'Fecha':t['created'],'Necesidad':t['type'],'Prioridad':t['priority'],'Estado':t['status'],'Responsable':t['responsible'],'Transcurrido (h)':round((datetime.fromisoformat(now())-datetime.fromisoformat(t['created'])).total_seconds()/3600,1)} for t in found])
    if not found: return
    tid=st.selectbox('Consultar solicitud',[t['id'] for t in found]); t=get(db,'tickets',tid)
    st.write(t['description']);st.caption(f"Contacto: {t['contact']} · Orden: {t.get('order_id') or 'Pendiente de programación'}")
    for p in t['photos']:
        path=path_for(p)
        if path.exists(): st.image(str(path),width=280)
    if not client and not t['order_id']:
        if t['status']=='Recibido' and st.button('Marcar en revisión'): update('tickets',tid,{'status':'En revisión','first_response':now()});st.rerun()
        with st.expander('Crear orden de servicio',expanded=True): new_order(db,t)
