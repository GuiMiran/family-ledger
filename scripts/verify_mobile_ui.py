"""Synthetic browser interaction evidence only; no live household or OCR claim."""
import json, base64, mimetypes, os, shutil
from urllib.parse import urlsplit
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
from playwright.sync_api import sync_playwright, expect
profile={'family_name':None,'postal_code':None,'preferred_stores':[],'basket':[],'club_memberships':[],'coupons_enabled':False,'max_age_hours':24,'max_budget':None}
parsed={'supermarket_key':'generic','purchase_date':None,'total_amount':None,'total_vat':None,'total_discounts':'0','discount_lines_total':'0','lines':[{'line_number':1,'raw_text':'SYNTHETIC 2.50','description':'Producto sintético de prueba','quantity':'1','unit':'unit','unit_price':'2.50','line_total':'2.50','discount_amount':'0','confidence':0.8}], 'pending_fields':[{'field_path':'purchase_date','confidence':0},{'field_path':'total_amount','confidence':0},{'field_path':'lines[0].unit_price','confidence':0.4}], 'overall_confidence':0.5}
Path(os.environ.get('UI_SCREENSHOT_DIR','/tmp')).mkdir(parents=True,exist_ok=True)
calls=[]; saves=[]
def route_handler(route):
 req=route.request;path=req.url.split('/api/v1/')[1];calls.append(path)
 assert req.headers.get('authorization')=='Bearer synthetic-browser-session'
 if path=='shopping/profile':
  if req.method=='PUT':profile.update(req.post_data_json)
  data=profile
 elif path=='shopping/compare':data={'comparison':{'postal_code':None,'coverage':0,'items':[]},'coverage':[]}
 elif path.startswith('receipts?'):data=[]
 elif path.startswith('inventory?'):data={'projection':'confirmed_purchases_not_consumption_balance','items':[]}
 elif path=='analytics':data={'confirmed_count':0,'confirmed_total':'0.00','pending_count':len(saves)>1}
 elif path=='dashboard':data={'confirmed_count':0,'confirmed_total':'0.00','pending_count':0,'monthly':[],'by_supermarket':[],'confirmed_discounts':None,'savings':None,'waste':None}
 elif path=='receipts/extract':
  assert 'multipart/form-data' in req.headers['content-type']
  data={'parsed_receipt':parsed,'ocr':{'provider':'tesseract','confidence':None},'warnings':[]}
 elif path=='receipts':
  saves.append((req.headers['idempotency-key'],req.post_data_json))
  if len(saves)==1:return route.fulfill(status=503,json={'detail':'Synthetic temporary failure'})
  data={'id':'synthetic-receipt','status':'pending_review','purchase_date':'2025-02-03','total_amount':'2.50','lines':parsed['lines']}
 else:raise AssertionError(path)
 route.fulfill(json=data,headers={'Cache-Control':'no-store'})
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path=os.environ.get('UI_BROWSER_EXECUTABLE') or shutil.which('google-chrome') or shutil.which('chromium'),args=['--no-sandbox'] + (['--single-process','--no-zygote'] if os.environ.get('UI_BROWSER_SINGLE_PROCESS') == '1' else []))
 page=browser.new_page(viewport={'width':390,'height':844},device_scale_factor=1)
 def static_route(route):
  file=(ROOT/'web/dist') / (urlsplit(route.request.url).path.lstrip('/') or 'index.html')
  if file.is_file():route.fulfill(body=file.read_bytes(),content_type=mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
  else:route.fulfill(status=404)
 page.route('**/*',static_route)
 page.route('**/api/v1/**',route_handler)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:4179/#token=synthetic-browser-session')
 expect(page.get_by_role('heading',name='Tu casa, en orden.')).to_be_visible()
 assert '#token' not in page.url
 assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
 page.screenshot(path=str(Path(os.environ.get('UI_SCREENSHOT_DIR','/tmp'))/'family-ui-home-mobile.png'),full_page=True)
 page.get_by_role('button',name='Perfil de mi familia',exact=True).click()
 expect(page.get_by_label('Código postal',exact=True)).to_have_value('')
 assert page.get_by_role('button',name='Guardar preferencias').is_enabled()
 assert page.get_by_role('button',name='Actualizar precios').is_disabled()
 assert page.get_by_label('Mercadona',exact=True).is_checked() is False
 page.get_by_role('button',name='Guardar preferencias').click()
 expect(page.get_by_role('status').filter(has_text='Preferencias guardadas.')).to_be_visible()
 assert profile['postal_code'] is None and profile['basket']==[] and profile['preferred_stores']==[]
 page.get_by_label('Añadir un producto a tu cesta').select_option('eggs_m')
 page.get_by_role('button',name='Añadir producto +').click()
 expect(page.get_by_label('Nombre en tu cesta')).to_have_value('Huevos tamaño M')
 page.get_by_role('button',name='Quitar Huevos tamaño M').click()
 expect(page.get_by_text('Tu cesta está vacía.',exact=False)).to_be_visible()
 page.get_by_role('button',name='Cámara',exact=True).click()
 page.get_by_label('Fotografiar o seleccionar ticket').set_input_files({'name':'synthetic.png','mimeType':'image/png','buffer':base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6nE0AAAAASUVORK5CYII=')})
 expect(page.get_by_role('heading',name='Solo falta lo que falta.')).to_be_visible()
 page.get_by_label('Fecha de compra').fill('2025-02-03')
 page.get_by_label('Importe total (€)').fill('2.50')
 page.screenshot(path=str(Path(os.environ.get('UI_SCREENSHOT_DIR','/tmp'))/'family-ui-capture-mobile.png'),full_page=True)
 page.get_by_role('button',name='Guardar para revisar',exact=True).click()
 expect(page.get_by_role('alert')).to_be_visible()
 page.get_by_role('button',name='Reintentar guardado',exact=True).click()
 expect(page.get_by_role('heading',name='Ticket guardado para revisión')).to_be_visible()
 assert len(saves)==2 and saves[0]==saves[1]
 assert saves[0][1]['pending_fields']==[{'field_path':'lines[0].unit_price','confidence':0.4}]
 assert saves[0][1]['purchase_date']=='2025-02-03' and saves[0][1]['total_amount']=='2.50'
 assert calls.count('analytics')==2 and calls.count('inventory?limit=100')==2
 page.get_by_role('button',name='Despensa',exact=True).click()
 expect(page.get_by_text('Según compras confirmadas; consumo pendiente',exact=True)).to_be_visible()
 page.get_by_role('button',name='Menús',exact=True).click()
 expect(page.get_by_text('En preparación',exact=True)).to_be_visible()
 page.get_by_role('button',name='Ahorro',exact=True).click()
 expect(page.get_by_role('heading',name='El ahorro aún no está medido.')).to_be_visible()
 assert page.locator('.monthly-chart').count()==0
 page.screenshot(path=str(Path(os.environ.get('UI_SCREENSHOT_DIR','/tmp'))/'family-ui-savings-mobile.png'),full_page=True)
 assert page.evaluate('localStorage.length===0 && sessionStorage.length===0')
 assert not errors, errors
 page.set_viewport_size({'width':1280,'height':900});page.get_by_role('button',name='Inicio',exact=True).click()
 assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
 page.screenshot(path=str(Path(os.environ.get('UI_SCREENSHOT_DIR','/tmp'))/'family-ui-home-desktop.png'),full_page=True)
 browser.close()
 print(json.dumps({'result':'passed','scope':'synthetic Chromium UI interactions','widths':[390,1280],'save_retries_same_key_and_payload':True,'unknown_pending_retained':True,'runtime_errors':errors}))
