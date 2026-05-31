# ui_components.py
# Componentes reutilizáveis da interface Streamlit

import streamlit as st
import pandas as pd
import config
from data_access import combina_existe, carregar_dados_existentes, excluir_registros_vaga
from utils import exibir_mensagem_centralizada, force_reset
import time
from datetime import datetime
import io
import csv
from fpdf import FPDF

# ---------------------------
# Função para gerar PDF da tabela filtrada (layout corrigido)
# ---------------------------
def gerar_pdf_tabela(df, titulo="Relatório de Paletes"):
    """
    Gera um arquivo PDF com layout profissional (A4, zebra striping, quebra de linha automática)
    a partir de um DataFrame.
    Retorna bytes do PDF.
    """
    if df.empty:
        return None

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Título
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, titulo, ln=True, align="C")
    pdf.ln(5)

    # Data e total
    pdf.set_font("Helvetica", "", 10)
    data_geracao = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    pdf.cell(0, 6, f"Gerado em: {data_geracao}", ln=True, align="R")
    pdf.cell(0, 6, f"Total de registros: {len(df)}", ln=True, align="R")
    pdf.ln(8)

    colunas = list(df.columns)
    # Definir larguras conforme número de colunas (em mm, total 190)
    if len(colunas) == 6:
        larguras = [32, 24, 24, 40, 40, 30]
    elif len(colunas) == 4:
        larguras = [40, 45, 55, 50]
    else:
        larguras = [35, 30, 28, 45, 45]

    # Cabeçalho
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(80, 80, 80)
    pdf.set_text_color(255, 255, 255)
    for i, col in enumerate(colunas):
        pdf.cell(larguras[i], 8, col, border=1, align="C", fill=True)
    pdf.ln()
    pdf.set_text_color(0, 0, 0)

    # Dados com zebra striping
    fill = False
    for idx, row in df.iterrows():
        # Calcular altura máxima necessária para esta linha
        alturas_celulas = []
        for i, col in enumerate(colunas):
            valor = str(row[col]) if pd.notna(row[col]) else ""
            pdf.set_font("Helvetica", "", 8)
            # Estima número de linhas que o texto ocupará
            palavras = valor.split()
            linha_atual = ""
            linhas = 1
            largura_max = larguras[i] - 2  # margem interna
            for palavra in palavras:
                teste = linha_atual + (" " if linha_atual else "") + palavra
                if pdf.get_string_width(teste) <= largura_max:
                    linha_atual = teste
                else:
                    linhas += 1
                    linha_atual = palavra
            alturas_celulas.append(linhas)
        altura_linha = max(alturas_celulas) * 5  # 5mm por linha

        # Verificar se precisa de nova página
        if pdf.get_y() + altura_linha > 280:  # margem inferior 10mm
            pdf.add_page()
            # Redesenhar cabeçalho na nova página
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_fill_color(80, 80, 80)
            pdf.set_text_color(255, 255, 255)
            for i, col in enumerate(colunas):
                pdf.cell(larguras[i], 8, col, border=1, align="C", fill=True)
            pdf.ln()
            pdf.set_text_color(0, 0, 0)
            fill = False  # reseta zebra na nova página

        # Desenhar células da linha
        x_inicial = pdf.get_x()
        y_inicial = pdf.get_y()
        pdf.set_font("Helvetica", "", 8)
        for i, col in enumerate(colunas):
            valor = str(row[col]) if pd.notna(row[col]) else ""
            pdf.set_y(y_inicial)
            pdf.set_x(x_inicial + sum(larguras[:i]))
            # Cor de fundo alternada
            if fill:
                pdf.set_fill_color(230, 230, 230)
            else:
                pdf.set_fill_color(255, 255, 255)
            # MultiCell com altura fixa baseada no cálculo
            pdf.multi_cell(larguras[i], 5, valor, border=1, align="L", fill=fill)
        # Move Y para o final da linha (após a última célula)
        pdf.set_y(y_inicial + altura_linha)
        pdf.set_x(x_inicial)
        fill = not fill

    # Gerar bytes do PDF
    buffer = io.BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()

# ---------------------------
# Componentes da UI (mesmo código anterior, apenas com a função corrigida)
# ---------------------------
def renderizar_secao_consulta(df_existente):
    """Renderiza a seção de consulta com botões para CSV e PDF."""
    st.markdown("---")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filtro_camara = st.selectbox(
            "Câmara",
            ["Todas"] + config.CAMARAS,
            key="filtro_camara"
        )
    with col_f2:
        filtro_vaga = st.selectbox(
            "Vaga",
            ["Todas"] + config.VAGAS,
            key="filtro_vaga"
        )

    filtro_texto = st.text_input("Buscar em marca/descrição", key="filtro_texto")

    # Aplicar filtros
    df_filtrado = df_existente.copy()
    if filtro_camara != "Todas":
        df_filtrado = df_filtrado[df_filtrado['camara'] == filtro_camara]
    if filtro_vaga != "Todas":
        df_filtrado = df_filtrado[df_filtrado['camara-vaga'] == filtro_vaga]
    if filtro_texto:
        texto = filtro_texto.lower()
        df_filtrado = df_filtrado[
            df_filtrado['produto-marca'].str.lower().str.contains(texto, na=False) |
            df_filtrado['produto-descricao'].str.lower().str.contains(texto, na=False)
        ]

    # Exibir resultados
    if filtro_camara != "Todas" and filtro_vaga != "Todas":
        st.write(f"**Registros encontrados para {filtro_camara} / {filtro_vaga}:**")
        if not df_filtrado.empty:
            st.dataframe(
                df_filtrado[['registro', 'produto-marca', 'produto-descricao', 'validade']],
                use_container_width=True,
                column_config={
                    "registro": st.column_config.DatetimeColumn(
                        "Registro",
                        format="DD/MM/YYYY HH:mm:ss"
                    ),
                    "validade": st.column_config.DateColumn(
                        "Validade",
                        format="DD/MM/YYYY"
                    )
                }
            )
        else:
            st.info("Nenhum registro encontrado para esta combinação.")
    else:
        st.write(f"**Registros encontrados: {len(df_filtrado)}**")
        if not df_filtrado.empty:
            st.dataframe(
                df_filtrado[['registro', 'camara', 'camara-vaga', 'produto-marca', 'produto-descricao', 'validade']],
                use_container_width=True,
                column_config={
                    "registro": st.column_config.DatetimeColumn(
                        "Registro",
                        format="DD/MM/YYYY HH:mm:ss"
                    ),
                    "validade": st.column_config.DateColumn(
                        "Validade",
                        format="DD/MM/YYYY"
                    )
                }
            )
        else:
            st.info("Nenhum registro corresponde aos filtros.")

    # Botões de exportação (CSV e PDF)
    if not df_filtrado.empty:
        # Preparar DataFrame para exportação (datas formatadas)
        df_export = df_filtrado.copy()
        if 'registro' in df_export.columns:
            df_export['registro'] = pd.to_datetime(df_export['registro'], errors='coerce')
            df_export['registro'] = df_export['registro'].dt.strftime('%d/%m/%Y %H:%M:%S')
        if 'validade' in df_export.columns:
            df_export['validade'] = pd.to_datetime(df_export['validade'], errors='coerce')
            df_export['validade'] = df_export['validade'].dt.strftime('%d/%m/%Y')

        col_botao1, col_botao2 = st.columns(2)
        with col_botao1:
            # CSV
            output_csv = io.StringIO()
            df_export.to_csv(output_csv, index=False, sep=';', encoding='utf-8-sig', quoting=csv.QUOTE_ALL)
            csv_data = output_csv.getvalue().encode('utf-8-sig')
            st.download_button(
                label="📥 Baixar CSV",
                data=csv_data,
                file_name="relatorio_paletes.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col_botao2:
            # PDF
            if st.button("📄 Baixar PDF (A4)", use_container_width=True):
                with st.spinner("Gerando PDF..."):
                    pdf_bytes = gerar_pdf_tabela(df_export, titulo="Relatório de Paletes - Perecíveis 410")
                    if pdf_bytes:
                        st.download_button(
                            label="✅ Clique para salvar PDF",
                            data=pdf_bytes,
                            file_name="relatorio_paletes.pdf",
                            mime="application/pdf",
                            key="pdf_download_ready"
                        )
                    else:
                        st.error("Erro ao gerar PDF. Tente novamente.")
    else:
        st.info("Nenhum dado para exportar.")

    st.markdown("---")

# As demais funções (renderizar_secao_cadastro, _renderizar_gerenciamento_vaga,
# _validar_dataframe, _converter_edited_df, renderizar_secao_produtos, _finalizar_palete)
# permanecem EXATAMENTE como na versão anterior, sem alterações.
# Para economizar espaço, elas não estão reescritas aqui, mas devem ser mantidas.
# Se necessário, copie do código anterior que você já possuía.