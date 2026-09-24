"""Datos sintéticos, identificadores estables y relaciones explícitas."""
from datetime import date, datetime, timedelta

TYPES = ['Calibración', 'Mantenimiento preventivo', 'Mantenimiento correctivo', 'Inspección', 'Verificación']
STATES = ['Creada', 'Enviada', 'Recibida', 'Vista', 'Aceptada', 'En desplazamiento', 'Check-in', 'En ejecución', 'Pausada', 'Check-out', 'Finalizada', 'Cancelada']

def seed():
    today = date.today()
    clients = []
    for i, (name, sector, contact) in enumerate([
        ('Hospital San Gabriel', 'Salud', 'Laura Rojas'), ('Laboratorio NovaLab', 'Laboratorio', 'Camilo Pérez'),
        ('Industrias Andina', 'Industria', 'Andrés Ruiz'), ('Universidad del Centro', 'Educación', 'Paula Torres'),
        ('Alimentos del Valle', 'Alimentos', 'Diana López')], 1):
        clients.append(dict(id=f'C{i:03}', name=name, sector=sector, nit=f'90012345{i}-1', contact=contact,
            phone=f'300555010{i}', email=f'contacto{i}@example.com', address=f'Carrera {12+i*3} # {40+i}-20',
            city='Bogotá', notes='Cliente ficticio para demostración.'))
    sites = [dict(id=f'S{i+1:03}', client_id=c['id'], name='Sede principal', address=c['address'], city='Bogotá') for i,c in enumerate(clients)]
    sites.append(dict(id='S006',client_id='C001',name='Sede Norte',address='Calle 145 # 18-30',city='Bogotá'))
    techs = [dict(id=f'T{i+1:03}',name=n,phone=f'310555020{i}',email=f'tecnico{i}@example.com',
        specialty=['Metrología','Electromecánica','Biomédica'][i%3],status=['Disponible','En servicio','En desplazamiento','Pausa'][i%4],
        lat=4.62+i*.012,lon=-74.10+i*.006,device=['Samsung A54','Motorola G84','iPhone 13'][i%3],battery=92-i*7)
        for i,n in enumerate(['Daniel Martínez','Sofía Ramírez','Carlos Méndez','Valentina Castro','Juan Herrera','Natalia Gómez','Felipe Vargas','Andrea Moreno'])]
    equipment=[]
    for i in range(20):
        c=clients[i%5]
        equipment.append(dict(id=f'E{i+1:03}',name=['Balanza analítica','Termohigrómetro','Manómetro digital','Centrífuga'][i//5],
            code=f'BASEP-EQ-{i+1:03}',serial=f'SN-2024-{1200+i}',brand=['Ohaus','Testo','WIKA','Hettich'][i//5],
            model=['AX224','608-H1','CPG1500','EBA 200'][i//5],category=['Masa','Temperatura','Presión','Laboratorio'][i//5],
            location=f'Área técnica {i//5+1}',client_id=c['id'],site_id=sites[i%5]['id'],
            status=['Activo','Activo','Próximo a vencer','Vencido','Fuera de servicio'][i%5],
            last_calibration=str(today-timedelta(days=330+i)),last_maintenance=str(today-timedelta(days=60+i)),
            next_calibration=str(today+timedelta(days=30-i*2)),next_review=str(today+timedelta(days=60-i)),notes='Equipo de demostración.',photos=[],documents=[]))
    orders=[]
    for i in range(18):
        e=equipment[i]
        status=['Enviada','Aceptada','En ejecución','Finalizada','Creada','Finalizada'][i%6]
        d=today+timedelta(days=(i%9)-4)
        if status=='Finalizada': d=today-timedelta(days=1+i%4)
        if status=='En ejecución': d=today
        event_day=min(d,today)
        timeline=[dict(state='Creada',at=f'{event_day}T07:00:00',actor='Marcela')]
        if status!='Creada': timeline.append(dict(state='Enviada',at=f'{event_day}T07:10:00',actor='Marcela'))
        if status in ['Aceptada','En ejecución','Finalizada']:
            for s,t in [('Recibida','07:11'),('Vista','07:12'),('Aceptada','07:13')]: timeline.append(dict(state=s,at=f'{event_day}T{t}:00',actor=techs[i%8]['name']))
        if status in ['En ejecución','Finalizada']:
            for s,t in [('En desplazamiento','08:00'),('Check-in','08:45'),('En ejecución','09:00')]: timeline.append(dict(state=s,at=f'{d}T{t}:00',actor=techs[i%8]['name']))
        if status=='Finalizada':
            for s,t in [('Check-out','10:45'),('Finalizada','11:00')]: timeline.append(dict(state=s,at=f'{d}T{t}:00',actor=techs[i%8]['name']))
        orders.append(dict(id=f'OT-{1001+i}',client_id=e['client_id'],site_id=e['site_id'],equipment_id=e['id'],tech_id=techs[i%8]['id'],
            type=TYPES[i%5],date=str(d),time='09:00',duration=120,priority=['Media','Alta','Baja'][i%3],
            address=clients[i%5]['address'],description='Verificar funcionamiento y registrar resultados del equipo.',status=status,ticket_id=None,
            timeline=timeline,photos=[],documents=[],notes=[],parts=[],published=status=='Finalizada',
            form=dict(condition='Operativo',reference=100,measured=100.02,error=.02,tolerance=.1,result='Dentro de tolerancia',work='Verificación y ajuste general',components='Sensores y conexiones',final_condition='Operativo',observations='Servicio de demostración.') if status=='Finalizada' else {},
            closure=dict(receiver=clients[i%5]['contact'],position='Coordinación técnica',quality=5,punctuality=4,attention=5,comments='Servicio satisfactorio.',signature=clients[i%5]['contact']) if status=='Finalizada' else {}))
    tickets=[dict(id=f'TK-{2001+i}',client_id=equipment[i]['client_id'],equipment_id=equipment[i]['id'],created=(datetime.now()-timedelta(hours=4+i*3)).isoformat(timespec='seconds'),
        type=TYPES[i%5],priority=['Alta','Media'][i%2],description='Solicitamos revisión y programación del equipo.',contact=clients[i%5]['contact'],
        status='Recibido' if i%2==0 else 'En revisión',responsible='Marcela',photos=[],order_id=None,first_response=None,closed_at=None) for i in range(10)]
    inventory=[dict(id=f'R{i+1:03}',name=n,category=c,stock=s,minimum=m,location='Bodega principal') for i,(n,c,s,m) in enumerate([
        ('Sensor de temperatura PT100','Sensores',12,4),('Fusible 5 A','Eléctrico',3,5),('Kit de sellos','Mecánico',8,3),('Cable de alimentación','Eléctrico',15,5),('Rodamiento 6202','Mecánico',2,4),('Solución de limpieza','Consumibles',20,8)])]
    return dict(schema_version=1,clients=clients,sites=sites,equipment=equipment,techs=techs,orders=orders,tickets=tickets,inventory=inventory,
        movements=[],part_requests=[dict(id='REP-001',order_id='OT-1003',tech_id='T003',equipment_id='E003',part_id='R002',quantity=2,reason='Reemplazo preventivo',priority='Alta',status='Pendiente')])
