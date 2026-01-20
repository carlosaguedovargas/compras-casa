import streamlit as st
from auth import login, logout, get_current_user, sync_users_to_db, change_password
from db import init_db
from ui.requester import render_requester_view
from ui.admin import render_admin_view
from ui.buyer import render_buyer_view
from ui.stats import render_stats_view

# Initialize DB (First thing!)
init_db()

# Sync Users
sync_users_to_db()

# Page Config
st.set_page_config(
    page_title="Gestión de Compras",
    page_icon="🛒",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
    }
    .status-badge {
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# Title
st.title("🛒 Compras Casa")

# Auth Flow
if not login():
    st.stop()

# Authenticated User
user = get_current_user()

with st.sidebar:
    st.divider()
    st.write(f"Usuario: **{user['username']}**")
    st.write(f"Rol: **{user['role']}**")
    
    with st.expander("🔑 Cambiar Contraseña"):
        new_pass = st.text_input("Nueva contraseña", type="password", key="new_pass")
        confirm_pass = st.text_input("Confirmar", type="password", key="conf_pass")
        if st.button("Actualizar Clave"):
            if new_pass and new_pass == confirm_pass and len(new_pass) > 0:
                if change_password(user['id'], new_pass):
                    st.success("¡Contraseña cambiada!")
            else:
                st.error("Error: Las contraseñas no coinciden o están vacías.")

    st.divider()
    if st.button("Cerrar Sesión"):
        logout()

# Routing based on Role
view_mode = "Solicitar"  # Default

if user['role'] == "Jefe":
    view_mode = st.sidebar.radio("Modo", ["Solicitar", "Aprobar", "Comprar", "Historial"])
elif user['role'] == "Solicitante":
    view_mode = "Solicitar"
elif user['role'] == "Comprador":
    view_mode = "Comprar"
elif user['role'] == "Administrador":
    view_mode = "Aprobar"

if view_mode == "Solicitar":
    render_requester_view(user)
elif view_mode == "Aprobar":
    render_admin_view(user)
elif view_mode == "Comprar":
    render_buyer_view(user)
elif view_mode == "Historial":
    render_stats_view(user)
else:
    st.error("Rol no reconocido.")
