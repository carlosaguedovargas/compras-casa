from db import get_connection, init_db
import io
import requests
import pandas as pd
import os

# CONFIGURACIÓN GOOGLE SHEETS
# Instrucciones para el usuario:
# 1. En Google Sheets, ve a Archivo > Compartir > Publicar en la web.
# 2. Selecciona la hoja y elige "Valores separados por comas (.csv)".
# 3. Copia el enlace y pégalo abajo en SHEET_URL.
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Eu9f5rabzwIIfaMWg4ZpyhPBQR_IAmpC1zbv3Za4dpk/export?format=csv"  # <--- URL CORREGIDA AUTOMÁTICAMENTE

EXCEL_PATH = "Cosas Casa.xlsx"

def load_products_from_excel():
    init_db()  # Ensure tables exist
    
    df = None
    source_name = ""

    # 1. Try Google Sheet URL first
    if SHEET_URL and "docs.google.com" in SHEET_URL:
        try:
            print(f"Intentando descargar desde Google Sheets...")
            response = requests.get(SHEET_URL)
            response.raise_for_status()
            df = pd.read_csv(io.StringIO(response.content.decode('utf-8')))
            source_name = "Google Sheets"
            print("Datos descargados correctamente de Google Sheets.")
        except Exception as e:
            print(f"Error al conectar con Google Sheets: {e}")
            print("Intentando archivo local...")
    
    # 2. Fallback to Local Excel
    if df is None:
        if os.path.exists(EXCEL_PATH):
            try:
                df = pd.read_excel(EXCEL_PATH)
                source_name = "Archivo Local Excel"
            except Exception as e:
                print(f"Error leyendo archivo local: {e}")
                return
        else:
            print(f"No se encontró ni URL configurada ni archivo local {EXCEL_PATH}")
            return
            
    try:
        # Normalize column names (strip spaces, lowercase)
        df.columns = [str(c).strip().lower() for c in df.columns]
        print(f"Columnas encontradas en {source_name}: {df.columns.tolist()}")

        # Map expected columns
        # Expected: Category, Product, Quantity (maybe?), Unit of Measure
        # DB: name, category, uom, brand, image_path, last_price_estimate
        
        # Mapping helpers
        col_map = {
            'product': 'name',
            'producto': 'name',
            'item': 'name',
            'nombre': 'name',
            'category': 'category',
            'categoría': 'category',
            'categoria': 'category',
            'tipo': 'category',  # Added based on earlier log seeing 'tipo' column
            'unit': 'uom',
            'unidad': 'uom',
            'medida': 'uom',
            'uom': 'uom',
            'u/m': 'uom'
        }
        
        # Rename columns based on map
        df = df.rename(columns={c: col_map[c] for c in df.columns if c in col_map})
        
        # Check required
        if 'name' not in df.columns:
            print("Error: Could not find 'Product' or 'Name' column.")
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
            
            # Check if exists
            c.execute("SELECT id FROM products WHERE name = ?", (name,))
            existing = c.fetchone()
            
            if not existing:
                c.execute('''
                    INSERT INTO products (name, category, uom)
                    VALUES (?, ?, ?)
                ''', (name, category, uom))
                count += 1
            else:
                # Update existing
                c.execute('''
                    UPDATE products SET category = ?, uom = ? WHERE name = ?
                ''', (category, uom, name))
                updated += 1
        
        conn.commit()
        conn.close()
        print(f"Successfully loaded {count} new products. Updated {updated} existing products.")
        
    except Exception as e:
        print(f"Error loading excel: {e}")

if __name__ == "__main__":
    load_products_from_excel()
