from datetime import date,datetime,timedelta
from html import escape
import streamlit as st
from services.store import get,update,add,now,mutate
from services.seed import TYPES
from services.workflow import create_order,transition,NEXT
from services.files import upload,path_for
from services.reports import report_html
from components.ui import heading,label,pick,table,order_rows,badge,go,badge_html,info_grid

def new_order(db,ticket=None):
    st.subheader('Crear orden de servicio')
    cid=ticket['client_id'] if ticket else pick(db,'clients','Cliente',key='new_order_client')
    if not cid: st.info('Primero registra un cliente.');return
    equipment=[e for e in db['equipment'] if e['client_id']==cid]
    eid=ticket['equipment_id'] if ticket else pick(db,'equipment','Equipo',key='new_order_equipment',items=equipment)
    if ticket: st.caption(f"{label(db,'clients',cid)} · {label(db,'equipment',eid)} · {ticket['id']}")
    if not eid: st.info('Registra un equipo para este cliente.');return
    with st.form('new_order_form'):
        tech=pick(db,'techs','Técnico')
        kind=st.selectbox('Tipo de servicio',TYPES,index=TYPES.index(ticket['type']) if ticket and ticket['type'] in TYPES else 0)
        c1,c2,c3=st.columns(3)
        day=c1.date_input('Fecha',date.today()); hour=c2.time_input('Hora',datetime.strptime('09:00','%H:%M').time()); duration=c3.number_input('Duración estimada (min)',15,1440,120,15)
        priority=st.selectbox('Prioridad',['Baja','Media','Alta','Urgente'],index=2 if ticket and ticket['priority']=='Alta' else 1)
        address=st.text_input('Dirección',get(db,'sites',get(db,'equipment',eid)['site_id']).get('address',''))
        description=st.text_area('Trabajo requerido',ticket['description'] if ticket else '')
        if st.form_submit_button('Crear orden de servicio',type='primary'):
            if not description.strip() or not address.strip(): st.error('Completa la dirección y el trabajo requerido.');return
            try:
                oid=create_order(dict(client_id=cid,equipment_id=eid,tech_id=tech,type=kind,date=str(day),time=hour.strftime('%H:%M'),duration=duration,priority=priority,address=address,description=description),ticket['id'] if ticket else None)
                go('Órdenes de servicio',oid)
            except ValueError as e: st.error(str(e))

def photos(db,o,editable):
    for i,p in enumerate(o['photos']):
        path=path_for(p)
        if path.exists(): st.image(str(path),caption=p['name'],width=280)
    if editable:
        files=st.file_uploader('Fotografías / evidencias (máximo 10 MB cada una)',type=['jpg','jpeg','png'],accept_multiple_files=True,key=f'photo_{o["id"]}')
        if st.button('Guardar fotografías',disabled=not files):
            try: upload(files,'orders',o['id']);st.rerun()
            except (ValueError,OSError) as e: st.error(str(e))

def technical_form(db,o):
    f=o['form']; editable=o['status'] in ['Check-in','En ejecución','Pausada']
    if not editable:
        if f: table([f])
        else: st.info('El formulario estará disponible después del check-in.')
        return
    with st.form(f'technical_{o["id"]}'):
        condition=st.text_input('Condición inicial',f.get('condition',''))
        values={'condition':condition}
        if o['type'] in ['Calibración','Verificación']:
            a,b,c=st.columns(3)
            ref=a.number_input('Valor de referencia',value=float(f.get('reference',100)),format='%.4f')
            measured=b.number_input('Valor medido',value=float(f.get('measured',100)),format='%.4f')
            tolerance=c.number_input('Tolerancia (±)',min_value=0.,value=float(f.get('tolerance',.1)),format='%.4f')
            error=round(measured-ref,8)
            values.update(reference=ref,measured=measured,error=error,tolerance=tolerance,result='Dentro de tolerancia' if abs(error)<=tolerance+1e-9 else 'Fuera de tolerancia')
            st.caption('Al guardar se calcula: error = valor medido − referencia; se compara su valor absoluto con la tolerancia.')
        values['work']=st.text_area('Trabajos realizados',f.get('work',''))
        values['components']=st.text_input('Componentes revisados',f.get('components',''))
        values['final_condition']=st.text_input('Condición final',f.get('final_condition',''))
        values['observations']=st.text_area('Observaciones',f.get('observations',''))
        if st.form_submit_button('Guardar formulario',type='primary'):
            if not condition.strip() or not values['work'].strip() or not values['final_condition'].strip(): st.error('Completa condición inicial, trabajos realizados y condición final.')
            else: update('orders',o['id'],{'form':values});st.rerun()
    if f.get('result'):
        (st.success if f['result']=='Dentro de tolerancia' else st.warning)(f"{f['result']} · Error: {f['error']}")

def closure_form(o):
    st.subheader('Finalizar servicio')
    st.caption('1. Guarda la recepción y firma. 2. Registra el check-out. 3. Finaliza desde el control de estado superior.')
    if o['form']: table([o['form']])
    else: st.warning('Aún no se ha guardado el formulario técnico.')
    if o['status'] in ['Finalizada','Cancelada','Check-out']:
        table([o['closure']] if o['closure'] else []);return
    if o['status'] not in ['En ejecución','Pausada','Check-in']: st.info('La recepción se habilita durante el servicio.');return
    c=o['closure']
    with st.form('closure'):
        receiver=st.text_input('Persona que recibe',c.get('receiver',''));position=st.text_input('Cargo',c.get('position',''))
        a,b,d=st.columns(3)
        quality=a.slider('Calidad del servicio ★',1,5,c.get('quality',5)); punctuality=b.slider('Puntualidad ★',1,5,c.get('punctuality',5)); attention=d.slider('Atención del técnico ★',1,5,c.get('attention',5))
        comments=st.text_area('Comentarios del cliente',c.get('comments',''))
        st.markdown('#### Firma del cliente')
        signature=st.text_input('Nombre escrito como firma simulada',c.get('signature',''))
        accepted=st.checkbox('Confirmo la recepción del servicio (simulación)',value=bool(c.get('signature')))
        if st.form_submit_button('Guardar recepción y firma'):
            if not receiver.strip() or not position.strip() or not signature.strip() or not accepted: st.error('Completa los datos de recepción y la confirmación.')
            else: update('orders',o['id'],{'closure':dict(receiver=receiver,position=position,quality=quality,punctuality=punctuality,attention=attention,comments=comments,signature=signature)});st.rerun()

def report_view(db,o,admin=False):
    if o['status']!='Finalizada': st.info('El informe definitivo del prototipo se genera al finalizar la orden.');return
    content=report_html(db,o)
    st.download_button('Descargar informe',content,file_name=f'BASEP_{o["id"]}.html',mime='text/html',key=f'dl_{o["id"]}')
    st.caption('Documento HTML autónomo con logo y evidencias. Ábrelo en el navegador para imprimir o guardar como PDF.')
    if admin:
        if st.button('Retirar del portal cliente' if o['published'] else 'Autorizar informe en portal cliente',key=f'publish_{o["id"]}'):
            update('orders',o['id'],{'published':not o['published']});st.rerun()
    st.iframe(content,height=720)

def detail(db,o,technician=False):
    client=get(db,'clients',o['client_id']); equipment=get(db,'equipment',o['equipment_id']); tech=get(db,'techs',o['tech_id'])
    st.markdown(f'<div class="order-head"><div class="order-kicker">{escape(o["id"])} {badge_html(o["status"])}</div><h2>{escape(o["type"])} · {escape(equipment["name"])}</h2><div class="order-meta"><div><small>Cliente</small><b>{escape(client["name"])}</b></div><div><small>Equipo / Serial</small><b>{escape(equipment["code"])} · {escape(equipment["serial"])}</b></div><div><small>Técnico asignado</small><b>{escape(tech["name"])}</b></div><div><small>Fecha programada</small><b>{o["date"]} · {o["time"]}</b></div></div></div>',unsafe_allow_html=True)
    states=NEXT[o['status']]
    if technician: states=[s for s in states if s!='Cancelada' and not (o['status']=='Creada')]
    labels={'Enviada':'Enviar tarea','Recibida':'Recibir tarea','Vista':'Registrar visualización','Aceptada':'Aceptar tarea','En desplazamiento':'Iniciar desplazamiento','Check-in':'Check-in','En ejecución':'Reanudar servicio' if o['status']=='Pausada' else 'Iniciar servicio','Pausada':'Pausar servicio','Check-out':'Check-out','Finalizada':'Finalizar servicio','Cancelada':'Cancelar orden'}
    if states:
        cols=st.columns(len(states))
        for col,state in zip(cols,states):
            if col.button(labels[state],key=f'state_{state}',type='primary' if state!='Cancelada' else 'secondary',width='stretch'):
                try: transition(o['id'],state,tech['name'] if technician else 'Marcela');st.rerun()
                except ValueError as e: st.error(str(e))
    tabs=st.tabs(['Resumen','Tareas','Equipos','Formularios','Archivos','Historial','Monitoreo'])
    with tabs[5]:
        steps=['Creada','Enviada','Recibida','Vista','Aceptada','En desplazamiento','Check-in','En ejecución','Check-out','Finalizada']
        for state in steps:
            event=next((t for t in reversed(o['timeline']) if t['state']==state),None)
            cls=('current' if o['status']==state else 'done' if event else '')+(' last' if state==steps[-1] else '')
            stamp=event['at'].replace('T',' · ')+' — '+event['actor'] if event else 'Pendiente'
            st.markdown(f'<div class="timeline {cls}"><span class="step-dot">{"✓" if event else "○"}</span><div><b>{escape(state)}</b><small>{escape(stamp)}</small></div></div>',unsafe_allow_html=True)
        with st.expander('Registro completo de eventos'):
            table([{'Evento':t['state'],'Fecha y hora':t['at'],'Responsable':t['actor']} for t in o['timeline']])
    with tabs[6]:
        st.subheader('Información del dispositivo')
        st.caption('SIMULACIÓN · Sin GPS ni sincronización real')
        a,b,c=st.columns(3);a.metric('Batería',f"{tech['battery']} %");b.metric('Dispositivo',tech['device']);c.metric('Conexión','Datos móviles')
        st.caption(f"Ubicación aproximada: {tech['lat']}, {tech['lon']} · Última sincronización simulada: {o['timeline'][-1]['at']}")
        table([{'Evento':t['state'],'Fecha y hora':t['at']} for t in o['timeline'] if t['state'] in ['Enviada','Recibida','Vista','Aceptada']])
        st.radio('Simular conectividad',['Datos móviles','WiFi','Sin conexión'],horizontal=True,key=f'connect_{o["id"]}')
        st.caption('El selector es ilustrativo. No existe sincronización ni funcionamiento offline real.')
    with tabs[0]:
        st.subheader('Información del servicio')
        st.write(o['description'])
        a,b=st.columns(2)
        a.markdown(f"**Cliente y contacto**\n\n{client['name']}\n\n{client['contact']} · {client['phone']}")
        b.markdown(f"**Ubicación**\n\n{o['address']}\n\n{label(db,'sites',o['site_id'])}")
        st.caption(f"Prioridad: {o['priority']} · Duración estimada: {o['duration']} min")
        with st.expander('Informe de servicio',expanded=o['status']=='Finalizada'): report_view(db,o,admin=not technician)
        if not technician and o['status'] not in ['Finalizada','Cancelada','Check-out']:
            with st.expander('Reprogramar / reasignar'):
                with st.form('reschedule'):
                    tid=st.selectbox('Técnico asignado',[x['id'] for x in db['techs']],index=[x['id'] for x in db['techs']].index(o['tech_id']),format_func=lambda x:label(db,'techs',x))
                    day=st.date_input('Nueva fecha',date.fromisoformat(o['date'])); hour=st.time_input('Nueva hora',datetime.strptime(o['time'],'%H:%M').time())
                    if st.form_submit_button('Guardar programación'):
                        def reschedule(data):
                            item=get(data,'orders',o['id']);item.update(tech_id=tid,date=str(day),time=hour.strftime('%H:%M'))
                            item['timeline'].append(dict(state='Programación actualizada',at=now(),actor='Marcela'))
                        mutate(reschedule);st.rerun()
    with tabs[3]: technical_form(db,o)
    with tabs[4]: photos(db,o,o['status'] not in ['Finalizada','Cancelada','Check-out'])
    with tabs[1]:
        st.subheader("Novedades y repuestos")
        table(o['notes'])
        if o['status'] not in ['Finalizada','Cancelada','Check-out']:
            with st.form('note'):
                note=st.text_area('Registrar novedad')
                if st.form_submit_button('Guardar novedad') and note.strip():
                    def append_note(data): get(data,'orders',o['id'])['notes'].append(dict(text=note,at=now(),actor=tech['name'] if technician else 'Marcela'))
                    mutate(append_note);st.rerun()
            with st.form('part_request'):
                part=pick(db,'inventory','Repuesto requerido');qty=st.number_input('Cantidad',1,100,1);reason=st.text_input('Motivo');priority=st.selectbox('Prioridad del repuesto',['Media','Alta','Urgente'])
                if st.form_submit_button('Solicitar repuesto'):
                    if not reason.strip(): st.error('Indica el motivo.')
                    else: add('part_requests',dict(order_id=o['id'],tech_id=o['tech_id'],equipment_id=o['equipment_id'],part_id=part,quantity=qty,reason=reason,priority=priority,status='Pendiente'),'REP-');st.rerun()
        table([r for r in db['part_requests'] if r['order_id']==o['id']])
    with tabs[1]:
        with st.expander('Recepción, firma y finalización',expanded=True): closure_form(o)
    with tabs[2]:
        st.subheader(equipment['name'])
        info_grid([(title,equipment.get(field,'—')) for field,title in [('code','Código'),('serial','Serial'),('brand','Marca'),('model','Modelo'),('category','Categoría'),('location','Ubicación'),('status','Estado'),('last_calibration','Última calibración'),('next_calibration','Próxima calibración')]])
        st.button('QR del equipo · Próximamente',disabled=True)
    with tabs[4]:
        st.subheader('Documentos adjuntos')
        for d in o.get('documents',[]):
            path=path_for(d)
            if path.exists(): st.download_button(d['name'],path.read_bytes(),file_name=d['name'],key=f'orddoc_{d["path"]}')
        if not technician:
            files=st.file_uploader('Adjuntar documentos de la orden',type=['pdf'],accept_multiple_files=True)
            if st.button('Guardar documentos',disabled=not files): upload(files,'orders',o['id'],'documents','Documento técnico');st.rerun()

def orders_page(db,technician=False,tech_id=None):
    heading('Mis servicios' if technician else 'Órdenes de servicio','Tu jornada en campo, organizada.' if technician else 'Cada intervención, desde la asignación hasta el cierre.')
    available=[o for o in db['orders'] if not technician or o['tech_id']==tech_id]
    if not technician:
        with st.expander('＋ Nueva orden de servicio'): new_order(db)
    statuses=['Todos']+list(dict.fromkeys(o['status'] for o in available))
    status=st.selectbox('Filtrar por estado',statuses)
    filtered=[o for o in available if status=='Todos' or o['status']==status]
    if technician:
        period=st.radio('Período de servicios',['Hoy','Semana','Todos'],horizontal=True,key='service_period')
        today=date.today();week=today-timedelta(days=today.weekday())
        visible=[o for o in filtered if period=='Todos' or (o['date']==str(today) if period=='Hoy' else str(week)<=o['date']<=str(week+timedelta(days=6)))]
        if st.session_state.get('tech_detail'):
            if st.button('← Mis servicios'): st.session_state.tech_detail=False;st.rerun()
        else:
            if not visible: st.info('No hay servicios en este período. Puedes consultar Semana o Todos.')
            for o in sorted(visible,key=lambda x:(x['date'],x['time'])):
                with st.container(border=True):
                    st.markdown(f'<div class="service-card"><div class="service-time">{o["time"]}<small>{o["date"][5:]}</small></div><div>{badge_html(o["status"])}<h3>{escape(label(db,"clients",o["client_id"]))}</h3><p>{escape(o["type"])}</p><p>{escape(label(db,"equipment",o["equipment_id"]))}</p><small>{escape(o["address"])}</small></div></div>',unsafe_allow_html=True)
                    if st.button('Abrir tarea',key=f'task_{o["id"]}',type='primary',width='stretch'): st.session_state.open_order=o['id'];st.session_state.tech_detail=True;st.rerun()
    else:
        with st.expander('Listado de órdenes',expanded=not bool(st.session_state.get('open_order'))): table(order_rows(db,filtered))
    if not available: st.info('No hay tareas asignadas.');return
    ids=[o['id'] for o in available]
    selected=st.session_state.pop('open_order',None)
    if selected in ids: st.session_state['selected_order']=selected
    if st.session_state.get('selected_order') not in ids: st.session_state['selected_order']=ids[0]
    def enter_service():
        if technician: st.session_state.tech_detail=True
    oid=st.selectbox('Detalle de la orden',ids,key='selected_order',on_change=enter_service)
    if not technician or st.session_state.get('tech_detail'): detail(db,get(db,'orders',oid),technician)
