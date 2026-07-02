import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os
import io

# --- CONFIGURACIÓN DE LA PÁGINA WEB ---
st.set_page_config(page_title="Simulador Financiero COMREIVIC", layout="wide", page_icon="📊")

logo_path = 'logo.png'
if os.path.exists(logo_path):
    st.image(logo_path, width=250)

st.title("📊 Simulador Financiero Interactivo")
st.markdown("---")

# --- 1. ENTRADAS EN LA BARRA LATERAL (SIDEBAR) ---
st.sidebar.header("👤 Datos del Cliente")
cliente_nom = st.sidebar.text_input("Cliente:", value="Juan Pérez")
cliente_ruc = st.sidebar.text_input("RUC:", value="10123456789")
cliente_dir = st.sidebar.text_input("Dirección:", value="Av. Principal 123")
cliente_tel = st.sidebar.text_input("Teléfono Cliente:", value="987654321")
cliente_aval = st.sidebar.text_input("Aval / Fiador:", value="-")
cliente_dni = st.sidebar.text_input("DNI Aval:", value="-")
cliente_tel_aval = st.sidebar.text_input("Teléfono Aval:", value="-")

st.sidebar.header("📝 Parámetros de Simulación")
precio = st.sidebar.number_input("Precio Total ($):", min_value=1.0, value=20000.0, step=100.0)

tipo_inicial = st.sidebar.radio("Tipo de Cuota Inicial:", ["Importe ($)", "Porcentaje (%)"])
valor_inicial = st.sidebar.number_input("Valor de la Inicial:", min_value=0.0, value=2000.0, step=100.0)

if precio > 0:
    if tipo_inicial == "Porcentaje (%)":
        monto_eq = precio * (valor_inicial / 100)
        st.sidebar.caption(f"💡 Equivale a: **${monto_eq:,.2f}**")
        inicial_monto = monto_eq
        inicial_porc = valor_inicial
    else:
        porc_eq = (valor_inicial / precio) * 100
        st.sidebar.caption(f"💡 Equivale al: **{porc_eq:.2f}%**")
        inicial_monto = valor_inicial
        inicial_porc = porc_eq

plazo = st.sidebar.number_input("Plazo (Meses):", min_value=1, value=12, step=1)
tasa = st.sidebar.number_input("Tasa de Interés Mensual (%):", min_value=0.0, value=1.9, step=0.1)

# --- 2. MOTOR FINANCIERO (SISTEMA FRANCÉS) ---
def simular_tabla(monto, meses, tasa_p):
    t_mes = tasa_p / 100
    cuota = (monto * t_mes) / (1 - (1 + t_mes)**(-meses)) if t_mes > 0 else monto / meses
    cronograma, saldo = [], monto
    fecha_base = datetime.now()
    
    for i in range(1, meses + 1):
        s_ini = saldo
        interes = s_ini * t_mes
        amort = cuota - interes
        saldo -= amort
        if abs(saldo) < 0.01: saldo = 0
        
        fecha_pago = (fecha_base + relativedelta(months=i)).strftime("%d/%m/%Y")
        cronograma.append([i, fecha_pago, s_ini, amort, interes, cuota, saldo])
    return cronograma

# --- CONTINUACIÓN DEL CÓDIGO (PEGAR INMEDIATAMENTE ABAJO) ---
if inicial_monto > precio:
    st.error("❌ La cuota inicial no puede ser mayor al precio total.")
else:
    saldo_credito = precio - inicial_monto
    seguro_total = precio * (4.7 / 1000) * 1.03 * 1.18

    matriz_credito = simular_tabla(saldo_credito, plazo, tasa)
    matriz_seguro = simular_tabla(seguro_total, plazo, tasa)
    
    matriz_combinado = []
    for c, s in zip(matriz_credito, matriz_seguro):
        matriz_combinado.append([
            c[0], c[1], c[2]+s[2], c[3]+s[3], c[4]+s[4], 
            c[5], s[5], c[5]+s[5], c[6]+s[6]
        ])

    cols_names_estandar = ['Mes', 'Fecha Pago', 'Saldo Inicial', 'Amortización', 'Interés', 'Cuota', 'Saldo Final']
    cols_names_combinado = ['Mes', 'Fecha Pago', 'Saldo Inicial', 'Amortización', 'Interés', 'Cuota Financiamiento', 'Cuota Seguro', 'Cuota Combinada Total', 'Saldo Final']

    # --- 3. PRESENTACIÓN EN LA WEB ---
    st.subheader("📋 Resumen General de la Cotización")
    col1, col2, col3 = st.columns(3)
    col1.metric("Saldo Crédito a Financiar", f"${saldo_credito:,.2f}")
    col2.metric("Saldo Seguro Financiado", f"${seguro_total:,.2f}")
    col3.metric("Cuota Mensual Combinada", f"${(matriz_combinado[0][7]):,.2f}")

    st.markdown("**Fórmula Informativa de Seguro Aplicada:**")
    st.latex(r"\text{Seguro Total} = \text{Precio Total} \times \left(\frac{4.7}{1000}\right) \times 1.03 \times 1.18")

    tab1, tab2, tab3 = st.tabs(["🧱 1. Cronograma de Crédito", "🛡️ 2. Cronograma de Seguro", "🔄 3. Cronograma Combinado Total"])
    
    def mostrar_web(tab_obj, datos, inicial, nombres_columnas):
        df = pd.DataFrame(datos, columns=nombres_columnas)
        
        # Generar fila totalizadora limpia
        tot = {'Mes': 'TOTAL', 'Fecha Pago': '', 'Saldo Inicial': inicial, 'Saldo Final': 0.0}
        for col in nombres_columnas:
            if col in ['Amortización', 'Interés', 'Cuota', 'Cuota Financiamiento', 'Cuota Seguro', 'Cuota Combinada Total']:
                tot[col] = df[col].sum()
                
        df_v = pd.concat([df, pd.DataFrame([tot])], ignore_index=True)
        
        # SOLUCIÓN AL ERROR DE ARROW: Convertimos 'Mes' a string para que acepte el número y el texto 'TOTAL'
        df_v['Mes'] = df_v['Mes'].astype(str)
        
        # SOLUCIÓN AL DEPRECATED: Reemplazamos use_container_width=True por width="stretch"
        tab_obj.dataframe(
            df_v.style.format({c: "${:,.2f}" for c in nombres_columnas if c not in ['Mes', 'Fecha Pago']}), 
            width="stretch", 
            hide_index=True
        )
        
    mostrar_web(tab1, matriz_credito, saldo_credito, cols_names_estandar)
    mostrar_web(tab2, matriz_seguro, seguro_total, cols_names_estandar)
    mostrar_web(tab3, matriz_combinado, saldo_credito + seguro_total, cols_names_combinado)

    # --- 4. GENERADOR Y DESCARGA DEL EXCEL PREMIUM ---
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        workbook = writer.book
        f_th = workbook.add_format({'font_name': 'Arial', 'font_size': 10, 'bold': True, 'font_color': '#FFFFFF', 'bg_color': '#1B365D', 'align': 'center', 'border': 1})
        f_txt = workbook.add_format({'font_name': 'Arial', 'font_size': 9, 'align': 'center', 'border': 1})
        f_num = workbook.add_format({'font_name': 'Arial', 'font_size': 9, 'num_format': '$#,##0.00', 'border': 1})
        f_porc = workbook.add_format({'font_name': 'Arial', 'font_size': 9, 'num_format': '0.00"%"', 'border': 1, 'align': 'center'})
        f_tot = workbook.add_format({'font_name': 'Arial', 'font_size': 10, 'bold': True, 'bg_color': '#F5F5F5', 'border': 1, 'align': 'center'})
        f_tot_num = workbook.add_format({'font_name': 'Arial', 'font_size': 10, 'bold': True, 'num_format': '$#,##0.00', 'bg_color': '#F5F5F5', 'border': 1})
        f_cab_label = workbook.add_format({'font_name': 'Arial', 'font_size': 9, 'bold': True, 'border': 1, 'bg_color': '#FAFAFA'})
        f_cab_val = workbook.add_format({'font_name': 'Arial', 'font_size': 9, 'border': 1})
        f_bloq = workbook.add_format({'font_name': 'Arial', 'font_size': 10, 'bold': True, 'bg_color': '#EAF0F6', 'border': 1, 'align': 'center'})

        pestanas = [
            ('1. Credito', matriz_credito, saldo_credito, cols_names_estandar, False), 
            ('2. Seguro', matriz_seguro, seguro_total, cols_names_estandar, False), 
            ('3. Combinado', matriz_combinado, saldo_credito + seguro_total, cols_names_combinado, True)
        ]

        for hoja, datos, s_inicial, cols_cab, es_combinado in pestanas:
            ws = workbook.add_worksheet(hoja)
            writer.sheets[hoja] = ws
            if os.path.exists(logo_path):
                ws.insert_image('A1', logo_path, {'x_scale': 0.5, 'y_scale': 0.5})
            
            ws.write('A3', ' CLIENTE :', f_cab_label); ws.merge_range('B3:D3', cliente_nom, f_cab_val)
            ws.write('E3', ' Fecha :', f_cab_label); ws.write('F3', datetime.now().strftime("%d/%m/%Y"), f_cab_val)
            ws.write('A4', ' RUC :', f_cab_label); ws.merge_range('B4:D4', cliente_ruc, f_cab_val)
            ws.write('E4', ' Teléfono :', f_cab_label); ws.write('F4', cliente_tel, f_cab_val)
            ws.write('A5', ' DIRECCION :', f_cab_label); ws.merge_range('B5:F5', cliente_dir, f_cab_val)
            ws.write('A6', ' AVAL :', f_cab_label); ws.merge_range('B6:D6', cliente_aval, f_cab_val)
            ws.write('E6', ' TELEFONO :', f_cab_label); ws.write('F6', cliente_tel_aval, f_cab_val)
            ws.write('A7', ' DNI :', f_cab_label); ws.merge_range('B7:F7', cliente_dni, f_cab_val)

            max_col_letra = 'I' if es_combinado else 'G'
            ws.merge_range(f'A9:{max_col_letra}9', '📊 CONDICIONES DE FINANCIAMIENTO', f_bloq)
            ws.write('A10', 'Precio Bien:', f_cab_label); ws.write('B10', precio, f_num)
            ws.write('C10', 'Cuota Inicial ($):', f_cab_label); ws.write('D10', inicial_monto, f_num)
            ws.write('E10', 'Cuota Inicial (%):', f_cab_label); ws.write('F10', inicial_porc, f_porc)
            ws.write('A11', 'Tramo Financiado:', f_cab_label); ws.write('B11', s_inicial, f_num)
            ws.write('C11', 'Plazo Total:', f_cab_label); ws.write('D11', f"{plazo} meses", f_txt)
            ws.write('E11', 'Tasa Mes:', f_cab_label); ws.write('F11', f"{tasa}%", f_txt)

            for col_idx, text in enumerate(cols_cab): 
                ws.write(13, col_idx, text, f_th)

            r_act = 14
            for fila in datos:
                ws.write(r_act, 0, int(fila[0]), f_txt)
                ws.write(r_act, 1, str(fila[1]), f_txt)
                for c_idx in range(2, len(cols_cab)): 
                    ws.write(r_act, c_idx, float(fila[c_idx]), f_num)
                r_act += 1

            ws.write(r_act, 0, 'TOTAL', f_tot); ws.write(r_act, 1, '', f_tot)
            ws.write(r_act, 2, s_inicial, f_tot_num)
            
            if not es_combinado:
                ws.write_formula(r_act, 3, f"=SUM(D15:D{r_act})", f_tot_num)
                ws.write_formula(r_act, 4, f"=SUM(E15:E{r_act})", f_tot_num)
                ws.write_formula(r_act, 5, f"=SUM(F15:F{r_act})", f_tot_num)
                ws.write(r_act, 6, 0.0, f_tot_num)
            else:
                ws.write_formula(r_act, 3, f"=SUM(D15:D{r_act})", f_tot_num)
                ws.write_formula(r_act, 4, f"=SUM(E15:E{r_act})", f_tot_num)
                ws.write_formula(r_act, 5, f"=SUM(F15:F{r_act})", f_tot_num)
                ws.write_formula(r_act, 6, f"=SUM(G15:G{r_act})", f_tot_num)
                ws.write_formula(r_act, 7, f"=SUM(H15:H{r_act})", f_tot_num)
                ws.write(r_act, 8, 0.0, f_tot_num)
                
            ws.set_column(f'A:{max_col_letra}', 19)

    st.sidebar.markdown("---")
    st.sidebar.download_button(
        label="📥 Descargar Excel Premium",
        data=buffer.getvalue(),
        file_name=f"Simulacion_{cliente_nom.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.ms-excel"
    )
