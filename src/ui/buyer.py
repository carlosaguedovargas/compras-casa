import streamlit as st
import pandas as pd
from datetime import datetime
from db import get_connection

def render_buyer_view(user):
    st.header(f"🛍️ Lista de Compras - Modo Comprador")
    
    conn = get_connection()
    
    # Fetch Approved Items (Includes Postponed ones so they persist in the list)
    shopping_list_df = pd.read_sql('''
        SELECT s.id, p.name, s.quantity_approved, p.uom, p.category, s.status, p.last_price_estimate
        FROM shopping_list_items s
        JOIN products p ON s.product_id = p.id
        WHERE s.status IN ('Aprobado', 'Postergado')
        ORDER BY p.category, p.name
    ''', conn)
    
    to_buy_df = shopping_list_df.copy()
    
    if to_buy_df.empty:
        st.info("No hay items pendientes de compra.")
    else:
        st.subheader(f"Items por Comprar ({len(to_buy_df)})")
        st.caption("Si no encuentras un producto, dale a 'Postergar' y seguirá aquí para la próxima.")
        
        # Group by Category for better shopping experience
        categories = to_buy_df['category'].unique()
        
        for cat in categories:
            st.markdown(f"### {cat}")
            cat_items = to_buy_df[to_buy_df['category'] == cat]
            
            for _, row in cat_items.iterrows():
                with st.container():
                    # Color highlight for Postponed items?
                    prefix = "⚠️ [PENDIENTE ANTERIOR] " if row['status'] == 'Postergado' else ""
                    
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

                    with col1:
                        st.markdown(f"**{prefix}{row['name']}**")
                        # Display original approved as info, but allow edit in next col
                        st.caption(f"Solicitado: {row['quantity_approved']} {row['uom']}")
                        
                    with col2:
                        # Editable Quantity (Step=1 for integers as requested, but keep float type to avoid errors)
                        qty_real = st.number_input(
                            "Cant",
                            min_value=0.0,
                            value=float(row['quantity_approved']),
                            step=1.0, # Forces integer steps but allows decimals if typed manually
                            format="%.1f", # Display 1 decimal
                            key=f"qty_{row['id']}",
                            label_visibility="collapsed"
                        )

                    with col3:
                        real_price = st.number_input(
                            "Precio",
                            min_value=0.0,
                            value=float(row['last_price_estimate'] or 0.0),
                            key=f"price_{row['id']}",
                            label_visibility="collapsed"
                        )
                        
                    with col4:
                        if st.button("🛒", key=f"buy_{row['id']}", help="Marcar como Comprado"):
                            c = conn.cursor()
                            
                            c.execute('''
                                UPDATE shopping_list_items 
                                SET status = 'Comprado', price_real = ?, shopping_date = ?, quantity_approved = ? 
                                WHERE id = ?
                            ''', (real_price, datetime.now(), qty_real, row['id']))
                            
                            # Update product master price
                            c.execute('''
                                UPDATE products
                                SET last_price_estimate = ?
                                WHERE name = ?
                            ''', (real_price, row['name']))
                            
                            conn.commit()
                            st.rerun()
                            
                    with col4:
                        if st.button("⏭️ Postergar", key=f"defer_{row['id']}"):
                             c = conn.cursor()
                             # Set to 'Postergado' so it stays in this view but marked
                             c.execute("UPDATE shopping_list_items SET status = 'Postergado' WHERE id = ?", (row['id'],))
                             conn.commit()
                             st.rerun()
                    st.divider()

    conn.close()
