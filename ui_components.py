# ui_components.py

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


def quebrar_palavra(palavra, largura_max, pdf):
    pedacos = []
    restante = palavra
    while restante:
        for i in range(len(restante), 0, -1):
            if pdf.get_string_width(restante[:i]) <= largura_max:
                pedacos.append(restante[:i])
                restante = restante[i:]
                break
        else:
            pedacos.append(restante[0])
            restante = restante[1:]
    return pedacos


def gerar_pdf_tabela(df, titulo="Relatório de Paletes"):
    if df.empty:
        return None

    LARGURA_PAGINA = 160
    ALTURA_PAGINA = 220
    MARGEM = 8
    ALTURA_LINHA_TEXTO = 4
    MARGEM_INTERNA = 2

    pdf = FPDF('P', 'mm', (LARGURA_PAGINA, ALTURA_PAGINA))
    pdf.set_auto_page_break(True, MARGEM)
    pdf.set_left_margin(MARGEM)
    pdf.set_right_margin(MARGEM)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, titulo, ln=1, align="C")
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 8)
    data_geracao = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    pdf.cell(0, 5, f"Gerado: {data_geracao}", ln=1, align="R")
    pdf.cell(0, 5, f"Total: {len(df)} registros", ln=1, align="R")
    pdf.ln(4)

    colunas = list(df.columns)
    if len(colunas) == 6:
        # Ajuste: registro 26, câmara 18, vaga 16, marca 26, descrição 38, validade 18 (soma 142)
        larguras = [26, 18, 16, 26, 38, 18]
    elif len(colunas) == 4:
        larguras = [34, 32, 42, 36]
    else:
        larguras = [28, 24, 20, 36, 36]

    idx_descricao = -1
    if "produto-descricao" in colunas:
        idx_descricao = colunas.index("produto-descricao")

    # Cabeçalho
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(80, 80, 80)
    pdf.set_text_color(255, 255, 255)
    for i, col in enumerate(colunas):
        pdf.cell(larguras[i], 6, col, 1, 0, "C", 1)
    pdf.ln()
    pdf.set_text_color(0, 0, 0)

    # Fonte normal para os dados
    pdf.set_font("Helvetica", "", 7)
    zebra = False
    for _, row in df.iterrows():
        # Quebra de texto para todas as colunas
        textos_quebrados = []
        max_linhas = 1
        for i, col in enumerate(colunas):
            valor = str(row[col]) if pd.notna(row[col]) else ""
            largura_util = larguras[i] - 2 * MARGEM_INTERNA
            palavras = valor.split()
            linhas = []
            linha_atual = ""
            for palavra in palavras:
                if pdf.get_string_width(palavra) > largura_util:
                    subs = quebrar_palavra(palavra, largura_util, pdf)
                    for sub in subs:
                        teste = linha_atual + (" " if linha_atual else "") + sub
                        if pdf.get_string_width(teste) <= largura_util:
                            linha_atual = teste
                        else:
                            if linha_atual:
                                linhas.append(linha_atual)
                            linha_atual = sub
                else:
                    teste = linha_atual + (" " if linha_atual else "") + palavra
                    if pdf.get_string_width(teste) <= largura_util:
                        linha_atual = teste
                    else:
                        if linha_atual:
                            linhas.append(linha_atual)
                        linha_atual = palavra
            if linha_atual:
                linhas.append(linha_atual)
            if not linhas:
                linhas = [""]
            textos_quebrados.append(linhas)
            if len(linhas) > max_linhas:
                max_linhas = len(linhas)

        altura_texto = max_linhas * ALTURA_LINHA_TEXTO
        altura_linha = altura_texto + 2 * MARGEM_INTERNA

        # Quebra de página
        if pdf.get_y() + altura_linha > ALTURA_PAGINA - MARGEM:
            pdf.add_page()
            # Redesenha cabeçalho (com negrito)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_fill_color(80, 80, 80)
            pdf.set_text_color(255, 255, 255)
            for i, col in enumerate(colunas):
                pdf.cell(larguras[i], 6, col, 1, 0, "C", 1)
            pdf.ln()
            pdf.set_text_color(0, 0, 0)
            # Volta a fonte normal para os dados
            pdf.set_font("Helvetica", "", 7)
            zebra = False

        x0 = pdf.get_x()
        y0 = pdf.get_y()
        for i, (largura, linhas) in enumerate(zip(larguras, textos_quebrados)):
            pdf.set_xy(x0 + sum(larguras[:i]), y0)
            if zebra:
                pdf.set_fill_color(230, 230, 230)
            else:
                pdf.set_fill_color(255, 255, 255)
            pdf.rect(pdf.get_x(), pdf.get_y(), largura, altura_linha, 'DF')

            largura_util = largura - 2 * MARGEM_INTERNA
            altura_texto_util = len(linhas) * ALTURA_LINHA_TEXTO
            offset_y = (altura_linha - 2 * MARGEM_INTERNA - altura_texto_util) / 2.0
            y_texto = y0 + MARGEM_INTERNA + offset_y

            eh_descricao = (i == idx_descricao)
            pdf.set_xy(x0 + sum(larguras[:i]) + MARGEM_INTERNA, y_texto)
            for j, linha in enumerate(linhas):
                if j > 0:
                    pdf.set_xy(pdf.get_x() - largura + MARGEM_INTERNA,
                               pdf.get_y() + ALTURA_LINHA_TEXTO * j)
                align = "L" if eh_descricao else "C"
                pdf.cell(largura_util, ALTURA_LINHA_TEXTO, linha, 0, 0, align)
            pdf.set_xy(x0 + sum(larguras[:i+1]), y0)

        pdf.set_xy(x0, y0 + altura_linha)
        zebra = not zebra

    buffer = io.BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()


def renderizar_secao_consulta(df_existente):
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

    if filtro_camara != "Todas" and filtro_vaga != "Todas":
        st.write(f"**Registros encontrados para {filtro_camara} / {filtro_vaga}:**")
        if not df_filtrado.empty:
            st.dataframe(
                df_filtrado[['registro', 'produto-marca', 'produto-descricao', 'validade']],
                use_container_width=True,
                column_config={
                    "registro": st.column_config.DatetimeColumn("Registro", format="DD/MM/YYYY HH:mm:ss"),
                    "validade": st.column_config.DateColumn("Validade", format="DD/MM/YYYY")
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
                    "registro": st.column_config.DatetimeColumn("Registro", format="DD/MM/YYYY HH:mm:ss"),
                    "validade": st.column_config.DateColumn("Validade", format="DD/MM/YYYY")
                }
            )
        else:
            st.info("Nenhum registro corresponde aos filtros.")

    if not df_filtrado.empty:
        df_export = df_filtrado.copy()
        if 'registro' in df_export.columns:
            df_export['registro'] = pd.to_datetime(df_export['registro'], errors='coerce')
            df_export['registro'] = df_export['registro'].dt.strftime('%d/%m/%Y %H:%M:%S')
        if 'validade' in df_export.columns:
            df_export['validade'] = pd.to_datetime(df_export['validade'], errors='coerce')
            df_export['validade'] = df_export['validade'].dt.strftime('%d/%m/%Y')

        if 'produto-descricao' in df_export.columns:
            df_export['produto-descricao'] = df_export['produto-descricao'].str.slice(0, 100)

        col_botao1, col_botao2 = st.columns(2)
        with col_botao1:
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
            if st.button("📄 Baixar PDF (smartphone)", use_container_width=True):
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


def renderizar_secao_cadastro(sheet, df_existente):
    camara_opts = ["Selecione a câmara"] + config.CAMARAS
    vaga_opts = ["Selecione a vaga"] + config.VAGAS

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

    if (st.session_state.exibir_gerenciamento and
        camara_selecionada != "Selecione a câmara" and
        vaga_selecionada != "Selecione a vaga"):
        _renderizar_gerenciamento_vaga(sheet, df_existente, camara_selecionada, vaga_selecionada)


def _renderizar_gerenciamento_vaga(sheet, df_existente, camara_selecionada, vaga_selecionada):
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
                    "registro": st.column_config.DatetimeColumn("Registro", format="DD/MM/YYYY HH:mm:ss"),
                    "validade": st.column_config.DateColumn("Validade", format="DD/MM/YYYY")
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
        if len(descricao) > 100:
            return False, f"Linha {idx+1}: a descrição não pode ter mais de 100 caracteres (atualmente {len(descricao)})."
    return True, ""


def _converter_edited_df(edited_df):
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
    if not (not st.session_state.bloqueado and st.session_state.camara and st.session_state.vaga):
        if st.session_state.bloqueado and not st.session_state.exibir_gerenciamento:
            st.info("💡 Altere a câmara ou vaga para uma combinação livre.")
        return

    st.subheader("📋 Produtos no Palete")

    st.markdown("➕ **Novo produto**")
    with st.form(key="produto_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            marca = st.selectbox("Produto / Marca", config.MARCA_OPCOES)
        with col2:
            descricao = st.text_input("Descrição do produto", max_chars=100,
                                      help="Máximo de 100 caracteres.")
            if descricao:
                st.caption(f"{len(descricao)}/100 caracteres")
        validade = st.date_input("Validade", value=None, format="DD/MM/YYYY")

        if st.form_submit_button("➕ Adicionar"):
            if not marca.strip():
                st.error("Selecione uma marca.")
            elif validade is None:
                st.error("Selecione a validade.")
            elif not descricao.strip():
                st.error("Informe a descrição.")
            elif len(descricao) > 100:
                st.error(f"A descrição ultrapassou 100 caracteres (atualmente {len(descricao)}).")
            else:
                st.session_state.produtos_temp.append({
                    "produto-marca": marca,
                    "produto-descricao": descricao,
                    "validade": validade.strftime("%d/%m/%Y")
                })
                st.rerun()

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
            "validade": st.column_config.DateColumn("Validade", format="DD/MM/YYYY", required=True)
        }

        st.write("**Produtos neste palete:**")
        edited_df = st.data_editor(
            df,
            column_config=column_config,
            num_rows="dynamic",
            use_container_width=True,
            key="produtos_editor"
        )

        colA, colB, colC = st.columns(3)
        with colA:
            if st.button("💾 Salvar alterações", use_container_width=True):
                ok, msg = _validar_dataframe(edited_df)
                if not ok:
                    st.error(f"❌ {msg}")
                else:
                    st.session_state.produtos_temp = _converter_edited_df(edited_df)
                    st.rerun()
        with colB:
            if st.button("✅ Finalizar palete", use_container_width=True, type="primary"):
                ok, msg = _validar_dataframe(edited_df)
                if not ok:
                    st.error(f"❌ {msg}")
                else:
                    st.session_state.produtos_temp = _converter_edited_df(edited_df)
                    _finalizar_palete(sheet)
        with colC:
            if st.button("🗑️ Cancelar palete", use_container_width=True):
                st.session_state.produtos_temp = []
                st.session_state.camara = None
                st.session_state.vaga = None
                st.session_state.bloqueado = False
                force_reset()
    else:
        st.info("Nenhum produto adicionado ainda.")


def _finalizar_palete(sheet):
    from data_access import salvar_registros
    registros_para_gravar = []
    for prod in st.session_state.produtos_temp:
        registros_para_gravar.append({
            "camara": st.session_state.camara,
            "camara-vaga": st.session_state.vaga,
            "produto-marca": prod["produto-marca"],
            "produto-descricao": prod["produto-descricao"],
            "validade": prod["validade"]
        })
    try:
        salvar_registros(sheet, registros_para_gravar)
        exibir_mensagem_centralizada(
            f"{len(registros_para_gravar)} produto(s) registrado(s) com sucesso!"
        )
        time.sleep(3)
        st.session_state.produtos_temp = []
        st.session