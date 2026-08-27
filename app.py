import streamlit as st
import pandas as pd
from datetime import datetime
from datetime import datetime, timedelta
import os
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.units import cm
import re
import unicodedata

# --- CONFIGURACIÓN DE LA PÁGINA WEB ---
st.set_page_config(page_title="Simulador Financiero COMREIVIC", layout="wide", page_icon="📊")

logo_path = 'Logo.jpg'
mhe_logo_path = 'mhe-color.png'
logo_col1, logo_col2 = st.columns([3, 1])
with logo_col1:
    if os.path.exists(logo_path):
        st.image(logo_path, width=250)
with logo_col2:
    if os.path.exists(mhe_logo_path):
        st.image(mhe_logo_path, width=180)

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
tipo_maquina = st.sidebar.text_input("Tipo de Máquina:", value="Excavadora Hidráulica")

cliente_seguro = unicodedata.normalize('NFKD', cliente_nom)
cliente_seguro = cliente_seguro.encode('ascii', 'ignore').decode('ascii')
cliente_seguro = re.sub(r'[^A-Za-z0-9_-]', '', cliente_seguro)

st.sidebar.header("📝 Parámetros de Simulación")
precio = st.sidebar.number_input("Precio Total ($):", min_value=1.0, value=200000.0, step=100.0, format="%.2f")
# VISUAL ANCHOR: Mostramos al usuario el formato de miles y millones exacto inmediatamente abajo
st.sidebar.write(f"💵 Monto ingresado: **${precio:,.2f}**")

tipo_inicial = st.sidebar.radio("Tipo de Cuota Inicial:", ["Importe ($)", "Porcentaje (%)"])

# # Asignar un valor inicial por defecto coherente según la selección
if tipo_inicial == "Porcentaje (%)":
    valor_defecto = 10.0  # 10% por defecto
    paso_cambio = 1.0  # Cambios de 1 en 1 por ciento
    max_permisible = 100.0
    formato_input = "%.2f"
else:
    # MODIFICACIÓN CLAVE: El valor por defecto ahora se adapta automáticamente al 10% del precio ingresado
    valor_defecto = float(precio * 0.10)  
    paso_cambio = 100.0  # Cambios de 100 en 100 dólares
    max_permisible = float(precio)
    formato_input = "%.2f"

# El campo ahora adapta sus límites y su valor según el botón de arriba de forma segura
valor_inicial = st.sidebar.number_input(
    "Valor de la Inicial:",
    min_value=0.0,
    max_value=float(max_permisible),
    value=float(valor_defecto),  # Forzamos conversión limpia a float para evitar conflictos de caché
    step=float(paso_cambio),
    format=formato_input
)

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
        
        #---fecha_pago = (fecha_base + relativedelta(months=i)).strftime("%d/%m/%Y")
        fecha_pago = (fecha_base + timedelta(days=30 * i)).strftime("%d/%m/%Y")
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
    
    # --- CRONOGRAMA COMBINADO ---
    # Los valores financieros corresponden únicamente al equipo/maquinaria.
    # El seguro se muestra por separado y se suma únicamente en "Cuota final".

    matriz_combinado = []

    for c, s in zip(matriz_credito, matriz_seguro):
        cuota_equipo = c[5]
        cuota_seguro = s[5]

        matriz_combinado.append([
            c[0],                  # Nro. Cuota
            c[1],                  # Fecha de Pago
            c[2],                  # Saldo Inicial - equipo
            c[3],                  # Amortización - equipo
            c[4],                  # Interés - equipo
            cuota_seguro,          # Seguro
            cuota_equipo + cuota_seguro,  # Cuota final
            c[6]                   # Saldo final - equipo
        ])

    cols_names_estandar = [
        'Nro. Cuota',
        'Fecha de Pago',
        'Saldo Inicial',
        'Amortización',
        'Interés',
        'Cuota',
        'Saldo Final'
    ]

    cols_names_combinado = [
        'Nro. Cuota',
        'Fecha de Pago',
        'Saldo Inicial',
        'Amortización',
        'Interés',
        'Seguro',
        'Cuota final',
        'Saldo final'
    ]

    # --- 3. PRESENTACIÓN EN LA WEB ---
    st.subheader("📋 Resumen General de la Cotización")
    col1, col2, col3 = st.columns(3)
    col1.metric("Saldo Crédito a Financiar", f"${saldo_credito:,.2f}")
    col2.metric("Saldo Seguro Financiado", f"${seguro_total:,.2f}")
    col3.metric("Cuota Mensual Combinada", f"${matriz_combinado[0][6]:,.2f}")

    st.markdown("**Fórmula Informativa de Seguro Aplicada:**")
    st.latex(r"\text{Seguro Total} = \text{Precio Total} \times \left(\frac{4.7}{1000}\right) \times 1.03 \times 1.18")

    tab1, tab2, tab3 = st.tabs(["🧱 1. Cronograma de Crédito", "🛡️ 2. Cronograma de Seguro", "🔄 3. Cronograma Combinado Total"])
    
    def mostrar_web(tab_obj, datos, inicial, nombres_columnas, es_combinado=False):
        with tab_obj:
            df = pd.DataFrame(datos, columns=nombres_columnas)

            # Fila TOTAL
            tot = {
                    'Nro. Cuota': 'TOTAL',
                    'Fecha de Pago': '',
                    'Saldo Inicial': inicial
                }
            # Colocar el saldo final en la misma columna existente
            if 'Saldo final' in nombres_columnas:
                tot['Saldo final'] = 0.0
            elif 'Saldo Final' in nombres_columnas:
                tot['Saldo Final'] = 0.0

            if es_combinado:
                columnas_sumables = [
                    'Amortización',
                    'Interés',
                    'Seguro',
                    'Cuota final'
                ]
            else:
                columnas_sumables = [
                    'Amortización',
                    'Interés',
                    'Cuota'
                ]

            for col in columnas_sumables:
                if col in df.columns:
                    tot[col] = df[col].sum()

            df_v = pd.concat(
                [df, pd.DataFrame([tot])],
                ignore_index=True
            )

            # Evita conflicto entre números y "TOTAL"
            df_v['Nro. Cuota'] = df_v['Nro. Cuota'].astype(str)

            tab_obj.dataframe(
                df_v.style.format({
                    c: "${:,.2f}"
                    for c in nombres_columnas
                    if c not in ['Nro. Cuota', 'Fecha de Pago']
                }),
                width="stretch",
                hide_index=True
            )

    mostrar_web(
        tab1,
        matriz_credito,
        saldo_credito,
        cols_names_estandar
    )

    mostrar_web(
        tab2,
        matriz_seguro,
        seguro_total,
        cols_names_estandar
    )

    mostrar_web(
        tab3,
        matriz_combinado,
        saldo_credito,
        cols_names_combinado,
        es_combinado=True
    )

    # --- 4. GENERADORES DE EXCEL Y PDF ---
    def generar_excel():
        buffer = io.BytesIO()

        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            workbook = writer.book
            ws = workbook.add_worksheet('Combinado')
            writer.sheets['Combinado'] = ws

            f_th = workbook.add_format({
                'font_name': 'Arial', 'font_size': 10, 'bold': True,
                'font_color': '#FFFFFF', 'bg_color': '#1B365D',
                'align': 'center', 'border': 1
            })
            f_txt = workbook.add_format({
                'font_name': 'Arial', 'font_size': 9,
                'align': 'center', 'border': 1
            })
            f_num = workbook.add_format({
                'font_name': 'Arial', 'font_size': 9,
                'num_format': '$#,##0.00', 'border': 1
            })
            f_porc = workbook.add_format({
                'font_name': 'Arial', 'font_size': 9,
                'num_format': '0.00"%"', 'border': 1, 'align': 'center'
            })
            f_tot = workbook.add_format({
                'font_name': 'Arial', 'font_size': 10, 'bold': True,
                'bg_color': '#F5F5F5', 'border': 1, 'align': 'center'
            })
            f_tot_num = workbook.add_format({
                'font_name': 'Arial', 'font_size': 10, 'bold': True,
                'num_format': '$#,##0.00', 'bg_color': '#F5F5F5', 'border': 1
            })
            f_cab_label = workbook.add_format({
                'font_name': 'Arial', 'font_size': 9, 'bold': True,
                'border': 1, 'bg_color': '#FAFAFA'
            })
            f_cab_val = workbook.add_format({
                'font_name': 'Arial', 'font_size': 9, 'border': 1
            })
            f_bloq = workbook.add_format({
                'font_name': 'Arial', 'font_size': 10, 'bold': True,
                'bg_color': '#EAF0F6', 'border': 1, 'align': 'center'
            })
            f_note = workbook.add_format({
                'font_name': 'Arial', 'font_size': 9,
                'text_wrap': True, 'valign': 'top', 'border': 1
            })

            # Altura de filas del encabezado
            ws.set_row(0, 35)
            ws.set_row(1, 25)

            if os.path.exists(logo_path):
                ws.insert_image('A1', logo_path, {'x_scale': 0.20, 'y_scale': 0.20})
            if os.path.exists(mhe_logo_path):
                ws.insert_image('H1', mhe_logo_path, {'x_scale': 0.12, 'y_scale': 0.12})

            titulo_fmt = workbook.add_format({
                'bold': True,
                'font_size': 20,
                'font_name': 'Arial',
                'font_color': '#1B365D',
                'align': 'center',
                'valign': 'vcenter'
            })
            ws.merge_range('C1:G2', 'Simulador Financiero Interactivo', titulo_fmt)

            ws.write('A4', ' CLIENTE :', f_cab_label)
            ws.merge_range('B4:D4', cliente_nom, f_cab_val)
            ws.write('E4', ' Fecha :', f_cab_label)
            ws.write('F4', datetime.now().strftime('%d/%m/%Y'), f_cab_val)

            ws.write('A5', ' RUC/DNI :', f_cab_label)
            ws.merge_range('B5:D5', cliente_ruc, f_cab_val)
            ws.write('E5', ' Teléfono :', f_cab_label)
            ws.write('F5', cliente_tel, f_cab_val)

            ws.write('A6', ' Dirección :', f_cab_label)
            ws.merge_range('B6:F6', cliente_dir, f_cab_val)

            ws.write('A7', ' Aval :', f_cab_label)
            ws.merge_range('B7:D7', cliente_aval, f_cab_val)
            ws.write('E7', ' Teléfono Aval :', f_cab_label)
            ws.write('F7', cliente_tel_aval, f_cab_val)

            ws.write('A8', ' DNI Aval :', f_cab_label)
            ws.merge_range('B8:F8', cliente_dni, f_cab_val)

            ws.merge_range('A9:H9', '📊 RESUMEN DEL FINANCIAMIENTO', f_bloq)

            ws.write('A10', 'Tipo Máquina:', f_cab_label)
            ws.merge_range('B10:D10', tipo_maquina, f_cab_val)
            ws.write('E10', 'Precio Bien:', f_cab_label)
            ws.write('F10', precio, f_num)

            ws.write('A11', 'Cuota Inicial ($):', f_cab_label)
            ws.write('B11', inicial_monto, f_num)
            ws.write('C11', 'Cuota Inicial (%):', f_cab_label)
            ws.write('D11', inicial_porc, f_porc)
            ws.write('E11', 'Importe Financiado:', f_cab_label)
            ws.write('F11', saldo_credito, f_num)

            ws.write('A12', 'Plazo Total:', f_cab_label)
            ws.write('B12', f'{plazo} meses', f_txt)
            ws.write('C12', 'Tasa Mes:', f_cab_label)
            ws.write('D12', f'{tasa}%', f_txt)

            for col_idx, text in enumerate(cols_names_combinado):
                ws.write(14, col_idx, text, f_th)

            r_act = 15
            for fila in matriz_combinado:
                ws.write(r_act, 0, int(fila[0]), f_txt)
                ws.write(r_act, 1, str(fila[1]), f_txt)
                for c_idx in range(2, len(cols_names_combinado)):
                    ws.write(r_act, c_idx, float(fila[c_idx]), f_num)
                r_act += 1

            ws.write(r_act, 0, 'TOTAL', f_tot)
            ws.write(r_act, 1, '', f_tot)
            ws.write(r_act, 2, saldo_credito, f_tot_num)
            ws.write_formula(r_act, 3, f'=SUM(D16:D{r_act})', f_tot_num)
            ws.write_formula(r_act, 4, f'=SUM(E16:E{r_act})', f_tot_num)
            ws.write_formula(r_act, 5, f'=SUM(F16:F{r_act})', f_tot_num)
            ws.write_formula(r_act, 6, f'=SUM(G16:G{r_act})', f_tot_num)
            ws.write(r_act, 7, 0.0, f_tot_num)

            ws.merge_range(
                r_act + 2, 0, r_act + 3, 7,
                'Nota: Saldo Inicial, Amortización, Interés y Saldo final '
                'corresponden al financiamiento del equipo/maquinaria. La '
                'columna Seguro corresponde a la cuota del seguro financiado. '
                'La Cuota final integra equipo + seguro.',
                f_note
            )

            ws.set_column('A:A', 12)
            ws.set_column('B:B', 16)
            ws.set_column('C:H', 18)
            ws.freeze_panes(15, 0)

        buffer.seek(0)
        return buffer.getvalue()

    def generar_pdf():
        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=0.5 * cm,
            leftMargin=0.5 * cm,
            topMargin=0.4 * cm,
            bottomMargin=0.4 * cm
        )

        styles = getSampleStyleSheet()
        normal = ParagraphStyle(
            'NormalCustom', parent=styles['Normal'],
            fontName='Helvetica', fontSize=7.2, leading=8.5
        )
        title = ParagraphStyle(
            'TitleCustom', parent=styles['Title'],
            fontName='Helvetica-Bold', fontSize=16, leading=18,
            alignment=TA_CENTER, textColor=colors.HexColor('#1B365D')
        )
        section = ParagraphStyle(
            'SectionCustom', parent=styles['Normal'],
            fontName='Helvetica-Bold', fontSize=10, leading=11,
            textColor=colors.HexColor('#1B365D')
        )
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=normal,
            fontName='Helvetica-Bold',
            textColor=colors.white,
            alignment=TA_CENTER
        )
        section_align = ParagraphStyle(
            'SectionAlign',
            parent=section,
            leftIndent=1.4 * cm
        )
        note_style = ParagraphStyle(
            'NoteStyle',
            parent=normal,
            leftIndent=1.4 * cm
        )

        story = []

        left_logo = Image(logo_path, width=5.0*cm, height=1.4*cm) if os.path.exists(logo_path) else ''
        right_logo = Image(mhe_logo_path, width=4.2*cm, height=1.1*cm) if os.path.exists(mhe_logo_path) else ''

        logos = Table(
            [[left_logo, '', right_logo]],
            colWidths=[7*cm, 13*cm, 7*cm]
        )
        logos.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (0,0), 'LEFT'),
            ('ALIGN', (2,0), (2,0), 'RIGHT')
        ]))
        story += [logos, Spacer(1, 0.08*cm), Paragraph(
            'Simulador Financiero Interactivo', title
        ), Spacer(1, 0.12*cm)]

        info = [
            ['Cliente', cliente_nom, 'RUC/DNI', cliente_ruc, 'Fecha', datetime.now().strftime('%d/%m/%Y')],
            ['Dirección', cliente_dir, 'Teléfono', cliente_tel, 'Máquina', tipo_maquina],
            ['Aval / Fiador', cliente_aval, 'DNI Aval', cliente_dni, 'Tel. Aval', cliente_tel_aval],
        ]
        info_rows = []
        for row in info:
            info_rows.append([
                Paragraph(f'<b>{v}</b>' if i in (0,2,4) else str(v), normal)
                for i, v in enumerate(row)
            ])

        info_table = Table(
            info_rows,
            colWidths=[2.0*cm, 6.0*cm, 2.0*cm, 4.0*cm, 2.0*cm, 7.0*cm]
        )
        info_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#D0D7DE')),
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#F5F7FA')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 3),
            ('RIGHTPADDING', (0,0), (-1,-1), 3),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2)
        ]))
        story += [info_table, Spacer(1, 0.1*cm)]

        resumen_data = [
            [
                "Precio del Bien",
                f"${precio:,.2f}",
                "Cuota Inicial",
                f"${inicial_monto:,.2f} ({inicial_porc:.2f}%)"
            ],
            [
                "Importe Financiado",
                f"${saldo_credito:,.2f}",
                "Plazo",
                f"{plazo} meses"
            ],
            [
                "Tasa Mensual",
                f"{tasa:.2f}%",
                "Seguro Total",
                f"${seguro_total:,.2f}"
            ]
        ]

        resumen_table = Table(
            resumen_data,
            colWidths=[3.0*cm, 2.8*cm, 3.0*cm, 3.2*cm]
        )

        resumen_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),

            ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#1B365D')),
            ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#1B365D')),

            ('TEXTCOLOR', (0,0), (0,-1), colors.white),
            ('TEXTCOLOR', (2,0), (2,-1), colors.white),

            ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8),

            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))

        titulo_table = Table(
            [[Paragraph('Cronograma Combinado (Equipo + Seguro)', section)]],
            colWidths=[24*cm]  # mismo ancho de la tabla principal
        )

        titulo_table.setStyle(TableStyle([
            ('LEFTPADDING', (0,0), (0,0), 0),
            ('RIGHTPADDING', (0,0), (0,0), 0),
            ('TOPPADDING', (0,0), (0,0), 0),
            ('BOTTOMPADDING', (0,0), (0,0), 0),
        ]))

        story += [
            resumen_table,
            Spacer(1, 0.12*cm),
            titulo_table,
            Spacer(1, 0.06*cm)
        ]

        pdf_data = [[
            Paragraph('<b>Nro. Cuota</b>', header_style),
            Paragraph('<b>Fecha de Pago</b>', header_style),
            Paragraph('<b>Saldo Inicial</b>', header_style),
            Paragraph('<b>Amortización</b>', header_style),
            Paragraph('<b>Interés</b>', header_style),
            Paragraph('<b>Seguro</b>', header_style),
            Paragraph('<b>Cuota final</b>', header_style),
            Paragraph('<b>Saldo final</b>', header_style)
        ]]

        for fila in matriz_combinado:
            pdf_data.append([
                str(fila[0]), str(fila[1]),
                f'${fila[2]:,.2f}', f'${fila[3]:,.2f}',
                f'${fila[4]:,.2f}', f'${fila[5]:,.2f}',
                f'${fila[6]:,.2f}', f'${fila[7]:,.2f}'
            ])

        pdf_data.append([
            'TOTAL', '',
            f'${saldo_credito:,.2f}',
            f'${sum(x[3] for x in matriz_combinado):,.2f}',
            f'${sum(x[4] for x in matriz_combinado):,.2f}',
            f'${sum(x[5] for x in matriz_combinado):,.2f}',
            f'${sum(x[6] for x in matriz_combinado):,.2f}',
            '$0.00'
        ])

        table = Table(
            pdf_data,
            repeatRows=1,
            colWidths=[2.0*cm, 3.0*cm, 3.3*cm, 3.3*cm,
                       3.0*cm, 2.8*cm, 3.3*cm, 3.3*cm]
        )
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1B365D')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#D0D7DE')),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTSIZE', (0,0), (-1,-1), 6.8),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#F5F5F5')),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold')
        ]))
        story.append(table)
        story.append(Spacer(1, 0.15*cm))
        story.append(Paragraph(
            '<b>Nota:</b> Saldo Inicial, Amortización, Interés y Saldo final '
            'corresponden al financiamiento del equipo/maquinaria. La columna '
            'Seguro corresponde a la cuota del seguro financiado. La Cuota '
            'final integra equipo + seguro.',
            note_style
        ))
        story.append(Paragraph(
            'Seguro Total = Precio Total × (4.7 / 1000) × 1.03 × 1.18',
            note_style
        ))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    excel_data = generar_excel()
    pdf_data = generar_pdf()

    st.sidebar.markdown("---")

#    st.download_button(
#        label="📊 Descargar Excel",
#        data=excel_data,
#        file_name=f"Simulacion_{cliente_seguro}_{datetime.now().strftime('%Y%m%d')}.xlsx"
#    )
    
#    st.download_button(
#        label="📄 Descargar PDF",
#        data=pdf_data,
#        file_name=f"Simulacion_{cliente_seguro}_{datetime.now().strftime('%Y%m%d')}.pdf"
#    )

#    st.sidebar.download_button(
#        label="📊 Descargar Excel",
#        data=excel_data,
#        file_name=f"Simulacion_{cliente_seguro}_{datetime.now().strftime('%Y%m%d')}.xlsx",
#        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#    )
    st.sidebar.download_button(
        label="📄 Descargar PDF",
        data=pdf_data,
        file_name=f"Simulacion_{cliente_seguro}_{datetime.now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf"
    )
