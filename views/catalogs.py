from datetime import date
import streamlit as st
from services.store import get,add,update
from services.files import upload,path_for
from components.ui import heading,table,pick,label,order_rows,info_grid

def clients_page(db):
    heading('Clientes','Relaciones, sedes y activos en un solo lugar.')
    table([{'ID':c['id'],'Razón social':c['name'],'Sector':c['sector'],'Contacto':c['contact'],'Ciudad':c['city'],'Equipos':sum(e['client_id']==c['id'] for e in db['equipment'])} for c in db['clients']])
    with st.expander('＋ Registrar cliente'):
        client_form(db,None)
    cid=pick(db,'clients','Ficha del cliente')
    if not cid: return
    c=get(db,'clients',cid)
    tabs=st.tabs(['Información','Sedes','Equipos','Solicitudes','Órdenes e historial','Documentos'])
    with tabs[0]: client_form(db,c)
    with tabs[1]:
        table([{'Sede':s['name'],'Dirección':s['address'],'Ciudad':s['city']} for s in db['sites'] if s['client_id']==cid])
        with st.form('site'):
            name=st.text_input('Nombre de sede');address=st.text_input('Dirección de sede');city=st.text_input('Ciudad de sede','Bogotá')
            if st.form_submit_button('Agregar sede'):
                if name.strip() and address.strip(): add('sites',dict(client_id=cid,name=name,address=address,city=city),'S');st.rerun()
                else: st.error('Completa nombre y dirección.')
    with tabs[2]: table([{'Código':e['code'],'Equipo':e['name'],'Estado':e['status']} for e in db['equipment'] if e['client_id']==cid])
    with tabs[3]: table([t for t in db['tickets'] if t['client_id']==cid])
    with tabs[4]: table(order_rows(db,[o for o in db['orders'] if o['client_id']==cid]))
    with tabs[5]:
        for e in db['equipment']:
            if e['client_id']==cid:
                st.markdown(f"**{e['name']} · {e['code']}**");documents(e,False)

def client_form(db,c):
    data=c or {}
    with st.form('client_'+data.get('id','new')):
        values={}
        for field,title in [('name','Razón social'),('nit','NIT'),('sector','Sector'),('contact','Contacto'),('phone','Teléfono'),('email','Correo'),('address','Dirección'),('city','Ciudad'),('notes','Observaciones')]:
            values[field]=st.text_input(title,data.get(field,''))
        if st.form_submit_button('Guardar cliente'):
            if not values['name'].strip() or not values['nit'].strip(): st.error('Razón social y NIT son obligatorios.');return
            if any(x['nit']==values['nit'] and x['id']!=data.get('id') for x in db['clients']): st.error('Ya existe un cliente con este NIT.');return
            if c: update('clients',c['id'],values)
            else:
                cid=add('clients',values,'C')
                add('sites',dict(client_id=cid,name='Sede principal',address=values['address'],city=values['city']),'S')
            st.rerun()

def documents(e,client):
    docs=[d for d in e['documents'] if not client or d.get('authorized')]
    if not docs: st.caption('Sin documentos autorizados.' if client else 'Puedes adjuntar manuales, certificados e informes PDF.')
    for d in docs:
        p=path_for(d)
        if p.exists(): st.download_button(f'{d["kind"]} · {d["name"]}',p.read_bytes(),file_name=d['name'],key=f'doc_{e["id"]}_{d["path"]}')

def equipment_form(db,e=None):
    if not db["clients"]:
        st.info("Primero registra un cliente.");return
    v=e or {}
    cid=st.selectbox('Cliente propietario',[x['id'] for x in db['clients']],index=[x['id'] for x in db['clients']].index(v['client_id']) if e else 0,format_func=lambda x:label(db,'clients',x),key='eq_client_'+v.get('id','new'),disabled=bool(e))
    sites=[s for s in db['sites'] if s['client_id']==cid]
    if not sites: st.info('Registra una sede para este cliente.');return
    with st.form('equipment_'+v.get('id','new')):
        values={'client_id':cid}
        ids=[s['id'] for s in sites]
        values['site_id']=st.selectbox('Sede',ids,index=ids.index(v['site_id']) if e and v['site_id'] in ids else 0,format_func=lambda x:label(db,'sites',x))
        for field,title in [('name','Nombre del equipo'),('code','Código interno'),('serial','Serial'),('brand','Marca'),('model','Modelo'),('category','Categoría'),('location','Ubicación'),('notes','Observaciones')]: values[field]=st.text_input(title,v.get(field,''))
        statuses=['Activo','Próximo a vencer','Vencido','Fuera de servicio']
        values['status']=st.selectbox('Estado del equipo',statuses,index=statuses.index(v.get('status','Activo')))
        a,b=st.columns(2)
        for i,(field,title) in enumerate([('last_calibration','Última calibración'),('last_maintenance','Último mantenimiento'),('next_calibration','Próxima calibración'),('next_review','Próxima revisión')]):
            values[field]=str((a if i%2==0 else b).date_input(title,date.fromisoformat(v[field]) if v.get(field) else date.today()))
        if st.form_submit_button('Guardar equipo'):
            if not all(values[k].strip() for k in ['name','code','serial']): st.error('Nombre, código y serial son obligatorios.');return
            if any(x['code']==values['code'] and x['id']!=v.get('id') for x in db['equipment']): st.error('El código ya está registrado.');return
            if e: update('equipment',e['id'],values)
            else: values.update(photos=[],documents=[]);add('equipment',values,'E')
            st.rerun()

def equipment_page(db,client=False):
    heading('Mis equipos' if client else 'Equipos','Trazabilidad técnica durante todo el ciclo de vida.')
    search=st.text_input('Buscar por nombre, código o serial')
    found=[e for e in db['equipment'] if search.lower() in f"{e['name']} {e['code']} {e['serial']}".lower()]
    table([{'Código':e['code'],'Equipo':e['name'],'Cliente':label(db,'clients',e['client_id']),'Estado':e['status'],'Próxima calibración':e['next_calibration']} for e in found])
    if not client:
        with st.expander('＋ Registrar equipo'): equipment_form(db)
    if not found: return
    eid=pick(db,'equipment','Ficha del equipo',items=found)
    e=get(db,'equipment',eid)
    tabs=st.tabs(['General','Historial','Servicios','Documentos','Fotografías'])
    with tabs[0]:
        st.subheader(f"{e['name']} · {e['code']}")
        info_grid([(title,label(db,'clients',e['client_id']) if field=='client_id' else label(db,'sites',e['site_id']) if field=='site_id' else e.get(field,'—')) for field,title in [('code','Código interno'),('serial','Número de serie'),('brand','Marca'),('model','Modelo'),('category','Categoría'),('location','Ubicación'),('client_id','Cliente'),('site_id','Sede'),('status','Estado'),('last_calibration','Última calibración'),('last_maintenance','Último mantenimiento'),('next_calibration','Próxima calibración'),('next_review','Próxima revisión'),('notes','Observaciones')]])
        st.button('QR del equipo · Próximamente',disabled=True)
        st.caption('Reserva para identificación del activo y acceso futuro a documentos autorizados.')
        if not client:
            with st.expander('Editar equipo'): equipment_form(db,e)
    with tabs[1]:
        history=[o for o in db['orders'] if o['equipment_id']==eid and o['status']=='Finalizada']
        table(order_rows(db,history))
    with tabs[2]: table(order_rows(db,[o for o in db['orders'] if o['equipment_id']==eid]))
    with tabs[3]:
        documents(e,client)
        if not client:
            files=st.file_uploader('Adjuntar documentos PDF',type=['pdf'],accept_multiple_files=True,key='equipment_docs')
            kind=st.selectbox('Tipo de documento',['Manual de mantenimiento','Certificado','Informe','Documento técnico'])
            authorized=st.checkbox('Autorizar descarga en portal cliente')
            if st.button('Guardar documentos del equipo',disabled=not files): upload(files,'equipment',eid,'documents',kind,authorized);st.rerun()
            for i,d in enumerate(e['documents']):
                if st.button(('Revocar acceso: ' if d['authorized'] else 'Autorizar acceso: ')+d['name'],key=f'auth_{i}'):
                    docs=e['documents'];docs[i]['authorized']=not d['authorized'];update('equipment',eid,{'documents':docs});st.rerun()
    with tabs[4]:
        for p in e['photos']:
            path=path_for(p)
            if path.exists(): st.image(str(path),caption=p['name'],width=300)
        if not e['photos']: st.caption('Sin fotografía del equipo; puedes adjuntar una imagen real para la prueba.')
        if not client:
            files=st.file_uploader('Fotografías del equipo',type=['png','jpg','jpeg'],accept_multiple_files=True)
            if st.button('Guardar fotografías del equipo',disabled=not files):
                try: upload(files,'equipment',eid);st.rerun()
                except (ValueError,OSError) as err: st.error(str(err))
