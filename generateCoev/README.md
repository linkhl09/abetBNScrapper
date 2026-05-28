# Script de Procesamiento de Coevaluaciones

Este script en Python procesa archivos de Excel con calificaciones de coevaluación y genera un archivo CSV consolidado con el formato requerido por bloque neón para subir las notas. Extrae la información de la hoja `Grades per student`.

## Requisitos Previos

Asegúrate de tener Python instalado en tu sistema. Luego, instala las dependencias necesarias ejecutando el siguiente comando en la terminal:

```bash
pip install -r requirements.txt
```

*(Esto instalará las librerías `pandas` y `openpyxl` que el script necesita para funcionar).*

## Preparación de los Archivos

1. Crea una carpeta llamada `coev` en el mismo directorio donde se encuentra el script `process_coev.py`.
2. Coloca todos los archivos de Excel (`.xlsx` o `.xls`) que deseas procesar dentro de la carpeta `coev`.

## Uso del Script

Puedes ejecutar el script desde la terminal de la siguiente manera básica:

```bash
python process_coev.py
```

Al ejecutarlo sin argumentos, el script hará lo siguiente por defecto:
- Leerá todos los archivos Excel que estén dentro de la carpeta `coev/`.
- Generará un archivo de salida llamado `output.csv`.
- Asignará el nombre `"Coevaluación Proyecto 1 Points Grade"` a la tercera columna.

### Opciones y Argumentos

El script permite modificar su comportamiento mediante los siguientes argumentos opcionales:

- **`-i`** o **`--input-dir`**: Permite especificar una carpeta diferente donde buscar los archivos Excel.
  - *Ejemplo:* `python process_coev.py -i otra_carpeta_de_excels`

- **`-o`** o **`--output-file`**: Permite especificar un nombre diferente para el archivo CSV generado.
  - *Ejemplo:* `python process_coev.py -o notas_consolidadas.csv`

- **`-c`** o **`--column-name`**: Permite seleccionar el tipo de evaluación para cambiar el título de la columna en el CSV generado. **Solo acepta dos abreviaturas**:
  - `P1` (Proyecto 1 - Opción por defecto)
  - `EA` (Expoandes)
  - *Ejemplo:* `python process_coev.py -c EA`

### Ejemplo de Uso Completo

Si deseas procesar los excels ubicados en una carpeta llamada `archivos_coev`, guardar el resultado en `notas_expoandes.csv` y usar el título de columna para Expoandes, el comando sería:

```bash
python process_coev.py -i archivos_coev -o notas_expoandes.csv -c EA
```
