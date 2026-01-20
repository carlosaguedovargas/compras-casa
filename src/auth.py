# Forzando update
import streamlit as st
import hashlib
from db import get_connection

# Usuarios por defecto (solo se usan si la base de datos está vacía al inicio)
DEFAULT_USERS = {
    "papa": {"password": "papa", "role": "Jefe", "id": 1},
    "mama": {"password": "mama", "role": "Jefe", "id": 2},
    "marlene": {"password": "marlene", "role": "Solicitante", "id": 3},
    "rafaela": {"password": "rafaela", "role": "Solicitante", "id": 4},
    "abi": {"password": "abi", "role": "Solicitante", "id": 5},
    "carlo": {"password": "carlo", "role": "Solicitante", "id": 6},
    "cristobal": {"password": "cristobal", "role": "Solicitante", "id": 7}
}

def sync_users_to_db():
    conn = get_connection()
    c = conn.cursor()
    # Verificar si hay usuarios
    try:
        c.execute("SELECT COUNT(*) as count FROM users")
        res = c.fetchone()
        count = res['count'] if isinstance(res, dict) else res[0]
    except:
        count = 0
            
    if count == 0:
        for username, data in DEFAULT_USERS.items():
            try:
                # Postgres
                c.execute("INSERT INTO users (id, username, password_hash, role) VALUES (%s, %s, %s, %s)",
                          (data['id'], username, data['password'], data['role']))
            except:
                # Sqlite fallback
                c.execute("INSERT INTO users (id, username, password_hash, role) VALUES (?, ?, ?, ?)",
                          (data['id'], username, data['password'], data['role']))
        conn.commit()
    conn.close()

def check_credentials_db(username, password):
    conn = get_connection()
    c = conn.cursor()
    try:
        # Postgres uses %s
        c.execute("SELECT id, username, role, password_hash FROM users WHERE username = %s AND password_hash = %s", (username, password))
    except:
        # DB-API 2.0 uses ?
        c.execute("SELECT id, username, role, password_hash FROM users WHERE username = ? AND password_hash = ?", (username, password))
        
    user = c.fetchone()
    conn.close()
    
    if user:
        if isinstance(user, tuple):
             return {"id": user[0], "username": user[1], "role": user[2]}
        else:
             return {"id": user['id'], "username": user['username'], "role": user['role']}
    return None

def change_password(user_id, new_password):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_password, user_id))
    except:
        c.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_password, user_id))
    conn.commit()
    conn.close()
    return True

def login():
    if "user" not in st.session_state:
        st.session_state.user = None

    if st.session_state.user:
        return True

    st.sidebar.header("Iniciar Sesión")
    username = st.sidebar.text_input("Usuario")
    password = st.sidebar.text_input("Contraseña", type="password")
    
    if st.sidebar.button("Entrar"):
        user_data = check_credentials_db(username, password)
        if user_data:
            st.session_state.user = user_data
            st.success(f"Bienvenido {username}")
            st.rerun()
        else:
            st.sidebar.error("Credenciales incorrectas")
    
    return False

def logout():
    st.session_state.user = None
    st.rerun()

