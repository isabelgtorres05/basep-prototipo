"""Repositorio JSON local. Sustituible por un repositorio PostgreSQL en el futuro."""
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
def now(): return datetime.now().isoformat(timespec='seconds')
def save(db):
    DATA.mkdir(parents=True,exist_ok=True)
    temp=FILE.with_suffix('.tmp')
    temp.write_text(json.dumps(db,ensure_ascii=False,indent=2),encoding='utf-8')
    temp.replace(FILE)
def load():
    with LOCK:
        if not FILE.exists(): save(seed())
        return json.loads(FILE.read_text(encoding='utf-8'))
def mutate(fn):
    with LOCK:
        db=load()
        result=fn(db)
        save(db)
        return deepcopy(result)
def get(db,table,key):
    return next((x for x in db[table] if x['id']==key),{})
def next_id(db,table,prefix):
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
