import os
import csv
import argparse

def get_unevaluated_activities(folder_path, output_file="unevaluated_summary.csv"):
    if not os.path.isdir(folder_path):
        print(f"Error: The folder '{folder_path}' does not exist.")
        return

    csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
    
    if not csv_files:
        print(f"No CSV files found in '{folder_path}'.")
        return

    summary = {}

    for file_name in csv_files:
        file_path = os.path.join(folder_path, file_name)
        unevaluated = []
        try:
            # Using utf-8-sig to handle optional BOM
            with open(file_path, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                
                # Check for required columns
                fieldnames = reader.fieldnames
                if not fieldnames or len(fieldnames) < 3:
                    print(f"Warning: {file_name} does not have the expected columns.")
                    continue
                
                name_col = fieldnames[0] # Usually 'Nombre/Grupo' or 'Nombre'
                
                for row in reader:
                    enviado = row.get('Enviado', '').strip()
                    evaluado = row.get('Evaluado', '').strip()
                    
                    if enviado == 'Sí' and evaluado == 'No':
                        unevaluated.append(row.get(name_col, 'Unknown').strip())
                        
        except Exception as e:
            print(f"Error reading {file_name}: {e}")
            
        if unevaluated:
            summary[file_name] = unevaluated

    if not summary:
        print("No uploaded but unevaluated activities found.")
        return

    try:
        with open(output_file, mode='w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Activity", "Name"])
            for activity, names in summary.items():
                for name in names:
                    writer.writerow([activity, name])
        print(f"Successfully saved the summary to '{output_file}'")
    except Exception as e:
        print(f"Error writing to {output_file}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Summarize uploaded activities that have not been evaluated.")
    parser.add_argument("folder", nargs="?", default="grades", help="Folder containing the CSV files (default: 'grades')")
    parser.add_argument("-o", "--output", default="unevaluated_summary.csv", help="Output CSV file name (default: 'unevaluated_summary.csv')")
    args = parser.parse_args()
    
    get_unevaluated_activities(args.folder, args.output)
