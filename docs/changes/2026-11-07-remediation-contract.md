# Corrección autorizada · contrato previo a implementación

El usuario indicó retomar las correcciones «Ahora». Esta fase corrige defectos y
conecta el flujo de tickets; el diagnóstico histórico del commit 0616d2b se conserva.

1. Visibilidad: una familia puede resolver productos globales (`family_id=NULL`)
   y propios; nunca productos privados ajenos. Se aplica a exact/fuzzy, propuestas
   IA, alias aprendidos e historial de precios. El mercado específico precede al
   alias sin mercado; la familia propia precede al global a igualdad de mercado.
   Los alias globales heredados cuya procedencia privada no pueda demostrarse se
   ponen en cuarentena durante migración hasta revisión explícita del propietario;
   no se publican automáticamente ni se inventa su familia de origen.
2. Instalación: `pip install -e ".[dev]"` debe instalar app, ORM y driver PostgreSQL.
   API usa sesiones SQLAlchemy síncronas con URL normalizada a psycopg; SQLite
   queda disponible para pruebas/desarrollo. Datos persistentes requieren un volumen.
3. Identidad: acceso a compras, inventario y analítica mediante token Bearer
   firmado con secreto de despliegue; familia derivada de token, nunca del cuerpo.
   Sin secreto válido no se permite acceso a esos datos. No se introduce registro
   público de familias ni un endpoint que emita tokens arbitrarios.
4. Ingesta: guardar ParsedReceipt validado devuelve compra confirmada o pendiente
   de revisión según campos. Se valida reconciliación independientemente de la
   confianza enviada por el cliente. Fecha ausente no se inventa.
5. Idempotencia: una clave por familia y cuerpo; reintento idéntico no duplica
   ticket, líneas, evento ni inventario; misma clave con distinto contenido produce
   conflicto. Operación completa transaccional, rollback ante fallo.
6. Confirmación/inventario: solo compras válidas confirmadas generan evento interno
   persistido y movimientos de inventario una vez; pendientes no crean existencias.
   Corrección posterior de una compra pendiente requiere nueva validación. Las
   consultas y proyecciones se filtran por familia.
7. Analítica: totales de compras confirmadas separados de pendientes; una fecha
   desconocida no se atribuye a un periodo. El histórico conserva precios/unidades
   tal como el parser; no se afirma comparación €/kg entre formatos distintos.

Criterios de cierre: desafío A/B antes fallido ahora pasa; se demuestra conservación
de descripción/importe en líneas no normalizadas; instalación limpia funciona;
pruebas negativas de auth, idempotencia, reconciliación, rollback y privacidad;
prueba persistente tras recrear sesiones y prueba PostgreSQL en CI si no hay motor
local disponible. OCR externo, menús IA y comparación normalizada por formato son
capacidades futuras que exigen proveedores/reglas propios, no se cierran por estas
correcciones. No hay despliegue ni importación productiva en esta fase.

Recuperación: revert del cambio funcional en un entorno sin datos, o restauración
del respaldo previo para un esquema existente. Ninguna actualización destructiva
automática de esquema; se documenta el procedimiento de actualización.
