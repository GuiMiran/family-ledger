import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';
import {Icon,BottomNav,Home,Pantry,Capture,Menus,Savings,type View,type Receipt,type Purchase,type Analytics,type Api} from './mobile';

// Consume the invitation before rendering or making requests. Session memory only.
const accessFragment = new URLSearchParams(window.location.hash.slice(1));
let invitation = accessFragment.get('token');
let accessError = '';
let privateInvite = accessFragment.get('invite');
accessFragment.delete('token');accessFragment.delete('invite');
if (window.location.hash) window.history.replaceState(null, '', window.location.pathname + window.location.search);
const request:Api=async(path,method='GET',body,extraHeaders={})=>{
 const form=body instanceof FormData;
 const response=await fetch('/api/v1/'+path,{method,headers:{Authorization:`Bearer ${invitation}`,...(body&&!form?{'Content-Type':'application/json'}:{}),...extraHeaders},body:body?(form?body:JSON.stringify(body)):undefined,cache:'no-store',credentials:'omit'});
 if(!response.ok){
  if(response.status===401||response.status===403){window.dispatchEvent(new Event('family-session-expired'));throw new Error('Esta invitación ya no es válida.');}
  if(path==='receipts/extract')throw new Error(response.status===413?'La foto supera el tamaño permitido. Haz otra con menor resolución.':response.status===415?'Usa una foto JPEG, PNG o WebP.':response.status===422?'No hemos podido leer el ticket con fiabilidad. Haz otra foto completa y bien iluminada.':'La lectura del ticket no está disponible ahora. Reintenta con la misma foto más tarde.');
  throw new Error(response.status===422?'Revisa los campos y los importes: no hemos podido validar estos datos.':response.status===409?'El envío ya existe con otro contenido. Conserva este borrador y revisa el resultado antes de repetir.':'No hemos podido completar la consulta. Puedes reintentar sin perder este borrador.');
 }
 return response.json();
};
const stores = ['mercadona', 'makro', 'lidl', 'dia', 'carrefour', 'condis'];
const names: Record<string,string> = {mercadona:'Mercadona', makro:'Makro', lidl:'Lidl', dia:'DIA', carrefour:'Carrefour', condis:'Condis'};
type BasketItem = {key:string;label:string;comparison_group:string;unit:string;desired_quantity:string;brand?:string|null;ean?:string|null};
type Profile = {family_name:string|null;postal_code:string|null;preferred_stores:string[];basket:BasketItem[];club_memberships:string[];coupons_enabled:boolean;max_age_hours:number;max_budget:string|null};
type Offer = {id:string;store:string;product_name:string;unit_price:string;comparison_unit:string;required_outlay:string;overbuy_quantity:string;outlay_estimated:boolean;source_name:string;source_url:string;observed_at:string;postal_code:string|null;location_verified:boolean;conditions:string[];cashback:string;reasons?:string[];available:boolean|null};
type Item = {key:string;label:string;top_offers:Offer[];per_store:{store:string;offers:Offer[]}[];eligible_offers:Offer[];references:Offer[];excluded:Offer[]};
type Comparison = {postal_code:string|null;coverage:number;items:Item[]};
type Coverage = {store:string;status:string;catalogue_url?:string};
type Agent = {mode:string;llm_used:boolean;plan:{key:string;label:string;offer:Offer}[];estimated_outlay:string;complete:boolean;within_budget:boolean|null;messages:string[]};
type ResponseData = {comparison:Comparison;coverage:Coverage[];agent?:Agent};
const euro = (value:string) => new Intl.NumberFormat('es-ES',{style:'currency',currency:'EUR',maximumFractionDigits:2}).format(Number(value));
const unitPrice = (value:string) => new Intl.NumberFormat('es-ES',{minimumFractionDigits:2,maximumFractionDigits:3}).format(Number(value));
const date = (value:string) => new Intl.DateTimeFormat('es-ES',{dateStyle:'short',timeStyle:'short'}).format(new Date(value));
const coverageText:Record<string,string> = {partial:'Cobertura parcial · consulta incompleta',store_not_selected:'Tienda no seleccionada',source_not_configured:'Fuente sin conectar', source_configuration_invalid:'Fuente pendiente de configuración',source_unavailable:'Fuente no disponible ahora',source_redirect_rejected:'Fuente no disponible ahora',invalid_data:'Datos sin validar',no_offers:'Sin ofertas para esta cesta',unlocalized:'Solo referencias sin verificar en tu zona',observations_received:'Observaciones recibidas',not_refreshed:'Pendiente de actualizar',zone_unverified:'Zona pendiente de verificar',response_too_large:'Fuente no disponible ahora',offer_limit_exceeded:'Fuente no disponible ahora'};
const reasonText:Record<string,string> = {comparison_group_mismatch:'Producto de otro tipo',incompatible_unit:'Unidad no comparable',egg_size_pending:'Elige el tamaño de huevo',brand_mismatch:'Otra marca',ean_mismatch:'Otra referencia',vat_unknown:'IVA desconocido',future_observation:'Fecha futura',stale_observation:'Precio antiguo',promotion_not_started:'Promoción aún no activa',promotion_expired:'Promoción caducada',club_required:'Requiere un club no activado',coupon_required:'Requiere un cupón no activado',unavailable:'No disponible',postcode_mismatch:'Otra zona',unverified_location:'Zona sin verificar',store_not_selected:'Tienda no seleccionada',ambiguous_duplicate:'Precios contradictorios',variable_weight_reference_missing_or_invalid:'Falta precio por peso verificado',variable_weight_reference_unit_mismatch:'Referencia de peso incompatible'};


// Generic comparison types. No catalogue entry is selected for a household.
const catalogue = [
  {group:'milk_whole_uht', label:'Leche entera UHT', unit:'l'},
  {group:'cheese_fresh', label:'Queso fresco', unit:'kg'},
  {group:'eggs_size_pending', label:'Huevos · tamaño pendiente', unit:'unit'},
  ...['s','m','l','xl'].map(size=>({group:'eggs_'+size,label:'Huevos tamaño '+size.toUpperCase(),unit:'unit'})),
  {group:'chicken_breast_fresh_boneless', label:'Pechuga de pollo fresca sin hueso', unit:'kg'},
  {group:'rice_long', label:'Arroz largo', unit:'kg'},
  {group:'pasta_dry_wheat', label:'Pasta seca de trigo', unit:'kg'},
  {group:'beef_sliced_unknown_cut', label:'Vacuno fileteado · corte sin especificar', unit:'kg'},
  {group:'beef_babilla_sliced', label:'Vacuno · babilla fileteada', unit:'kg'},
  {group:'beef_tapa_sliced', label:'Vacuno · tapa fileteada', unit:'kg'},
  {group:'beef_cadera_sliced', label:'Vacuno · cadera fileteada', unit:'kg'},
];
const safeGroup = /^[a-z][a-z0-9_]{0,127}$/;
function BasketEditor({items,onChange,disabled}:{items:BasketItem[];onChange:(items:BasketItem[])=>void;disabled:boolean}){
  const [choice,setChoice]=useState('');
  function update(index:number,changes:Partial<BasketItem>){onChange(items.map((item,i)=>i===index?{...item,...changes}:item));}
  function add(){
    const selected=catalogue.find(c=>c.group===choice);
    if(!selected&&choice!=='custom')return;
    onChange([...items,{key:crypto.randomUUID(),label:selected?.label||'',comparison_group:selected?.group||'',
      unit:selected?.unit||'kg',desired_quantity:'1',brand:null,ean:null}]);
    setChoice('');
  }
  return <>
    {!items.length&&<div className="gap onboarding-empty">Tu cesta está vacía. Elige un tipo de producto para empezar; nada se añade sin tu elección.</div>}
    <div className="custom-basket-grid">{items.map((item,index)=><fieldset className="product-editor" key={item.key} disabled={disabled}>
      <div className="editor-heading"><strong>Producto {index+1}</strong><button type="button" className="remove-item" aria-label={'Quitar '+(item.label||'producto '+(index+1))} onClick={()=>onChange(items.filter((_,i)=>i!==index))}>Quitar ×</button></div>
      <label className="field">Nombre en tu cesta<input maxLength={300} value={item.label} placeholder="Nombre del producto" onChange={e=>update(index,{label:e.target.value})}/></label>
      <label className="field">Tipo comparable<select value={catalogue.some(c=>c.group===item.comparison_group)?item.comparison_group:'custom'} onChange={e=>{const selected=catalogue.find(c=>c.group===e.target.value);update(index,{comparison_group:selected?.group||'',unit:selected?.unit||item.unit});}}>{catalogue.map(c=><option key={c.group} value={c.group}>{c.label}</option>)}<option value="custom">Otro tipo · definir grupo</option></select></label>
      {!catalogue.some(c=>c.group===item.comparison_group)&&<label className="field">Grupo de comparación<input maxLength={128} value={item.comparison_group} placeholder="Ej.: cereal_avena_integral" pattern="[a-z][a-z0-9_]*" onChange={e=>update(index,{comparison_group:e.target.value})}/><span className="note">Usa letras minúsculas, números y guiones bajos. Solo se comparan ofertas del mismo grupo; un grupo nuevo puede no tener fuente.</span></label>}
      <div className="editor-pair"><label className="field">Cantidad de referencia<input type="number" min="0.000001" max="1000000" step="any" value={item.desired_quantity??''} onChange={e=>update(index,{desired_quantity:e.target.value})}/></label><label className="field">Unidad<select value={item.unit} onChange={e=>update(index,{unit:e.target.value})}><option value="kg">kg</option><option value="l">litros</option><option value="unit">unidades</option></select></label></div>
      <label className="field">Marca (opcional)<input maxLength={200} value={item.brand||''} placeholder="Cualquier marca" onChange={e=>update(index,{brand:e.target.value||null})}/></label>
      <details className="product-reference"><summary>Referencia exacta (opcional)</summary><label className="field">EAN<input maxLength={32} value={item.ean||''} placeholder="Código del producto" onChange={e=>update(index,{ean:e.target.value||null})}/></label></details>
    </fieldset>)}</div>
    <div className="add-product"><label className="field" htmlFor="catalogue-choice">Añadir un producto a tu cesta<select id="catalogue-choice" value={choice} disabled={disabled||items.length>=30} onChange={e=>setChoice(e.target.value)}><option value="">Elige un tipo de producto</option>{catalogue.map(c=><option key={c.group} value={c.group}>{c.label}</option>)}<option value="custom">Otro producto · definir tipo</option></select></label><button type="button" className="secondary" disabled={disabled||!choice||items.length>=30} onClick={add}>Añadir producto +</button></div>
    {items.length>=30&&<p className="note">Puedes comparar hasta 30 productos. Quita uno para añadir otro.</p>}
  </>;
}

function OfferCard({offer, reference=false, position}:{offer:Offer;reference?:boolean;position?:number}) {
  const safeUrl = offer.source_url.startsWith('https://') ? offer.source_url : undefined;
  return <article className={'offer '+(reference?'reference':'')}>
    <div className="offer-top"><span className="store-name">{names[offer.store] || offer.store}</span>{position===0&&!reference&&<span className="badge">Menor precio por unidad</span>}</div>
    <h4>{offer.product_name}</h4>
    {offer.unit_price && <div className="price">{unitPrice(offer.unit_price)} <span>€/{offer.comparison_unit === 'unit' ? 'ud.' : offer.comparison_unit}</span></div>}
    {offer.required_outlay && <p className="checkout">{offer.outlay_estimated?'Salida estimada':'Importe de compra'} <strong>{euro(offer.required_outlay)}</strong></p>}
    {offer.outlay_estimated&&<p className="note">Peso variable: el peso y el importe finales pueden cambiar.</p>}
    {Number(offer.overbuy_quantity)>0&&<p className="note">Incluye {new Intl.NumberFormat('es-ES',{maximumFractionDigits:3}).format(Number(offer.overbuy_quantity))} {offer.comparison_unit==='unit'?'ud.':offer.comparison_unit} extra por el formato del pack.</p>}
    <p className={'zone '+(reference?'muted':'')}>{reference?'Referencia sin verificación local':`Zona verificada · ${offer.postal_code}`}</p>
    {offer.available===null&&<p className="note">Disponibilidad sin confirmar.</p>}
    {(offer.conditions||[]).map((c,i)=><p className="condition" key={i}>{c}</p>)}
    {Number(offer.cashback)>0&&<p className="note">Reembolso separado: {euro(offer.cashback)}. No reduce el pago en caja.</p>}
    <footer><a href={safeUrl} target="_blank" rel="noopener noreferrer" referrerPolicy="no-referrer">Ver fuente ↗</a><span>{date(offer.observed_at)}</span></footer>
    <span className="source-name">{offer.source_name}</span>
  </article>;
}

function ShoppingView({mode,onProfile,onNavigate}:{mode:'profile'|'compare';onProfile:(profile:Profile)=>void;onNavigate:(view:View)=>void}){
  const [profile,setProfile]=useState<Profile|null>(null);
  const [data,setData]=useState<ResponseData|null>(null);
  const [tab,setTab]=useState('all');
  const [busy,setBusy]=useState('');
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');
  const [dirty,setDirty]=useState(false);
  const unauthorized=false;
  const api=(path:string,method='GET',body?:unknown)=>request('shopping/'+path,method,body);
  useEffect(()=>{
    if(!invitation)return;
    let active=true;
    setBusy('load');
    Promise.all([api('profile'),api('compare')]).then(([p,d])=>{if(active){setProfile(p.profile||p);onProfile(p.profile||p);setData(d);}}).catch(e=>{if(active)setError(e.message);}).finally(()=>{if(active)setBusy('');});
    return()=>{active=false;};
  },[]);
  function edit(next:Profile){setProfile(next);setDirty(true);setNotice('');setData(null);if(tab!=='all'&&!next.preferred_stores.includes(tab))setTab('all');}
  const validPostalCode = !!profile && (profile.postal_code===null || /^[0-9]{5}$/.test(profile.postal_code));
  const validBasket = !!profile && profile.basket.every(item=>item.label.trim().length>0 && safeGroup.test(item.comparison_group) && Number(item.desired_quantity)>0 && Number(item.desired_quantity)<=1000000);
  const ready = !!profile && !!profile.postal_code && validPostalCode && profile.preferred_stores.length>0 && profile.basket.length>0 && validBasket;
  async function act(action:'save'|'refresh'|'agent'){
    if(!profile||!validPostalCode||!validBasket||(action!=='save'&&!ready))return;
    setBusy(action);setError('');setNotice('');
    try{
      if(dirty||action==='save') {const saved=await api('profile','PUT',profile);setProfile(saved.profile||saved);onProfile(saved.profile||saved);setDirty(false);}
      if(action==='save'){setData(await api('compare'));setNotice('Preferencias guardadas.');}
      else {setData(await api(action,'POST'));setNotice(action==='refresh'?'Consulta terminada. Revisa la cobertura de cada tienda.':'Plan preparado con las ofertas verificadas disponibles.');onNavigate('compare');}
    }catch(e){setError(e instanceof Error?e.message:'No se ha podido completar la consulta.');}
    finally{setBusy('');}
  }
  if(!invitation||unauthorized) return <main className="welcome"><div className="brand-mark">f<span>·</span></div><span className="eyebrow">FAMILY LEDGER</span><h1>La compra, con<br/>más perspectiva.</h1><p>Tu cesta, los precios de tu zona y un plan que cuida el presupuesto familiar.</p><div className="welcome-note"><span>↗</span><div><strong>Entra con tu invitación familiar</strong><p>{unauthorized?'El enlace ya no es válido. Pide una nueva invitación a quien gestiona vuestra familia.':'Abre el enlace privado de tu familia para consultar y organizar vuestra compra.'}</p></div></div><small>Acceso privado. No guardamos la invitación en este dispositivo. Si recargas, vuelve a abrir tu enlace.</small></main>;
  return <div className="shopping-view">
    <main><section className="hero"><div><span className="eyebrow">COMPRA CON CRITERIO</span><h1>{profile&&!ready?<>Tu familia.<br/><span>Tu propia forma de comprar.</span></>:<>Lo que necesitas.<br/><span>Al precio que tiene sentido.</span></>}</h1><p>{profile&&!ready?'Configura tu nombre familiar, tu zona, tus tiendas y los productos que tú elijas. Puedes guardar los cambios y continuar después.':'Compara productos equivalentes y prepara tu próxima compra, con fuentes y condiciones a la vista.'}</p></div><div className="hero-stamp"><span>Tu zona</span><strong>{profile?.postal_code||'—'}</strong><span>Precios con IVA</span></div></section>
    {error&&<div className="alert" role="alert">{error}</div>}{notice&&<div className="notice" role="status">{notice}</div>}
    {!profile?<div className="loading" role="status">{busy?'Preparando tu espacio…':'No se han podido cargar tus preferencias.'}</div>:<>
    {mode==='profile'&&<><section className="settings panel"><div className="section-heading"><div><span className="eyebrow">01 · TUS PREFERENCIAS</span><h2>Cerca de ti</h2></div><span className="subtle">Editable para tu familia</span></div><div className="family-name-row"><label className="field">Nombre de tu familia<input maxLength={120} value={profile.family_name||''} placeholder="Opcional" disabled={!!busy} onChange={e=>edit({...profile,family_name:e.target.value||null})}/></label><p className="note">Estas preferencias pertenecen a la familia de tu invitación. Tú decides qué información guardar.</p></div><div className="settings-grid"><label className="field">Código postal<input inputMode="numeric" pattern="[0-9]{5}" maxLength={5} value={profile.postal_code||''} placeholder="Sin configurar" onChange={e=>edit({...profile,postal_code:e.target.value.replace(/\D/g,'')||null})}/></label><label className="field">Presupuesto de referencia (€)<input type="number" min="0" step="0.01" placeholder="Opcional" value={profile.max_budget||''} onChange={e=>edit({...profile,max_budget:e.target.value||null})}/></label><div className="store-picker"><span className="field-label">Tiendas que quieres comparar</span><div className="checks">{stores.map(store=><label className="check" key={store}><input type="checkbox" checked={profile.preferred_stores.includes(store)} onChange={e=>edit({...profile,preferred_stores:e.target.checked?[...profile.preferred_stores,store]:profile.preferred_stores.filter(s=>s!==store)})}/>{names[store]}</label>)}</div></div></div>
    <details className="preferences"><summary>Clubs, cupones y antigüedad de precios</summary><p className="note">Activa solo las condiciones que cumples. El comparador no inscribe ni aplica cupones por ti.</p><div className="checks">{stores.map(store=><label className="check" key={store}><input type="checkbox" checked={profile.club_memberships.includes(store)} onChange={e=>edit({...profile,club_memberships:e.target.checked?[...profile.club_memberships,store]:profile.club_memberships.filter(s=>s!==store)})}/>Club {names[store]}</label>)}</div><div className="advanced"><label className="check"><input type="checkbox" checked={profile.coupons_enabled} onChange={e=>edit({...profile,coupons_enabled:e.target.checked})}/>Tengo los cupones necesarios</label><label>Antigüedad máxima <select value={profile.max_age_hours} onChange={e=>edit({...profile,max_age_hours:Number(e.target.value)})}>{[6,12,24,48,72,168].map(h=><option key={h} value={h}>{h} horas</option>)}</select></label></div></details></section>
    <section className="panel basket"><div className="section-heading"><div><span className="eyebrow">02 · TU CESTA DE REFERENCIA</span><h2>Lo que tu familia elige</h2></div><span className="subtle">{profile.basket.length} productos</span></div><p className="section-copy">Estas cantidades sirven para comparar; ajústalas a tu próxima compra.</p><BasketEditor items={profile.basket} disabled={!!busy} onChange={basket=>edit({...profile,basket})}/><div className="editor-validation" role="status">{!validPostalCode&&<p className="warning">Introduce cinco dígitos para el código postal o borra el campo para dejarlo sin configurar.</p>}{!validBasket&&<p className="warning">Cada producto necesita nombre, grupo de comparación válido y una cantidad mayor que cero. Puedes quitar los productos que aún no quieras configurar.</p>}</div><div className="actions"><button className="secondary" disabled={!!busy||!validPostalCode||!validBasket} onClick={()=>act('save')}>{busy==='save'?'Guardando…':'Guardar preferencias'}</button><button className="primary" disabled={!!busy||!ready} onClick={()=>act('refresh')}>{busy==='refresh'?'Consultando fuentes…':'Actualizar precios'} <span>↗</span></button></div>{!ready&&<p className="setup-hint" role="status">Para consultar precios y preparar un plan, configura un código postal válido, al menos una tienda y un producto. Puedes guardar una configuración incompleta.</p>}</section>
    </>}{mode==='compare'&&<><button className="profile-shortcut" onClick={()=>onNavigate('profile')}><Icon name="user" size={18}/> Editar familia, cesta y tiendas <Icon name="arrow" size={16}/></button><div className="compare-actions"><button className="primary" disabled={!!busy||!ready} onClick={()=>act('refresh')}>{busy==='refresh'?'Consultando fuentes…':'Actualizar precios'} <Icon name="refresh" size={16}/></button></div><section className="results"><div className="section-heading"><div><span className="eyebrow">03 · EL PRECIO, CON CONTEXTO</span><h2>Opciones para tu cesta</h2></div>{data&&<span className="coverage-pill">{data.comparison.coverage} de {profile.basket.length} productos con opciones locales</span>}</div><p className="section-copy">Hasta tres opciones por producto, ordenadas por precio por unidad. El formato del pack puede cambiar el importe final de compra.</p>
    {!data||!ready?<div className="empty panel"><span>⌕</span><h3>{!ready?'Tu espacio empieza vacío':dirty?'Tu cesta ha cambiado':'Todo empieza con una consulta'}</h3><p>{!ready?'Elige tu zona, tus tiendas y tus productos. Las opciones aparecerán cuando consultes precios.':dirty?'Guarda o actualiza para comparar con tus nuevas preferencias.':'Actualiza precios para saber qué fuentes tienen opciones verificadas para tu zona.'}</p></div>:<><div className="coverage-grid">{data.coverage.map((c,i)=><div className="coverage-store" key={c.store+i}><strong>{names[c.store]||c.store}</strong><span>{coverageText[c.status]||'Revisar cobertura de la fuente'}</span></div>)}</div><div className="tabs" role="tablist" aria-label="Filtrar por tienda">{['all',...profile.preferred_stores].map(store=><button role="tab" aria-selected={tab===store} className={tab===store?'active':''} key={store} onClick={()=>setTab(store)}>{store==='all'?'Todas las tiendas':names[store]}</button>)}</div>{data.comparison.items.map(item=>{const visible=tab==='all'?item.top_offers:item.per_store.find(s=>s.store===tab)?.offers||[];return <section className="product-result" key={item.key}><div className="product-heading"><h3>{item.label}</h3><span>{visible.length?`${visible.length} opciones`: 'Sin precio local comparable'}</span></div>{visible.length?<div className="offer-grid">{visible.map((o,i)=><OfferCard key={o.store+o.id} offer={o} position={i}/>)}</div>:<div className="gap">{profile.basket.find(b=>b.key===item.key)?.comparison_group==='eggs_size_pending'?'Elige el tamaño de los huevos para comparar productos equivalentes.':'Faltan ofertas elegibles verificadas en esta zona. No hemos rellenado este espacio con precios de referencia.'}</div>}{item.references.length>0&&<details className="reference-details"><summary>{item.references.length} referencias de catálogo · sin verificar para {profile.postal_code}</summary><p className="note">No participan en el ranking local ni garantizan precio o disponibilidad en tu zona.</p><div className="offer-grid">{item.references.map(o=><OfferCard key={o.store+o.id} offer={o} reference/>)}</div></details>}{item.excluded.length>0&&<details className="excluded"><summary>Por qué se han descartado {item.excluded.length} observaciones</summary><ul>{Array.from(new Set(item.excluded.flatMap(o=>o.reasons||[]))).map(r=><li key={r}>{reasonText[r]||'Condiciones de comparación sin verificar'}</li>)}</ul></details>}</section>})}</>}
    </section><section className="advisor panel"><div><span className="eyebrow">TU AYUDA PARA DECIDIR</span><h2>Una compra con más intención.</h2><p>Un plan basado en tu cesta y en las ofertas verificadas. Tú decides dónde y cuándo comprar.</p><button className="primary" disabled={!!busy||!ready} onClick={()=>act('agent')}>{busy==='agent'?'Preparando el plan…':'Preparar mi plan de compra'} <span>→</span></button></div><div className="advisor-output">{data?.agent?<><span className="badge">Reglas verificables · sin modelo de lenguaje</span><h3>{data.agent.complete?'Tu cesta tiene un plan':'Un plan parcial, con las dudas a la vista'}</h3><p className="plan-total">{euro(data.agent.estimated_outlay)} <span>salida estimada</span></p><p className="note">Puede incluir pesos aproximados. Faltan transporte, entrega y posibles cambios de disponibilidad.</p><ul className="plan">{data.agent.plan.map(p=><li key={p.key}><span>{p.label}<small>{names[p.offer.store]}</small></span><strong>{euro(p.offer.required_outlay)}</strong></li>)}</ul>{data.agent.within_budget===false&&<p className="warning">El plan supera el presupuesto de referencia.</p>}{!data.agent.complete&&<p className="warning">Faltan productos: este importe no representa toda tu compra.</p>}{data.agent.messages.map((m,i)=><p className="note" key={i}>{m}</p>)}</>:<><span className="advisor-symbol">✳</span><h3>Datos claros. Decisiones tuyas.</h3><p>Sin compras automáticas ni ahorros inventados. Si falta una fuente, el plan lo dice.</p></>}</div></section>
    </> }
    </>}
    <footer className="site-footer"><strong>Family Ledger</strong><p>Precios observados, no reservas. Comprueba las condiciones en la fuente antes de comprar.</p><span>Tu invitación solo permanece en esta sesión.</span></footer></main></div>;
}


type Dashboard = Analytics & {monthly:{period:string;total:string;count:number}[];by_supermarket:{name:string;total:string;count:number}[];confirmed_discounts:string|null};
function App(){
 const [view,setView]=useState<View>('home');
 const [profile,setProfile]=useState<Profile|null>(null);
 const [receipts,setReceipts]=useState<Receipt[]|null>(null);
 const [inventory,setInventory]=useState<Purchase[]|null>(null);
 const [analytics,setAnalytics]=useState<Analytics|null>(null);
 const [dashboard,setDashboard]=useState<Dashboard|null>(null);
 const [loading,setLoading]=useState(false);
 const [error,setError]=useState('');
 const [expired,setExpired]=useState(false);
 async function reload(){
  setLoading(true);setError('');
  const results=await Promise.allSettled([request('receipts?limit=100'),request('inventory?limit=100'),request('analytics'),request('dashboard')]);
  if(results[0].status==='fulfilled')setReceipts(results[0].value);
  if(results[1].status==='fulfilled')setInventory(results[1].value.items);
  if(results[2].status==='fulfilled')setAnalytics(results[2].value);
  if(results[3].status==='fulfilled')setDashboard(results[3].value);
  if(results.slice(0,3).some(r=>r.status==='rejected'))setError('Algunos datos no se han podido actualizar. La información que ves puede corresponder a la consulta anterior.');
  setLoading(false);
 }
 useEffect(()=>{const expire=()=>setExpired(true);window.addEventListener('family-session-expired',expire);if(invitation)void reload();return()=>window.removeEventListener('family-session-expired',expire);},[]);
 function navigate(next:View){setView(next);window.scrollTo({top:0,behavior:'instant'});}
 if(!invitation||expired)return <main className="welcome"><div className="brand-mark">f<span>·</span></div><span className="eyebrow">FAMILY LEDGER</span><h1>Tu familia.<br/><span>Un poco más de calma.</span></h1><p>Organiza tus compras, consulta tus registros y decide con perspectiva.</p><div className="welcome-note"><Icon name="user"/><div><strong>Entra con tu invitación familiar</strong><p>{accessError|| (expired?'Este enlace ya no da acceso. Solicita una nueva invitación a quien gestiona vuestra familia.':'Abre el enlace privado de tu familia para empezar. Cada familia configura su propio espacio.')}</p></div></div><small>La invitación solo permanece en memoria durante esta sesión. Si recargas, vuelve a abrir el enlace.</small></main>;
 return <div className="family-app"><header className="family-header"><button className="logo" onClick={()=>navigate('home')} aria-label="Family Ledger, inicio"><span className="brand-mark small">f<span>·</span></span><span>Family Ledger<small>UN POCO MÁS DE CALMA</small></span></button><button className={'profile-button '+(view==='profile'?'active':'')} onClick={()=>navigate('profile')} aria-label="Perfil de mi familia"><Icon name="user" size={20}/><span>{profile?.family_name||'Mi familia'}</span></button></header><main className="mobile-main">
 {error&&<div className="alert" role="alert">{error}<button className="text-action" disabled={loading} onClick={()=>void reload()}>Actualizar datos</button></div>}
 {view==='home'&&<Home analytics={analytics} receipts={receipts} onNavigate={navigate} loading={loading}/>}
 {view==='pantry'&&<Pantry items={inventory} loading={loading}/>}
 <div hidden={view!=='capture'}><Capture api={request} onSaved={reload}/></div>
 {view==='menus'&&<Menus/>}
 {view==='savings'&&<><Savings analytics={dashboard||analytics}/>{dashboard&&dashboard.monthly.some(m=>m.count>0)&&<section className="real-history"><div className="section-heading"><h2>Tus registros por mes</h2><span className="subtle">Solo tickets confirmados</span></div><p>No representa todos tus gastos. Los meses sin tickets guardados no prueban gasto cero.</p><div className="monthly-chart">{dashboard.monthly.map(month=><div key={month.period}><strong>{month.count>0?euro(month.total):'Sin tickets'}</strong><span className={'month-bar '+(month.count?'':'no-records')} style={{height:month.count?Math.max(8,Number(month.total)/Math.max(1,...dashboard.monthly.map(m=>Number(m.total)))*130)+'px':'3px'}}/><small>{new Intl.DateTimeFormat('es-ES',{month:'short',timeZone:'UTC'}).format(new Date(month.period+'-15T12:00:00Z'))}</small></div>)}</div></section>}</>}
 </main><div hidden={view!=='compare'&&view!=='profile'}><ShoppingView mode={view==='profile'?'profile':'compare'} onProfile={setProfile} onNavigate={navigate}/></div><BottomNav view={view} onChange={navigate}/></div>;
}

const root = createRoot(document.getElementById('root')!);
async function openPrivateInvitation(){
 if(privateInvite){
  root.render(<main className="welcome"><h1>Abriendo tu familia…</h1><p role="status">Verificando tu invitación privada.</p></main>);
  try{
   const response=await fetch('/api/v1/access/exchange',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({invitation:privateInvite}),cache:'no-store',credentials:'omit'});
   if(!response.ok)throw new Error(response.status===429?'Espera un minuto y vuelve a abrir tu enlace.':'Esta invitación no está disponible o ha caducado. Solicita un enlace nuevo.');
   const result=await response.json();
   if(typeof result.access_token!=='string'||!result.access_token)throw new Error('No se pudo abrir la sesión. Vuelve a abrir tu enlace.');
   invitation=result.access_token;
  }catch(error){invitation=null;accessError=error instanceof Error?error.message:'No se pudo abrir tu familia. Vuelve a abrir el enlace.';}
  finally{privateInvite=null;}
 }
 root.render(<App/>);
}
void openPrivateInvitation();
if('serviceWorker' in navigator) window.addEventListener('load',()=>{navigator.serviceWorker.register('/sw.js').catch(()=>{});});
