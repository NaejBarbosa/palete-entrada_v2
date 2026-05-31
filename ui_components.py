# ui_components.py

import streamlit as st
import pandas as pd
import config
from data_access import combina_existe, carregar_dados_existentes, excluir_registros_vaga
from utils import exibir_mensagem_centralizada, force_reset
from pdf_generator import gerar_pdf_tabela   # <-- PDF movido para módulo separado
import time
from datetime import datetime
import io
import csv


def renderizar_secao_consulta(df_existente):
    st.markdown("---")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filtro_camara = st.selectbox(
            "Camara",
            ["Todas"] + config.CAMARAS,
            key="filtro_camara"
        )
    with col_f2:
        filtro_vaga = st.selectbox(
            "Vaga",
            ["Todas"] + config.VAGAS,
            key="filtro_vaga"
        )

    filtro_texto = st.text_input("Buscar em marca/descricao", key="filtro_texto")

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
            st.info("Nenhum registro encontrado para esta combinacao.")
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
                label="Baixar CSV",
                data=csv_data,
                file_name="relatorio_paletes.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col_botao2:
            if st.button("Baixar PDF (smartphone)", use_container_width=True):
                with st.spinner("Gerando PDF..."):
                    pdf_bytes = gerar_pdf_tabela(df_export, titulo="Relatorio de Paletes - Pereciveis 410")
                    if pdf_bytes:
                        st.download_button(
                            label="Salvar PDF",
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
    camara_opts = ["Selecione a camara"] + config.CAMARAS
    vaga_opts = ["Selecione a vaga"] + config.VAGAS

    reset_token = st.session_state.get('reset_counter', 0)

    camara_selecionada = st.selectbox(
        "Camara",
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

    if camara_selecionada != "Selecione a camara" and vaga_selecionada != "Selecione a vaga":
        if combina_existe(camara_selecionada, vaga_selecionada, df_existente):
            st.error(f"Combinacao {camara_selecionada} / {vaga_selecionada} ja esta sendo usada.")
            st.session_state.bloqueado = True
            st.session_state.camara = None
            st.session_state.vaga = None
            st.session_state.exibir_gerenciamento = True
        else:
            st.success("Vaga disponivel!")
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
        camara_selecionada != "Selecione a camara" and
        vaga_selecionada != "Selecione a vaga"):
        _renderizar_gerenciamento_vaga(sheet, df_existente, camara_selecionada, vaga_selecionada)


def _renderizar_gerenciamento_vaga(sheet, df_existente, camara_selecionada, vaga_selecionada):
    with st.expander("Gerenciar vaga ocupada", expanded=True):
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
            st.info("Nenhum registro detalhado encontrado.")

        st.divider()
        st.warning("**Acao irreversivel:** Excluir todos os registros desta vaga.")

        col_confirm1, col_confirm2 = st.columns(2)
        with col_confirm1:
            confirmar_exclusao = st.checkbox("Confirmar exclusao de todos os registros desta vaga")
        with col_confirm2:
            if st.button("Excluir todos os registros", type="primary", disabled=not confirmar_exclusao):
                with st.spinner("Excluindo registros..."):
                    num_excluidos = excluir_registros_vaga(sheet, camara_selecionada, vaga_selecionada)
                    if num_excluidos > 0:
                        mensagem = f"{num_excluidos} registro(s) excluido(s) com sucesso! A vaga agora esta livre."
                        exibir_mensagem_centralizada(mensagem, quebrar_linha=True)
                        time.sleep(3)
                        st.session_state.bloqueado = False
                        st.session_state.camara = camara_selecionada
                        st.session_state.vaga = vaga_selecionada
                        st.session_state.exibir_gerenciamento = False
                        st.session_state.produtos_temp = []
                        force_reset()
                    else:
                        st.error("Nenhum registro foi excluido. Verifique se a combinacao realmente existe.")
        st.info("Apos excluir, a vaga ficara livre para novo cadastro.")


def _validar_dataframe(df):
    for idx, row in df.iterrows():
        marca = str(row.get("produto-marca", "")).strip()
        descricao = str(row.get("produto-descricao", "")).strip()
        validade = row.get("validade")
        if pd.isna(validade) or validade == "":
            return False, f"Linha {idx+1}: data de validade e obrigatoria."
        if not marca:
            return False, f"Linha {idx+1}: marca e obrigatoria."
        if not descricao:
            return False, f"Linha {idx+1}: descricao e obrigatoria."
        if len(descricao) > 100:
            return False, f"Linha {idx+1}: a descricao nao pode ter mais de 100 caracteres (atualmente {len(descricao)})."
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
            st.info("Altere a camara ou vaga para uma combinacao livre.")
        return

    st.subheader("Produtos no Palete")

    st.markdown("**Novo produto**")
    with st.form(key="produto_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            marca = st.selectbox("Produto / Marca", config.MARCA_OPCOES)
        with col2:
            descricao = st.text_input("Descricao do produto", max_chars=100,
                                      help="Maximo de 100 caracteres.")
            if descricao:
                st.caption(f"{len(descricao)}/100 caracteres")
        validade = st.date_input("Validade", value=None, format="DD/MM/YYYY")

        if st.form_submit_button("Adicionar"):
            if not marca.strip():
                st.error("Selecione uma marca.")
            elif validade is None:
                st.error("Selecione a validade.")
            elif not descricao.strip():
                st.error("Informe a descricao.")
            elif len(descricao) > 100:
                st.error(f"A descricao ultrapassou 100 caracteres (atualmente {len(descricao)}).")
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
            if st.button("Salvar alteracoes", use_container_width=True):
                ok, msg = _validar_dataframe(edited_df)
                if not ok:
                    st.error(f" {msg}")
                else:
                    st.session_state.produtos_temp = _converter_edited_df(edited_df)
                    st.rerun()
        with colB:
            if st.button("Finalizar palete", use_container_width=True, type="primary"):
                ok, msg = _validar_dataframe(edited_df)
                if not ok:
                    st.error(f" {msg}")
                else:
                    st.session_state.produtos_temp = _converter_edited_df(edited_df)
                    _finalizar_palete(sheet)
        with colC:
            if st.button("Cancelar palete", use_container_width=True):
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