"""Informe HTML autónomo imprimible; no emite certificados de calibración."""
from html import escape
import base64
from services.store import get,ROOT
from services.files import path_for

def report_html(db,o):
    def esc(v): return escape(str(v))
    def name(t,k): return get(db,t,k).get('name','—')
    logo=base64.b64encode((ROOT/'assets'/'logo_basep_ui.png').read_bytes()).decode()
    photos=''
    for p in o['photos']:
        path=path_for(p)
        if path.exists():
            mime='image/png' if path.suffix=='.png' else 'image/jpeg'
            photos+=f'<figure><img style="max-width:280px;max-height:230px" src="data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"><figcaption>{esc(p["name"])}</figcaption></figure>'
    rows={'Orden':o['id'],'Cliente':name('clients',o['client_id']),'Sede':name('sites',o['site_id']),
          'Equipo':name('equipment',o['equipment_id']),'Serial':get(db,'equipment',o['equipment_id']).get('serial',''),
          'Técnico':name('techs',o['tech_id']),'Fecha':o['date'],'Servicio':o['type'],'Actividad':o['description'],'Estado':o['status']}
    arrival=next((x['at'] for x in o['timeline'] if x['state']=='Check-in'),'—')
    departure=next((x['at'] for x in reversed(o['timeline']) if x['state']=='Check-out'),'—')
    from datetime import datetime
    duration=round((datetime.fromisoformat(departure)-datetime.fromisoformat(arrival)).total_seconds()/60,1) if arrival!='—' and departure!='—' else '—'
    rows.update({'Llegada':arrival,'Salida':departure,'Duración (min)':duration})
    form_names={'condition':'Condición inicial','reference':'Referencia','measured':'Medición','error':'Error','tolerance':'Tolerancia','result':'Resultado','work':'Trabajo realizado','components':'Componentes','final_condition':'Condición final','observations':'Observaciones'}
    body=''.join(f'<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>' for k,v in rows.items())
    result=''.join(f'<tr><th>{esc(form_names.get(k,k))}</th><td>{esc(v)}</td></tr>' for k,v in o['form'].items())
    closure=o['closure']
    reception=''.join(f'<p><b>{esc(k)}:</b> {esc(closure.get(v,"—"))}</p>' for k,v in [('Recibe','receiver'),('Cargo','position'),('Calidad / 5','quality'),('Puntualidad / 5','punctuality'),('Atención / 5','attention'),('Comentarios','comments')])
    parts=[f'{get(db,"inventory",r["part_id"]).get("name",r["part_id"])} × {r["quantity"]} — {r["reason"]}' for r in db['part_requests'] if r['order_id']==o['id']]
    return f'''<!doctype html><html lang="es"><meta charset="utf-8"><title>BASEP {esc(o['id'])}</title>
    <style>body{{font:14px Arial;color:#20332f;max-width:850px;margin:35px auto;padding:25px}}header{{display:flex;align-items:center;justify-content:space-between;border-bottom:4px solid #008cbb}}header img{{width:150px}}h1,h2{{color:#07558c}}table{{border-collapse:collapse;width:100%}}th,td{{text-align:left;padding:9px;border-bottom:1px solid #ddd}}th{{width:30%}}footer{{margin-top:30px;color:#637684}}figure{{display:inline-block;margin:8px}}@media print{{body{{margin:0}}button{{display:none}}}}</style>
    <header><img src="data:image/png;base64,{logo}"><div><h1>Informe de servicio</h1><p>{esc(o['id'])} · BASEP</p></div></header>
    <p>PROTOTIPO · Datos de demostración · No constituye certificado metrológico</p><table>{body}</table>
    <h2>Resultados técnicos</h2><table>{result}</table><h2>Evidencias</h2>{photos or '<p>Sin fotografías adjuntas.</p>'}
    <h2>Novedades y repuestos</h2><p>{esc('; '.join(x['text'] for x in o['notes']) or 'Sin novedades')}</p><p>{esc('; '.join(parts) or 'Sin repuestos solicitados')}</p>
    <h2>Recepción y satisfacción</h2>{reception}<p style="font:italic 26px cursive;border-bottom:1px solid #aaa;padding:20px">{esc(closure.get('signature','Pendiente'))}</p><small>Firma simulada mediante nombre escrito.</small>
    <footer>BASEP · Ingeniería a su Servicio · Informe generado desde el prototipo local. Para PDF: imprimir y guardar como PDF desde el navegador.</footer></html>'''
