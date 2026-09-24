from datetime import date,datetime,timedelta
import calendar
import pandas as pd
import streamlit as st
from services.store import get,update
from services.workflow import stock_move
from components.ui import heading,hero,table,label,pick,order_rows,order_cards,go,kpis,panel_title,calendar_html,badge_html
from views.orders import new_order,report_view

def minutes(o,start,end):
    if start=='En ejecución' and end=='Check-out':
        total=0;begin=None;closed=False
        for event in o['timeline']:
            if event['state']=='En ejecución': begin=datetime.fromisoformat(event['at'])
            elif event['state'] in ['Pausada','Check-out'] and begin:
                total+=max(0,(datetime.fromisoformat(event['at'])-begin).total_seconds()/60);begin=None
                if event['state']=='Check-out': closed=True
        return total if closed else None
    a=next((x['at'] for x in o['timeline'] if x['state']==start),None)
    b=next((x['at'] for x in reversed(o['timeline']) if x['state']==end),None)
    return max(0,(datetime.fromisoformat(b)-datetime.fromisoformat(a)).total_seconds()/60) if a and b else None
def avg(values):
    values=[v for v in values if v is not None]
    return round(sum(values)/len(values),1) if values else None
def metric_value(v,suffix=''): return f'{v}{suffix}' if v is not None else 'Sin datos'
def satisfaction(orders): return avg([avg([o['closure'].get(k) for k in ['quality','punctuality','attention']]) for o in orders if o['status']=='Finalizada'])

def _dashboard_indicators(db,indicators=True):
    today=date.today();orders=db['orders'];done=[o for o in orders if o['status']=='Finalizada'];pending=[o for o in orders if o['status'] not in ['Finalizada','Cancelada']]
    heading('Indicadores' if indicators else 'Centro de operaciones',today.strftime('%d / %m / %Y')+' · Información de demostración actualizada con tus pruebas')
    if not indicators: hero('Cada servicio, bajo control.',f"Hola, Marcela. Tienes {len(pending)} órdenes abiertas y {sum(t['status']=='Recibido' for t in db['tickets'])} solicitudes por revisar.")
    metrics=[('Órdenes del mes',sum(o['date'][:7]==str(today)[:7] for o in orders)),('Pendientes',len(pending)),('En ejecución',sum(o['status']=='En ejecución' for o in orders)),('Completadas',len(done)),('Técnicos activos',len(db['techs'])),('Equipos registrados',len(db['equipment'])),('Satisfacción',metric_value(satisfaction(orders),' / 5'))]
    for start in [0,4]:
        cols=st.columns(4 if start==0 else 3)
        for col,(title,value) in zip(cols,metrics[start:start+4]): col.metric(title,value)
    if not indicators:
        a,b,c=st.columns(3)
        if a.button('Ver órdenes →',width='stretch'): go('Órdenes de servicio')
        if b.button('Planificar semana →',width='stretch'): go('Programación')
        if c.button('Atender solicitudes →',width='stretch'): go('Solicitudes / Tickets')
    a,b=st.columns(2)
    with a:
        st.subheader('Servicios por estado')
        if orders: st.bar_chart(pd.Series([o['status'] for o in orders]).value_counts(),color='#008dbb')
        st.subheader('Servicios por semana')
        if orders:
            df=pd.DataFrame(orders);df['Semana']=pd.to_datetime(df['date']).dt.to_period('W').astype(str)
            st.line_chart(df.groupby('Semana').size(),color='#07558c')
    with b:
        st.subheader('Distribución por servicio')
        if orders: st.bar_chart(pd.Series([o['type'] for o in orders]).value_counts(),horizontal=True,color='#07558c')
        st.subheader('Satisfacción del cliente')
        if done: st.bar_chart(pd.DataFrame({'Calificación':[satisfaction([o]) for o in done]},index=[o['id'] for o in done]),color='#009fc5')
    if indicators:
        eligible=[o for o in orders if o['date']<=str(today) and o['status']!='Cancelada']
        ontime=[o for o in eligible if o['status']=='Finalizada' and next((t['at'][:10] for t in reversed(o['timeline']) if t['state']=='Finalizada'),'9999')<=o['date']]
        repeated=sum(sum(x['equipment_id']==o['equipment_id'] for x in done)>1 for o in done)
        response=[(datetime.fromisoformat(t['first_response'])-datetime.fromisoformat(t['created'])).total_seconds()/3600 for t in db['tickets'] if t.get('first_response')]
        values=[('Cumplimiento de programación',f'{len(ontime)/len(eligible)*100:.0f} %' if eligible else 'Sin datos'),('Equipos atendidos',len({o['equipment_id'] for o in done})),('Tiempo promedio de servicio',metric_value(avg([minutes(o,'En ejecución','Check-out') for o in done]),' min')),('Desplazamiento promedio',metric_value(avg([minutes(o,'En desplazamiento','Check-in') for o in orders]),' min')),('Tickets recibidos',len(db['tickets'])),('Tickets cerrados',sum(t['status']=='Finalizado' for t in db['tickets'])),('Tickets pendientes',sum(t['status']!='Finalizado' for t in db['tickets'])),('Primera respuesta promedio',metric_value(avg(response),' h')),('Solicitudes de repuesto pendientes',sum(r['status']=='Pendiente' for r in db['part_requests'])),('Servicios con reincidencia',repeated)]
        table([{'Indicador':k,'Valor':str(v)} for k,v in values])
        st.caption('Cumplimiento: órdenes vencidas o de hoy finalizadas en su fecha o antes. Reincidencia: servicios terminados en equipos con más de un servicio terminado. Horas efectivas excluyen pausas. Los tiempos se calculan a partir de la trazabilidad registrada.')
        st.subheader('Servicios realizados por tipo')
        table([{'Tipo':kind,'Terminados':sum(o['type']==kind for o in done)} for kind in ['Calibración','Mantenimiento preventivo','Mantenimiento correctivo','Inspección','Verificación']])
        response_close=[(datetime.fromisoformat(t['closed_at'])-datetime.fromisoformat(t['created'])).total_seconds()/3600 for t in db['tickets'] if t.get('closed_at')]
        st.metric('Tiempo promedio de cierre de tickets',metric_value(avg(response_close),' h'))
        st.subheader('Desempeño por técnico')
        table([{'Técnico':t['name'],'Asignadas':sum(o['tech_id']==t['id'] for o in orders),'Finalizadas':sum(o['tech_id']==t['id'] for o in done),'Horas efectivas':round(sum(minutes(o,'En ejecución','Check-out') or 0 for o in done if o['tech_id']==t['id'])/60,1),'Satisfacción':satisfaction([o for o in done if o['tech_id']==t['id']])} for t in db['techs']])
        st.subheader('Equipos por cliente');st.bar_chart(pd.Series([label(db,'clients',e['client_id']) for e in db['equipment']]).value_counts(),color='#008dbb')
        return
    left,right=st.columns([1.6,1])
    with left:
        st.subheader('Programación de hoy');order_cards(db,[o for o in orders if o['date']==str(today)],prefix='today')
        st.subheader('Esta semana');table(order_rows(db,[o for o in orders if today-timedelta(days=today.weekday())<=date.fromisoformat(o['date'])<=today+timedelta(days=6-today.weekday())]))
        st.subheader('Próximos servicios');order_cards(db,sorted([o for o in pending if o['date']>str(today)],key=lambda o:o['date'])[:3],prefix='upcoming')
    with right:
        st.subheader('Atención prioritaria')
        late=[o for o in pending if o['date']<str(today)]
        st.warning(f'{len(late)} órdenes atrasadas · {sum(e["status"]=="Vencido" for e in db["equipment"])} equipos vencidos')
        table(order_rows(db,late))
        st.subheader('Técnicos en campo')
        table([{'Técnico':label(db,'techs',o['tech_id']),'Cliente':label(db,'clients',o['client_id']),'Estado':o['status']} for o in orders if o['status'] in ['En desplazamiento','Check-in','En ejecución']])
        st.subheader('Actividad reciente')
        events=sorted([dict(Orden=o['id'],Evento=t['state'],Fecha=t['at']) for o in orders for t in o['timeline']],key=lambda t:t['Fecha'],reverse=True)[:6]
        table(events)

def schedule(db):
    heading('Programación','Organiza la agenda del equipo y abre cada intervención.')
    a,b,c=st.columns([1,1,2]);view=a.radio('Vista',['Día','Semana','Mes'],index=1,horizontal=True,key='calendar_switch');anchor=b.date_input('Período',date.today())
    tech=c.selectbox('Filtrar técnico',['Todos']+[t['id'] for t in db['techs']],format_func=lambda x:label(db,'techs',x) if x!='Todos' else x)
    if view=='Día': days=[anchor]
    elif view=='Semana':
        start=anchor-timedelta(days=anchor.weekday());days=[start+timedelta(days=i) for i in range(7)]
    else: days=[d for week in calendar.Calendar(firstweekday=0).monthdatescalendar(anchor.year,anchor.month) for d in week]
    filtered=[o for o in db['orders'] if tech=='Todos' or o['tech_id']==tech]
    st.caption('🔵 Planificada · 🟠 En curso · 🟢 Finalizada · ⚪ Cancelada')
    if view=='Día': order_cards(db,[o for o in filtered if o['date']==str(anchor)],prefix='cal_day')
    else: calendar_html(db,days,filtered)
    with st.expander('＋ Nueva tarea'): new_order(db)
    st.subheader('Tareas pendientes de envío');table(order_rows(db,[o for o in filtered if o['status']=='Creada']))
    st.caption('Las órdenes nuevas reciben fecha desde su creación; las creadas quedan pendientes de envío al técnico.')
    st.subheader('Solicitudes no programadas')
    table([{'Solicitud':t['id'],'Cliente':label(db,'clients',t['client_id']),'Necesidad':t['type'],'Prioridad':t['priority']} for t in db['tickets'] if not t['order_id']])
    if st.button('Programar solicitudes →'): go('Solicitudes / Tickets')

def technicians(db,map_view=False):
    heading('Ubicación / Mapa' if map_view else 'Técnicos','Coordenadas, recorridos y dispositivos simulados. Sin GPS real.')
    table([{'Técnico':t['name'],'Estado':next((o['status'] for o in db['orders'] if o['tech_id']==t['id'] and o['status'] in ['En ejecución','En desplazamiento','Pausada']),t['status']),
            'Servicios hoy':sum(o['tech_id']==t['id'] and o['date']==str(date.today()) for o in db['orders']),
            'Tarea actual':next((o['id'] for o in db['orders'] if o['tech_id']==t['id'] and o['status'] in ['En ejecución','En desplazamiento']), '—'),
            'Cliente actual':next((label(db,'clients',o['client_id']) for o in db['orders'] if o['tech_id']==t['id'] and o['status'] in ['En ejecución','En desplazamiento']), '—'),
            'Última ubicación':f"{t['lat']:.3f}, {t['lon']:.3f}"} for t in db['techs']])
    tid=pick(db,'techs','Seleccionar técnico');t=get(db,'techs',tid);orders=[o for o in db['orders'] if o['tech_id']==tid]
    a,b=st.columns([1,2])
    with a:
        st.subheader(t['name']);st.write(t['specialty']);st.write(t['phone']);st.write(t['email']);st.caption(f"{t['device']} · {t['battery']} % batería")
        st.metric('Horas registradas',round(sum(minutes(o,'En ejecución','Check-out') or 0 for o in orders)/60,1))
        st.metric('Finalización',f"{sum(o['status']=='Finalizada' for o in orders)/len(orders)*100:.0f} %" if orders else 'Sin tareas')
    with b:
        st.map(pd.DataFrame([{'lat':x['lat'],'lon':x['lon']} for x in (db['techs'] if map_view else [t])]),zoom=11)
        st.caption(f"Última ubicación simulada de {t['name']}: {t['lat']}, {t['lon']}")
    st.subheader('Agenda y servicios');table(order_rows(db,orders))
    st.subheader('Recorrido y presencia registrados')
    table([{'Orden':o['id'],'Cliente':label(db,'clients',o['client_id']),'Evento':event['state'],'Hora':event['at'],'Dirección':o['address']} for o in orders for event in o['timeline'] if event['state'] in ['En desplazamiento','Check-in','Check-out']])

def inventory(db):
    heading('Inventario','Repuestos, existencias y solicitudes del equipo de campo.')
    table([{'Código':p['id'],'Producto':p['name'],'Categoría':p['category'],'Stock':p['stock'],'Mínimo':p['minimum'],'Ubicación':p['location'],'Estado':'Bajo mínimo' if p['stock']<p['minimum'] else 'Disponible'} for p in db['inventory']])
    a,b=st.columns(2)
    with a:
        st.subheader('Registrar movimiento')
        with st.form('movement'):
            pid=pick(db,'inventory','Producto / repuesto');kind=st.selectbox('Movimiento',['Entrada','Salida','Consumo en servicio']);qty=st.number_input('Cantidad del movimiento',1,10000,1)
            oid=st.selectbox('Orden asociada',[None]+[o['id'] for o in db['orders']],format_func=lambda x:x or 'Sin orden')
            if st.form_submit_button('Registrar movimiento'):
                try: stock_move(pid,kind,qty,oid);st.rerun()
                except ValueError as e: st.error(str(e))
    with b:
        st.subheader('Solicitudes de repuesto')
        table([{'Solicitud':r['id'],'Orden':r['order_id'],'Técnico':label(db,'techs',r['tech_id']),'Repuesto':label(db,'inventory',r['part_id']),'Cantidad':r['quantity'],'Motivo':r['reason'],'Prioridad':r['priority'],'Estado':r['status']} for r in db['part_requests']])
        if db['part_requests']:
            rid=st.selectbox('Revisar solicitud',[r['id'] for r in db['part_requests']]);r=get(db,'part_requests',rid)
            status=st.selectbox('Decisión',['Pendiente','Aprobada','Rechazada'],index=['Pendiente','Aprobada','Rechazada'].index(r['status']))
            if st.button('Guardar revisión'): update('part_requests',rid,{'status':status});st.rerun()
            st.caption('Aprobar no descuenta stock. Registra el consumo cuando entregues el repuesto.')
    st.subheader('Historial de movimientos');table(db['movements'])

def reports(db,client=False):
    heading('Informes','Biblioteca de servicios terminados y documentación técnica.')
    orders=[o for o in db['orders'] if o['status']=='Finalizada' and (not client or o['published'])]
    a,b,c=st.columns(3)
    cid=a.selectbox('Cliente del informe',['Todos']+[x['id'] for x in db['clients']],format_func=lambda x:label(db,'clients',x) if x!='Todos' else x)
    tid=b.selectbox('Técnico del informe',['Todos']+sorted({o['tech_id'] for o in orders}),format_func=lambda x:label(db,'techs',x) if x!='Todos' else x)
    eid=c.selectbox('Equipo del informe',['Todos']+[x['id'] for x in db['equipment']],format_func=lambda x:label(db,'equipment',x) if x!='Todos' else x)
    a,b,c=st.columns(3);kind=a.selectbox('Tipo de servicio',['Todos']+sorted({o['type'] for o in orders}));start=b.date_input('Desde',date.today()-timedelta(days=365));end=c.date_input('Hasta',date.today()+timedelta(days=365))
    found=[o for o in orders if (cid=='Todos' or o['client_id']==cid) and (tid=='Todos' or o['tech_id']==tid) and (eid=='Todos' or o['equipment_id']==eid) and (kind=='Todos' or o['type']==kind) and str(start)<=o['date']<=str(end)]
    table(order_rows(db,found))
    if not found: st.info('Sin informes autorizados para estos filtros.' if client else 'Sin informes para estos filtros.');return
    oid=st.selectbox('Abrir informe',[o['id'] for o in found]);report_view(db,get(db,'orders',oid),admin=not client)

def dashboard(db,indicators=False):
    if indicators: return _dashboard_indicators(db,True)
    import altair as alt
    from html import escape
    today=date.today();orders=db['orders']
    done=[o for o in orders if o['status']=='Finalizada'];pending=[o for o in orders if o['status'] not in ['Finalizada','Cancelada']]
    heading('Dashboard',f'Operación de servicios · {today.strftime("%d / %m / %Y")}')
    in_field=[o for o in orders if o['status'] in ['En ejecución','En desplazamiento','Check-in']]
    kpis([('Órdenes del mes',sum(o['date'][:7]==str(today)[:7] for o in orders),'Programadas en el período','file',''),
          ('Pendientes',len(pending),f"{sum(o['date']<str(today) for o in pending)} requieren atención",'clock','warm'),
          ('En ejecución',sum(o['status']=='En ejecución' for o in orders),'Servicios en curso','play',''),
          ('Completadas',len(done),'Con informe de servicio','check','green'),
          ('Técnicos activos',len(db['techs']),f'{len({o["tech_id"] for o in in_field})} en campo','users',''),
          ('Equipos registrados',len(db['equipment']),f'{len(db["clients"])} empresas','box',''),
          ('Satisfacción',metric_value(satisfaction(orders),' / 5'),f'{len([o for o in done if o["closure"]])} evaluaciones','star','green')])
    with st.container(key='dashboard_ops'):
        left,center,right=st.columns([1.5,1.05,.9],gap='small')
        with left,st.container(border=True):
            panel_title('Programación de servicios','Programación')
            start=today-timedelta(days=today.weekday())
            st.caption(f'{start.strftime("%d %b")} – {(start+timedelta(days=6)).strftime("%d %b %Y")} · Semana')
            calendar_html(db,[start+timedelta(days=i) for i in range(5)],orders,mini=True)
            if st.button('Abrir calendario',key='dash_calendar',width='stretch'): go('Programación')
        with center,st.container(border=True):
            panel_title('Técnicos en campo','Ubicación / Mapa')
            active_ids={o['tech_id'] for o in in_field}
            points=[t for t in db['techs'] if t['id'] in active_ids]
            if points: st.map(pd.DataFrame([{'lat':t['lat'],'lon':t['lon']} for t in points]),zoom=10,height=185,size=70,color='#007ac4')
            else: st.caption('Sin servicios en campo en este momento.')
            for o in in_field[:3]:
                name=label(db,'techs',o['tech_id']);initials=''.join(n[0] for n in name.split()[:2])
                st.markdown(f'<div class="tech-row"><span class="avatar">{initials}</span><div><b>{escape(name)}</b><small>{escape(label(db,"clients",o["client_id"]))}</small></div>{badge_html(o["status"])}</div>',unsafe_allow_html=True)
            st.caption('Ubicaciones simuladas · Bogotá')
        with right,st.container(border=True):
            panel_title('Actividad reciente','Órdenes de servicio')
            events=sorted([(o,t) for o in orders for t in o['timeline']],key=lambda x:x[1]['at'],reverse=True)[:5]
            for o,t in events:
                dt=datetime.fromisoformat(t['at']);elapsed=max(0,int((datetime.now()-dt).total_seconds()/60))
                ago=f'Hace {elapsed} min' if elapsed<60 else f'Hace {elapsed//60} h' if elapsed<1440 else f'Hace {elapsed//1440} días'
                st.markdown(f'<div class="activity"><span class="activity-icon">✓</span><div><b>{escape(t["state"])} · {escape(o["id"])}</b><small>{escape(label(db,"clients",o["client_id"]))}</small><small>{ago}</small></div></div>',unsafe_allow_html=True)
            received=sum(t['status']=='Recibido' for t in db['tickets'])
            if st.button(f'{received} solicitudes por revisar →',key='dash_tickets',width='stretch'): go('Solicitudes / Tickets')
    a,b,c=st.columns([1.1,1.2,1],gap='small')
    with a,st.container(border=True):
        panel_title('Órdenes por estado','Órdenes de servicio')
        counts=pd.Series([o['status'] for o in orders]).value_counts().rename_axis('Estado').reset_index(name='Órdenes')
        chart=alt.Chart(counts).mark_arc(innerRadius=52,outerRadius=77).encode(theta='Órdenes:Q',color=alt.Color('Estado:N',scale=alt.Scale(domain=['Finalizada','En ejecución','Enviada','Aceptada','Creada','Cancelada','Pausada','Check-in','Check-out','Recibida','Vista','En desplazamiento'],range=['#009d83','#0787c7','#2582c4','#83bce6','#b8c6d3','#d46570','#efb04c','#168fae','#5bad93','#60a6da','#87badb','#28a6cb']),legend=alt.Legend(orient='right',title=None,labelFontSize=9)),tooltip=['Estado','Órdenes']).properties(height=195)
        st.altair_chart(chart,width='stretch')
    with b,st.container(border=True):
        panel_title('Servicios del mes','Indicadores')
        current=[o for o in orders if o['date'][:7]==str(today)[:7]]
        buckets=pd.DataFrame([{'Semana':f'Sem {(date.fromisoformat(o["date"]).day-1)//7+1}','Servicios':1} for o in current])
        if not buckets.empty:
            chart=alt.Chart(buckets.groupby('Semana',as_index=False).sum()).mark_bar(color='#078bcd',cornerRadiusTopLeft=5,cornerRadiusTopRight=5,size=32).encode(x=alt.X('Semana:N',title=None,axis=alt.Axis(labelAngle=0)),y=alt.Y('Servicios:Q',title=None),tooltip=['Semana','Servicios']).properties(height=195)
            st.altair_chart(chart,width='stretch')
    with c,st.container(border=True):
        panel_title('Cumplimiento','Indicadores')
        due=[o for o in orders if o['date']<=str(today) and o['status']!='Cancelada']
        ontime=[o for o in due if o['status']=='Finalizada' and next((t['at'][:10] for t in reversed(o['timeline']) if t['state']=='Finalizada'),'9999')<=o['date']]
        pct=round(len(ontime)/len(due)*100) if due else 0
        st.metric('Finalizadas en fecha',f'{pct} %');st.progress(pct/100)
        st.caption(f'{len(ontime)} de {len(due)} órdenes con fecha hasta hoy')
        st.caption(f'{len([e for e in db["equipment"] if e["status"]=="Vencido"])} equipos con calibración vencida')
        if st.button('Ver indicadores →',key='dash_indicators',width='stretch'): go('Indicadores')
    with st.expander('Programación de hoy y próximos servicios',expanded=False):
        order_cards(db,[o for o in orders if o['date']==str(today)],prefix='today')
        st.subheader('Próximos servicios');order_cards(db,sorted([o for o in pending if o['date']>str(today)],key=lambda o:o['date'])[:5],prefix='upcoming')
    with st.expander('Alertas y tareas atrasadas',expanded=False):
        table(order_rows(db,[o for o in pending if o['date']<str(today)]))
