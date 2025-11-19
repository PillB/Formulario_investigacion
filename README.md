Manual de Uso y Pruebas – Aplicación de Gestión de Casos de Fraude (Tkinter)
Este documento explica cómo utilizar y probar la versión de escritorio de la aplicación de gestión de casos de fraude implementada en Python usando Tkinter. Está orientado a usuarios y evaluadores no técnicos que necesiten comprobar que todas las funcionalidades del sistema se comportan como se espera.
1. Requisitos previos
Python 3.7 o superior instalado en el equipo.
Dependencia adicional: instala `python-docx` para habilitar la generación del informe en Word (`pip install python-docx`).
Carpeta `external drive/` ubicada junto a este repositorio. La aplicación intenta crearla si no existe, pero conviene verificar los permisos porque allí se escriben los respaldos automáticos.
Archivos CSV de referencia ubicados en la misma carpeta que el paquete (BASE_DIR):
client_details.csv: datos maestros de clientes para autopoblar.
team_details.csv: datos maestros de colaboradores para autopoblar.
clientes_masivos.csv, colaboradores_masivos.csv, productos_masivos.csv, datos_combinados_masivos.csv – ejemplos para importación masiva.
riesgos_masivos.csv, normas_masivas.csv, reclamos_masivos.csv – ejemplos para importación de riesgos, normas y reclamos.
2. Ejecución de la aplicación
Abrir una terminal y navegar hasta la carpeta donde se encuentran los archivos.
Ejecutar el comando:
python -m main
La ventana principal mostrará varias pestañas: Caso, Clientes, Colaboradores, Productos, Riesgos, Normas, Análisis y Acciones.
La aplicación cargará automáticamente el autosave más reciente (si existe) y mostrará los datos guardados. Para empezar un caso nuevo, utilice el botón Borrar todos los datos en la pestaña de acciones.
3. Completar un caso
En la pestaña Caso, introduzca el número de caso (AAAA-NNNN), seleccione el tipo de informe (Gerencia, Interno o Credicorp) y elija las categorías y modalidad de la taxonomía de fraude. Seleccione también el canal y el proceso impactado. Estas opciones inicializan valores predeterminados para todos los productos.
Los campos se validan al perder el foco. Si hay un error (formato incorrecto, campo obligatorio vacío, etc.), aparecerá un mensaje en rojo debajo del campo o en la parte inferior de la ventana. Corrija cualquier error antes de continuar.
4. Añadir clientes
Vaya a la pestaña Clientes y pulse Añadir cliente para crear un registro.
Seleccione el tipo de ID (DNI, Pasaporte, RUC, Carné de extranjería, No aplica) e introduzca el número en el campo ID del cliente. Al perder el foco, la aplicación consultará el archivo client_details.csv y autopoblará el tipo de ID, el flag, teléfonos, correos, direcciones y accionado si encuentra el ID. Puede editar estos campos manualmente.
Escriba teléfonos, correos y direcciones separados por punto y coma ;. Seleccione el Flag de cliente (Involucrado, Afectado o No aplica).
Use Eliminar cliente para borrar una entrada y confirmar la acción.
Repita el proceso para cada cliente necesario.
5. Añadir colaboradores (team members)
Abra la pestaña Colaboradores y pulse Añadir colaborador para crear un registro.
Escriba el ID del colaborador (una letra seguida de cinco dígitos). Al perder el foco, la aplicación busca en team_details.csv y autopuebla los campos de división, área, servicio, puesto, nombre de agencia y código de agencia. Si el ID no se encuentra, se registra una advertencia en los logs.
Seleccione el Flag del colaborador (Involucrado, Relacionado o No aplica), el tipo de falta y el tipo de sanción.
Elimine un colaborador con Eliminar colaborador y confirme.
6. Crear productos
En la pestaña Productos, pulse Añadir producto para cada cuenta o contrato afectado. Para que el botón esté activo debe existir al menos un cliente y un colaborador válidos.
Introduzca el ID del producto (longitud 13, 14, 16 o 20 caracteres o mayor a 100).
Seleccione el Cliente asociado. El producto debe pertenecer a un único cliente.
Ajuste las categorías, canal y proceso si difieren del caso. Seleccione la Fecha de ocurrencia y la Fecha de descubrimiento (orden correcto y no pueden ser futuras).
Introduzca el Monto investigado y los montos parciales de pérdida, falla, contingencia, recuperado y pago de deuda. La suma de pérdida, falla, contingencia y recuperado debe ser igual al monto investigado. Si el producto es un crédito o tarjeta, el monto de contingencia debe ser igual al investigado.
Seleccione la Tipo de moneda (Soles, Dólares o No aplica). Seleccione el Tipo de producto según la lista.
Si hay montos de pérdida, falla o contingencia positivos, introduzca el ID de reclamo (C+8 dígitos), el Nombre analítica y el Código analítica (10 dígitos comenzando con 43, 45, 46 o 56). De lo contrario estos campos son opcionales.
Seleccione en Cliente accionado una o más tribus/áreas que accionaron el reclamo (Ctrl+clic para seleccionar varios).
Use Añadir involucrado para crear filas que asignan montos a uno o varios colaboradores. Seleccione el colaborador y escriba el monto asignado. No repita colaboradores en la misma lista.
Elimine productos con Eliminar producto y confirme.
7. Riesgos y normas
Riesgos
En la pestaña Riesgos, pulse Añadir riesgo para crear registros. Cada riesgo tiene un ID (formato RSK-XXXXXX), un líder, una descripción, una criticidad (Bajo, Moderado, Relevante, Alto, Crítico), una exposición residual en US$ y planes de acción separados por ;. Puede usar Eliminar para borrar un riesgo.
Valide que los IDs de riesgo sean únicos y que los planes no se repitan entre riesgos.
Normas
En la pestaña Normas, use Añadir norma para crear registros. Introduzca el número de norma (XXXX.XXX.XX.XX) o déjelo en blanco para que se genere un correlativo aleatorio. Agregue una descripción y la fecha de vigencia (no puede ser futura). Puede eliminar normas con el botón Eliminar.
8. Análisis y narrativas
En la pestaña Análisis, escriba las narrativas de Antecedentes, Modus operandi, Hallazgos principales, Descargos del colaborador, Conclusiones y Recomendaciones y mejoras. Estos campos aceptan texto libre.
9. Acciones y gestión de versiones
En la pestaña Acciones encontrará los botones:
Guardar y enviar: Valida todos los datos. Si no hay errores, la aplicación coloca automáticamente los archivos CSV (casos, clientes, colaboradores, productos, reclamos, asignaciones, riesgos, normas, análisis, logs), el JSON completo del caso, el informe en Markdown y el informe en Word (`<id_caso>_informe.docx`) bajo `BASE_DIR/exports/` usando el ID del caso como prefijo y sin pedirte que elijas una carpeta. Después se espejan esos mismos archivos dentro de `external drive/<id_caso>/` para mantener un respaldo local, mostrando una advertencia sólo si la copia secundaria falla.
Cargar versión: Permite elegir un archivo JSON generado previamente para restaurar el formulario al estado guardado.
Borrar todos los datos: Elimina el contenido del formulario y el autosave tras confirmación.
Importar CSV: Botones para cargar clientes, colaboradores, productos, combinados, riesgos, normas y reclamos. Seleccione el archivo adecuado y revise que los datos aparezcan en sus pestañas correspondientes. Se omitirán registros duplicados.
Además, la aplicación guarda versiones temporales (<id_caso>_temp_<timestamp>.json) cada vez que se edita un campo. Estos archivos se crean en la misma carpeta del script para tener un historial de cambios.
Los eventos (navegación, validación, advertencias) se registran en un log interno. Al usar Guardar y enviar, se exportan en logs.csv para su análisis.
10. Persistencia y respaldos
`BASE_DIR` corresponde a la carpeta raíz del proyecto (donde viven `app.py`, `main.py` y los CSV base). Allí se almacenan el autosave principal (`autosave.json`), el JSON canónico del caso (`<id_caso>_version.json`), los reportes Markdown/Word (`<id_caso>_informe.md` y `.docx`) y los CSV exportados que describen cada entidad.

Cada vez que se dispara un guardado o un autosave temporal, la aplicación duplica la información en la carpeta `external drive/<id_caso>/`. Ese espejo contiene los logs (`logs.csv`), los JSON temporales y los mismos archivos exportados que quedan en `BASE_DIR/exports/`. Gracias a este esquema, siempre hay una copia lista para mover a un medio externo real; si alguna escritura falla, el sistema lo registra y muestra la alerta correspondiente.
11. Pruebas de validación de negocio
Para garantizar que las reglas se apliquen correctamente, pruebe los siguientes escenarios:
Clave técnica duplicada: Cree dos productos con el mismo ID, cliente, colaborador, fecha de ocurrencia e ID de reclamo. El sistema debe advertir de la duplicidad.
Fechas fuera de orden: Ponga la fecha de descubrimiento antes de la de ocurrencia. Debe aparecer un error.
Reclamo obligatorio: Ingrese un monto de pérdida mayor a cero sin rellenar los campos de reclamo; el sistema exigirá completarlos.
Suma de montos: Introduzca valores que no sumen al monto investigado. Se mostrará un error y deberá corregirlos.
Contingencia en créditos y tarjetas: Seleccione “Crédito personal” o “Tarjeta de crédito” y asegúrese de que la contingencia sea igual al monto investigado. Si no lo es, se marca error.
Código analítica: Introduzca un código analítica de menos de 10 dígitos o que no empiece por 43, 45, 46 o 56. Debería mostrar un error.
Validación de IDs: Escriba IDs de cliente, colaborador o riesgo con formatos incorrectos; los campos deben marcarse en rojo y aparecer un mensaje explicando el formato correcto.
Autopoblado: Introduzca un ID de cliente o colaborador que figure en los archivos client_details.csv o team_details.csv. Sus datos se rellenan automáticamente. Escriba uno inexistente y compruebe que aparece una advertencia en el log.
Advertencia de Fraude Externo: Seleccione “Fraude Externo” en la categoría Nivel 2 y verifique que se muestre el mensaje de advertencia sobre reclamos externos.
Guardar y cargar: Llene el formulario con un caso de ejemplo y utilice “Guardar y enviar”. Examine los archivos CSV generados para comprobar que las relaciones se representan correctamente. Luego borre los datos, pulse “Cargar versión” y elija el archivo JSON recién guardado; el formulario debe reconstruirse exactamente como antes.
12. Análisis de logs
Los eventos registrados en logs.csv incluyen:
timestamp: Fecha y hora en que ocurrió el evento.
tipo: "navegacion" para cambios de campos, "validacion" para errores y advertencias.
mensaje: Descripción del evento (qué campo se modificó, si hubo errores, etc.).
Utilice esta información para detectar los puntos del formulario donde los usuarios cometen más errores o tardan más tiempo, lo que ayudará a mejorar la usabilidad y las validaciones.

Por defecto la aplicación escribe los eventos tanto en `logs.csv` (junto al código fuente) como en `external drive/logs.csv`. Si necesitas evitar escrituras locales, actualiza la constante `STORE_LOGS_LOCALLY` en `settings.py` a `False`. En ese modo la bitácora sólo se persiste en la unidad externa simulada y la aplicación mostrará una advertencia si alguno de los destinos falla al escribir.

Con esta guía y el script proporcionado, podrá recrear la gestión de casos de fraude en un entorno de escritorio, probar todas las reglas de negocio, importar datos masivamente y analizar los registros para mejorar la experiencia del usuario.

13. Cobertura enfocada en guardado/exportación/logs
Para verificar automáticamente las rutas críticas de guardado, exportación y bitácoras sin ejecutar toda la batería de pruebas, puedes lanzar:

```
pytest --cov=app --cov=ui --cov-report=term-missing
```

Este comando imprime un resumen de cobertura en la terminal destacando qué porciones de `app.py` y los módulos de `ui/` están cubiertos por las pruebas relacionadas a `save_and_send`, respaldos en la “unidad externa” y el flujo de logs. A raíz de los cambios de almacenamiento se añadieron casos como `tests/test_save_and_send.py::test_save_temp_version_mirrors_to_external_drive` y `tests/test_save_and_send.py::test_flush_log_queue_writes_external_when_local_blocked`, por lo que asegúrate de contar con la carpeta `external drive/` y con las dependencias `pytest`, `pytest-cov` y `python-docx` antes de ejecutar la cobertura.

14. Instrucciones para CI y automatizaciones
- Asegúrate de instalar `python-docx` antes de ejecutar `pytest` para que la exportación de Word funcione también en los entornos de integración continua.
- Conserva como artefactos tanto `*_informe.md` como `*_informe.docx`, ya que las pruebas verifican que ambos se generen y se copien a la carpeta espejo.
