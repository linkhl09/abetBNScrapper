import argparse
import pandas as pd
import qrcode
from PIL import Image
import os

def create_dirs():
    os.makedirs("qrs", exist_ok=True)

def process_data(df):
    create_dirs()
    count = 0
    for index, row in df.iterrows():
        name = str(row['groupName']).replace("/", "_").replace("\\", "_")
        url = row['formsURL']
        
        if pd.isna(url) or not str(url).strip():
            print(f"Saltando {name} debido a que no tiene URL")
            continue
            
        print(f"Generando y redimensionando QR para {name}...")
        # 1. Generar QR
        img = qrcode.make(url)
        
        # 2. Redimensionar QR y guardar directamente
        # Convertir a RGB por si acaso tiene canal Alpha (necesario para JPEG)
        if img.mode != "RGB":
            img = img.convert("RGB")
            
        imResize = img.resize((400, 400))
        
        # Guardar como JPEG solo en la carpeta qrs
        resized_path = f"qrs/{name}.jpg"
        imResize.save(resized_path, 'JPEG', quality=90)
        count += 1
        
    print(f"\nProceso finalizado. Se generaron {count} códigos QR.")

def from_csv(csv_path):
    print(f"Leyendo datos desde CSV: {csv_path}")
    df = pd.read_csv(csv_path)
    
    if 'groupName' not in df.columns or 'formsURL' not in df.columns:
        raise ValueError("El archivo CSV debe contener las columnas 'groupName' y 'formsURL'.")
        
    process_data(df)

def from_excel(excel_path):
    print(f"Leyendo datos desde Excel: {excel_path} (Hoja: 'Evaluación')")
    # header=1 indica que la segunda fila (índice 1) contiene los encabezados
    df = pd.read_excel(excel_path, sheet_name='Evaluación', header=1)
    
    required_cols = ['Stand', 'Nombre', 'URLs pre llenadas ']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"El archivo Excel debe contener la columna '{col}'. Columnas encontradas: {df.columns.tolist()}")
            
    # Filtrar filas donde Stand o Nombre sean nulos para evitar errores de concatenación
    df = df.dropna(subset=['Stand', 'Nombre'])
    
    # groupName = "Stand " + Columna "Stand" + "-" + Columna "Nombre"
    # Convertimos a string por si 'Stand' es numérico. Se elimina el ".0" en caso de que pandas lo lea como float.
    stands = df['Stand'].astype(str).str.replace(r'\.0$', '', regex=True)
    df['groupName'] = "Stand " + stands + "-" + df['Nombre'].astype(str)
    df['formsURL'] = df['URLs pre llenadas ']
    
    process_data(df)

def main():
    parser = argparse.ArgumentParser(description="Script para generar y redimensionar QRs desde un CSV o Excel.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--csv", type=str, help="Ruta al archivo CSV de configuración.")
    group.add_argument("--excel", type=str, help="Ruta al archivo Excel de configuración.")
    
    args = parser.parse_args()
    
    try:
        if args.csv:
            from_csv(args.csv)
        elif args.excel:
            from_excel(args.excel)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
