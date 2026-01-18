import streamlit as st
import hashlib

from db import get_connection

# Mock Users for MVP
# In production, fetch from DB
USERS = {
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
    for username, data in USERS.items():
        # Check if exists
        c.execute("SELECT id FROM users WHERE id = ?", (data['id'],))
        if not c.fetchone():
            c.execute("INSERT INTO users (id, username, password_hash, role) VALUES (?, ?, ?, ?)",
                      (data['id'], username, data['password'], data['role']))
        else:
            # Update role or password if needed (optional)
            c.execute("UPDATE users SET role = ? WHERE id = ?", (data['role'], data['id']))
            
    conn.commit()
    conn.close()

def login():
    if "user" not in st.session_state:
        st.session_state.user = None

    if st.session_state.user:
        return True

    st.sidebar.header("Iniciar Sesión")
    username = st.sidebar.text_input("Usuario")
    password = st.sidebar.text_input("Contraseña", type="password")
    
    if st.sidebar.button("Entrar"):
        if username in USERS and USERS[username]["password"] == password:
            user_data = USERS[username].copy()
            user_data['username'] = username
            st.session_state.user = user_data
            st.success(f"Bienvenido {username}")
            st.rerun()
        else:
            st.sidebar.error("Credenciales incorrectas")
    
    return False

def logout():
    st.session_state.user = None
    st.rerun()

def get_current_user():
    return st.session_state.get("user")
