import streamlit as st
import pandas as pd
from db import get_connection

def render_admin_view(user):
    st.header(f"👑 Administración - Hola {user['username']}")
    
    conn = get_connection()

    # -- Sync Button --
    with st.expander("🔄 Actualizar Catálogo (Google Sheets / Excel)"):
        # Diagnostics
        c = conn.cursor()
        try:
            c.execute("SELECT COUNT(*) as count FROM products")
            result = c.fetchone()
            # Handle DictCursor vs Tuple
            prod_count = result['count'] if isinstance(result, dict) else result[0]
            
            c.execute("SELECT COUNT(*) as count FROM users")
            result_u = c.fetchone()
            user_count = result_u['count'] if isinstance(result_u, dict) else result_u[0]
            
            st.write(f"📊 Estado actual DB: **{prod_count}** Productos | **{user_count}** Usuarios")
        except Exception as e:
            st.error(f"Error DB: {e}")

        st.info("Pega tu enlace de Google Sheets en 'src/loader.py' si aún no lo has hecho.")
        if st.button("Descargar y Actualizar Productos"):
            with st.spinner("Actualizando..."):
                import sys
                from io import StringIO
                
                # Capture output to show user
                old_stdout = sys.stdout
                sys.stdout = mystdout = StringIO()
                
                try:
                    from loader import load_products_from_excel
                    load_products_from_excel()
                    output = mystdout.getvalue()
                    st.success("Proceso completado.")
                    st.code(output)
                except Exception as e:
                    st.error(f"Error: {e}")
                finally:
                    sys.stdout = old_stdout
    
    # Fetch Pending Requests
    pending_df = pd.read_sql('''
        SELECT 
            s.id, 
            p.name as "Producto", 
            s.quantity_requested as "Cantidad", 
            p.uom as "Unidad",
            u.username as "Solicitante", 
            'Pendiente' as "Estado"
        FROM shopping_list_items s
        JOIN products p ON s.product_id = p.id
        JOIN users u ON s.requester_id = u.id
        WHERE s.status = 'Pendiente'
        ORDER BY s.created_at ASC
    ''', conn)
    
    if pending_df.empty:
        st.success("No hay solicitudes pendientes por revisar.")
    else:
        st.subheader("Solicitudes Pendientes")
        
        # Add "Aprobar" columns
        pending_df['Aprobar'] = False 
        pending_df['Rechazar'] = False
        
        edited_df = st.data_editor(
            pending_df,
            column_config={
                "id": None, # Hide
                "Estado": None, # Hide
                "Aprobar": st.column_config.CheckboxColumn("✅ Aprobar", default=False),
                "Rechazar": st.column_config.CheckboxColumn("❌ Rechazar", default=False),
                "Producto": st.column_config.TextColumn("Producto", disabled=True),
                "Cantidad": st.column_config.NumberColumn("Cantidad", min_value=0.0, step=0.5),
                "Unidad": st.column_config.TextColumn("Unidad", disabled=True),
                "Solicitante": st.column_config.TextColumn("Solicitante", disabled=True)
            },
            use_container_width=True,
            hide_index=True,
            key="admin_editor"
        )
        
        if st.button("Procesar Cambios", type="primary"):
            c = conn.cursor()
            count_approved = 0
            count_rejected = 0
            
            for index, row in edited_df.iterrows():
                if row['Rechazar']:
                    # Use %s for native Postgres compatibility
                    c.execute("UPDATE shopping_list_items SET status = 'Rechazado' WHERE id = %s", (row['id'],))
                    count_rejected += 1
                elif row['Aprobar']:
                    c.execute("UPDATE shopping_list_items SET status = 'Aprobado', quantity_approved = %s WHERE id = %s", (float(row['Cantidad']), row['id']))
                    count_approved += 1
            
            conn.commit()
            if count_approved > 0 or count_rejected > 0:
                st.success(f"Procesado: {count_approved} aprobados, {count_rejected} rechazados.")
                st.rerun()
            else:
                st.info("No seleccionaste ninguna acción.")

    conn.close()
