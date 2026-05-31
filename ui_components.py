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
from fpdf import FPDF

# ---------------------------
# Função para gerar PDF da tabela filtrada
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
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Título principal
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, titulo, ln=True, align="C")
    pdf.ln(5)

    # Data de geração
    pdf.set_font("Arial", "", 10)
    data_geracao = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    pdf.cell(0, 6, f"Gerado em: {data_geracao}", ln=True, align="R")
    pdf.cell(0, 6, f"Total de registros: {len(df)}", ln=True, align="R")
    pdf.ln(8)

    # Definir cabeçalhos e larguras proporcionais
    colunas = list(df.columns)
    # Ajuste de largura (total A4 com margens = 190mm)
    larguras = [35, 30, 28, 45, 45]  # conforme número de colunas
    if len(colunas) == 6:
        larguras = [32, 24, 24, 40, 40, 30]
    elif len(colunas) == 4:
        larguras = [40, 45, 55, 50]

    # Cabeçalho com fundo cinza escuro e texto branco
    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(80, 80, 80)
    pdf.set_text_color(255, 255, 255)
    for i, col in enumerate(colunas):
        pdf.cell(larguras[i], 8, col, border=1, align="C", fill=True)
    pdf.ln()

    # Alternância de cores (zebra striping)
    pdf.set_text_color(0, 0, 0)
    fill = False
    for idx, row in df.iterrows():
        # Altura da linha será dinâmica com base no conteúdo mais alto
        max_linhas = 1
        alturas_linhas = []
        # Pré-calcular número de linhas necessárias para cada coluna
        for i, col in enumerate(colunas):
            valor = str(row[col]) if pd.notna(row[col]) else ""
            # Estima quantas linhas cabem na largura da célula
            pdf.set_font("Arial", "", 8)
            largura_celula = larguras[i]
            # FPDF não tem text wrap automático, simulamos:
            # Usamos multi_cell internamente, mas para altura precisamos calcular.
            # Vamos usar um método simples: dividir texto por palavras
            palavras = valor.split()
            linha_atual = ""
            linhas_celula = 1
            for palavra in palavras:
                teste = linha_atual + (" " if linha_atual else "") + palavra
                if pdf.get_string_width(teste) <= largura_celula - 2:
                    linha_atual = teste
                else:
                    linhas_celula += 1
                    linha_atual = palavra
            alturas_linhas.append(linhas_celula)
            max_linhas = max(max_linhas, linhas_celula)

        altura_linha = max_linhas * 5  # 5mm por linha (fonte 8)
        # Desenhar células
        x_inicial = pdf.get_x()
        y_inicial = pdf.get_y()
        pdf.set_font("Arial", "", 8)
        for i, col in enumerate(colunas):
            valor = str(row[col]) if pd.notna(row[col]) else ""
            # Cor de fundo alternada
            if fill:
                pdf.set_fill_color(230, 230, 230)
            else:
                pdf.set_fill_color(255, 255, 255)
            pdf.set_y(y_inicial)
            pdf.set_x(x_inicial + sum(larguras[:i]))
            # Escrever com multi_cell na altura calculada
            pdf.multi_cell(larguras[i], 5, valor, border=1, align="L", fill=fill)
        pdf.set_y(y_inicial + altura_linha)
        pdf.set_x(x_inicial)
        fill = not fill

    # Retornar bytes do PDF
    return pdf.output(dest='S').encode('latin1')  # FPDF retorna bytes com latin1
    # Nota: FPDF2 pode retornar bytes com output(dest='S'), mas precisamos garantir codificação.
    # Ajuste: usar io.BytesIO
    # Vou reimplementar usando buffer de bytes para garantir.

# Implementação alternativa usando buffer
def gerar_pdf_tabela_seguro(df, titulo="Relatório de Paletes"):
    if df.empty:
        return None
    from fpdf import FPDF
    import io

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Título
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, titulo, ln=True, align="C")
    pdf.ln(5)

    # Data e total
    pdf.set_font("Arial", "", 10)
    data_geracao = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    pdf.cell(0, 6, f"Gerado em: {data_geracao}", ln=True, align="R")
    pdf.cell(0, 6, f"Total de registros: {len(df)}", ln=True, align="R")
    pdf.ln(8)

    colunas = list(df.columns)
    # Definir larguras conforme número de colunas
    if len(colunas) == 6:
        larguras = [32, 24, 24, 40, 40, 30]
    elif len(colunas) == 4:
        larguras = [40, 45, 55, 50]
    else:
        larguras = [35, 30, 28, 45, 45]

    # Cabeçalho
    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(80, 80, 80)
    pdf.set_text_color(255, 255, 255)
    for i, col in enumerate(colunas):
        pdf.cell(larguras[i], 8, col, border=1, align="C", fill=True)
    pdf.ln()
    pdf.set_text_color(0, 0, 0)

    # Dados com zebra
    fill = False
    for idx, row in df.iterrows():
        # Calcular altura máxima da linha
        alturas = []
        for i, col in enumerate(colunas):
            valor = str(row[col]) if pd.notna(row[col]) else ""
            pdf.set_font("Arial", "", 8)
            # Número aproximado de linhas: largura da célula
            # Usamos get_string_width e quebra manual
            largura_util = larguras[i] - 2
            palavras = valor.split()
            linhas = 1
            linha_atual = ""
            for palavra in palavras:
                if pdf.get_string_width(linha_atual + (" " if linha_atual else "") + palavra) <= largura_util:
                    linha_atual = linha_atual + (" " if linha_atual else "") + palavra
                else:
                    linhas += 1
                    linha_atual = palavra
            alturas.append(linhas)
        altura_linha = max(alturas) * 5
        x_inicial = pdf.get_x()
        y_inicial = pdf.get_y()
        for i, col in enumerate(colunas):
            valor = str(row[col]) if pd.notna(row[col]) else ""
            pdf.set_font("Arial", "", 8)
            pdf.set_y(y_inicial)
            pdf.set_x(x_inicial + sum(larguras[:i]))
            if fill:
                pdf.set_fill_color(230, 230, 230)
            else:
                pdf.set_fill_color(255, 255, 255)
            pdf.multi_cell(larguras[i], 5, valor, border=1, align="L", fill=fill)
        pdf.set_y(y_inicial + altura_linha)
        pdf.set_x(x_inicial)
        fill = not fill

    # Gerar bytes do PDF
    buffer = io.BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()

# ---------------------------
# Componentes da UI
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

    # Botões de exportação (CSV e PDF) - apenas se houver dados
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
            import csv
            from io import StringIO
            output_csv = StringIO()
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
                    pdf_bytes = gerar_pdf_tabela_seguro(df_export, titulo="Relatório de Paletes - Perecíveis 410")
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

def renderizar_secao_cadastro(sheet, df_existente):
    """Renderiza a seção de cadastro de palete (câmara/vaga)."""
    # Título "Cadastro de Palete" removido conforme solicitado

    camara_opts = ["Selecione a câmara"] + config.CAMARAS
    vaga_opts = ["Selecione a vaga"] + config.VAGAS

    # Obtém o contador de reset do session_state (incrementado pelo force_reset)
    reset_token = st.session_state.get('reset_counter', 0)

    camara_selecionada = st.selectbox(
        "Câmara",
        camara_opts,
        index=0,
        key=f"camara_{reset_token}"
    )
    vaga_selecionada = st.selectbox(
        "Vaga",
        vaga_opts,
        index=0,
        key=f"vaga_{reset_token}"
    )

    if camara_selecionada != "Selecione a câmara" and vaga_selecionada != "Selecione a vaga":
        if combina_existe(camara_selecionada, vaga_selecionada, df_existente):
            st.error(f"⚠️ A combinação {camara_selecionada} / {vaga_selecionada} já está sendo usada.")
            st.session_state.bloqueado = True
            st.session_state.camara = None
            st.session_state.vaga = None
            st.session_state.exibir_gerenciamento = True
        else:
            st.success("✅ Vaga disponível!")
            st.session_state.bloqueado = False
            st.session_state.camara = camara_selecionada
            st.session_state.vaga = vaga_selecionada
            st.session_state.exibir_gerenciamento = False
    else:
        st.session_state.bloqueado = False
        st.session_state.camara = None
        st.session_state.vaga = None
        st.session_state.exibir_gerenciamento = False

    # Gerenciamento de vaga ocupada
    if (st.session_state.exibir_gerenciamento and
        camara_selecionada != "Selecione a câmara" and
        vaga_selecionada != "Selecione a vaga"):
        _renderizar_gerenciamento_vaga(sheet, df_existente, camara_selecionada, vaga_selecionada)

def _renderizar_gerenciamento_vaga(sheet, df_existente, camara_selecionada, vaga_selecionada):
    """Renderiza o expander de gerenciamento de vaga ocupada."""
    with st.expander("🔧 Gerenciar vaga ocupada", expanded=True):
        df_filtrado = df_existente[
            (df_existente['camara'] == camara_selecionada) &
            (df_existente['camara-vaga'] == vaga_selecionada)
        ]

        st.write(f"**Registros encontrados para {camara_selecionada} / {vaga_selecionada}:**")
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
            st.info("Nenhum registro detalhado encontrado (inconsistência de dados).")

        st.divider()
        st.warning("⚠️ **Ação irreversível:** Excluir todos os registros desta vaga.")

        col_confirm1, col_confirm2 = st.columns(2)
        with col_confirm1:
            confirmar_exclusao = st.checkbox("✅ Confirmar exclusão de todos os registros desta vaga")
        with col_confirm2:
            if st.button("🗑️ Excluir todos os registros", type="primary", disabled=not confirmar_exclusao):
                with st.spinner("Excluindo registros..."):
                    num_excluidos = excluir_registros_vaga(sheet, camara_selecionada, vaga_selecionada)
                    if num_excluidos > 0:
                        mensagem = f"{num_excluidos} registro(s) excluído(s) com sucesso!<br><br>A vaga agora está livre."
                        exibir_mensagem_centralizada(mensagem, quebrar_linha=True)
                        time.sleep(3)
                        st.session_state.bloqueado = False
                        st.session_state.camara = camara_selecionada
                        st.session_state.vaga = vaga_selecionada
                        st.session_state.exibir_gerenciamento = False
                        st.session_state.produtos_temp = []
                        force_reset()
                    else:
                        st.error("Nenhum registro foi excluído. Verifique se a combinação realmente existe.")
        st.info("💡 Após excluir, a vaga ficará livre para novo cadastro.")

def _validar_dataframe(df):
    """Retorna (True, mensagem_erro) se houver campos vazios ou inválidos."""
    for idx, row in df.iterrows():
        marca = str(row.get("produto-marca", "")).strip()
        descricao = str(row.get("produto-descricao", "")).strip()
        validade = row.get("validade")
        if pd.isna(validade) or validade == "":
            return False, f"Linha {idx+1}: data de validade é obrigatória."
        if not marca:
            return False, f"Linha {idx+1}: marca é obrigatória."
        if not descricao:
            return False, f"Linha {idx+1}: descrição é obrigatória."
    return True, ""

def _converter_edited_df(edited_df):
    """Converte o DataFrame editado para lista de dicionários, formatando datas."""
    produtos = edited_df.to_dict("records")
    for p in produtos:
        if isinstance(p.get("validade"), pd.Timestamp):
            p["validade"] = p["validade"].strftime("%d/%m/%Y")
        elif pd.isna(p.get("validade")):
            p["validade"] = ""
        p["produto-marca"] = str(p.get("produto-marca", "")).strip()
        p["produto-descricao"] = str(p.get("produto-descricao", "")).strip()
    return produtos

def renderizar_secao_produtos(sheet):
    """Renderiza a seção de adição/edição/exclusão de produtos ao palete."""
    if not (not st.session_state.bloqueado and st.session_state.camara and st.session_state.vaga):
        if st.session_state.bloqueado and not st.session_state.exibir_gerenciamento:
            st.info("💡 Altere a câmara ou vaga para uma combinação livre.")
        return

    st.subheader("📋 Produtos no Palete")

    # Formulário de adição
    st.markdown("➕ **Novo produto**")
    with st.form(key="produto_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            marca = st.selectbox("Produto / Marca", config.MARCA_OPCOES)
        with col2:
            descricao = st.text_input("Descrição do produto")
        validade = st.date_input("Validade", value=None, format="DD/MM/YYYY")

        if st.form_submit_button("➕ Adicionar"):
            if not marca.strip():
                st.error("Selecione uma marca.")
            elif validade is None:
                st.error("Selecione a validade.")
            elif not descricao.strip():
                st.error("Informe a descrição.")
            else:
                st.session_state.produtos_temp.append({
                    "produto-marca": marca,
                    "produto-descricao": descricao,
                    "validade": validade.strftime("%d/%m/%Y")
                })
                st.rerun()

    # Tabela editável
    if st.session_state.produtos_temp:
        df = pd.DataFrame(st.session_state.produtos_temp)
        df = df[["produto-marca", "produto-descricao", "validade"]]
        df["validade"] = pd.to_datetime(df["validade"], format="%d/%m/%Y", errors="coerce")

        column_config = {
            "produto-marca": st.column_config.SelectboxColumn(
                "Marca",
                help="Selecione a marca do produto",
                width="medium",
                options=config.MARCA_OPCOES,
                required=True
            ),
            "validade": st.column_config.DateColumn(
                "Validade",
                format="DD/MM/YYYY",
                required=True
            )
        }

        st.write("**Produtos neste palete:**")
        edited_df = st.data_editor(
            