import streamlit as st
import pandas as pd
from db import get_connection

def render_requester_view(user):
    st.header(f"📝 Solicitud de Productos - Hola {user['username']}")
    
    conn = get_connection()
    
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
    
    df = pd.read_sql(query, conn)
    # Fill NaN with 0.0 and cast to float (Postgres returns Decimal for SUM)
    # Use to_numeric with coerce to handle any edge case strings
    df['Solicitado'] = pd.to_numeric(df['Solicitado'], errors='coerce').fillna(0.0)
    
    # -- Search & Filter --
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search_term = st.text_input("🔍 Buscar producto...")
    with col2:
        # Check if empty
        if df.empty:
            categories = ["Todas"]
        else:
            categories = ["Todas"] + df['Categoría'].dropna().unique().tolist()
        category_filter = st.selectbox("Categoría", categories)
    with col3:
        # Save Button
        save_clicked = st.button("💾 Guardar Cambios", type="primary")

    # Filter Logic
    filtered = df.copy()
    if search_term and not filtered.empty:
        filtered = filtered[filtered['Producto'].str.contains(search_term, case=False, na=False)]
    if category_filter != "Todas" and not filtered.empty:
        filtered = filtered[filtered['Categoría'] == category_filter]

    # Config Data Editor
    edited_df = st.data_editor(
        filtered,
        column_config={
            "id": None, # Hide ID
            "Producto": st.column_config.TextColumn("Producto", disabled=True),
            "Categoría": st.column_config.TextColumn("Categoría", disabled=True),
            "Unidad": st.column_config.TextColumn("Unidad", disabled=True),
            # Quantity editable
            "Solicitado": st.column_config.NumberColumn(
                "Cantidad a Solicitar",
                min_value=0.0,
                step=0.5,
                help="Ingresa la cantidad que necesitas."
            )
        },
        use_container_width=True,
        hide_index=True,
        disabled=["Producto", "Categoría", "Unidad"],
        key="requester_editor"
    )

    if save_clicked:
        c = conn.cursor()
        changes_count = 0
        
        for index, row in edited_df.iterrows():
            product_id = row['id']
            new_qty = float(row['Solicitado'])
            
            # Get old qty from original df to reduce DB hits
            if not df.empty:
                original_row = df[df['id'] == product_id].iloc[0]
                old_qty = float(original_row['Solicitado'])
            else:
                old_qty = 0.0
            
            if new_qty != old_qty:
                # Update DB
                c.execute("SELECT id FROM shopping_list_items WHERE product_id = %s AND status = 'Pendiente'", (product_id,))
                existing_item = c.fetchone()
                
                if new_qty > 0:
                    if existing_item:
                         # Use dictionary access if DictCursor, or tuple index if fallback
                        item_id = existing_item['id'] if isinstance(existing_item, dict) else existing_item[0]
                        c.execute("UPDATE shopping_list_items SET quantity_requested = %s WHERE id = %s", (new_qty, item_id))
                    else:
                        # Create new
                        c.execute('''
                            INSERT INTO shopping_list_items (product_id, requester_id, quantity_requested, status, created_at)
                            VALUES (%s, %s, %s, 'Pendiente', NOW())
                        ''', (product_id, user['id'], new_qty))
                else:
                    if existing_item:
                        item_id = existing_item['id'] if isinstance(existing_item, dict) else existing_item[0]
                        c.execute("DELETE FROM shopping_list_items WHERE id = %s", (item_id,))
                
                changes_count += 1
        
        conn.commit()
        if changes_count > 0:
            st.success("✅ Lista actualizada correctamente.")
            st.rerun()
        else:
            st.info("No hubo cambios.")

    conn.close()
