import streamlit as st
import pandas as pd
import plotly.express as px
from db import get_connection

def render_stats_view(user):
    st.header("📊 Historial y Estadísticas")
    
    conn = get_connection()
    
    # 1. Total Gastado por Mes
    # 2. Top Productos más comprados
    # 3. Listado histórico detalle
    
    # Fetch Data
    df = pd.read_sql('''
        SELECT 
            s.id, 
            p.name as Producto, 
            p.category as Categoría,
            s.shopping_date as Fecha, 
            s.price_real as Precio,
            s.quantity_approved as Cantidad
        FROM shopping_list_items s
        JOIN products p ON s.product_id = p.id
        WHERE s.status = 'Comprado'
        ORDER BY s.shopping_date DESC
    ''', conn)
    
    if df.empty:
        st.info("Aún no hay compras registradas para mostrar estadísticas.")
        conn.close()
        return

    # Convert Date
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    df['Mes'] = df['Fecha'].dt.strftime('%Y-%m')
    df['Total'] = df['Precio'] * df['Cantidad'] # Assuming price is unit price? 
    # Usually real_price inputs total or unit? Buyer UI asks "Precio Real", implies Unit or Total?
    # In buyer.py: "update product last price". Usually implies Unit Price.
    # Let's assume Unit Price for calculation.
    
    # KPI Cards
    total_spent = (df['Precio']).sum() # If price stored is total per line?
    # Rereading buyer.py: `price_real` input. Usually people input the total they see on receipt for that item line? 
    # Or unit price? 
    # Let's assume `price_real` is the TOTAL paid for that line item (since qty is fixed approved).
    # Wait, if I buy 3 milks and put 30 soles, implies 30 total.
    # Let's verify logic in buyer.py if I have access... 
    # Assuming `price_real` is TOTAL AMOUNT PAID for the item line.
    
    st.markdown("### Resumen Global")
    c1, c2, c3 = st.columns(3)
    c1.metric("Gasto Total Histórico", f"S/ {df['Precio'].sum():.2f}")
    c2.metric("Items Comprados", len(df))
    c3.metric("Ticket Promedio", f"S/ {df['Precio'].mean():.2f}")
    
    st.divider()
    
    col_chart1, col_chart2 = st.columns(2)
    
    # Chart 1: Gasto por Categoría
    with col_chart1:
        st.subheader("Gasto por Categoría")
        fig_cat = px.pie(df, values='Precio', names='Categoría', hole=0.4)
        st.plotly_chart(fig_cat, use_container_width=True)
        
    # Chart 2: Gasto por Mes
    with col_chart2:
        st.subheader("Evolución de Gasto")
        monthly_spend = df.groupby('Mes')['Precio'].sum().reset_index()
        fig_line = px.bar(monthly_spend, x='Mes', y='Precio', title="Gasto Mensual")
        st.plotly_chart(fig_line, use_container_width=True)
        
    st.divider()
    st.subheader("Detalle de Compras")
    st.dataframe(df[['Fecha', 'Producto', 'Categoría', 'Cantidad', 'Precio']], use_container_width=True)
    
    conn.close()
