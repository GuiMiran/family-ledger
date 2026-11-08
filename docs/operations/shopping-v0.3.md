# Comparador familiar 0.3.0 · operación y límites

## Recorrido

La familia abre un enlace temporal, ajusta CP/cesta/cantidades/tamaño de huevos,
guarda y pulsa actualizar. Ve hasta tres opciones globales o por supermercado
con €/kg, €/l o €/unidad, desembolso del formato, condiciones, fecha y enlace.
Las cantidades iniciales (1 kg/l o 12 huevos) son referencias editables y no una
previsión de consumo. El asesor elige menor desembolso para esa cantidad entre
ofertas compatibles y muestra sobrantes. Una recomendación no es una compra.

Perfil inicial: CP 08038; Mercadona, Makro, Lidl, DIA, Carrefour y Condis. Leche
entera, vacuno fileteado y queso fresco confirmados. Puleva Max es grupo separado.
Arroz largo y pasta seca de trigo son referencias editables. Tamaño de huevos
pendiente. El corte concreto de vacuno y variantes exactas no se infieren; si la
fuente no acredita equivalencia, queda hueco. Menos de tres ofertas es resultado
válido y visible. El comparador no mezcla una leche especial con leche normal.

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
Puleva Max no disponible y vacuno sin corte conocido. No son precios cero.

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
Barcelona. No incluye viaje, entrega, precios de fuentes ausentes ni consumo real.
Presupuesto solo se declara cumplido cuando la cesta tiene cobertura completa.
No hay predicción de caducidad/consumo ni reserva del congelador en este módulo.
