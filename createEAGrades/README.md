# Consilidador de Notas de ExpoAndes 📊

Este script está diseñado para facilitar enormemente el proceso de subir las notas de **ExpoAndes** a la plataforma de calificaciones (Bloque Neón). 

El archivo Excel principal se encarga de calcular y consolidar los resultados de los formatos de evaluación del jurado y profesores. Este script toma ese consolidado y lo asocia automáticamente con los códigos y correos de los estudiantes exportados de Bloque Neón para generar un archivo CSV listo para subir.

---

## 🛠️ Requisitos e Instalación

Para ejecutar el script, asegúrate de tener configurado el entorno virtual (`.venv`) e instaladas las dependencias.

1. **Instalar Dependencias**:
   Instala las librerías necesarias especificadas en el archivo `requirements.txt`:
   ```bash
   .venv/bin/pip install -r requirements.txt
   ```

---

## 🚀 Instrucciones de Uso y Ejecución

Por defecto, si ejecutas el script sin parámetros, buscará los archivos predeterminados en la carpeta actual:
- Excel de Notas: `Evaluación expoandes 202610.xlsx`
- CSV de Calificaciones: `GradesTest.csv`
- CSV de Salida: `consolidated_grades_EA.csv`

### Ejecución Estándar (Archivos por Defecto):
```bash
.venv/bin/python consolidate_grades.py
```

---

## ⚙️ ¿Cómo especificar otros nombres de archivos?

El script cuenta con argumentos de línea de comandos para que puedas especificar diferentes rutas de Excel, CSV de entrada, o cambiar el nombre del archivo de salida. Esto es especialmente útil para próximos semestres.

### Opciones Disponibles:
- `-e` o `--excel`: Ruta al archivo Excel consolidado (ej. `"Evaluación expoandes 202610.xlsx"`).
- `-c` o `--csv`: Ruta al archivo CSV exportado de Bloque Neón (ej. `"GradesTest.csv"`).
- `-o` or `--output`: Nombre o ruta del archivo CSV de salida resultante.

### Ejemplos de uso personalizado:

1. **Especificar otro archivo Excel**:
   ```bash
   .venv/bin/python consolidate_grades.py -e "Evaluacion_Expoandes_202620.xlsx"
   ```

2. **Especificar tanto un Excel como un CSV de entrada diferentes**:
   ```bash
   .venv/bin/python consolidate_grades.py -e "Evaluacion_2026_20.xlsx" -c "Calificaciones_BN.csv"
   ```

3. **Especificar todos los parámetros incluyendo un nombre de salida personalizado**:
   ```bash
   .venv/bin/python consolidate_grades.py -e "Evaluacion.xlsx" -c "Entrada.csv" -o "Notas_Subir_Expoandes.csv"
   ```

4. **Ver la ayuda de los comandos**:
   ```bash
   .venv/bin/python consolidate_grades.py --help
   ```

---

## 🔍 ¿Cómo funciona por detrás?

1. **Lectura del Excel**:
   - Accede a la pestaña **`ResultadosProfes`**.
   - Busca la tabla con nombre **`NotasEA`** (debe ser un objeto de Tabla oficial en Excel).
   - Extrae la relación de `Sección`, `Grupo`, y las columnas correspondientes a las calificaciones de **`Poster`** y **`Feria`**.

2. **Lectura del CSV**:
   - Lee el CSV exportado de Bloque Neón, el cual contiene columnas clave como `OrgDefinedId`, `Email` y `ExpoAndes` (que almacena la sección y grupo en formatos como `"Sección X - Grupo Y"` o `"ExpoaAndes Sección X - Grupo Y"`).

3. **Match Dinámico**:
   - Extrae el identificador de la sección y el grupo del texto en el campo `ExpoAndes` del CSV usando expresiones regulares.
   - Normaliza los nombres para eliminar espacios en blanco adicionales (por ejemplo, empareja correctamente `"Omega "` con `"Omega"`).
   - Genera el `Username` recortando la sección previa al `@` en el correo electrónico.

4. **Generación del CSV de salida**:
   - Genera un archivo con las columnas exactas requeridas por Bloque Neón para la carga masiva: `OrgDefinedId`, `Username`, `Poster Expoandes Points Grade`, `Feria Points Grade` y el indicador de fin de línea `#`.
