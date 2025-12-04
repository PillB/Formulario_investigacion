# Fixtures de guardado

El archivo `test-save.json` replica la estructura que devuelve `_serialize_full_form_state` (claves `dataset` y `form_state`) y cumple las reglas de negocio descritas en el design doc:

- IDs válidos: caso `AAAA-NNNN`, reclamos `CXXXXXXXX`, riesgos `RSK-XXXXXX`, normas `XXXX.XXX.XX.XX`, colaborador letra+5 dígitos y analítica contable de 10 dígitos (43/45/46/56).
- Fechas coherentes (`YYYY-MM-DD`), sin valores futuros y con ocurrencia anterior al descubrimiento.
- Montos no negativos con dos decimales, sumas que cuadran (`investigado = pérdida + falla + contingencia + recuperado`), pago de deuda ≤ investigado y contingencia = investigado en productos de crédito.
- Combinaciones de productos que cubren cliente+miembro, solo cliente y solo miembro.

Para un autosave listo para usar con valores que respetan catálogos/autocompletar (clientes y colaboradores presentes en los `*_details.csv`), utiliza `autosave-valid.json` en este mismo directorio.

## Uso rápido
1. Inicia la aplicación (`python -m main`).
2. En la pestaña **Acciones**, pulsa **Cargar formulario** y selecciona `tests/fixtures/test-save.json`.
3. Verifica que los combobox y campos de texto se poblaban (incluye `form_state` con variables Tk para restaurar selecciones).
4. Ejecuta **Guardar y enviar** para validar y generar los reportes con datos consistentes.
