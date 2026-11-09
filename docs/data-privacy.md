# Datos privados, ejemplos y publicación

El repositorio público contiene código reutilizable, contratos y pruebas o demostraciones enteramente sintéticas. No es un archivo de tickets ni de preferencias de una familia. Los nombres, códigos postales, cestas, transacciones, fotos, identificadores y observaciones de precios particulares se guardan en almacenamiento privado bajo la identidad de la familia.

## Separación

| Categoría | Ubicación y uso |
|---|---|
| Código y contratos | Repositorio público; ninguna familia implícita |
| Ejemplos sintéticos | Archivos JSON explícitos y pruebas; nunca valores iniciales de producción |
| Perfiles y compras reales | Base de datos privada con acceso autenticado por familia |
| Exportaciones y secretos | Fuera de Git, con control de acceso y política de retención |

GET del perfil usa exclusivamente la familia autenticada del JWT: devuelve su registro persistido o un estado de alta vacío. No toma una identidad familiar del cuerpo de la petición. Una familia nueva recibe un perfil vacío. Debe configurar su nombre, zona, tiendas y cesta; el sistema no toma valores de otra familia ni del prototipo. La recogida de fuentes y el asesor requieren configuración completa. La demostración antigua se ha sustituido por `prototype/demo-data.json`, con artículos y valores ficticios creados de nuevo, sin copiar ni escalar una compra particular. El ejemplo `data/demo/shopping-profile.json` se carga solo por elección explícita y declara `auto_load=false`; nunca se aplica al GET de una familia nueva. El prototipo está rotulado **NON-PRODUCTION SYNTHETIC DEMO** y no conecta servicios.

## Evidencia histórica redactada

La corrección de privacidad elimina el registro público de una compra particular y retira las observaciones de fuentes vinculadas a un caso privado. Los informes históricos conservan el método, obligaciones y hallazgos, pero sus copias públicas han sido redactadas. Los registros sensibles se sustituyen por avisos de retirada; no se fabrica una salida PASS en su lugar. Las huellas previas de archivos modificados o retirados dejan de acreditar la copia actual. Los resultados que se conservan describen ejecuciones históricas, no una nueva evaluación del cambio de privacidad.

Los informes no se presentan como originales byte a byte ni se recertifican. Las baselines antiguas describen únicamente su revisión histórica; el cambio autorizado de privacidad requiere su propio inventario y verificación. Una prueba con datos sintéticos acredita ese comportamiento acotado, no precios reales, disponibilidad comercial ni una operación productiva.

## Historial y despliegue

Esta modificación corrige el árbol actual. **No elimina datos ya publicados en commits antiguos, descripciones de pull requests, comentarios, cachés, clones o registros externos.** Borrar ese historial requiere una operación independiente revisada, coordinación de copias y evaluación de referencias; no se ha realizado por este parche.

El despliegue está bloqueado hasta completar y verificar el alta de perfiles privados, la edición independiente de familias y el bloqueo de recogida con configuración incompleta. No se importa automáticamente ningún ticket privado ni se publica una cuenta de demostración. Las invitaciones y tokens se entregan por canales privados y no se guardan en el repositorio.
