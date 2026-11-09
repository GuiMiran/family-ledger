# Comparador familiar 0.3.0 · operación y límites

## Recorrido

La familia autenticada empieza con un perfil vacío. Configura nombre, código
postal, tiendas y cesta, guarda y después puede actualizar las fuentes. Puede
editar cada artículo, variante y cantidad o eliminarlo. La recogida y el asesor
se bloquean si falta la configuración requerida; no se reutilizan preferencias
de otra familia ni de una demostración.

El comparador muestra hasta tres opciones globales o por tienda con precio por
unidad, desembolso del formato, condiciones, fecha y enlace. Las cantidades son
referencias explícitas de la familia, no una previsión automática de consumo.
Las variantes incompatibles se mantienen separadas. Menos de tres ofertas es
un resultado válido. La recomendación no constituye un pedido.

## Fuentes

MercadonaProvider consulta un escaparate público anónimo con hasta once peticiones
acotadas: contexto postal, siete categorías conocidas y hasta tres fichas de leche
para acreditar UHT por producto mediante denominación legal. No se extrapola la
ficha de un producto a los demás. No es una API oficial
publicada ni integración contractual. Requiere respuesta que pruebe CP/almacén;
si no se acredita zona se conserva referencia sin ranking local. Interrupciones,
cambios de formato o bloqueo se muestran; no se eluden ni se usan credenciales.
La publicación de un producto no garantiza stock. Se mantiene IVA incluido y
peso aproximado con precio/kg publicado, sin recomputarlo desde pesos redondeados.
La clasificación conservadora puede dejar sin resultados leche sin prueba UHT por producto,
una variante ausente o un corte sin equivalencia acreditada. No son precios cero.

Las otras cinco cadenas requieren fuente o acuerdo configurado; el adaptador
`SHOPPING_PRICE_FEED_URL`/`SHOPPING_PRICE_FEED_TOKEN` permite recibir observaciones
con el contrato de [price-sources.md](price-sources.md). Los tests usan datos
sintéticos. Las webs de catálogo registradas no son seis conectores activos.
Un proxy de salida de Mercadona puede configurarse por operador con
`MERCADONA_OUTBOUND_PROXY`; alternativamente `MERCADONA_USE_ENV_PROXY=1` habilita
explícitamente la configuración de proxy del entorno. Por defecto no se hereda.
Nunca desde el perfil del usuario. No publicar secretos.

## API y acceso

Rutas autenticadas:

| Método | Ruta | Resultado |
|---|---|---|
| GET / PUT | `/api/v1/shopping/profile` | Perfil de la familia del JWT |
| POST | `/api/v1/shopping/refresh` | Recoge y sustituye snapshot propio; audita cobertura |
| GET | `/api/v1/shopping/compare` | Reevalúa snapshot con frescura y perfil actual |
| POST | `/api/v1/shopping/agent` | Actualiza, calcula plan y guarda auditoría |

JWT de familia provisionada, emisor/audiencia/caducidad como API 0.2.0. Un operador
crea el enlace con `python -m app.admin token --family UUID --hours 8 --web-url
https://dominio-familiar.example`. El enlace contiene un token temporal sensible:
entregar solo por canal privado. El cliente elimina el fragmento inmediatamente,
lo guarda solo en memoria y no almacena datos familiares offline. Al recargar hay
que reabrir enlace. Login familiar renovable y recuperación de acceso quedan pendientes.

La API no crea ni migra esquema al arrancar. Tras backup y ensayo explícito,
`python -m app.admin migrate-db` agrega tres tablas nuevas al esquema 0.2.0;
conserva migración anterior y datos. No se ha ejecutado sobre datos productivos.
El snapshot se sustituye por familia; auditoría requiere política de retención
operativa antes de producción. No se expone fuente arbitraria desde HTTP usuario.

## Pantalla y despliegue

React+Vite, `cd web && npm ci && npm run build`; FastAPI sirve `web/dist` si existe.
En desarrollo Vite reenvía `/api` a localhost:8000. Docker compila la pantalla en
etapa Node y copia el resultado al runtime Python. `SHOPPING_WEB_DIR` es override
operativo de ruta. PWA con manifest y shell; no cachear API privada/tokens.
No hay despliegue, compra ni importación de ticket real por este cambio.

## Asesor y ahorro

`mode=bounded_rules`, `llm_used=false`: un flujo de herramientas limitado con
política determinista, sin LLM, pago ni pedido. Diferencia potencial = comparación
contra el desembolso más caro entre opciones equivalentes observadas para los
mismos artículos cubiertos. No representa ahorro logrado ni la mejor cesta de
una zona geográfica. No incluye viaje, entrega, precios de fuentes ausentes ni consumo real.
Presupuesto solo se declara cumplido cuando la cesta tiene cobertura completa.
No hay predicción de caducidad/consumo ni reserva del congelador en este módulo.

## Condición de publicación
Despliegue bloqueado hasta validar alta inicial, edición e independencia de perfiles y bloqueo de recogida incompleta. Los datos públicos son sintéticos. Los antiguos recibos de fuentes vinculados a un caso particular han sido retirados; no acreditan precios actuales. Ver [privacidad](../data-privacy.md).
