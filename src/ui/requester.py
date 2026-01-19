import streamlit as st
import pandas as pd
from db import get_connection

def render_requester_view(user):
    st.header(f"📝 Solicitud de Productos - Hola {user['username']}")
    
    conn = get_connection()
    
    # Check for reload query param or button (optional), for now just load
    
    # 1. Get all products
    # 2. Get current pending items for this user (or global? User said "Available until purchase", let's assume global pending makes sense for a family list, but safer to stick to per-user edits first, or merge. 
    # Let's try: Show what *I* have requested or what is requested in total? 
    # "Información disponible hasta que la compra se realice".
    # I will show the TOTAL pending quantity for each product to avoid duplicates?
    # No, simple approach: Show products, Left Join with list_items (status='Pendiente')
    
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
    # Fill NaN with 0 for logic, but maybe blank for UI? 0 is fine.
    df['Solicitado'] = df['Solicitado'].fillna(0.0)
    
    # -- Search & Filter --
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search_term = st.text_input("🔍 Buscar producto...")
    with col2:
        categories = ["Todas"] + df['Categoría'].dropna().unique().tolist()
        category_filter = st.selectbox("Categoría", categories)
    with col3:
        # Save Button
        save_clicked = st.button("💾 Guardar Cambios", type="primary")

    # Filter Logic
    filtered = df.copy()
    if search_term:
        filtered = filtered[filtered['Producto'].str.contains(search_term, case=False, na=False)]
    if category_filter != "Todas":
        filtered = filtered[filtered['Categoría'] == category_filter]

    # Config Data Editor
    # We want 'Solicitado' to be editable.
    # We will hide ID.
    
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
        # Logic to save changes
        # We need to detect diffs between 'df' (original) and 'edited_df'.
        # Since we filtered, edited_df only has visible rows. We should only update those?
        # Or simpler: Update all rows present in edited_df where Solicitado changed?
        # Streamlit data_editor returns the current state.
        
        # We will iterate through edited_df and upsert/delete pending items.
        # Limitation: If multiple users edit, last save wins. Acceptable for MVP.
        
        c = conn.cursor()
        changes_count = 0
        
        for index, row in edited_df.iterrows():
            product_id = row['id']
            new_qty = float(row['Solicitado'])
            
            # Get old qty from original df to reduce DB hits
            original_row = df[df['id'] == product_id].iloc[0]
            old_qty = float(original_row['Solicitado'])
            
            if new_qty != old_qty:
                # Update DB
                # Strategy: 
                # If new_qty > 0: Check if exists pending item. Update or Insert.
                # If new_qty == 0: Delete pending item.
                # NOTE: This approach merges all requests into one 'Pendiente' row per product per user?
                # Actually query above sums all requests. 
                # To simplify: We will attribute all edits to the Current User.
                # But wait, if 'Solicitado' is sum of Mom + Dad, and Dad edits it, he might overwrite Mom.
                # User said: "Available until purchase".
                # Let's assume SINGLE pending line per product to keep it simple as a "Family List".
                
                # Check for existing pending item (any requester)
                c.execute("SELECT id FROM shopping_list_items WHERE product_id = ? AND status = 'Pendiente'", (product_id,))
                existing_item = c.fetchone()
                
                if new_qty > 0:
                    if existing_item:
                        c.execute("UPDATE shopping_list_items SET quantity_requested = ? WHERE id = ?", (new_qty, existing_item['id']))
                    else:
                        # Create new
                        c.execute('''
                            INSERT INTO shopping_list_items (product_id, requester_id, quantity_requested, status, created_at)
                            VALUES (?, ?, ?, 'Pendiente', datetime('now'))
                        ''', (product_id, user['id'], new_qty))
                else:
                    if existing_item:
                        c.execute("DELETE FROM shopping_list_items WHERE id = ?", (existing_item['id'],))
                
                changes_count += 1
        
        conn.commit()
        if changes_count > 0:
            st.success("✅ Lista actualizada correctamente.")
            st.rerun()
        else:
            st.info("No hubo cambios.")

    conn.close()

