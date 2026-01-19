from db import get_connection, init_db
import io
import requests
import pandas as pd
import os

# --- ASEGÚRATE DE QUE ESTA LÍNEA TENGA TU ENLACE REAL ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Eu9f5rabzwIIfaMWg4ZpyhPBQR_IAmpC1zbv3Za4dpk/export?format=csv"
EXCEL_PATH = "Cosas Casa.xlsx"

def load_products_from_excel():
    init_db()
    
    df = None
    source_name = ""

    # CHIVATO 1: Ver si detecta la URL
    print(f"DEBUG: Revisando URL... Longitud: {len(SHEET_URL) if SHEET_URL else 0}")
    
    if SHEET_URL and "docs.google.com" in SHEET_URL:
        try:
            print(f"DEBUG: Intentando descargar desde Google Sheets: {SHEET_URL[:30]}...")
            response = requests.get(SHEET_URL)
            response.raise_for_status()
            df = pd.read_csv(io.StringIO(response.content.decode('utf-8')))
            source_name = "Google Sheets"
            print(f"DEBUG: Datos descargados. Filas encontradas: {len(df)}")
        except Exception as e:
            print(f"ERROR: Fallo al conectar con Google Sheets: {e}")
            print("Intentando archivo local...")
    else:
        print("DEBUG: NO se detectó URL válida de Google Sheets en el código.")
    
    # INTENTO 2: Archivo Local
    if df is None:
        if os.path.exists(EXCEL_PATH):
            try:
                df = pd.read_excel(EXCEL_PATH)
                source_name = "Archivo Local Excel"
            except Exception as e:
                print(f"Error leyendo archivo local: {e}")
                return
        else:
            print(f"ERROR FATAL: No se encontró URL ni archivo local.")
            return

    # PROCESAMIENTO
    try:
        # Standardize columns
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        col_map = {
            'product': 'name', 'producto': 'name', 'item': 'name', 'nombre': 'name',
            'category': 'category', 'categoría': 'category', 'categoria': 'category', 'tipo': 'category',
            'unit': 'uom', 'unidad': 'uom', 'medida': 'uom', 'uom': 'uom', 'u/m': 'uom'
        }
        df = df.rename(columns={c: col_map[c] for c in df.columns if c in col_map})
        
        if 'name' not in df.columns:
            print(f"ERROR: Columnas encontradas: {df.columns.tolist()}. Falta 'name/producto'.")
            return

        conn = get_connection()
        c = conn.cursor()
        
        count = 0
        updated = 0
        for _, row in df.iterrows():
            name = row.get('name')
            if pd.isna(name): continue
            
            category = row.get('category', 'General')
            uom = row.get('uom', 'Unidad')
            
            # Check existance
            c.execute("SELECT id FROM products WHERE name = %s", (name,)) # USAMOS %s POR SI ES POSTGRES
            existing = c.fetchone()
            
            if not existing:
                c.execute("SELECT id FROM products WHERE name = ?", (name,)) # FALLBACK SQLITE
                existing = c.fetchone()

            if not existing:
                # INSERT (Try generic first)
                try:
                    c.execute('INSERT INTO products (name, category, uom) VALUES (?, ?, ?)', (name, category, uom))
                except:
                     c.execute('INSERT INTO products (name, category, uom) VALUES (%s, %s, %s)', (name, category, uom))
                count += 1
            else:
                # UPDATE
                try:
                    c.execute('UPDATE products SET category = ?, uom = ? WHERE name = ?', (category, uom, name))
                except:
                    c.execute('UPDATE products SET category = %s, uom = %s WHERE name = %s', (category, uom, name))
                updated += 1
        
        conn.commit()
        conn.close()
        print(f"ÉXITO: Se cargaron {count} nuevos y se actualizaron {updated}.")
        
    except Exception as e:
        print(f"ERROR PROCESANDO DATOS: {e}")

if __name__ == "__main__":
    load_products_from_excel()
