import os
import pandas as pd
import argparse

def process_coev_files(input_dir="coev", output_file="output.csv", column_name="Coevaluación Proyecto 1 Points Grade"):
    # Check if directory exists
    if not os.path.exists(input_dir):
        print(f"Error: Directory '{input_dir}' not found.")
        print(f"Please create the directory and place the Excel files there.")
        return

    all_data = []

    # Iterate over all files in the directory
    for filename in os.listdir(input_dir):
        if filename.endswith('.xlsx') or filename.endswith('.xls'):
            filepath = os.path.join(input_dir, filename)
            try:
                # Read the specific sheet
                df = pd.read_excel(filepath, sheet_name='Grades per student')
                
                # Check for required columns
                required_cols = {'Student ID', 'Student email', 'AdjustedGrade'}
                if not required_cols.issubset(df.columns):
                    print(f"Warning: File '{filename}' is missing some required columns {required_cols}. Skipping.")
                    continue
                    
                temp_df = pd.DataFrame()
                
                temp_df['OrgDefinedId'] = df['Student ID']
                temp_df['Username'] = df['Student email'].str.replace('@uniandes.edu.co', '', regex=False)
                temp_df[column_name] = pd.to_numeric(df['AdjustedGrade'], errors='coerce').round(4)
                temp_df['End-of-Line Indicator'] = '#'
                                
                all_data.append(temp_df)
                print(f"Processed: {filename}")
            except ValueError as ve:
                print(f"Error processing '{filename}': Sheet 'Grades per student' may not exist. Details: {ve}")
            except Exception as e:
                print(f"Error processing '{filename}': {e}")

    if all_data:
        # Concatenate all dataframes
        final_df = pd.concat(all_data, ignore_index=True)
        
        # Write to CSV
        final_df.to_csv(output_file, index=False)
        print(f"\nSuccessfully generated '{output_file}' with {len(final_df)} records.")
    else:
        print("\nNo valid data found to generate the CSV.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process coevaluation Excel files and generate a CSV.")
    parser.add_argument("-i", "--input-dir", default="coev", help="Directory containing the Excel files (default: 'coev')")
    parser.add_argument("-o", "--output-file", default="output.csv", help="Name of the output CSV file (default: 'output.csv')")
    parser.add_argument("-c", "--column-name", 
                        choices=["P1", "EA"], 
                        default="P1", 
                        help="Select the evaluation type: P1 (Proyecto 1) or EA (Expoandes)")
    args = parser.parse_args()

    column_mapping = {
        "P1": "Coevaluación Proyecto 1 Points Grade",
        "EA": "Coevaluación Expoandes Points Grade"
    }
    full_column_name = column_mapping[args.column_name]

    process_coev_files(args.input_dir, args.output_file, full_column_name)
