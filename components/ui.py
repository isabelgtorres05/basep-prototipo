from html import escape
from urllib.parse import urlencode,quote
from datetime import date,timedelta
import base64
import json
import streamlit as st
import pandas as pd
from services.store import ROOT,get

LOGO=ROOT/'assets'/'logo_basep_ui.png'
NAV_ICONS={'Dashboard':'▦','Programación':'▣','Órdenes de servicio':'▤','Solicitudes / Tickets':'◷','Clientes':'♧','Equipos':'▧','Técnicos':'♙','Ubicación / Mapa':'⌖','Inventario':'▥','Informes':'▱','Indicadores':'▥','Portal Cliente':'▣','Configuración':'⚙','Inicio':'⌂','Mis equipos':'▧','Mis solicitudes':'◷','Servicios programados':'▣','Historial':'↺','Documentos':'▤','Solicitar servicio':'＋','Certificados':'✓','Mis tareas':'▤','Mi agenda':'▣'}
def nav_label(page):
    title={'Mis solicitudes':'Solicitudes','Servicios programados':'Servicios','Mis tareas':'Mis servicios'}.get(page,page)
    return title
def styles():
    st.session_state['_table_seq']=0
    st.markdown('<style>'+ (ROOT/'assets/styles.css').read_text(encoding='utf-8-sig')+'</style>',unsafe_allow_html=True)
def heading(title,subtitle=''):
    st.markdown(f'<div class="page-title"><div><h1>{escape(title)}</h1><p>{escape(subtitle)}</p></div></div>',unsafe_allow_html=True)
def hero(title,subtitle):
    st.markdown(f'<div class="hero"><h2>{escape(title)}</h2><p>{escape(subtitle)}</p></div>',unsafe_allow_html=True)
def tone(value):
    if value in ['Finalizada','Finalizado','Activo','Vigente','Disponible','Aprobada','Dentro de tolerancia','Check-out']: return 'green'
    if value in ['Próximo','Próximo a vencer','Pendiente','Pendientes','Pausada','En revisión','Bajo mínimo','Alta','Urgente']: return 'orange'
    if value in ['Vencido','Fuera de servicio','Fuera de tolerancia','Rechazada']: return 'red'
    if value in ['Cancelada','Creada','Baja']: return 'gray'
    return 'blue'
def badge_html(value): return f'<span class="badge {tone(value)}">{escape(str(value))}</span>'
def badge(value): st.markdown(badge_html(value),unsafe_allow_html=True)
def table(rows):
    st.session_state['_table_seq']=st.session_state.get('_table_seq',0)+1
    key=f'tbl_{st.session_state.get("nav","page")}_{st.session_state["_table_seq"]}'
    if not rows:
        st.markdown('<div class="table-empty">No hay registros para esta selección.</div>',unsafe_allow_html=True);return
    df=pd.DataFrame(rows).fillna('')
    selected=df
    if len(df)>=4:
        a,b,c=st.columns([3,2,1])
        query=a.text_input('Buscar en la tabla',placeholder='Buscar por nombre, código o cliente...',key=key+'_q',label_visibility='collapsed')
        if query: selected=selected[selected.astype(str).apply(lambda col:col.str.contains(query,case=False,regex=False)).any(axis=1)]
        state_col=next((s for s in ['Estado','status','Prioridad'] if s in df.columns),None)
        if state_col:
            state=b.selectbox('Filtrar registros',['Todos']+sorted(df[state_col].astype(str).unique().tolist()),key=key+'_state',label_visibility='collapsed')
            if state!='Todos': selected=selected[selected[state_col].astype(str)==state]
        c.download_button('↓ CSV',selected.to_csv(index=False).encode('utf-8-sig'),file_name='BASEP_registros.csv',mime='text/csv',key=key+'_csv',width='stretch')
    statuses={'Activo','Vigente','Próximo','Próximo a vencer','Vencido','Fuera de servicio','Pendiente','En ejecución','Finalizado','Finalizada','Enviada','Recibida','Vista','Aceptada','En desplazamiento','Check-in','Check-out','Pausada','Creada','Cancelada','Recibido','Programado','En revisión','Disponible','Bajo mínimo','Aprobada','Rechazada','Alta','Media','Baja','Urgente'}
    def cell(v):
        text=json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else str(v)
        return badge_html(text) if text in statuses else escape(text)
    head=''.join(f'<th>{escape(str(c))}</th>' for c in selected.columns)
    body=''.join('<tr>'+''.join(f'<td title="{escape(str(v),quote=True)}">{cell(v)}</td>' for v in row)+'</tr>' for row in selected.itertuples(index=False,name=None))
    st.markdown(f'<div class="table-shell"><table class="basep-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div><div class="table-meta">{len(selected)} registros</div>',unsafe_allow_html=True)
def label(db,table_name,key,field='name'): return get(db,table_name,key).get(field,'—')
def pick(db,table_name,title,key=None,items=None):
    values=db[table_name] if items is None else items
    requested=st.session_state.get('search_record')
    ids=[x['id'] for x in values]
    if title in ['Ficha del cliente','Ficha del equipo']:
        key=key or f'catalog_{table_name}'
        if requested in ids:
            st.session_state.pop('search_record',None);st.session_state[key]=requested
        elif st.session_state.get(key) not in ids and ids: st.session_state[key]=ids[0]
    return st.selectbox(title,ids,format_func=lambda i:f'{i} · {label(db,table_name,i)}',key=key)

def order_rows(db,orders):
    return [{'Orden':o['id'],'Cliente':label(db,'clients',o['client_id']),'Equipo':label(db,'equipment',o['equipment_id']),'Técnico':label(db,'techs',o['tech_id']),'Servicio':o['type'],'Fecha':o['date'],'Hora':o['time'],'Estado':o['status']} for o in orders]
def go(page,order_id=None):
    st.session_state['pending_nav']=page
    if order_id: st.session_state['open_order']=order_id
    st.rerun()
def href(page,order_id=None): return '?'+urlencode({'page':page,**({'order':order_id} if order_id else {})})
def panel_title(title,page=None):
    link=f'<a href="{escape(href(page),quote=True)}" target="_self">Ver todos →</a>' if page else ''
    st.markdown(f'<div class="panel-title"><span>{escape(title)}</span>{link}</div>',unsafe_allow_html=True)
def order_cards(db,orders,destination='Órdenes de servicio',prefix='card'):
    if not orders: st.info('No hay servicios en este período.')
    for o in orders:
        with st.container(border=True):
            a,b=st.columns([5,1])
            with a:
                st.markdown(f"**{o['time']} · {o['id']} — {label(db,'clients',o['client_id'])}**")
                st.caption(f"{o['type']} · {label(db,'equipment',o['equipment_id'])} · {label(db,'techs',o['tech_id'])}")
                badge(o['status'])
            if b.button('Abrir',key=f'{prefix}_{o["id"]}',width='stretch'): go(destination,o['id'])
def icon(name):
    paths={'file':'<path d="M6 3h8l4 4v14H6zM14 3v5h4M9 12h6M9 16h6"/>','clock':'<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>','play':'<circle cx="12" cy="12" r="9"/><path d="m10 8 6 4-6 4z"/>','check':'<path d="m5 12 4 4L19 6"/>','users':'<circle cx="9" cy="8" r="3"/><path d="M3 21v-4a6 6 0 0 1 12 0v4M16 5a3 3 0 0 1 0 6M18 14a5 5 0 0 1 3 5v2"/>','box':'<path d="m3 7 9-4 9 4v11l-9 4-9-4zM3 7l9 4 9-4M12 11v11"/>','star':'<path d="m12 3 3 6 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1z"/>'}
    paths.update({'calendar':'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 10h18M7 14h2M12 14h2M7 18h2"/>','grid':'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>','pin':'<path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 0 1 14 0z"/><circle cx="12" cy="10" r="2"/>','chart':'<path d="M4 3v18h17M8 16v-5M13 16V6M18 16V9"/>','settings':'<circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2"/>','home':'<path d="m3 10 9-7 9 7M5 9v12h14V9M10 21v-7h4v7"/>'})
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{paths.get(name,paths["file"])}</svg>'
def kpis(items):
    st.markdown('<div class="kpi-grid">'+''.join(f'<div class="kpi {color}"><div class="kpi-top"><span class="kpi-icon">{icon(symbol)}</span><span class="kpi-name">{escape(title)}</span></div><div class="kpi-value">{escape(str(value))}</div><div class="kpi-foot">{escape(note)}</div></div>' for title,value,note,symbol,color in items)+'</div>',unsafe_allow_html=True)
def calendar_html(db,days,orders,mini=False):
    out='<div class="calendar-scroll"><div class="calendar-grid'+(' mini' if mini else '')+'">'
    for day in days:
        out+=f'<div class="cal-day {"today" if day==date.today() else ""}"><div class="cal-date">{["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"][day.weekday()]}<b>{day.day:02}</b></div>'
        items=sorted([o for o in orders if o['date']==str(day)],key=lambda o:o['time'])
        for o in items:
            out+=f'<a class="cal-event {tone(o["status"])}" target="_self" href="{escape(href("Órdenes de servicio",o["id"]),quote=True)}"><b>{o["time"]} · {escape(o["type"])}</b>{escape(label(db,"clients",o["client_id"]))}<small>{escape(label(db,"techs",o["tech_id"]))}</small><small>{escape(o["status"])}</small></a>'
        if not items: out+='<div class="cal-empty">Sin servicios</div>'
        out+='</div>'
    st.markdown(out+'</div></div>',unsafe_allow_html=True)
def topbar(db,role,person):
    with st.container(key='topbar'):
        a,b,c=st.columns([6,1,2])
        query=a.text_input('Buscador global',placeholder='Buscar órdenes, clientes, equipos...',label_visibility='collapsed',key='global_search')
        alerts=[o for o in db['orders'] if o['status'] not in ['Finalizada','Cancelada'] and o['date']<str(date.today())]
        with b.popover(str(len(alerts)),icon=':material/notifications:',help='Notificaciones'):
            st.markdown('**Notificaciones**')
            if not alerts: st.caption('No hay órdenes atrasadas.')
            for o in alerts[:8]: st.caption(f"{o['id']} · {label(db,'clients',o['client_id'])} · Programada para {o['date']}")
        short=person.split()[0];initials=''.join(n[0] for n in person.split()[:2])
        c.markdown(f'<div class="profile"><span class="avatar">{escape(initials)}</span><div><b>{escape(short)}</b><small>{escape(role)}</small></div></div>',unsafe_allow_html=True)
    if query.strip():
        q=query.casefold();found=[]
        for tab,page in [('orders','Órdenes de servicio'),('clients','Clientes'),('equipment','Equipos')]:
            for item in db[tab]:
                if q in ' '.join(str(v) for k,v in item.items() if k in ['id','name','code','serial','description']).casefold(): found.append((tab,page,item))
        with st.expander(f'{len(found)} resultados de búsqueda',expanded=True):
            for tab,page,item in found[:15]:
                title=item.get('name',item['id']);description=item.get('type',item.get('code',item.get('city','')))
                st.markdown(f'**{escape(title)}** · {escape(description)}')
                if role=='Administradora' and st.button('Abrir resultado',key=f'result_{tab}_{item["id"]}'):
                    if tab!='orders': st.session_state['search_record']=item['id']
                    go(page,item['id'] if tab=='orders' else None)
                elif role!='Administradora': st.caption('Consulta el registro en tu menú de servicios o equipos.')
            if not found: st.caption('Prueba con un número de orden, nombre de cliente o serial.')


def navigation_style(menu):
    names={'Dashboard':'grid','Programación':'calendar','Órdenes de servicio':'file','Solicitudes / Tickets':'clock','Clientes':'users','Equipos':'box','Técnicos':'users','Ubicación / Mapa':'pin','Inventario':'box','Informes':'file','Indicadores':'chart','Portal Cliente':'home','Configuración':'settings','Inicio':'home','Mis equipos':'box','Mis solicitudes':'clock','Servicios programados':'calendar','Historial':'clock','Documentos':'file','Solicitar servicio':'file','Certificados':'check','Mis tareas':'file','Mi agenda':'calendar'}
    css=''
    for i,page in enumerate(menu,1):
        svg=icon(names.get(page,'file')).replace('currentColor','#000')
        data='data:image/svg+xml,'+quote(svg)
        css+=f'[data-testid="stSidebar"] [data-testid="stRadioOption"]:nth-child({i}) p:before{{mask-image:url("{data}")}}'
    st.markdown('<style>'+css+'</style>',unsafe_allow_html=True)


def info_grid(items):
    st.markdown('<div class="info-grid">'+''.join(f'<div class="info-cell"><small>{escape(title)}</small><strong>{escape(str(value))}</strong></div>' for title,value in items)+'</div>',unsafe_allow_html=True)
