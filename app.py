import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io

# --- CONFIGURACIÓN DE LA PÁGINA WEB ---
st.set_page_config(page_title="Simulador Financiero COMREIVIC", layout="wide", page_icon="📊")

# FUNCIÓN INTELIGENTE PARA DETECTAR EL LOGO EN EL SERVIDOR
def encontrar_archivo_logo():
    opciones = ['logo.png', 'logo.png.png', 'logo_empresa.png', 'logo_empresa.png.png', 'LOGO.PNG', 'Logo.png']
    for opcion in opciones:
        if os.path.exists(opcion):
            return opcion
    return None

archivo_logo_real = encontrar_archivo_logo()

# Cargar el logo dinámicamente en la web si existe
if archivo_logo_real:
    st.image(archivo_logo_real, width=250)

st.title("📊 Simulador Financiero Interactiva")
st.markdown("---")

# --- 1. ENTRADAS EN LA BARRA LATERAL (SIDEBAR) ---
st.sidebar.header("📝 Parámetros de Simulación")
precio = st.sidebar.number_input("Precio Total ($):", min_value=1.0, value=20000.0, step=100.0)

tipo_inicial = st.sidebar.radio("Tipo de Cuota Inicial:", ["Importe ($)", "Porcentaje (%)"])
valor_inicial = st.sidebar.number_input("Valor de la Inicial:", min_value=0.0, value=2000.0, step=100.0)

# Cálculo y muestra de equivalencia en tiempo real en la barra lateral
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
    for i in range(1, meses + 1):
        s_ini = saldo
        interes = s_ini * t_mes
        amort = cuota - interes
        saldo -= amort
        if abs(saldo) < 0.01: saldo = 0
        cronograma.append([i, s_ini, amort, interes, cuota, saldo])
    return cronograma

if inicial_monto > precio:
    st.error("❌ La cuota inicial no puede ser mayor al precio total.")
else:
    saldo_credito = precio - inicial_monto
    seguro_total = precio * (4.7 / 1000) * 1.03 * 1.18

    matriz_credito = simular_tabla(saldo_credito, plazo, tasa)
    matriz_seguro = simular_tabla(seguro_total, plazo, tasa)
    
    matriz_combinado = []
    for idx in range(len(matriz_credito)):
        c = matriz_credito[idx]
        s = matriz_seguro[idx]
        matriz_combinado.append([c[0], c[1]+s[1], c[2]+s[2], c[3]+s[3], c[4]+s[4], c[5]+s[5]])

    cols_names = ['Mes', 'Saldo Inicial', 'Amortización', 'Interés', 'Cuota', 'Saldo Final']

    # --- 3. PRESENTACIÓN EN LA WEB ---
    st.subheader("📋 Resumen General de la Cotización")
    cuota_fija_combinada = matriz_combinado[0][4]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Saldo Crédito a Financiar", f"${saldo_credito:,.2f}")
    col2.metric("Saldo Seguro Financiado", f"${seguro_total:,.2f}")
    col3.metric("Cuota Mensual Combinada", f"${cuota_fija_combinada:,.2f}")

    st.markdown("**Fórmula Informativa de Seguro Aplicada:**")
    st.latex(r"\text{Seguro Total} = \text{Precio Total} \times \left(\frac{4.7}{1000}\right) \times 1.03 \times 1.18")

    # Mostrar las 3 pestañas en la página web
    tab1, tab2, tab3 = st.tabs(["🧱 1. Cronograma de Crédito", "🛡️ 2. Cronograma de Seguro", "🔄 3. Cronograma Combinado Total"])
    
    def mostrar_web(tab_obj, datos, inicial):
        df = pd.DataFrame(datos, columns=cols_names)
        tot = {'Mes': 'TOTAL', 'Saldo Inicial': inicial, 'Amortización': df['Amortización'].sum(), 'Interés': df['Interés'].sum(), 'Cuota': df['Cuota'].sum(), 'Saldo Final': 0.0}
        df_v = pd.concat([df, pd.DataFrame([tot])], ignore_index=True)
        tab_obj.dataframe(df_v.style.format({c: "${:,.2f}" for c in cols_names if c != 'Mes'}), use_container_width=True, hide_index=True)

    mostrar_web(tab1, matriz_credito, saldo_credito)
    mostrar_web(tab2, matriz_seguro, seguro_total)
    mostrar_web(tab3, matriz_combinado, saldo_credito + seguro_total)

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

        pestanas = [('1. Credito', matriz_credito, saldo_credito), 
                    ('2. Seguro', matriz_seguro, seguro_total), 
                    ('3. Combinado', matriz_combinado, saldo_credito + seguro_total)]

        for hoja, datos, s_inicial in pestanas:
            ws = workbook.add_worksheet(hoja)
            writer.sheets[hoja] = ws
            if archivo_logo_real:
                ws.insert_image('A1', archivo_logo_real, {'x_scale': 0.5, 'y_scale': 0.5})
            
            # Cabecera de la Imagen Vacía
            ws.write('A3', ' CLIENTE :', f_cab_label); ws.merge_range('B3:D3', '', f_cab_val)
            ws.write('E3', ' Fecha :', f_cab_label); ws.write('F3', datetime.now().strftime("%d/%m/%Y"), f_cab_val)
            ws.write('A4', ' RUC :', f_cab_label); ws.merge_range('B4:D4', '', f_cab_val)
            ws.write('E4', ' Teléfono :', f_cab_label); ws.write('F4', '', f_cab_val)
            ws.write('A5', ' DIRECCION :', f_cab_label); ws.merge_range('B5:F5', '', f_cab_val)
            ws.write('A6', ' AVAL :', f_cab_label); ws.merge_range('B6:D6', '', f_cab_val)
            ws.write('E6', ' TELEFONO :', f_cab_label); ws.write('F6', '', f_cab_val)
            ws.write('A7', ' DNI :', f_cab_label); ws.merge_range('B7:F7', '', f_cab_val)

            # Condiciones de Financiamiento
            ws.merge_range('A9:F9', '📊 CONDICIONES DE FINANCIAMIENTO', f_bloq)
            ws.write('A10', 'Precio Bien:', f_cab_label); ws.write('B10', precio, f_num)
            ws.write('C10', 'Cuota Inicial ($):', f_cab_label); ws.write('D10', inicial_monto, f_num)
            ws.write('E10', 'Cuota Inicial (%):', f_cab_label); ws.write('F10', inicial_porc, f_porc)
            ws.write('A11', 'Tramo Financiado:', f_cab_label); ws.write('B11', s_inicial, f_num)
            ws.write('C11', 'Plazo Total:', f_cab_label); ws.write('D11', f"{plazo} meses", f_txt)
            ws.write('E11', 'Tasa Mes:', f_cab_label); ws.write('F11', f"{tasa}%", f_txt)

            for col_idx, text in enumerate(cols_names): ws.write(13, col_idx, text, f_th)

            r_act = 14
            for fila_d in datos:
                ws.write(r_act, 0, int(fila_d[0]), f_txt)
                for c_idx in range(1, 6): ws.write(r_act, c_idx, float(fila_d[c_idx]), f_num)
                r_act += 1

            ws.write(r_act, 0, 'TOTAL', f_tot); ws.write(r_act, 1, s_inicial, f_tot_num)
            ws.write_formula(r_act, 2, f"=SUM(C15:C{r_act})", f_tot_num)
            ws.write_formula(r_act, 3, f"=SUM(D15:D{r_act})", f_tot_num)
            ws.write_formula(r_act, 4, f"=SUM(E15:E{r_act})", f_tot_num)
            ws.write(r_act, 5, 0.0, f_tot_num)
            ws.set_column('A:F', 18)

    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button(label="📥 Descargar Reporte en Excel Premium", data=buffer.getvalue(), file_name="Reporte_Financiero_COMREIVIC.xlsx", mime="application/vnd.ms-excel")
