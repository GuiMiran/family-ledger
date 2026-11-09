# Frontal familiar y captura 0.4.0

## Producto

Inicio, Despensa, Cámara, Menús y Ahorro usan navegación inferior móvil. Perfil y
comparador son accesibles desde la misma aplicación, conservando preferencias
privadas. La referencia visual aporta tarjetas blancas, fondo suave, tipografía
legible y acción de cámara central; no se copian cifras, nombre, compras ni
preferencias de las capturas del propietario.

Home y Ahorro usan GET /api/v1/dashboard: registros confirmados propios, serie de
seis meses y agrupación por supermercado conocido. Mes sin tickets no significa
que la familia haya gastado cero. Ahorro logrado/desperdicio/descuentos brutos no
calificados siguen nulos; no se fabrican KPIs. Despensa es la proyección existente
de compras confirmadas, no un saldo físico de consumo. Menús, congelación y
caducidad predictiva permanecen pendientes de motor funcional.

## Foto y revisión

POST /api/v1/receipts/extract requiere JWT de familia provisionada y multipart
con un único campo image. Admite JPEG/PNG/WebP de hasta 10 MiB y 20 MP; HEIC no se
soporta. Se valida firma/decodificación y se normaliza orientación EXIF, RGB y
metadatos antes de OCR. Solo se admite una extracción simultánea por proceso;
las demás reciben 429/Retry-After. Tesseract local usa spa+cat+eng, timeout20s y
salida máxima500kB. No hay envío de imagen a una IA externa ni precio por llamada
a proveedor OCR; consume recursos del servidor. Límites de CPU/memoria del
servicio siguen siendo necesarios; probar fotografías reales antes de abrir
públicamente el piloto. Docker limita hilos con OMP_THREAD_LIMIT=1.

La extracción devuelve parsed_receipt y metadata del proveedor, con confianza
OCR nula porque no se ha medido una probabilidad calibrada. La confianza del
parser es distinta. Fotos ilegibles, formatos de ticket no reconocidos o totales
inconsistentes piden nueva captura, sin reintroducción manual completa. No se
promete cobertura universal de tickets españoles.

La extracción no escribe compras, no actualiza existencias y limpia archivos
temporales. El original no se retiene en disco, BD ni object storage. Guardar
imagen original requiere un futuro contrato de almacenamiento privado/retención.
El borrador permanece en memoria del cliente y solo se guarda mediante POST
/api/v1/receipts existente, con clave idempotente por borrador/reintento. Pendientes
sin resolver permanecen pendientes; validación financiera del servidor prevalece.

## Ejecución y verificación

Dependencias runtime: Pillow y python-multipart; Tesseract y datos de idiomas
se instalan en la imagen Docker. Para desarrollo, instalar esos binarios/datos
del sistema. No se migra esquema automáticamente al importar ni al arrancar.
El nuevo dashboard/OCR no añade tablas; conserva el esquema privado existente.

Tests sintéticos: tests/test_capture.py, test_capture_real.py, test_dashboard.py;
regresión y PostgreSQL dedicados en CI. El smoke real renderiza una imagen nueva
de un ticket enteramente sintético y verifica OCR→borrador→compra→inventario sin
duplicar en reintentos. No usa fotos privadas. Browser smoke verifica navegación,
alta y captura con datos sintéticos en una base de datos efímera.

Publicación del código no actualiza una instancia fijada a un commit. Revisar y
fusionar PR, desplegar la revisión aprobada y comprobar HTTP/BD antes de anunciar
la actualización. Mantener perfiles/compras fuera de Git y no importar ejemplos.
