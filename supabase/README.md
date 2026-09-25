# Persistencia privada con Supabase

## Estado
El esquema y los buckets se aplicaron desde SQL Editor el 24 de septiembre de 2026.
Las migraciones `20260924000100` y `20260924000200` son la fuente del esquema.
`schema.sql` es una copia de referencia: no ejecutar ambos métodos sobre la misma base.
No se importaron los datos demo ni se borró el JSON local.

## Conexión del servidor
1. Instalar `requirements.txt` en el entorno Python del servidor.
2. Copiar `.streamlit/secrets.toml.example` a `.streamlit/secrets.toml` y rellenar
   SUPABASE_URL, SUPABASE_KEY y BASEP_ACCESS_PASSWORD. La contraseña debe tener
   al menos 16 caracteres. El archivo real está ignorado por Git.
3. SUPABASE_KEY debe ser una Secret key del servidor o la antigua service_role.
   No usar anon/publishable: las tablas no conceden permisos a esos roles.
4. Ejecutar `python -m streamlit run app.py`. El lanzador Windows usa `.venv`
   si existe. Para Community Cloud, configurar las mismas variables en App settings
   → Secrets; nunca en GitHub. No se han publicado claves ni configurado Cloud automáticamente.

Con ambas credenciales presentes se utiliza Supabase; cualquier fallo detiene la
operación y no escribe silenciosamente en el JSON. Sin credenciales se conserva
el modo demo. Una configuración incompleta muestra un error explícito.

## Seguridad del piloto
RLS está habilitado en todas las tablas. No hay políticas públicas ni privilegios
anon/authenticated. Solo el servidor usa la clave privada. Las funciones RPC son
SECURITY INVOKER y su ejecución se limita a service_role. Los buckets son privados.
La contraseña del piloto protege el acceso antes de cargar datos o archivos.
El selector Marcela/Técnico/Cliente sigue siendo un simulador para participantes
de confianza: no representa permisos separados ni autenticación empresarial.
La contraseña compartida es temporal; no distribuir este piloto a usuarios externos.

## Datos y transacciones
Las diez tablas solicitadas usan UUID. `app_id` conserva las referencias que usa
la interfaz; `data` conserva campos adicionales del prototipo (formulario técnico,
firma escrita, notas y estado de publicación). Los campos de negocio normalizados
tienen prioridad al leer; eventos, evidencias y satisfacción tienen tablas propias.
Inventario y movimientos también se guardan para mantener el flujo existente.
`basep_revision` permite detectar escrituras simultáneas. Cada mutación completa
se envía a `basep_commit` en una transacción: cambios de orden, ticket, equipo,
eventos y satisfacción se confirman juntos. Ante conflicto, actualizar y repetir.
La lectura RPC es consistente y no está truncada al límite habitual de 1000 filas.
Este adaptador aún carga el conjunto completo del piloto; una operación a gran
escala requerirá paginación y consultas por módulo.

## Storage
- basep-evidencias: fotografías de órdenes, equipos y solicitudes.
- basep-documentos: manuales, certificados, informes y documentos.
- basep-firmas: reservado para futuras firmas como imagen.
Rutas: `orders|equipment|tickets/<app_id>/<uuid>.<ext>`; límite 10 MB.
Los archivos se descargan con la clave en el servidor, sin enlaces públicos.
La caché local `data/.cache` es descartable e ignorada por Git.
Las firmas actuales siguen siendo nombres escritos en la recepción; no se
convirtieron en firmas biométricas. Los informes HTML conservan la descarga
actual y pueden adjuntarse posteriormente como documentos.

## Migraciones y pruebas
En un proyecto NUEVO: `supabase link` y `supabase db push`, o ejecutar las
migraciones en SQL Editor en orden. En este proyecto ya aplicado por SQL Editor,
antes de usar db push: `supabase migration repair --status applied 20260924000100 20260924000200`.
Requiere login de CLI; no se guardó ningún token de administración en el repositorio.
La CLI no estaba disponible; se usó la sesión autorizada del dashboard.
`python -m unittest discover -s tests -v` prueba el modo demo, navegación vacía,
traducción relacional y conflictos. Estas pruebas fuerzan credenciales vacías y
no escriben en la base remota. La prueba SQL de lectura/escritura se ejecutó con
rollback; quedaron cero clientes de prueba.

## Prueba con Marcela
Entrar con la contraseña del piloto → Clientes: crear cliente (crea sede principal)
→ Técnicos: registrar técnico → Equipos: crear equipo del cliente → Órdenes:
crear y enviar orden asignada. Cerrar y abrir otra sesión: verificar los registros.
En vista Técnico: Recibir → Vista → Aceptar → Desplazamiento → Check-in → Iniciar.
Guardar formulario, cargar fotografía, guardar recepción y firma, Check-out,
Finalizar. Confirmar eventos y fechas en Supabase; descargar evidencia después
de reiniciar el servidor. Esta comprobación se completó localmente: lectura/escritura en Supabase, orden
finalizada con diez eventos y cuatro fechas, evidencia privada descargada en un
nuevo proceso y acceso desde una nueva sesión Streamlit. La orden de prueba
está identificada como VALIDACIÓN y se conserva para revisión. Community Cloud
requiere configurar sus propios secretos; secrets.toml local no se publica.
