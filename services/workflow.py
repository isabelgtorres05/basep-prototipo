from services.store import mutate,get,now,next_id

NEXT={'Creada':['Enviada','Cancelada'],'Enviada':['Recibida','Cancelada'],'Recibida':['Vista','Cancelada'],
      'Vista':['Aceptada','Cancelada'],'Aceptada':['En desplazamiento','Cancelada'],'En desplazamiento':['Check-in','Cancelada'],
      'Check-in':['En ejecución'],'En ejecución':['Pausada','Check-out'],'Pausada':['En ejecución'],
      'Check-out':['Finalizada'],'Finalizada':[],'Cancelada':[]}
def transition(order_id,state,actor):
    def run(db):
        o=get(db,'orders',order_id)
        if state not in NEXT.get(o.get('status'),[]): raise ValueError('La transición ya no está disponible. Actualiza la pantalla.')
        if state in ['Check-out','Finalizada'] and (not o['form'] or not o['closure'].get('signature')):
            raise ValueError('Guarda el formulario y la recepción con firma antes del check-out.')
        o['status']=state; o['timeline'].append(dict(state=state,at=now(),actor=actor))
        if o.get('ticket_id'):
            t=get(db,'tickets',o['ticket_id'])
            t['status']='Finalizado' if state=='Finalizada' else 'En ejecución' if state in ['Check-in','En ejecución','Pausada','Check-out'] else 'En revisión' if state=='Cancelada' else 'Programado'
            if state=='Finalizada': t['closed_at']=now()
            if state=='Cancelada': t['order_id']=None
        if state=='Finalizada':
            e=get(db,'equipment',o['equipment_id'])
            if o['type']=='Calibración': e['last_calibration']=now()[:10]
            if 'Mantenimiento' in o['type']: e['last_maintenance']=now()[:10]
    mutate(run)
def create_order(record,ticket_id=None):
    def run(db):
        if ticket_id and get(db,'tickets',ticket_id).get('order_id'): raise ValueError('Esta solicitud ya tiene una orden.')
        e=get(db,'equipment',record['equipment_id'])
        if e.get('client_id')!=record['client_id']: raise ValueError('El equipo no pertenece al cliente.')
        if not get(db,'techs',record['tech_id']): raise ValueError('Selecciona un técnico.')
        record.update(id=next_id(db,'orders','OT-'),site_id=e['site_id'],status='Creada',ticket_id=ticket_id,
            timeline=[dict(state='Creada',at=now(),actor='Marcela')],photos=[],documents=[],notes=[],parts=[],form={},closure={},published=False)
        db['orders'].append(record)
        if ticket_id:
            get(db,'tickets',ticket_id).update(order_id=record['id'],status='Programado',first_response=now())
        return record['id']
    return mutate(run)
def stock_move(part_id,kind,quantity,order_id=None):
    def run(db):
        part=get(db,'inventory',part_id)
        delta=quantity if kind=='Entrada' else -quantity
        if quantity<=0 or part['stock']+delta<0: raise ValueError('Cantidad inválida o stock insuficiente.')
        if kind=='Consumo en servicio' and not get(db,'orders',order_id): raise ValueError('Selecciona una orden para el consumo.')
        part['stock']+=delta
        db['movements'].append(dict(id=next_id(db,'movements','MOV-'),part_id=part_id,type=kind,quantity=quantity,order_id=order_id,at=now()))
    mutate(run)
