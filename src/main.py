import streamlit as st
import sys

st.set_page_config(page_title="Super Debug", layout="wide")
st.title("🕵️ Super Debugger")

st.write("Python Version:", sys.version)

st.divider()

st.subheader("1. Test Import 'auth'")
try:
    import auth
    st.success("✅ Modulo 'auth' importado correctamente.")
    st.write("Contenido de auth (dir):")
    st.code(dir(auth))
    
    # Chequear funciones clave
    functions = ['login', 'logout', 'change_password', 'sync_users_to_db']
    for f in functions:
        if hasattr(auth, f):
            st.write(f"✅ Función `{f}` encontrada.")
        else:
            st.error(f"❌ Función `{f}` NO encontrada.")
            
except Exception as e:
    st.error(f"❌ Error CRÍTICO al importar auth: {e}")
    import traceback
    st.code(traceback.format_exc())

st.divider()

st.subheader("2. Test Import 'db'")
try:
    import db
    st.success("✅ Modulo 'db' importado correctamente.")
except Exception as e:
    st.error(f"❌ Error al importar db: {e}")
