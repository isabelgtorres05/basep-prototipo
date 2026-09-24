import uuid
from pathlib import Path
from PIL import Image
from services.store import DATA,mutate,get,now

def upload(files,table,key,field='photos',kind='Fotografía',authorized=False):
    DATA.mkdir(parents=True,exist_ok=True)
    folder=DATA/'uploads';folder.mkdir(exist_ok=True)
    entries=[]
    for f in files:
        if f.size>10*1024*1024: raise ValueError('Cada archivo debe pesar menos de 10 MB.')
        suffix=Path(f.name).suffix.lower()
        if suffix not in ['.png','.jpg','.jpeg','.pdf']: raise ValueError('Solo se admiten JPG, PNG y PDF.')
        if field=='photos':
            if suffix=='.pdf': raise ValueError('Selecciona una imagen.')
            Image.open(f).verify();f.seek(0)
        path=folder/(str(uuid.uuid4())+suffix);path.write_bytes(f.getvalue())
        entries.append(dict(name=f.name,path=str(path.relative_to(DATA)),kind=kind,authorized=authorized,at=now()))
    def run(db): get(db,table,key).setdefault(field,[]).extend(entries)
    mutate(run)
def path_for(item):
    p=(DATA/item['path']).resolve()
    if not p.is_relative_to(DATA.resolve()): raise ValueError('Ruta de archivo inválida.')
    return p
