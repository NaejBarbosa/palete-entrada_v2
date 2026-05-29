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
    """Renderiza a seção de consulta de registros existentes."""
    st.checkbox("🔍 Consultar registros existentes", key="check_consulta")

    if not st.session_state.check_consulta:
        return False

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

    st.markdown("---")
    return True

def renderizar_secao_cadastro(sheet, df_existente):
    """Renderiza a seção de cadastro de palete (câmara/vaga)."""
    if st.session_state.check_consulta:
        return

    st.markdown("## 📦 Cadastro de Palete")

    camara_opts = ["Selecione a câmara"] + config.CAMARAS
    vaga_opts = ["Selecione a vaga"] + config.VAGAS

    reset_token = st.query_params.get("reset_token", 0)
    try:
        reset_token = int(reset_token)
    except:
        reset_token = 0

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
                        # Recarregar dados
                        st.session_state.bloqueado = False
                        st.session_state.camara = camara_selecionada
                        st.session_state.vaga = vaga_selecionada
                        st.session_state.exibir_gerenciamento = False
                        st.session_state.produtos_temp = []
                        force_reset()
                    else:
                        st.error("Nenhum registro foi excluído. Verifique se a combinação realmente existe.")
        st.info("💡 Após excluir, a vaga ficará livre para novo cadastro.")

def renderizar_secao_produtos(sheet):
    """Renderiza a seção de adição/edição/exclusão de produtos ao palete."""
    if not (not st.session_state.bloqueado and st.session_state.camara and st.session_state.vaga):
        if st.session_state.bloqueado and not st.session_state.exibir_gerenciamento:
            st.info("💡 Altere a câmara ou vaga para uma combinação livre.")
        return

    st.subheader("📋 Produtos no Palete")

    # ------------------------------------------------------------
    # 1. Formulário (adição ou edição) – SEMPRE NO TOPO
    # ------------------------------------------------------------
    edit_mode = st.session_state.edit_index is not None

    if edit_mode:
        col_tit, col_cancel = st.columns([5, 1])
        with col_tit:
            st.markdown("✎ **Editar produto**")
        with col_cancel:
            if st.button("↩ Cancelar", key="cancel_edit"):
                st.session_state.edit_index = None
                st.session_state.edit_data = {}
                st.rerun()
    else:
        st.markdown("➕ **Novo produto**")

    with st.form(key="produto_form", clear_on_submit=not edit_mode):
        # Marca
        default_marca = ""
        idx_marca = 0
        if edit_mode:
            default_marca = st.session_state.edit_data.get("produto-marca", "")
            if default_marca in config.MARCA_OPCOES:
                idx_marca = config.MARCA_OPCOES.index(default_marca)
        marca = st.selectbox("Produto / Marca", config.MARCA_OPCOES, index=idx_marca)

        # Descrição
        default_desc = st.session_state.edit_data.get("produto-descricao", "") if edit_mode else ""
        descricao = st.text_input("Descrição do produto", value=default_desc)

        # Validade
        validade_date = None
        if edit_mode and st.session_state.edit_data.get("validade"):
            try:
                validade_date = datetime.strptime(st.session_state.edit_data["validade"], "%d/%m/%Y").date()
            except:
                pass
        data_validade = st.date_input("Validade", value=validade_date, format="DD/MM/YYYY")

        submit_label = "💾 Salvar alterações" if edit_mode else "➕ Adicionar este produto"
        submitted = st.form_submit_button(submit_label)

        if submitted:
            if not marca.strip():
                st.error("Por favor, selecione uma marca/produto válida.")
            elif data_validade is None:
                st.error("Por favor, selecione a data de validade.")
            elif not descricao.strip():
                st.error("Por favor, informe a descrição do produto.")
            else:
                validade_str = data_validade.strftime("%d/%m/%Y")
                novo_produto = {
                    "produto-marca": marca,
                    "produto-descricao": descricao,
                    "validade": validade_str
                }
                if edit_mode:
                    idx = st.session_state.edit_index
                    st.session_state.produtos_temp[idx] = novo_produto
                    st.session_state.edit_index = None
                    st.session_state.edit_data = {}
                else:
                    st.session_state.produtos_temp.append(novo_produto)
                st.rerun()

    # ------------------------------------------------------------
    # 2. Lista de produtos (COM ÍCONES MINIMALISTAS)
    # ------------------------------------------------------------
    if st.session_state.produtos_temp:
        st.write("**Produtos neste palete:**")
        for i, prod in enumerate(st.session_state.produtos_temp):
            col1, col2, col3 = st.columns([6, 1, 1])
            with col1:
                st.write(f"{i+1}. {prod['produto-marca']} - {prod['produto-descricao']} (val.: {prod['validade']})")
            with col2:
                if st.button("✎", key=f"edit_{i}"):   # lápis minimalista
                    st.session_state.edit_index = i
                    st.session_state.edit_data = prod.copy()
                    st.rerun()
            with col3:
                if st.button("✕", key=f"del_{i}"):   # xis discreto
                    st.session_state.produtos_temp.pop(i)
                    if st.session_state.edit_index == i:
                        st.session_state.edit_index = None
                        st.session_state.edit_data = {}
                    st.rerun()

        # Botões de ação do palete (Finalizar / Cancelar)
        colA, colB = st.columns(2)
        with colA:
            if st.button("✅ Finalizar e enviar", use_container_width=True, type="primary", key="finalizar_button"):
                _finalizar_palete(sheet)
        with colB:
            if st.button("🗑️ Cancelar palete", use_container_width=True, type="secondary", key="cancelar_palete"):
                st.session_state.produtos_temp = []
                st.session_state.camara = None
                st.session_state.vaga = None
                st.session_state.bloqueado = False
                force_reset()
    else:
        st.info("Nenhum produto adicionado ainda.")

def _finalizar_palete(sheet):
    """Finaliza o cadastro do palete e envia para a planilha."""
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