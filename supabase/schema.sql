-- Copia de referencia generada desde migrations/. Aplicar migraciones una sola vez.
-- BASEP: esquema privado. Sin datos demo, sin políticas públicas.
begin;
create table public.basep_revision (id integer primary key check(id=1), revision bigint not null default 0);
insert into public.basep_revision(id) values (1);
alter table public.basep_revision enable row level security;
revoke all on public.basep_revision from anon, authenticated;
grant all on public.basep_revision to service_role;
create function public.basep_updated_at() returns trigger language plpgsql set search_path='' as $$
begin new.updated_at=clock_timestamp(); return new; end; $$;
create function public.basep_bump_revision() returns trigger language plpgsql set search_path='' as $$
begin update public.basep_revision set revision=revision+1 where id=1; return null; end; $$;

create table public.clientes (
 id uuid primary key default gen_random_uuid(),
 app_id text not null unique default gen_random_uuid()::text,
 razon_social text not null, nit text not null unique, contacto text default '', telefono text default '', email text default '', direccion text default '', ciudad text default '', observaciones text default '', activo boolean not null default true,
 data jsonb not null default '{}'::jsonb,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
alter table public.clientes enable row level security;
revoke all on public.clientes from anon, authenticated;
grant all on public.clientes to service_role;
create trigger clientes_updated before update on public.clientes for each row execute function public.basep_updated_at();
create trigger clientes_revision after insert or update or delete on public.clientes for each statement execute function public.basep_bump_revision();

create table public.sedes (
 id uuid primary key default gen_random_uuid(),
 app_id text not null unique default gen_random_uuid()::text,
 cliente_id uuid not null references public.clientes(id), nombre text not null, direccion text default '', ciudad text default '', latitud double precision check(latitud between -90 and 90), longitud double precision check(longitud between -180 and 180), contacto text default '', telefono text default '', activo boolean not null default true, unique(id,cliente_id),
 data jsonb not null default '{}'::jsonb,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
alter table public.sedes enable row level security;
revoke all on public.sedes from anon, authenticated;
grant all on public.sedes to service_role;
create trigger sedes_updated before update on public.sedes for each row execute function public.basep_updated_at();
create trigger sedes_revision after insert or update or delete on public.sedes for each statement execute function public.basep_bump_revision();
create index sedes_cliente_id_idx on public.sedes(cliente_id);

create table public.tecnicos (
 id uuid primary key default gen_random_uuid(),
 app_id text not null unique default gen_random_uuid()::text,
 nombre text not null, documento text default '', telefono text default '', email text default '', cargo text default '', estado text not null default 'Disponible', activo boolean not null default true,
 data jsonb not null default '{}'::jsonb,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
alter table public.tecnicos enable row level security;
revoke all on public.tecnicos from anon, authenticated;
grant all on public.tecnicos to service_role;
create trigger tecnicos_updated before update on public.tecnicos for each row execute function public.basep_updated_at();
create trigger tecnicos_revision after insert or update or delete on public.tecnicos for each statement execute function public.basep_bump_revision();
create index tecnicos_estado_idx on public.tecnicos(estado);

create table public.equipos (
 id uuid primary key default gen_random_uuid(),
 app_id text not null unique default gen_random_uuid()::text,
 cliente_id uuid not null references public.clientes(id), sede_id uuid not null, codigo_interno text not null unique, nombre text not null, serial text default '', marca text default '', modelo text default '', categoria text default '', ubicacion text default '', estado text not null default 'Activo', ultima_calibracion date, proxima_calibracion date, ultimo_mantenimiento date, proximo_mantenimiento date, observaciones text default '', unique(id,cliente_id), unique(id,sede_id,cliente_id), foreign key(sede_id,cliente_id) references public.sedes(id,cliente_id),
 data jsonb not null default '{}'::jsonb,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
alter table public.equipos enable row level security;
revoke all on public.equipos from anon, authenticated;
grant all on public.equipos to service_role;
create trigger equipos_updated before update on public.equipos for each row execute function public.basep_updated_at();
create trigger equipos_revision after insert or update or delete on public.equipos for each statement execute function public.basep_bump_revision();
create index equipos_cliente_id_idx on public.equipos(cliente_id);
create index equipos_sede_id_idx on public.equipos(sede_id);
create index equipos_estado_idx on public.equipos(estado);

create table public.solicitudes (
 id uuid primary key default gen_random_uuid(),
 app_id text not null unique default gen_random_uuid()::text,
 numero_ticket text not null unique, cliente_id uuid not null references public.clientes(id), equipo_id uuid, fecha timestamptz not null default now(), tipo_necesidad text not null, prioridad text not null default 'Media', descripcion text not null, estado text not null default 'Recibido', contacto text default '', foreign key(equipo_id,cliente_id) references public.equipos(id,cliente_id), unique(id,cliente_id),
 data jsonb not null default '{}'::jsonb,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
alter table public.solicitudes enable row level security;
revoke all on public.solicitudes from anon, authenticated;
grant all on public.solicitudes to service_role;
create trigger solicitudes_updated before update on public.solicitudes for each row execute function public.basep_updated_at();
create trigger solicitudes_revision after insert or update or delete on public.solicitudes for each statement execute function public.basep_bump_revision();
create index solicitudes_cliente_id_idx on public.solicitudes(cliente_id);
create index solicitudes_equipo_id_idx on public.solicitudes(equipo_id);
create index solicitudes_estado_idx on public.solicitudes(estado);

create table public.ordenes_servicio (
 id uuid primary key default gen_random_uuid(),
 app_id text not null unique default gen_random_uuid()::text,
 numero_ot text not null unique, solicitud_id uuid, cliente_id uuid not null references public.clientes(id), sede_id uuid not null, equipo_id uuid not null, tecnico_id uuid not null references public.tecnicos(id), tipo_servicio text not null, prioridad text not null default 'Media', fecha_programada date not null, hora_programada time not null, duracion_estimada_minutos integer not null check(duracion_estimada_minutos > 0), direccion text default '', descripcion text default '', estado text not null default 'Creada', checkin_at timestamptz, checkout_at timestamptz, inicio_servicio_at timestamptz, fin_servicio_at timestamptz, observaciones text default '', foreign key(equipo_id,sede_id,cliente_id) references public.equipos(id,sede_id,cliente_id), foreign key(solicitud_id,cliente_id) references public.solicitudes(id,cliente_id), unique(id,cliente_id),
 data jsonb not null default '{}'::jsonb,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
alter table public.ordenes_servicio enable row level security;
revoke all on public.ordenes_servicio from anon, authenticated;
grant all on public.ordenes_servicio to service_role;
create trigger ordenes_servicio_updated before update on public.ordenes_servicio for each row execute function public.basep_updated_at();
create trigger ordenes_servicio_revision after insert or update or delete on public.ordenes_servicio for each statement execute function public.basep_bump_revision();
create index ordenes_servicio_solicitud_id_idx on public.ordenes_servicio(solicitud_id);
create index ordenes_servicio_cliente_id_idx on public.ordenes_servicio(cliente_id);
create index ordenes_servicio_sede_id_idx on public.ordenes_servicio(sede_id);
create index ordenes_servicio_equipo_id_idx on public.ordenes_servicio(equipo_id);
create index ordenes_servicio_tecnico_id_idx on public.ordenes_servicio(tecnico_id);
create index ordenes_servicio_estado_idx on public.ordenes_servicio(estado);

create table public.eventos_orden (
 id uuid primary key default gen_random_uuid(),
 app_id text not null unique default gen_random_uuid()::text,
 orden_id uuid not null references public.ordenes_servicio(id), tipo_evento text not null, fecha_hora timestamptz not null default now(), descripcion text default '', bateria_porcentaje integer check(bateria_porcentaje between 0 and 100), tipo_conexion text, latitud double precision check(latitud between -90 and 90), longitud double precision check(longitud between -180 and 180),
 data jsonb not null default '{}'::jsonb,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
alter table public.eventos_orden enable row level security;
revoke all on public.eventos_orden from anon, authenticated;
grant all on public.eventos_orden to service_role;
create trigger eventos_orden_updated before update on public.eventos_orden for each row execute function public.basep_updated_at();
create trigger eventos_orden_revision after insert or update or delete on public.eventos_orden for each statement execute function public.basep_bump_revision();
create index eventos_orden_orden_id_idx on public.eventos_orden(orden_id);

create table public.evidencias (
 id uuid primary key default gen_random_uuid(),
 app_id text not null unique default gen_random_uuid()::text,
 orden_id uuid references public.ordenes_servicio(id), equipo_id uuid references public.equipos(id), solicitud_id uuid references public.solicitudes(id), tipo text not null, nombre_archivo text not null, ruta_storage text not null unique, bucket text not null default 'basep-evidencias', descripcion text default '', check(num_nonnulls(orden_id,equipo_id,solicitud_id)=1),
 data jsonb not null default '{}'::jsonb,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
alter table public.evidencias enable row level security;
revoke all on public.evidencias from anon, authenticated;
grant all on public.evidencias to service_role;
create trigger evidencias_updated before update on public.evidencias for each row execute function public.basep_updated_at();
create trigger evidencias_revision after insert or update or delete on public.evidencias for each statement execute function public.basep_bump_revision();
create index evidencias_orden_id_idx on public.evidencias(orden_id);
create index evidencias_equipo_id_idx on public.evidencias(equipo_id);
create index evidencias_solicitud_id_idx on public.evidencias(solicitud_id);

create table public.inventario (
 id uuid primary key default gen_random_uuid(),
 app_id text not null unique default gen_random_uuid()::text,
 nombre text not null, categoria text default '', stock integer not null default 0 check(stock>=0), minimo integer not null default 0 check(minimo>=0), ubicacion text default '' ,
 data jsonb not null default '{}'::jsonb,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
alter table public.inventario enable row level security;
revoke all on public.inventario from anon, authenticated;
grant all on public.inventario to service_role;
create trigger inventario_updated before update on public.inventario for each row execute function public.basep_updated_at();
create trigger inventario_revision after insert or update or delete on public.inventario for each statement execute function public.basep_bump_revision();

create table public.movimientos_inventario (
 id uuid primary key default gen_random_uuid(),
 app_id text not null unique default gen_random_uuid()::text,
 repuesto_id uuid not null references public.inventario(id), orden_id uuid references public.ordenes_servicio(id), tipo text not null, cantidad integer not null check(cantidad>0), fecha_hora timestamptz not null default now(),
 data jsonb not null default '{}'::jsonb,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
alter table public.movimientos_inventario enable row level security;
revoke all on public.movimientos_inventario from anon, authenticated;
grant all on public.movimientos_inventario to service_role;
create trigger movimientos_inventario_updated before update on public.movimientos_inventario for each row execute function public.basep_updated_at();
create trigger movimientos_inventario_revision after insert or update or delete on public.movimientos_inventario for each statement execute function public.basep_bump_revision();
create index movimientos_inventario_repuesto_id_idx on public.movimientos_inventario(repuesto_id);
create index movimientos_inventario_orden_id_idx on public.movimientos_inventario(orden_id);

create table public.solicitudes_repuestos (
 id uuid primary key default gen_random_uuid(),
 app_id text not null unique default gen_random_uuid()::text,
 orden_id uuid not null references public.ordenes_servicio(id), tecnico_id uuid not null references public.tecnicos(id), equipo_id uuid not null references public.equipos(id), repuesto_id uuid references public.inventario(id), descripcion text not null, cantidad integer not null check(cantidad>0), prioridad text default 'Media', estado text not null default 'Pendiente', observaciones text default '' ,
 data jsonb not null default '{}'::jsonb,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
alter table public.solicitudes_repuestos enable row level security;
revoke all on public.solicitudes_repuestos from anon, authenticated;
grant all on public.solicitudes_repuestos to service_role;
create trigger solicitudes_repuestos_updated before update on public.solicitudes_repuestos for each row execute function public.basep_updated_at();
create trigger solicitudes_repuestos_revision after insert or update or delete on public.solicitudes_repuestos for each statement execute function public.basep_bump_revision();
create index solicitudes_repuestos_orden_id_idx on public.solicitudes_repuestos(orden_id);
create index solicitudes_repuestos_tecnico_id_idx on public.solicitudes_repuestos(tecnico_id);
create index solicitudes_repuestos_equipo_id_idx on public.solicitudes_repuestos(equipo_id);
create index solicitudes_repuestos_repuesto_id_idx on public.solicitudes_repuestos(repuesto_id);
create index solicitudes_repuestos_estado_idx on public.solicitudes_repuestos(estado);

create table public.satisfaccion_cliente (
 id uuid primary key default gen_random_uuid(),
 app_id text not null unique default gen_random_uuid()::text,
 orden_id uuid not null unique, cliente_id uuid not null references public.clientes(id), calificacion_general integer not null check(calificacion_general between 1 and 5), puntualidad integer not null check(puntualidad between 1 and 5), calidad_servicio integer not null check(calidad_servicio between 1 and 5), atencion_tecnico integer not null check(atencion_tecnico between 1 and 5), comentario text default '', nombre_persona_recibe text not null, foreign key(orden_id,cliente_id) references public.ordenes_servicio(id,cliente_id),
 data jsonb not null default '{}'::jsonb,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
alter table public.satisfaccion_cliente enable row level security;
revoke all on public.satisfaccion_cliente from anon, authenticated;
grant all on public.satisfaccion_cliente to service_role;
create trigger satisfaccion_cliente_updated before update on public.satisfaccion_cliente for each row execute function public.basep_updated_at();
create trigger satisfaccion_cliente_revision after insert or update or delete on public.satisfaccion_cliente for each statement execute function public.basep_bump_revision();
create index satisfaccion_cliente_orden_id_idx on public.satisfaccion_cliente(orden_id);
create index satisfaccion_cliente_cliente_id_idx on public.satisfaccion_cliente(cliente_id);

create index ordenes_fecha_idx on public.ordenes_servicio(fecha_programada,tecnico_id);
create index eventos_fecha_idx on public.eventos_orden(orden_id,fecha_hora);
create unique index orden_solicitud_activa_idx on public.ordenes_servicio(solicitud_id) where solicitud_id is not null and estado <> 'Cancelada';
create function public.basep_snapshot() returns jsonb language sql stable security invoker set search_path='' as $$
select jsonb_build_object('revision',(select revision from public.basep_revision where id=1),'tables',jsonb_build_object(
'clientes',coalesce((select jsonb_agg(t order by created_at,id) from public.clientes t),'[]'::jsonb),
'sedes',coalesce((select jsonb_agg(t order by created_at,id) from public.sedes t),'[]'::jsonb),
'tecnicos',coalesce((select jsonb_agg(t order by created_at,id) from public.tecnicos t),'[]'::jsonb),
'equipos',coalesce((select jsonb_agg(t order by created_at,id) from public.equipos t),'[]'::jsonb),
'solicitudes',coalesce((select jsonb_agg(t order by created_at,id) from public.solicitudes t),'[]'::jsonb),
'ordenes_servicio',coalesce((select jsonb_agg(t order by created_at,id) from public.ordenes_servicio t),'[]'::jsonb),
'eventos_orden',coalesce((select jsonb_agg(t order by created_at,id) from public.eventos_orden t),'[]'::jsonb),
'evidencias',coalesce((select jsonb_agg(t order by created_at,id) from public.evidencias t),'[]'::jsonb),
'inventario',coalesce((select jsonb_agg(t order by created_at,id) from public.inventario t),'[]'::jsonb),
'movimientos_inventario',coalesce((select jsonb_agg(t order by created_at,id) from public.movimientos_inventario t),'[]'::jsonb),
'solicitudes_repuestos',coalesce((select jsonb_agg(t order by created_at,id) from public.solicitudes_repuestos t),'[]'::jsonb),
'satisfaccion_cliente',coalesce((select jsonb_agg(t order by created_at,id) from public.satisfaccion_cliente t),'[]'::jsonb)
)); $$;

-- One transaction for the order, its ticket, events, closure and equipment.
-- Optimistic version check prevents a stale browser/session overwriting another.
create function public.basep_commit(expected_revision bigint, changes jsonb)
returns bigint language plpgsql security invoker set search_path='' as $$
declare current_revision bigint; item jsonb; row_data jsonb; tab text; cols text; vals text; updates text;
begin
 select revision into current_revision from public.basep_revision where id=1 for update;
 if current_revision <> expected_revision then raise exception 'BASEP_CONFLICT' using errcode='40001'; end if;
 if jsonb_typeof(changes) <> 'array' then raise exception 'Invalid changes'; end if;
 for item in select value from jsonb_array_elements(changes) loop
  tab=item->>'table'; row_data=item->'row';
  if not (tab=any(ARRAY['clientes','sedes','tecnicos','equipos','solicitudes','ordenes_servicio','eventos_orden','evidencias','inventario','movimientos_inventario','solicitudes_repuestos','satisfaccion_cliente'])) then raise exception 'Invalid table'; end if;
  if jsonb_typeof(row_data) <> 'object' or not row_data ? 'id' then raise exception 'Invalid row'; end if;
  if exists(select 1 from jsonb_object_keys(row_data) k where k in ('created_at','updated_at')) then raise exception 'Managed timestamps'; end if;
  select string_agg(format('%I',k),',' order by k), string_agg(format('r.%I',k),',' order by k),
   string_agg(format('%I=excluded.%I',k,k),',' order by k) filter(where k<>'id')
   into cols,vals,updates from jsonb_object_keys(row_data) k;
  execute format('insert into public.%I (%s) select %s from jsonb_populate_record(null::public.%I,$1) r on conflict(id) do update set %s',tab,cols,vals,tab,updates) using row_data;
 end loop;
 return (select revision from public.basep_revision where id=1);
end; $$;
revoke all on function public.basep_updated_at(), public.basep_bump_revision(), public.basep_snapshot(), public.basep_commit(bigint,jsonb) from public, anon, authenticated;
grant execute on function public.basep_updated_at(), public.basep_bump_revision(), public.basep_snapshot(), public.basep_commit(bigint,jsonb) to service_role;
commit;

-- Buckets privados. Acceso solamente desde el servidor autorizado.
begin;
insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types) values
 ('basep-evidencias','basep-evidencias',false,10485760,ARRAY['image/jpeg','image/png','application/pdf']),
 ('basep-documentos','basep-documentos',false,10485760,ARRAY['application/pdf','text/html','image/png','image/jpeg']),
 ('basep-firmas','basep-firmas',false,10485760,ARRAY['image/png','image/jpeg'])
on conflict(id) do nothing;
commit;
