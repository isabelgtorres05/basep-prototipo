"""Repositorio: Supabase configurado tiene prioridad; JSON conserva el modo demo."""
from services.supabase_client import configured
import json
import os
import threading
from pathlib import Path
from datetime import datetime
from copy import deepcopy
from services.seed import seed

ROOT=Path(__file__).resolve().parents[1]
DATA=Path(os.environ.get('BASEP_DATA_DIR',str(ROOT/'data')))
FILE=DATA/'basep.json'
LOCK=threading.RLock()
def now():
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo('America/Bogota')).replace(tzinfo=None).isoformat(timespec='seconds')
def save(db):
    if configured():
        raise ValueError("No se permite sobrescribir el respaldo JSON con Supabase activo.")
    DATA.mkdir(parents=True,exist_ok=True)
    temp=FILE.with_suffix('.tmp')
    temp.write_text(json.dumps(db,ensure_ascii=False,indent=2),encoding='utf-8')
    temp.replace(FILE)
def load():
    if configured():
        from services.supabase_store import load as remote_load
        return remote_load()
    with LOCK:
        if not FILE.exists(): save(seed())
        return json.loads(FILE.read_text(encoding='utf-8'))
def mutate(fn):
    with LOCK:
        db=load()
        before=deepcopy(db)
        result=fn(db)
        if configured():
            from services.supabase_store import commit
            commit(before,db)
        else:
            save(db)
        return deepcopy(result)
def get(db,table,key):
    return next((x for x in db[table] if x['id']==key),{})
def next_id(db,table,prefix):
    if configured():
        import uuid
        return prefix+uuid.uuid4().hex[:12].upper()
    return f'{prefix}{max([int(x["id"].removeprefix(prefix)) for x in db[table]],default=0)+1:03}'
def add(table,record,prefix):
    def run(db):
        record['id']=next_id(db,table,prefix); db[table].append(record); return record['id']
    return mutate(run)
def update(table,key,changes):
    def run(db):
        record=get(db,table,key)
        if not record: raise ValueError('Registro no encontrado.')
        record.update(changes)
    mutate(run)
def scoped(db,client_id):
    """La UI del cliente recibe únicamente relaciones de la empresa seleccionada."""
    out=deepcopy(db)
    for table in ['clients','sites','equipment','orders','tickets']:
        out[table]=[x for x in out[table] if (x['id'] if table=='clients' else x['client_id'])==client_id]
    order_ids={x['id'] for x in out['orders']}
    out['part_requests']=[x for x in out['part_requests'] if x['order_id'] in order_ids]
    out['inventory']=[]; out['movements']=[]
    return out
