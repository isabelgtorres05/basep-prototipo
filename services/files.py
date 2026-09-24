import uuid
import mimetypes
from services.supabase_client import configured,client
from pathlib import Path
from PIL import Image
from services.store import DATA,mutate,get,now

def upload(files,table,key,field='photos',kind='Fotografía',authorized=False):
    DATA.mkdir(parents=True,exist_ok=True)
    folder=DATA/'uploads';folder.mkdir(exist_ok=True)
    entries=[]
    commit_attempted=False
    try:
        for f in files:
            if f.size>10*1024*1024: raise ValueError('Cada archivo debe pesar menos de 10 MB.')
            suffix=Path(f.name).suffix.lower()
            if suffix not in ['.png','.jpg','.jpeg','.pdf']: raise ValueError('Solo se admiten JPG, PNG y PDF.')
            if field=='photos':
                if suffix=='.pdf': raise ValueError('Selecciona una imagen.')
                Image.open(f).verify();f.seek(0)
            if configured():
                bucket='basep-evidencias' if field=='photos' else 'basep-documentos'
                remote_path=f'{table}/{key}/{uuid.uuid4()}{suffix}'
                try:
                    client().storage.from_(bucket).upload(remote_path,f.getvalue(),{'content-type':mimetypes.guess_type(f.name)[0] or 'application/octet-stream','upsert':'false'})
                except Exception:
                    raise ValueError('No se pudo subir la evidencia a Storage privado.') from None
                entries.append(dict(name=f.name,path=remote_path,bucket=bucket,kind=kind,authorized=authorized,at=now()))
            else:
                path=folder/(str(uuid.uuid4())+suffix);path.write_bytes(f.getvalue())
                entries.append(dict(name=f.name,path=str(path.relative_to(DATA)),kind=kind,authorized=authorized,at=now()))
        def run(db): get(db,table,key).setdefault(field,[]).extend(entries)
        commit_attempted=True
        mutate(run)
    except Exception as error:
        from services.supabase_store import ConflictError
        # A transport timeout may occur AFTER a successful commit: keep files.
        if commit_attempted and not isinstance(error,ConflictError):
            raise
        for item in entries:
            if item.get('bucket'):
                try: client().storage.from_(item['bucket']).remove([item['path']])
                except Exception: pass
        raise
def path_for(item):
    if item.get('bucket'):
        if not configured(): raise ValueError('Se requiere Supabase para leer esta evidencia.')
        if item['bucket'] not in ('basep-evidencias','basep-documentos','basep-firmas'):
            raise ValueError('Bucket inválido.')
        # Private server cache, never a public URL; existing views keep their contract.
        import hashlib
        folder=DATA/'.cache';folder.mkdir(parents=True,exist_ok=True)
        token=hashlib.sha256((item['bucket']+'/'+item['path']).encode()).hexdigest()
        p=folder/(token+Path(item['path']).suffix)
        if not p.exists():
            try: p.write_bytes(client().storage.from_(item['bucket']).download(item['path']))
            except Exception: raise ValueError('No se pudo descargar el archivo privado.') from None
        return p
    p=(DATA/item['path']).resolve()
    if not p.is_relative_to(DATA.resolve()): raise ValueError('Ruta de archivo inválida.')
    return p
