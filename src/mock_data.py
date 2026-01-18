import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from db import get_connection

def insert_mock_data():
    conn = get_connection()
    c = conn.cursor()
    
    # Check if we have products
    c.execute("SELECT id, name, last_price_estimate FROM products LIMIT 5")
    products = c.fetchall()
    
    if not products:
        print("No products found. Load products first.")
        return

    # Mock Purchase 1 (2 weeks ago)
    date1 = datetime.now() - timedelta(days=14)
    # Pick first 2 products appropriately if available
    if len(products) >= 1:
        p = products[0] # e.g. Leche
        price = 6.5
        c.execute('''
            INSERT INTO shopping_list_items (product_id, requester_id, quantity_requested, quantity_approved, status, price_real, shopping_date)
            VALUES (?, 1, 3, 3, 'Comprado', ?, ?)
        ''', (p['id'], price, date1))
        
    if len(products) >= 2:
        p = products[1] # e.g. Pan
        price = 12.0
        c.execute('''
            INSERT INTO shopping_list_items (product_id, requester_id, quantity_requested, quantity_approved, status, price_real, shopping_date)
            VALUES (?, 1, 2, 2, 'Comprado', ?, ?)
        ''', (p['id'], price, date1))

    # Mock Purchase 2 (Added today/yesterday)
    date2 = datetime.now() - timedelta(days=1)
    if len(products) >= 3:
        p = products[2] # e.g. Huevos/Others
        price = 18.5
        c.execute('''
            INSERT INTO shopping_list_items (product_id, requester_id, quantity_requested, quantity_approved, status, price_real, shopping_date)
            VALUES (?, 1, 1, 1, 'Comprado', ?, ?)
        ''', (p['id'], price, date2))
        
    conn.commit()
    conn.close()
    print("Datos simulados insertados correctamente.")

if __name__ == "__main__":
    insert_mock_data()
