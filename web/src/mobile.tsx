import React, { useRef, useState } from 'react';
export type View = 'home'|'pantry'|'capture'|'menus'|'savings'|'compare'|'profile';
export type Api = (path:string,method?:string,body?:unknown,headers?:Record<string,string>)=>Promise<any>;
export type Receipt = {id:string;purchase_date:string|null;total_amount:string|null;status:string;lines:{description:string;quantity:string;unit:string;line_total:string}[]};
export type Purchase = {id:string;description:string;quantity:string;unit:string;expiry_date:string|null};
export type Analytics = {confirmed_count:number;confirmed_total:string;pending_count:number};
const money=(value:string)=>new Intl.NumberFormat('es-ES',{style:'currency',currency:'EUR'}).format(Number(value));
const receiptDate=(value:string|null)=>value?new Intl.DateTimeFormat('es-ES',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}).format(new Date(value+'T12:00:00Z')):'Fecha pendiente';
const quantity=(value:string)=>new Intl.NumberFormat('es-ES',{maximumFractionDigits:3}).format(Number(value));
export function Icon({name,size=22}:{name:string;size?:number}){
 const paths:Record<string,React.ReactNode>={
 home:<><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z"/></>,
 pantry:<><rect x="4" y="3" width="16" height="18" rx="3"/><path d="M4 11h16M8 7h2M8 15h2"/></>,
 camera:<><path d="M8 6 9.5 3h5L16 6h4a1 1 0 0 1 1 1v12H3V7a1 1 0 0 1 1-1z"/><circle cx="12" cy="12" r="4"/></>,
 menus:<><path d="M5 3v6m3-6v6M2 3v6a3 3 0 0 0 6 0M5 12v9M19 3c-4 3-5 8-2 10h3M20 3v18"/></>,
 savings:<><path d="M4 20V9m8 11V4m8 16V12M2 21h20"/></>,
 user:<><circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/></>,
 arrow:<path d="m9 5 7 7-7 7"/>,
 receipt:<><path d="M5 3h14v18l-3-2-4 2-4-2-3 2zM9 7h6M9 11h6M9 15h3"/></>,
 compare:<><path d="M3 6h18M3 12h18M3 18h18"/><circle cx="8" cy="6" r="2"/><circle cx="16" cy="12" r="2"/><circle cx="10" cy="18" r="2"/></>,
 leaf:<><path d="M20 3C9 1 2 7 6 15c8 6 16-2 14-12ZM4 21 17 7"/></>,
 check:<path d="m5 12 4 4L19 6"/>,
 refresh:<><path d="M20 8a8 8 0 1 0 0 8M20 3v5h-5"/></>,
 image:<><rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8" cy="8" r="2"/><path d="m3 18 6-6 4 4 3-4 5 6"/></>,
 };
 return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]||paths.receipt}</svg>;
}
export function BottomNav({view,onChange}:{view:View;onChange:(view:View)=>void}){
 return <nav className="bottom-nav" aria-label="Navegación principal">{[['home','Inicio'],['pantry','Despensa'],['capture','Cámara'],['menus','Menús'],['savings','Ahorro']].map(([key,label])=><button key={key} className={(key==='capture'?'nav-camera ':'')+(view===key?'selected':'')} aria-current={view===key?'page':undefined} onClick={()=>onChange(key as View)}><span className="nav-icon"><Icon name={key==='capture'?'camera':key}/></span><span>{label}</span></button>)}</nav>;
}
export function Home({analytics,receipts,onNavigate,loading}:{analytics:Analytics|null;receipts:Receipt[]|null;onNavigate:(view:View)=>void;loading:boolean}){
 const recent=[...(receipts||[])].sort((a,b)=>(b.purchase_date||'').localeCompare(a.purchase_date||'')).slice(0,5);
 return <>
 <div className="view-heading"><span className="eyebrow">TU DÍA A DÍA</span><h1>Tu casa,<br/><span>en orden.</span></h1><p>Lo que compras, lo que registras y lo que decides. En un mismo lugar.</p></div>
 <section className="spending-card"><div><span>Gasto confirmado</span><strong>{analytics?money(analytics.confirmed_total):'—'}</strong><p>Total registrado · todas las fechas</p></div><span className="round-icon"><Icon name="savings" size={28}/></span><div className="spending-bottom"><span>{analytics?`${analytics.confirmed_count} tickets confirmados`:'Datos pendientes de cargar'}</span><span>{analytics?`${analytics.pending_count} por revisar`:'—'}</span></div></section>
 <div className="home-shortcuts"><button className="shortcut" onClick={()=>onNavigate('capture')}><span className="tile-icon"><Icon name="camera"/></span><strong>Añadir un ticket</strong><span>Una foto para empezar</span><Icon name="arrow" size={17}/></button><button className="shortcut" onClick={()=>onNavigate('pantry')}><span className="tile-icon lavender"><Icon name="pantry"/></span><strong>Ver mi despensa</strong><span>Según compras confirmadas</span><Icon name="arrow" size={17}/></button></div>
 <button className="comparator-link" onClick={()=>onNavigate('compare')}><span className="round-icon"><Icon name="compare"/></span><div><strong>Compra con perspectiva</strong><p>Compara tu cesta y consulta las fuentes de tu zona.</p></div><Icon name="arrow" size={18}/></button>
 <section className="recent-section"><div className="section-heading"><h2>Tus tickets</h2><span className="subtle">Registros cargados</span></div>{loading&&!receipts?<div className="soft-empty" role="status">Cargando tus compras…</div>:receipts===null?<div className="soft-empty">No hemos podido cargar los tickets. Puedes volver a consultar tus datos.</div>:!recent.length?<div className="soft-empty"><Icon name="receipt" size={30}/><h3>Tu primera compra empieza aquí</h3><p>Fotografía un ticket para extraer sus datos y revisarlos antes de guardarlo.</p><button className="text-action" onClick={()=>onNavigate('capture')}>Añadir mi primer ticket <Icon name="arrow" size={15}/></button></div>:<div className="receipt-list">{recent.map(r=><details className="receipt-row" key={r.id}><summary><span className="receipt-icon"><Icon name="receipt"/></span><span className="receipt-title"><strong>{receiptDate(r.purchase_date)}</strong><small>{r.lines.length} productos · {r.status==='confirmed'?'Confirmado':'Pendiente de revisión'}</small></span><strong>{r.total_amount===null?'Pendiente':money(r.total_amount)}</strong><Icon name="arrow" size={15}/></summary><ul>{r.lines.map((line,i)=><li key={i}><span>{line.description}</span><strong>{money(line.line_total)}</strong></li>)}</ul></details>)}</div>}</section>
 </>;
}
export function Pantry({items,loading}:{items:Purchase[]|null;loading:boolean}){
 return <><div className="view-heading"><span className="eyebrow">LO QUE HAS COMPRADO</span><h1>Tu despensa.</h1><p>Una vista de los productos que has registrado para tu familia.</p></div><div className="projection-note"><Icon name="pantry"/><div><strong>Según compras confirmadas; consumo pendiente</strong><p>Estas cantidades reflejan compras registradas. Aún no descontamos lo que consumes ni verificamos existencias físicas.</p></div></div>{loading&&items===null?<div className="soft-empty">Cargando productos…</div>:items===null?<div className="soft-empty">No se han podido consultar las compras.</div>:!items.length?<div className="soft-empty"><Icon name="pantry" size={36}/><h3>Aquí aparecerán tus productos</h3><p>Cuando un ticket quede confirmado, sus productos se añadirán a esta vista.</p></div>:<section className="pantry-list">{items.map(item=><article className="pantry-row" key={item.id}><span className="tile-icon"><Icon name="leaf"/></span><div><h3>{item.description}</h3><p>{item.expiry_date?'Caducidad impresa: '+receiptDate(item.expiry_date):'Caducidad no registrada'}</p></div><strong>{quantity(item.quantity)} <small>{item.unit==='unit'?'ud.':item.unit}</small></strong></article>)}</section>}<div className="capability-note"><strong>Congelador y consumo</strong><p>Su seguimiento todavía no está disponible. No inferimos dónde guardas tus productos.</p></div></>;
}
export function Menus(){return <><div className="view-heading"><span className="eyebrow">UN POCO MÁS DE CALMA</span><h1>Ideas para<br/><span>tu mesa.</span></h1><p>La planificación empieza por conocer lo que tienes y lo que necesitas.</p></div><section className="unavailable-card"><span className="feature-art"><Icon name="menus" size={62}/></span><span className="badge">En preparación</span><h2>Los menús llegarán<br/>a su tiempo.</h2><p>La planificación de menús todavía no está disponible. Primero necesitamos un seguimiento fiable de tus existencias y de las preferencias de tu familia.</p><div className="capability-note">No se han generado recetas ni reservado productos.</div></section></>;}
export function Savings({analytics}:{analytics:Analytics|null}){return <><div className="view-heading"><span className="eyebrow">CADA EURO, CON CONTEXTO</span><h1>Una mirada<br/><span>a tus compras.</span></h1><p>Antes de medir el ahorro, los datos tienen que contar lo que realmente ha pasado.</p></div><section className="savings-summary"><article><span>Gasto confirmado</span><strong>{analytics?money(analytics.confirmed_total):'—'}</strong><small>Total registrado · sin periodo mensual aplicado</small></article><article><span>Tickets confirmados</span><strong>{analytics?.confirmed_count??'—'}</strong><small>{analytics?`${analytics.pending_count} pendientes de revisión`:'Datos sin cargar'}</small></article></section><section className="unavailable-card savings-note"><span className="feature-art"><Icon name="savings" size={48}/></span><h2>El ahorro aún<br/>no está medido.</h2><p>El gasto registrado no demuestra un ahorro. Todavía no hay una medida del ahorro conseguido, una previsión anual ni una comparación histórica completa.</p></section></>;}

type Pending = {field_path:string;confidence:number;detected_value?:string|null;suggestion?:string|null};
type ParsedLine = {line_number:number;description:string;quantity:string;unit:string;line_total:string;[key:string]:unknown};
type ParsedReceipt = {supermarket_key:string;purchase_date:string|null;total_amount:string|null;total_vat:string|null;lines:ParsedLine[];pending_fields:Pending[];[key:string]:unknown};
type Extraction = {parsed_receipt:ParsedReceipt;ocr:{provider:string;confidence:number|null};warnings:string[]};
const supported:Record<string,string>={purchase_date:'Fecha de compra',total_amount:'Importe total (€)',total_vat:'IVA total (€)'};
const pendingLabel=(path:string)=>{const match=path.match(/^lines\[(\d+)\]\.(.+)$/);if(match){const labels:Record<string,string>={quantity:'Cantidad',unit_price:'Precio por unidad',line_total:'Importe',description:'Descripción',unit:'Unidad',expiry_date:'Caducidad'};return (labels[match[2]]||'Dato')+' del producto '+(Number(match[1])+1);}return ({total_discounts:'Descuentos',payment_method:'Forma de pago',supermarket_key:'Tienda'} as Record<string,string>)[path]||'Dato pendiente de revisión';};
const validCorrection=(field:string,value:string)=>field==='purchase_date'?/^\d{4}-\d{2}-\d{2}$/.test(value)&&!isNaN(Date.parse(value)):value.trim()!==''&&Number.isFinite(Number(value))&&Number(value)>=0;
export function Capture({api,onSaved}:{api:Api;onSaved:()=>Promise<void>}){
 const input=useRef<HTMLInputElement>(null);
 const [draft,setDraft]=useState<Extraction|null>(null);
 const [corrections,setCorrections]=useState<Record<string,string>>({});
 const [draftKey,setDraftKey]=useState('');
 const [submitted,setSubmitted]=useState<ParsedReceipt|null>(null);
 const [busy,setBusy]=useState('');
 const [error,setError]=useState('');
 const [saved,setSaved]=useState<Receipt|null>(null);
 async function extract(file:File|undefined){
  if(!file)return;
  setError('');
  if(!['image/jpeg','image/png','image/webp'].includes(file.type)){setError('Usa una imagen JPEG, PNG o WebP. Haz otra foto si tu cámara guarda en otro formato.');return;}
  if(file.size>10*1024*1024){setError('La imagen supera 10 MB. Haz una foto con menor resolución.');return;}
  setBusy('extract');setDraft(null);setSaved(null);setSubmitted(null);setCorrections({});
  const body=new FormData();body.append('image',file);
  try{const value:Extraction=await api('receipts/extract','POST',body);if(!value.parsed_receipt?.lines?.length){throw new Error('No hemos podido leer productos. Haz otra foto con todo el ticket enfocado.');}setDraft(value);setDraftKey(crypto.randomUUID());}
  catch(e){setError(e instanceof Error?e.message:'No se ha podido leer la imagen. Haz otra foto.');}
  finally{setBusy('');if(input.current)input.current.value='';}
 }
 const fields=draft?[...draft.parsed_receipt.pending_fields]:[];
 if(draft&&!draft.parsed_receipt.purchase_date&&!fields.some(f=>f.field_path==='purchase_date'))fields.push({field_path:'purchase_date',confidence:0});
 if(draft&&draft.parsed_receipt.total_amount===null&&!fields.some(f=>f.field_path==='total_amount'))fields.push({field_path:'total_amount',confidence:0});
 const pending=fields.filter(f=>!supported[f.field_path]||!validCorrection(f.field_path,corrections[f.field_path]||''));
 async function save(){
  if(!draft||!draft.parsed_receipt.lines.length)return;
  setBusy('save');setError('');
  const payload:ParsedReceipt=submitted||{...draft.parsed_receipt,pending_fields:pending};
  if(!submitted){for(const [key,value]of Object.entries(corrections)){if(supported[key]&&validCorrection(key,value))payload[key]=value;}setSubmitted(payload);}
  try{const receipt:Receipt=await api('receipts','POST',payload,{'Idempotency-Key':draftKey});setSaved(receipt);setDraft(null);await onSaved();}
  catch(e){setError(e instanceof Error?e.message:'No se ha podido guardar. Reintenta con este mismo borrador.');}
  finally{setBusy('');}
 }
 return <><div className="view-heading"><span className="eyebrow">UNA FOTO. MENOS TRABAJO.</span><h1>Tu ticket,<br/><span>bien registrado.</span></h1><p>Fotografía, revisa lo que falta y decide cuándo guardarlo.</p></div><input ref={input} className="visually-hidden" type="file" accept="image/jpeg,image/png,image/webp" capture="environment" aria-label="Fotografiar o seleccionar ticket" disabled={!!busy} onChange={e=>extract(e.target.files?.[0])}/>
 {error&&<div className="alert" role="alert">{error}</div>}
 {saved&&<div className="saved-receipt" role="status"><span className="round-icon"><Icon name="check"/></span><h2>{saved.status==='confirmed'?'Ticket confirmado':'Ticket guardado para revisión'}</h2><p>{saved.status==='confirmed'?'La compra ya aparece en tus registros.':'Los campos pendientes se conservan. Esta compra aún no suma como confirmada ni añade productos a la despensa.'}</p></div>}
 {!draft?<section className="capture-card"><div className="camera-frame"><Icon name="receipt" size={66}/><span className="corner tl"/><span className="corner tr"/><span className="corner bl"/><span className="corner br"/></div><h2>{busy==='extract'?'Leyendo tu ticket…':'Que se vea todo el ticket.'}</h2><p>Luz natural, papel plano y una imagen enfocada. JPEG, PNG o WebP, hasta 10 MB.</p><button className="primary" disabled={!!busy} onClick={()=>input.current?.click()}><Icon name="camera" size={19}/>{busy==='extract'?'Extrayendo datos…':saved?'Fotografiar otro ticket':'Fotografiar o elegir imagen'}</button><span className="capture-privacy">Lectura local con Tesseract. La extracción no guarda la compra ni conserva la imagen.</span></section>:<section className="draft-review"><div className="review-top"><span className="badge">Borrador · aún sin guardar</span><button className="text-action" disabled={!!busy} onClick={()=>input.current?.click()}>Repetir foto</button></div><h2>Solo falta lo que falta.</h2><p className="section-copy">Los productos detectados se muestran sin cambios. Revisa únicamente los campos ambiguos.</p>{draft.warnings.map((warning,i)=><p className="warning" key={i}>{warning}</p>)}<p className="note">Lectura: {draft.ocr.provider}{draft.ocr.confidence!==null?` · confianza ${Math.round(draft.ocr.confidence*100)} %`:''}</p><div className="receipt-facts"><span>Fecha <strong>{receiptDate(draft.parsed_receipt.purchase_date)}</strong></span><span>Total <strong>{draft.parsed_receipt.total_amount===null?'Pendiente':money(draft.parsed_receipt.total_amount)}</strong></span></div>
 {fields.some(f=>supported[f.field_path])&&<div className="ambiguous-fields">{fields.filter(f=>supported[f.field_path]).map(field=><label className="field" key={field.field_path}>{supported[field.field_path]}<input type={field.field_path==='purchase_date'?'date':'number'} min={field.field_path==='purchase_date'?undefined:'0'} step={field.field_path==='purchase_date'?undefined:'0.01'} disabled={!!busy||!!submitted} value={corrections[field.field_path]||''} onChange={e=>setCorrections({...corrections,[field.field_path]:e.target.value})}/><span className="note">Detectado: {field.detected_value??'sin dato fiable'}. Déjalo vacío para mantenerlo pendiente.</span></label>)}</div>}
 {fields.some(f=>!supported[f.field_path])&&<div className="projection-note"><div><strong>Quedan datos que necesitan revisión</strong><p>No se pueden corregir desde esta pantalla. Se conservarán como pendientes al guardar.</p><ul>{fields.filter(f=>!supported[f.field_path]).map((field,i)=><li key={i}>{pendingLabel(field.field_path)}</li>)}</ul></div></div>}
 <div className="detected-lines"><h3>Productos detectados</h3>{draft.parsed_receipt.lines.map(line=><div key={line.line_number}><span><strong>{line.description}</strong><small>{quantity(line.quantity)} {line.unit==='unit'?'ud.':line.unit}</small></span><strong>{money(line.line_total)}</strong></div>)}</div>
 <p className="note">{pending.length?'Se guardará como pendiente de revisión. El servidor validará los importes.':'Los campos ambiguos se han resuelto. El servidor comprobará los importes antes de confirmar.'}</p>{submitted&&<p className="note">Este envío mantiene el mismo contenido para evitar duplicados al reintentar. Repite la foto si necesitas otro borrador.</p>}<button className="primary save-draft" disabled={!!busy} onClick={save}>{busy==='save'?'Guardando…':submitted?'Reintentar guardado':pending.length?'Guardar para revisar':'Guardar ticket'}</button></section>}
 </>;
}
