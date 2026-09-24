from datetime import date
import streamlit as st
from components.ui import heading,hero,table,label,order_rows,kpis,go
from views.catalogs import equipment_page,documents
from views.tickets import new_ticket,tickets_page
from views.operations import reports

CLIENT_MENU=['Inicio','Mis equipos','Mis solicitudes','Servicios programados','Informes','Certificados','Documentos','Historial','Solicitar servicio']
def portal(db,cid,page):
    if page=='Inicio':
        heading('Portal del cliente','Equipos, servicios y documentos de tu empresa.')
        hero(label(db,'clients',cid),'Tus equipos, solicitudes y servicios en un mismo lugar.')
        kpis([('Mis equipos',len(db['equipment']),'Activos de tu empresa','box',''),('Solicitudes abiertas',sum(t['status']!='Finalizado' for t in db['tickets']),'Seguimiento de requerimientos','clock','warm'),('Informes disponibles',sum(o['status']=='Finalizada' and o['published'] for o in db['orders']),'Autorizados por BASEP','file','green')])
        a,b,c=st.columns(3)
        if a.button('＋ Solicitar servicio',type='primary',width='stretch'): go('Solicitar servicio')
        if b.button('Mis equipos →',width='stretch'): go('Mis equipos')
        if c.button('Ver documentos →',width='stretch'): go('Documentos')
        st.subheader('Próximos servicios');table(order_rows(db,[o for o in db['orders'] if o['date']>=str(date.today()) and o['status'] not in ['Finalizada','Cancelada']]))
        st.subheader('Mis solicitudes recientes');table([{'Número':t['id'],'Necesidad':t['type'],'Estado':t['status'],'Equipo':label(db,'equipment',t['equipment_id'])} for t in db['tickets'][-5:]])
    elif page=='Mis equipos': equipment_page(db,client=True)
    elif page=='Solicitar servicio': new_ticket(db,cid)
    elif page=='Mis solicitudes': tickets_page(db,client=True)
    elif page in ['Servicios programados','Historial']:
        heading(page)
        table(order_rows(db,[o for o in db['orders'] if (o['status']=='Finalizada' if page=='Historial' else o['status'] not in ['Finalizada','Cancelada'])]))
    elif page=='Informes': reports(db,client=True)
    elif page=='Certificados':
        heading('Certificados','Documentos autorizados para los equipos de tu empresa.')
        count=0
        for e in db['equipment']:
            certs=[d for d in e['documents'] if d.get('authorized') and d.get('kind')=='Certificado']
            if certs:
                st.subheader(f"{e['code']} · {e['name']}");documents(dict(e,documents=certs),True);count+=len(certs)
        if not count: st.info('Aún no hay certificados autorizados. BASEP los publicará aquí cuando estén disponibles.')
    elif page=='Documentos':
        heading('Documentos','Manuales, certificados y documentación autorizada por BASEP.')
        for e in db['equipment']:
            with st.expander(f"{e['code']} · {e['name']}",expanded=True): documents(e,True)
        st.caption('Los informes de servicio autorizados se encuentran en Informes. Los certificados deben adjuntarse como documentos; el prototipo no los emite.')
