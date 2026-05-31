# ui_components.py
# Componentes reutilizáveis da interface Streamlit

import streamlit as st
import pandas as pd
import config
from data_access import combina_existe, carregar_dados_existentes, excluir_registros_vaga
from utils import exibir_mensagem_centralizada, force_reset
import time
from datetime import datetime

def renderizar_secao_consulta(df_existente):
    """Renderiza a seção de consulta de registros existentes com botão de download CSV compatível com Excel Brasil e Google Sheets."""
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

    # --- BOTÃO DE DOWNLOAD CSV (com separador ponto e vírgula) ---
    if not df_filtrado.empty:
        import csv
        from io import StringIO

        df_export = df_filtrado.copy()

        # Formata as colunas de data para o padrão brasileiro
        if 'registro' in df_export.columns:
            df_export['registro'] = pd.to_datetime(df_export['registro'], errors='coerce')
            df_export['registro'] = df_export['registro'].dt.strftime('%d/%m/%Y %H:%M:%S')
        if 'validade' in df_export.columns:
            df_export['validade'] = pd.to_datetime(df_export['validade'], errors='coerce')
            df_export['validade'] = df_export['validade'].dt.strftime('%d/%m/%Y')

        # Converte para CSV com separador ';' e aspas (compatível com Excel Brasil)
        output = StringIO()
        df_export.to_csv(
            output,
            index=False,
            sep=';',
            encoding='utf-8-sig',      # BOM para reconhecimento de acentos no Excel
            quoting=csv.QUOTE_ALL,      # Coloca aspas em TODOS os campos (mais seguro)
            quotechar='"'
        )
        csv_data = output.getvalue().encode('utf-8-sig')

        st.download_button(
            label="📥 Baixar relatório (CSV para Excel/Google)",
            data=csv_data,
            file_name="relatorio_paletes.csv",
            mime="text/csv",
            use_container_width=True
        )
        st.caption("✅ Formato: separador **ponto e vírgula (;)** | Aspas em todos os campos | UTF-8 com BOM")
        st.caption("📌 **No Google Sheets**: Ao importar, escolha 'Separador personalizado' e digite **;**")

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
                    st.error(f"❌ Campos obrigatórios não preenchidos: {msg}")
                else:
                    st.session_state.produtos_temp = _converter_edited_df(edited_df)
                    st.rerun()
        with colB:
            if st.button("✅ Finalizar palete", use_container_width=True, type="primary"):
                ok, msg = _validar_dataframe(edited_df)
                if not ok:
                    st.error(f"❌ Campos obrigatórios não preenchidos: {msg}")
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
        st.session_state.camara = None
        st.session_state.vaga = None
        st.session_state.bloqueado = False
        force_reset()
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")