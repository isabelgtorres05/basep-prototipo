"""Entrada del prototipo. La navegación, vistas y lógica están separadas."""
import streamlit as st
from services.store import load,scoped
from components.ui import LOGO,styles,heading,pick,nav_label,topbar,label,navigation_style
from views.operations import dashboard,schedule,technicians,inventory,reports
from views.orders import orders_page
from views.catalogs import clients_page,equipment_page
from views.tickets import tickets_page
from views.portal import portal,CLIENT_MENU

st.set_page_config(page_title='BASEP · Gestión de servicios',page_icon='🔧',layout='wide',initial_sidebar_state='expanded')
styles()
db=load()
ADMIN_MENU=['Dashboard','Programación','Órdenes de servicio','Solicitudes / Tickets','Clientes','Equipos','Técnicos','Ubicación / Mapa','Inventario','Informes','Indicadores','Portal Cliente','Configuración']
with st.sidebar:
    st.image(str(LOGO),width=210)
    st.caption('OPERACIONES · PROTOTIPO V2')
    role=st.selectbox('Vista como',['Marcela / Administradora','Técnico','Cliente'])
    if st.session_state.get('_previous_role')!=role:
        st.session_state['_previous_role']=role
        st.session_state.pop('nav',None);st.session_state.pop('selected_order',None);st.session_state.pop('open_order',None)
    cid=pick(db,'clients','Empresa de demostración',key='portal_company') if role=='Cliente' else None
    tid=pick(db,'techs','Técnico de demostración',key='demo_technician') if role=='Técnico' else None
    menu=ADMIN_MENU if role=='Marcela / Administradora' else CLIENT_MENU if role=='Cliente' else ['Mis tareas','Mi agenda']
    if 'pending_nav' in st.session_state:
        target=st.session_state.pop('pending_nav')
        if target in menu: st.session_state.nav=target
    if st.session_state.get('nav') not in menu: st.session_state.nav=menu[0]
    if st.query_params.get('page') in menu:
        st.session_state.nav=st.query_params['page']
        if st.query_params.get('order'): st.session_state.open_order=st.query_params['order']
        st.query_params.clear()
    navigation_style(menu)
    page=st.radio('Navegación',menu,key='nav',format_func=nav_label,label_visibility='collapsed')
    st.divider();st.caption('Ingeniería a su Servicio')
    st.caption('Datos ficticios · Cambios guardados localmente')

role_class='role-client' if role=='Cliente' else 'role-technician' if role=='Técnico' else 'role-admin'
st.markdown(f'<span class="{role_class}"></span>',unsafe_allow_html=True)
view_db=scoped(db,cid) if role=='Cliente' else db
if role=='Técnico':
    view_db=dict(db)
    view_db['orders']=[o for o in db['orders'] if o['tech_id']==tid]
    client_ids={o['client_id'] for o in view_db['orders']}
    view_db['clients']=[c for c in db['clients'] if c['id'] in client_ids]
    view_db['equipment']=[e for e in db['equipment'] if e['client_id'] in client_ids]
topbar(view_db,'Administradora' if role=='Marcela / Administradora' else role,'Marcela' if role=='Marcela / Administradora' else label(db,'techs',tid) if role=='Técnico' else label(db,'clients',cid))
if role=='Cliente': portal(view_db,cid,page)
elif role=='Técnico':
    if page=='Mis tareas': orders_page(db,True,tid)
    else:
        from components.ui import order_cards
        heading('Mi agenda','Servicios asignados al técnico seleccionado.')
        order_cards(db,sorted([o for o in db['orders'] if o['tech_id']==tid],key=lambda x:(x['date'],x['time'])),'Mis tareas','tech_agenda')
else:
    if page=='Dashboard': dashboard(db)
    elif page=='Indicadores': dashboard(db,True)
    elif page=='Programación': schedule(db)
    elif page=='Órdenes de servicio': orders_page(db)
    elif page=='Solicitudes / Tickets': tickets_page(db)
    elif page=='Clientes': clients_page(db)
    elif page=='Equipos': equipment_page(db)
    elif page=='Técnicos': technicians(db)
    elif page=='Ubicación / Mapa': technicians(db,True)
    elif page=='Inventario': inventory(db)
    elif page=='Informes': reports(db)
    elif page=='Portal Cliente':
        cid=pick(db,'clients','Empresa a consultar',key='admin_portal_company')
        portal_page=st.selectbox('Sección del portal',CLIENT_MENU)
        portal(scoped(db,cid),cid,portal_page)
    elif page=='Configuración':
        heading('Configuración','Alcance y evolución del prototipo BASEP.')
        st.success('Persistencia local JSON activada. Los formularios y estados se conservan al reiniciar.')
        st.markdown('**Disponible:** gestión de clientes y sedes, equipos, tickets, programación, órdenes, evidencias, recepción, inventario, informes e indicadores.')
        st.info('El selector de vistas permite probar experiencias. No es autenticación ni un control de acceso empresarial. Usar únicamente datos de prueba.')
        st.markdown('**Simulado:** recepción del dispositivo, conectividad, ubicación, recorrido y firma escrita. El QR es una reserva visual.')
        st.markdown('**Evolución prevista:** repositorios PostgreSQL, autenticación, API de sincronización, almacenamiento de evidencias y aplicaciones móviles offline. No implementados en V1.')
        st.caption('Prototipo de un solo proceso local. Las entidades tienen identificadores y relaciones separadas; cada orden conserva su línea de tiempo.')
