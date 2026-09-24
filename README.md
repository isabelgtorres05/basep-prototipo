# BASEP · Prototipo funcional V1

## Abrir

Doble clic en `Iniciar_BASEP.bat` y abre http://localhost:8501.

Si necesitas instalar dependencias: `python -m pip install -r requirements.txt`.
Inicio manual: `python -m streamlit run app.py`.

## Recorrido con Marcela

1. Vista Cliente → seleccionar Hospital San Gabriel → Solicitar servicio. Elegir equipo, describir necesidad y enviar. Anotar TK.
2. Vista Marcela → Solicitudes / Tickets → seleccionar TK → crear orden con técnico y fecha. Anotar OT. Enviar tarea desde su detalle.
3. Vista Técnico → seleccionar el asignado → abrir OT → Recibir tarea → Registrar visualización → Aceptar → Desplazamiento → Check-in → Iniciar servicio.
4. Formulario técnico → completar y guardar. En calibración o verificación se calcula error y tolerancia. Adjuntar fotografías, novedades y repuestos.
5. Finalización → guardar receptor, cargo, calificaciones y nombre como firma simulada → Check-out → Finalizar servicio.
6. Marcela → Informes → revisar OT → Autorizar informe en portal cliente. Descargar HTML; imprimir desde el navegador para guardar PDF.
7. Cliente → Informes e Historial. Marcela → Equipos e Indicadores para comprobar la actualización.

## Organización

- `app.py`: arranque y navegación.
- `views/`: pantallas por función.
- `components/`: identidad visual y componentes comunes.
- `services/seed.py`: datos sintéticos iniciales.
- `services/store.py`: repositorio JSON con escritura atómica y bloqueo del proceso.
- `services/workflow.py`: transiciones, conversión de tickets e inventario.
- `services/files.py`: evidencias locales; JPG/PNG/PDF de hasta 10 MB.
- `services/reports.py`: informe HTML autónomo, con logo y fotografías incrustadas.
- `data/basep.json`: información persistente; `data/uploads/`: archivos adjuntos.
- `tests/`: pruebas de flujo y navegación.

El logo real `assets/logo_basep.jpeg` se conserva sin modificar. Los archivos AI y PDF oficiales permanecen intactos.

## Límites y evolución

Sin autenticación real, GPS, offline, sincronización, firma avanzada o QR funcional. La recepción y visualización se registran manualmente para simular el dispositivo. Cambiar de empresa en el selector es una función de demostración. El portal filtra entidades de la empresa elegida, pero este prototipo no sustituye permisos empresariales. Servidor enlazado exclusivamente a 127.0.0.1.

No emite certificados metrológicos ni PDF automáticamente. Descarga informes HTML imprimibles; permite adjuntar certificados existentes en PDF y autorizar su consulta. Los mapas requieren conexión para los mosaicos. Los formularios guardan con sus botones; editar un campo sin guardar no persiste.

Preparado conceptualmente para reemplazar el repositorio por PostgreSQL y exponer casos de uso mediante API. Para offline real serán necesarios UUID de dispositivo, versiones, cola de operaciones, política de conflictos y almacenamiento móvil. No se incluye infraestructura empresarial ni facturación.

La V1 está diseñada para un único proceso local. Para reiniciar los datos, detener el servidor y **hacer una copia de seguridad** de `data/` antes de retirar `data/basep.json`; la siguiente apertura regenerará los datos de demostración.


## Iteración visual V2

- Referencia observada: `assets/referencia_visual_BASEP.png`.
- Logo para interfaz e informes: `assets/logo_basep_ui.png` (810 × 738). Derivado del JPEG oficial, sin reescalar, redibujar ni recolorear. Se retiró la paleta inferior y el fondo exterior; el original permanece intacto.
- Estilos centralizados: `assets/styles.css`; componentes de tarjetas, tablas, badges, iconos, calendario y cabecera en `components/ui.py`.
- Dashboard: KPI, calendario semanal, mapa con coordenadas simuladas, actividad y gráficas.
- La navegación conserva controles accesibles de teclado; su representación visual es un menú sin círculos.
- Técnico: Hoy / Semana / Todos, tarjetas y detalle con acciones grandes. Cliente: acceso simplificado y sección de certificados autorizados.
- Los enlaces del calendario abren el detalle correspondiente. El buscador global filtra datos según la vista seleccionada.
- Limitaciones: tablas y calendario se desplazan horizontalmente en pantallas pequeñas; no hay arrastre de eventos. El mapa requiere internet. El JPEG de origen limita el detalle del logo y no se inventaron píxeles nuevos.

## Despliegue en Streamlit Community Cloud

- Repositorio: `isabelgtorres05/basep-prototipo`.
- Branch: `main`.
- Archivo principal: `app.py` en la raíz.
- Python recomendado: 3.13 (versión usada en las pruebas locales).
- Instalar las dependencias desde `requirements.txt`.
- Se deben conservar las carpetas `.streamlit`, `assets`, `components`, `data`, `services`, `tests` y `views`.
- La dirección del servidor no se fija en la configuración compartida. El iniciador local conserva `127.0.0.1`.
- Los datos JSON y archivos adjuntos del prototipo en Community Cloud pueden perder cambios al reiniciar o desplegar; este repositorio contiene datos de demostración, no una base de datos empresarial.
