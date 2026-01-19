import sqlite3
import os
import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# DB CONFIG
DB_PATH = os.path.join("data", "shopping_app.db")

# Detect Cloud vs Local
def is_cloud_db():
    return "DB_URL" in st.secrets

def get_connection():
    if is_cloud_db():
        # Postgres Connection
        conn = psycopg2.connect(st.secrets["DB_URL"], cursor_factory=RealDictCursor)
        return PostgresConnectionWrapper(conn)
    else:
        # Local SQLite Connection
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

# Wrapper to mimic SQLite behavior on top of Postgres
class PostgresConnectionWrapper:
    def __init__(self, conn):
        self.conn = conn

    def cursor(self):
        return PostgresCursorWrapper(self.conn.cursor())

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()
        
    def execute(self, sql, params=None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

class PostgresCursorWrapper:
    def __init__(self, cursor):
        self.cursor = cursor
        
    def execute(self, sql, params=None):
        # Translate '?' to '%s'
        sql = sql.replace("?", "%s")
        # Translate 'datetime('now')' to 'NOW()'
        sql = sql.replace("datetime('now')", "NOW()")
        # Handle 'INTEGER PRIMARY KEY AUTOINCREMENT' (for init script)
        sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        
        try:
            if params:
                self.cursor.execute(sql, params)
            else:
                self.cursor.execute(sql)
        except Exception as e:
            print(f"Error executing SQL: {sql} | Params: {params}")
            raise e
            
    def fetchone(self):
        return self.cursor.fetchone()
        
    def fetchall(self):
        return self.cursor.fetchall()
        
    @property
    def rowcount(self):
        return self.cursor.rowcount

    @property  # <--- ESTO ES LO NUEVO
    def description(self):
        return self.cursor.description

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Usuarios
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    
    # Productos (Inventario Maestro)
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            uom TEXT,
            brand TEXT,
            image_path TEXT,
            last_price_estimate REAL DEFAULT 0.0
        )
    ''')
    
    # Items de Lista de Compras
    c.execute('''
        CREATE TABLE IF NOT EXISTS shopping_list_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            requester_id INTEGER,
            quantity_requested REAL DEFAULT 1,
            quantity_approved REAL,
            status TEXT DEFAULT 'Pendiente', -- Pendiente, Aprobado, Comprado, Postergado
            price_real REAL,
            shopping_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (id),
            FOREIGN KEY (requester_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Base de datos inicializada (Modo Nube: " + str(is_cloud_db()) + ")")
