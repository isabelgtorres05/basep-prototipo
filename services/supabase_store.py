"""Adaptador del contrato de las vistas a tablas relacionales de Supabase.
Los campos de negocio son columnas; data conserva los campos del prototipo.
Cada cambio se confirma en una sola transacción con control de concurrencia.
"""
from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo
import uuid
from services.supabase_client import client

MAP = {
 'clients': ('clientes', {'name':'razon_social','nit':'nit','contact':'contacto','phone':'telefono','email':'email','address':'direccion','city':'ciudad','notes':'observaciones'}),
 'sites': ('sedes', {'client_id':'cliente_id','name':'nombre','address':'direccion','city':'ciudad'}),
 'techs': ('tecnicos', {'name':'nombre','document':'documento','phone':'telefono','email':'email','specialty':'cargo','status':'estado'}),
 'equipment': ('equipos', {'client_id':'cliente_id','site_id':'sede_id','code':'codigo_interno','name':'nombre','serial':'serial','brand':'marca','model':'modelo','category':'categoria','location':'ubicacion','status':'estado','last_calibration':'ultima_calibracion','next_calibration':'proxima_calibracion','last_maintenance':'ultimo_mantenimiento','next_review':'proximo_mantenimiento','notes':'observaciones'}),
 'tickets': ('solicitudes', {'id':'numero_ticket','client_id':'cliente_id','equipment_id':'equipo_id','created':'fecha','type':'tipo_necesidad','priority':'prioridad','description':'descripcion','status':'estado','contact':'contacto'}),
 'orders': ('ordenes_servicio', {'id':'numero_ot','ticket_id':'solicitud_id','client_id':'cliente_id','site_id':'sede_id','equipment_id':'equipo_id','tech_id':'tecnico_id','type':'tipo_servicio','priority':'prioridad','date':'fecha_programada','time':'hora_programada','duration':'duracion_estimada_minutos','address':'direccion','description':'descripcion','status':'estado'}),
 'inventory': ('inventario', {'name':'nombre','category':'categoria','stock':'stock','minimum':'minimo','location':'ubicacion'}),
 'movements': ('movimientos_inventario', {'part_id':'repuesto_id','order_id':'orden_id','type':'tipo','quantity':'cantidad','at':'fecha_hora'}),
 'part_requests': ('solicitudes_repuestos', {'order_id':'orden_id','tech_id':'tecnico_id','equipment_id':'equipo_id','part_id':'repuesto_id','reason':'descripcion','quantity':'cantidad','priority':'prioridad','status':'estado'})
}
REFS={'client_id':'clients','site_id':'sites','equipment_id':'equipment','tech_id':'techs','ticket_id':'tickets','part_id':'inventory','order_id':'orders'}
EVENTS={'Creada':'creada','Enviada':'enviada','Recibida':'recibida','Vista':'vista','Aceptada':'aceptada','En desplazamiento':'en_desplazamiento','Check-in':'check_in','En ejecución':'inicio_servicio','Pausada':'pausa','Check-out':'check_out','Finalizada':'finalizada','Cancelada':'cancelada','Programación actualizada':'programacion_actualizada'}
DEFAULTS={
 'clients':dict(sector='',contact='',phone='',email='',address='',city='',notes=''),
 'techs':dict(document='',specialty='',status='Disponible',lat=0.0,lon=0.0,device='Sin dispositivo',battery=0),
 'equipment':dict(photos=[],documents=[],notes='',last_calibration='',last_maintenance='',next_calibration='',next_review=''),
 'tickets':dict(photos=[],order_id=None,first_response=None,closed_at=None,responsible='Marcela'),
 'orders':dict(timeline=[],photos=[],documents=[],notes=[],parts=[],form={},closure={},published=False,ticket_id=None)
}
class PersistenceError(ValueError): pass
class ConflictError(PersistenceError): pass

def uid(table, key):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'basep:'+table+':'+str(key)))

def timestamp(value):
    if not value: return None
    d=datetime.fromisoformat(value)
    if d.tzinfo is None: d=d.replace(tzinfo=ZoneInfo('America/Bogota'))
    return d.isoformat()

def localtime(value):
    if not value: return value
    d=datetime.fromisoformat(value.replace('Z','+00:00'))
    if d.tzinfo: d=d.astimezone(ZoneInfo('America/Bogota')).replace(tzinfo=None)
    return d.isoformat(timespec='seconds')

def decode(snapshot):
    tables=snapshot['tables']; db={'schema_version':2,'_revision':snapshot['revision']}
    lookup={tab:{r['id']:r['app_id'] for r in tables[name]} for tab,(name,_) in MAP.items()}
    for tab,(name,fields) in MAP.items():
        db[tab]=[]
        for r in tables[name]:
            item=deepcopy(DEFAULTS.get(tab,{})); item.update(r.get('data') or {})
            for field,col in fields.items():
                value=r.get(col)
                if field in REFS: value=lookup[REFS[field]].get(value) if value else None
                elif field in ('created','at'): value=localtime(value)
                elif field=='time' and value: value=value[:5]
                elif value is None: value=''
                item[field]=value
            item.update(id=r['app_id'],_uuid=r['id'])
            if tab in ('orders','equipment','tickets'):
                item['photos']=[]
                if tab!='tickets': item['documents']=[]
            if tab=='orders': item['timeline']=[]
            db[tab].append(item)
    byid={tab:{x['_uuid']:x for x in db[tab]} for tab in MAP}
    for r in sorted(tables['eventos_orden'],key=lambda x:(x['fecha_hora'],(x.get('data') or {}).get('_sequence',0))):
        o=byid['orders'][r['orden_id']]
        ev=deepcopy(r.get('data') or {})
        ev.update(state=next((s for s,k in EVENTS.items() if k==r['tipo_evento']),r['tipo_evento']),at=localtime(r['fecha_hora']),actor=r['descripcion'])
        ev['_event_id']=r['id']
        o['timeline'].append(ev)
    for r in tables['evidencias']:
        tab,col=next((t,c) for t,c in [('orders','orden_id'),('equipment','equipo_id'),('tickets','solicitud_id')] if r.get(c))
        e=deepcopy(r.get('data') or {})
        e.update(name=r['nombre_archivo'],path=r['ruta_storage'],bucket=r['bucket'],kind=r['tipo'],at=e.get('at',localtime(r['created_at'])),authorized=e.get('authorized',False))
        byid[tab][r[col]].setdefault(e.pop('_field','photos'),[]).append(e)
    for r in tables['satisfaccion_cliente']:
        o=byid['orders'][r['orden_id']]
        o['closure'].update(receiver=r['nombre_persona_recibe'],quality=r['calidad_servicio'],punctuality=r['puntualidad'],attention=r['atencion_tecnico'],comments=r['comentario'])
    for o in db['orders']:
        if o.get('ticket_id') and o['status']!='Cancelada':
            next(t for t in db['tickets'] if t['id']==o['ticket_id'])['order_id']=o['id']
    return db

def load():
    try: return decode(client().rpc('basep_snapshot').execute().data)
    except Exception as exc:
        raise PersistenceError('No se pudo leer Supabase. Verifica conexión, clave y migraciones. No se cambió al respaldo local.') from None

def changes(before, after):
    ids={tab:{x['id']:x.get('_uuid',uid(tab,x['id'])) for x in after[tab]} for tab in MAP}
    out=[]
    for tab,(name,fields) in MAP.items():
        old={r['id']:r for r in before[tab]}
        for item in after[tab]:
            if old.get(item['id'])==item: continue
            clean={k:v for k,v in item.items() if not k.startswith('_')}
            row=dict(id=ids[tab][item['id']],app_id=item['id'],data=clean)
            for field,col in fields.items():
                value=item.get(field)
                if field in REFS: value=ids[REFS[field]].get(value) if value else None
                elif field in ('created','at'): value=timestamp(value)
                elif col in ('ultima_calibracion','proxima_calibracion','ultimo_mantenimiento','proximo_mantenimiento'): value=value or None
                row[col]=value
            if tab=='orders':
                for state,col in [('Check-in','checkin_at'),('Check-out','checkout_at'),('En ejecución','inicio_servicio_at'),('Finalizada','fin_servicio_at')]:
                    row[col]=next((timestamp(e['at']) for e in item['timeline'] if e['state']==state),None)
            out.append(dict(table=name,row=row))
    # Children after all parent rows, in the same transaction.
    for tab in ('orders','equipment','tickets'):
        old={r['id']:r for r in before[tab]}
        for item in after[tab]:
            if old.get(item['id'])==item: continue
            parent=ids[tab][item['id']]
            if tab=='orders':
                for i,e in enumerate(item['timeline']):
                    eid=e.get('_event_id') or uid('event',parent+':'+str(i))
                    out.append(dict(table='eventos_orden',row=dict(id=eid,app_id=eid,orden_id=parent,tipo_evento=EVENTS.get(e['state'],e['state']),fecha_hora=timestamp(e['at']),descripcion=e['actor'],data=dict(e,_sequence=i))))
                c=item.get('closure') or {}
                if c.get('receiver'):
                    sid=uid('satisfaction',parent)
                    out.append(dict(table='satisfaccion_cliente',row=dict(id=sid,app_id=sid,orden_id=parent,cliente_id=ids['clients'][item['client_id']],calificacion_general=round((c['quality']+c['punctuality']+c['attention'])/3),puntualidad=c['punctuality'],calidad_servicio=c['quality'],atencion_tecnico=c['attention'],comentario=c.get('comments',''),nombre_persona_recibe=c['receiver'],data=c)))
            for field in ('photos','documents'):
                for e in item.get(field,[]):
                    if not e.get('bucket'): raise PersistenceError('Importa primero los archivos locales a Storage; no se guardan rutas locales en Supabase.')
                    eid=uid('evidence',e['bucket']+'/'+e['path'])
                    out.append(dict(table='evidencias',row=dict(id=eid,app_id=eid,**{dict(orders='orden_id',equipment='equipo_id',tickets='solicitud_id')[tab]:parent},tipo=e['kind'],nombre_archivo=e['name'],ruta_storage=e['path'],bucket=e['bucket'],data=dict(e,_field=field))))
    return out

def commit(before, after):
    patch=changes(before,after)
    if not patch: return
    try: client().rpc('basep_commit',dict(expected_revision=before['_revision'],changes=patch)).execute()
    except Exception as exc:
        if 'BASEP_CONFLICT' in str(exc) or '40001' in str(exc):
            raise ConflictError('Otro usuario cambió los datos. Actualiza la pantalla y vuelve a guardar.') from None
        raise PersistenceError('Supabase no confirmó el cambio. Revisa la conexión y las relaciones; no se guardó en JSON local.') from None
