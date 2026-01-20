import streamlit as st
import pandas as pd
from datetime import datetime
from db import get_connection

def render_buyer_view(user):
    st.header(f"🛍️ Lista de Compras - Modo Comprador")
    
    conn = get_connection()
    
    # query
    df = pd.read_sql('''
        SELECT 
            s.id, 
            p.name as "Producto", 
            s.quantity_approved as "Cantidad", 
            p.uom as "Unidad", 
            p.category as "Categoría", 
            s.status as "Estado", 
            p.last_price_estimate as "PrecioRef"
        FROM shopping_list_items s
        JOIN products p ON s.product_id = p.id
        WHERE s.status IN ('Aprobado', 'Postergado')
        ORDER BY p.category, p.name
    ''', conn)
    
    if df.empty:
        st.info("No hay items pendientes de compra. ¡Todo listo!")
        conn.close()
        return

    st.caption("Marca 'Comprar' ✅ o 'Postergar' ⏭️ y procesa todo al final.")

    # 1. Añadir columnas de acción
    df['Comprado'] = False
    df['Postergar'] = False
    
    # 2. Preparar numéricos
    df['PrecioRef'] = pd.to_numeric(df['PrecioRef'], errors='coerce').fillna(0.0)
    df['Precio Real'] = df['PrecioRef'] # Pre-llenar con el último precio
    df['Cantidad'] = pd.to_numeric(df['Cantidad'], errors='coerce').fillna(1.0)

    # 3. CONFIGURAR TABLA
    edited_df = st.data_editor(
        df,
        column_config={
            "id": None, 
            "Estado": None, 
            "PrecioRef": None, # Lo ocultamos para mostrar el editable
            "Comprado": st.column_config.CheckboxColumn("✅ Comprar", default=False),
            "Postergar": st.column_config.CheckboxColumn("⏭️ Postergar", default=False),
            "Producto": st.column_config.TextColumn("Producto", disabled=True),
            "Categoría": st.column_config.TextColumn("Categoría", disabled=True),
            "Unidad": st.column_config.TextColumn("Unidad", disabled=True, width="small"),
            "Cantidad": st.column_config.NumberColumn("Cantidad", min_value=0.0, step=0.5, format="%.2f"),
            "Precio Real": st.column_config.NumberColumn("Precio Real (S/)", min_value=0.0, step=0.5, format="%.2f")
        },
        use_container_width=True,
        hide_index=True,
        # Orden visual de columnas
        column_order=["Comprado", "Postergar", "Producto", "Cantidad", "Unidad", "Precio Real"],
        key="buyer_editor"
    )

    # BOTÓN DE PROCESAR
    if st.button("Procesar Compra 🛒", type="primary"):
        c = conn.cursor()
        processed_count = 0
        
        for index, row in edited_df.iterrows():
            item_id = row['id']
            is_bought = row['Comprado']
            is_deferred = row['Postergar']
            
            if is_bought:
                real_price = float(row['Precio Real'])
                real_qty = float(row['Cantidad'])
                product_name = row['Producto']
                
                # Marcar como comprado
                c.execute('''
                    UPDATE shopping_list_items 
                    SET status = 'Comprado', price_real = %s, shopping_date = NOW(), quantity_approved = %s 
                    WHERE id = %s
                ''', (real_price, real_qty, item_id))
                
                # Actualizar precio maestro del producto
                c.execute('UPDATE products SET last_price_estimate = %s WHERE name = %s', (real_price, product_name))
                processed_count += 1
                
            elif is_deferred:
                # Postergar
                c.execute("UPDATE shopping_list_items SET status = 'Postergado' WHERE id = %s", (item_id,))
                processed_count += 1
        
        conn.commit()
        if processed_count > 0:
            st.success(f"✅ Se procesaron {processed_count} items.")
            st.rerun()
        else:
            st.info("No has marcado nada. Selecciona 'Comprar' o 'Postergar' en la tabla.")

    conn.close()
