-- Buckets privados. Acceso solamente desde el servidor autorizado.
begin;
insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types) values
 ('basep-evidencias','basep-evidencias',false,10485760,ARRAY['image/jpeg','image/png','application/pdf']),
 ('basep-documentos','basep-documentos',false,10485760,ARRAY['application/pdf','text/html','image/png','image/jpeg']),
 ('basep-firmas','basep-firmas',false,10485760,ARRAY['image/png','image/jpeg'])
on conflict(id) do nothing;
commit;
