import streamlit as st
import pandas as pd
from db import get_connection

def render_requester_view(user):
    st.header(f"📝 Solicitud de Productos - Hola {user['username']}")
    
    # --- MEMORIA (CARRITO) ---
    if 'cart_updates' not in st.session_state:
        st.session_state['cart_updates'] = {}

    conn = get_connection()
    
    # 1. Cargar datos de la BD
    query = '''
        SELECT 
            p.id, 
            p.name as "Producto", 
            p.category as "Categoría", 
            p.uom as "Unidad",
            SUM(s.quantity_requested) as "Solicitado"
        FROM products p
        LEFT JOIN shopping_list_items s 
            ON p.id = s.product_id 
            AND s.status = 'Pendiente'
        GROUP BY p.id
    '''
    
    df_db = pd.read_sql(query, conn)
    df_db['Solicitado'] = pd.to_numeric(df_db['Solicitado'], errors='coerce').fillna(0.0)

    # 2. Aplicar cambios de la Memoria sobre la vista
    df_display = df_db.copy()
    
    for pid, new_qty in st.session_state['cart_updates'].items():
        idx = df_display.index[df_display['id'] == pid]
        if not idx.empty:
            df_display.loc[idx, 'Solicitado'] = new_qty
            
    pending_count = len(st.session_state['cart_updates'])

    # -- BARRA DE HERRAMIENTAS --
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        search_term = st.text_input("🔍 Buscar producto...")
    with col2:
        if df_display.empty:
            categories = ["Todas"]
        else:
            categories = ["Todas"] + sorted(df_display['Categoría'].dropna().unique().tolist())
        category_filter = st.selectbox("Categoría", categories)
    with col3:
        # Botón inteligente
        btn_label = "💾 Guardar"
        if pending_count > 0:
            btn_label = f"💾 Guardar ({pending_count})"
            st.warning(f"Tienes {pending_count} cambios sin guardar.")
            
        save_clicked = st.button(btn_label, type="primary", use_container_width=True)

    # -- FILTRADO --
    filtered = df_display.copy()
    if search_term:
        filtered = filtered[filtered['Producto'].str.contains(search_term, case=False, na=False)]
    if category_filter != "Todas":
        filtered = filtered[filtered['Categoría'] == category_filter]

    # -- TABLA --
    edited_df = st.data_editor(
        filtered,
        column_config={
            "id": None, 
            "Producto": st.column_config.TextColumn("Producto", disabled=True),
            "Categoría": None, # Oculto para ahorrar espacio en móvil
            "Unidad": st.column_config.TextColumn("Unidad", disabled=True, width="small"),
            "Solicitado": st.column_config.NumberColumn(
                "Cantidad",
                min_value=0.0,
                step=0.5,
                format="%.1f"
            )
        },
        use_container_width=True,
        hide_index=True,
        disabled=["Producto", "Categoría", "Unidad"],
        key="requester_editor"
    )

    # -- DETECTAR CAMBIOS --
    # Si la tabla editada es diferente a lo que mostramos, actualizamos la memoria
    if not edited_df.equals(filtered):
        for index, row in edited_df.iterrows():
            pid = row['id']
            current_val = float(row['Solicitado'])
            
            # Buscamos el valor original en la BASE DE DATOS
            db_row = df_db[df_db['id'] == pid]
            original_val = float(db_row.iloc[0]['Solicitado']) if not db_row.empty else 0.0
                
            # Si es diferente a lo que hay en la BD, lo guardamos en el carrito
            if current_val != original_val:
                st.session_state['cart_updates'][pid] = current_val
            else:
                # Si volvió al valor original, lo quitamos del carrito
                if pid in st.session_state['cart_updates']:
                    del st.session_state['cart_updates'][pid]
                    
            # Nota: Necesitas interactuar otra vez para que se actualice el contador visual,
            # (Limitación de Streamlit), pero los datos SÍ se están guardando en memoria.

    # -- GUARDAR EN BD --
    if save_clicked:
        if not st.session_state['cart_updates']:
            st.info("No hay cambios para guardar.")
        else:
            c = conn.cursor()
            changes_count = 0
            
            try:
                for pid, new_qty in st.session_state['cart_updates'].items():
                    # Buscar si ya existe pendiente
                    c.execute("SELECT id FROM shopping_list_items WHERE product_id = %s AND status = 'Pendiente'", (pid,))
                    existing = c.fetchone()
                    
                    if new_qty > 0:
                        if existing:
                            # Update
                            item_id = existing['id'] if isinstance(existing, dict) else existing[0]
                            c.execute("UPDATE shopping_list_items SET quantity_requested = %s WHERE id = %s", (new_qty, item_id))
                        else:
                            # Insert
                            c.execute('''
                                INSERT INTO shopping_list_items (product_id, requester_id, quantity_requested, status, created_at)
                                VALUES (%s, %s, %s, 'Pendiente', NOW())
                            ''', (pid, user['id'], new_qty))
                            
                    else:
                        # Quantity 0 -> Delete
                        if existing:
                            item_id = existing['id'] if isinstance(existing, dict) else existing[0]
                            c.execute("DELETE FROM shopping_list_items WHERE id = %s", (item_id,))
                    
                    changes_count += 1
                
                conn.commit()
                st.success(f"✅ Se guardaron {changes_count} actualizaciones correctamente.")
                
                # Vaciar carrito
                st.session_state['cart_updates'] = {}
                st.rerun()
                
            except Exception as e:
                st.error(f"Error al guardar: {e}")

    conn.close()
