# ANÁLISIS DE TABLA 0x2E - ESTRUCTURA DE PLAYLISTS

# ================================================

## PATRÓN DETECTADO

Cada "row" en la tabla 0x2E parece contener MÚLTIPLES entradas de playlist concatenadas.

### Ejemplo de ROW 1 (Offset 36)

```
Offset 12-15: ID = 5
Offset 16-19: Valor = 9  
Offset 25+:   String = "Minimal Vol 1"

Offset 48-51: ID = 1
Offset 52-55: Valor = 14
Offset 61+:   String = "Ave Fenix22"

Offset 80-83: ID = 3
Offset 84-87: Valor = 1
Offset 93+:   String = "mh_tech_vol1"
```

## ESTRUCTURA DE CADA ENTRADA

```
[12 bytes padding/header]
[4 bytes: Playlist ID]
[4 bytes: Unknown (track count?)]
[4 bytes: Padding]
[1 byte: String length]
[N bytes: Playlist name (null-terminated)]
[Padding to align]
```

## NOMBRES ENCONTRADOS EN TABLA 0x2E

### LIMPIOS (sin basura)

- Minimal Vol 1
- mh_tech_vol1
- House Vol5
- House Vol6
- House Vol7

### CON BASURA

- Ave Fenix**22** (debería ser "Ave Fenix2")
- Acid Vol**21** (debería ser "Acid Vol2")
- Acid Vol2 **111** (ghost duplicate)

## OBSERVACIONES CLAVE

1. **La tabla 0x2E NO es la fuente de nombres limpios** - también tiene basura
2. **Los nombres están CONCATENADOS** en cada row (múltiples playlists por row)
3. **El byte antes del string** (ej: 0x1D, 0x17, 0x15) podría ser:
   - Longitud del string
   - Tipo/flag del string
   - Offset relativo

## HIPÓTESIS

La "basura" (13, 15, 22, 21, 111) podría ser:

- **Versiones de playlist**: Rekordbox guarda historial de cambios
- **IDs de carpeta padre**: El "13" en "Hard Vol13" podría ser el folder ID
- **Metadata de sincronización**: Timestamps o sync counters

## PATRÓN DE LIMPIEZA OBSERVADO

```
Hard Vol13 → Hard Vol1  (remove trailing single digit)
Hard Vol15 → Hard Vol1  (remove trailing single digit)
Ave Fenix22 → Ave Fenix2 (remove trailing single digit)
Acid Vol21 → Acid Vol2  (remove trailing single digit)
#Progressive → Progressive (remove leading #)
Acid Vol2 111 → [filtered out] (ghost duplicate)
```

## RECOMENDACIÓN

El regex actual `(Vol\d)(\d)$` funciona para TU caso específico, pero para hacerlo robusto:

### Opción A: Regex más agresivo

```python
# Remove ANY trailing digits after "Vol" + single digit
name = re.sub(r'(Vol\d+?)(\d+)$', r'\1', name)
```

### Opción B: Buscar tabla alternativa

Investigar si existe otra tabla (0x14, 0x16, etc.) que contenga solo nombres display.

### Opción C: Usar longitud de string

El byte antes del string podría indicar la longitud "real" vs "total".
Si string length byte = 0x15 (21) pero el string es "Acid Vol21" (10 chars),
entonces los últimos chars son basura.

## PRÓXIMOS PASOS

1. ¿Quieres que pruebe la Opción A (regex más agresivo)?
2. ¿Investigamos otras tablas (0x14, 0x16)?
3. ¿Analizamos el byte de longitud para detectar basura automáticamente?
