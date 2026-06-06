import streamlit as st
import pandas as pd
import config
from data_access import (
    combina_existe,
    carregar_dados_existentes,
    excluir_registros_vaga,
    salvar_registros,
    atualizar_registro,
    excluir_registros_por_ids
)
from utils import exibir_mensagem_centralizada, force_reset
from pdf_generator import gerar_pdf_tabela
import time
from datetime import datetime
import io
import csv

def renderizar_secao_consulta(df_existente):
    st.markdown("---")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filtro_camara = st.selectbox("Camara", ["Todas"] + config.CAMARAS, key="filtro_camara")
    with col_f2:
        filtro_vaga = st.selectbox("Vaga", ["Todas"] + config.VAGAS, key="filtro_vaga")
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

    # Exibição (oculta colunas 'id' e 'usuario-inclusao')
    colunas_exibir = ['registro', 'camara', 'camara-vaga', 'produto-marca', 'produto-descricao', 'validade']
    if filtro_camara != "Todas" and filtro_vaga != "Todas":
        st.write(f"**Registros encontrados para {filtro_camara} / {filtro_vaga}:**")
        if not df_filtrado.empty:
            st.dataframe(
                df_filtrado[colunas_exibir],
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
                df_filtrado[colunas_exibir],
                use_container_width=True,
                column_config={
                    "registro": st.column_config.DatetimeColumn("Registro", format="DD/MM/YYYY HH:mm:ss"),
                    "validade": st.column_config.DateColumn("Validade", format="DD/MM/YYYY")
                }
            )
        else:
            st.info("Nenhum registro corresponde aos filtros.")

    # Exportação (remover colunas id e usuario)
    if not df_filtrado.empty:
        df_export = df_filtrado.copy()
        # Remove colunas sensíveis/internas
        for col in ['id', 'usuario-inclusao']:
            if col in df_export.columns:
                df_export = df_export.drop(columns=[col])
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
            def gerar_pdf_bytes():
                pdf_bytes = gerar_pdf_tabela(df_export, titulo="Relatorio de Paletes - Pereciveis 410")
                if pdf_bytes is None:
                    st.error("Erro ao gerar PDF. Tente novamente.")
                    return b""
                return pdf_bytes
            st.download_button(label="📄 Baixar PDF", data=gerar_pdf_bytes(), file_name="relatorio_paletes.pdf", mime="application/pdf", use_container_width=True, key="pdf_download_button")
        with col_botao2:
            output_csv = io.StringIO()
            df_export.to_csv(output_csv, index=False, sep=';', encoding='utf-8-sig', quoting=csv.QUOTE_ALL)
            csv_data = output_csv.getvalue().encode('utf-8-sig')
            st.download_button(label="📊 Baixar CSV", data=csv_data, file_name="relatorio_paletes.csv", mime="text/csv", use_container_width=True)
    else:
        st.info("Nenhum dado para exportar.")
    st.markdown("---")

def renderizar_secao_cadastro(aba_inclusoes, aba_log, df_existente, client, usuario):
    camara_opts = ["Selecione a camara"] + config.CAMARAS
    vaga_opts = ["Selecione a vaga"] + config.VAGAS
    reset_token = st.session_state.get('reset_counter', 0)

    camara_selecionada = st.selectbox("Camara", camara_opts, index=0, key=f"camara_{reset_token}")
    vaga_selecionada = st.selectbox("Vaga", vaga_opts, index=0, key=f"vaga_{reset_token}")

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
        _renderizar_gerenciamento_vaga(aba_inclusoes, aba_log, df_existente, camara_selecionada, vaga_selecionada, usuario)

def _renderizar_gerenciamento_vaga(aba_inclusoes, aba_log, df_existente, camara_selecionada, vaga_selecionada, usuario):
    with st.expander("Gerenciar vaga ocupada", expanded=True):
        # Filtra apenas os registros da vaga atual
        df_vaga = df_existente[
            (df_existente['camara'] == camara_selecionada) &
            (df_existente['camara-vaga'] == vaga_selecionada)
        ].copy()
        
        if df_vaga.empty:
            st.info("Nenhum registro encontrado para esta combinação.")
            return
        
        # Prepara as colunas para edição
        df_edit = df_vaga[['id', 'registro', 'produto-marca', 'produto-descricao', 'validade']].copy()
        
        # Converte datetime para objeto
        df_edit['registro'] = df_edit['registro'].dt.strftime('%d/%m/%Y %H:%M:%S')
        df_edit['validade'] = pd.to_datetime(df_edit['validade']).dt.date
        
        # Adiciona coluna de seleção (checkbox) no início
        # Inicializa o estado de seleção a partir da session_state ou padrão False
        if f"selecao_{camara_selecionada}_{vaga_selecionada}" not in st.session_state:
            st.session_state[f"selecao_{camara_selecionada}_{vaga_selecionada}"] = [False] * len(df_edit)
        
        # Cria uma cópia com a coluna 'Selecionar' baseada no session_state
        df_edit_com_selecao = df_edit.copy()
        df_edit_com_selecao.insert(0, 'Selecionar', st.session_state[f"selecao_{camara_selecionada}_{vaga_selecionada}"])
        
        # Configuração das colunas do editor
        column_config = {
            "Selecionar": st.column_config.CheckboxColumn("❌", help="Marque para excluir"),
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "registro": st.column_config.TextColumn("Registro", disabled=True),
            "produto-marca": st.column_config.SelectboxColumn(
                "Marca",
                options=config.MARCA_OPCOES,
                required=True
            ),
            "produto-descricao": st.column_config.TextColumn(
                "Descrição",
                max_chars=100,
                required=True
            ),
            "validade": st.column_config.DateColumn(
                "Validade",
                format="DD/MM/YYYY",
                required=True
            )
        }
        
        # Checkbox "Selecionar todos" acima da tabela
        col_select_all, col_clear_all = st.columns(2)
        with col_select_all:
            if st.button("☑️ Selecionar todos", use_container_width=True):
                # Atualiza todas as seleções para True
                st.session_state[f"selecao_{camara_selecionada}_{vaga_selecionada}"] = [True] * len(df_edit)
                st.rerun()
        with col_clear_all:
            if st.button("⬜ Limpar seleção", use_container_width=True):
                st.session_state[f"selecao_{camara_selecionada}_{vaga_selecionada}"] = [False] * len(df_edit)
                st.rerun()
        
        st.write("**Registros da vaga (edite os campos desejados e marque para excluir):**")
        
        # Data editor
        edited_df = st.data_editor(
            df_edit_com_selecao,
            column_config=column_config,
            num_rows="fixed",
            use_container_width=True,
            key=f"editor_vaga_{camara_selecionada}_{vaga_selecionada}"
        )
        
        # Salvar o estado atual das seleções para a próxima renderização
        # (quando o usuário marcar/desmarcar no editor, capturamos no final)
        # Precisamos atualizar o session_state com os valores atuais do edited_df
        if 'Selecionar' in edited_df.columns:
            st.session_state[f"selecao_{camara_selecionada}_{vaga_selecionada}"] = edited_df['Selecionar'].tolist()
        
        # Botões de ação
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💾 Salvar edições", use_container_width=True):
                # Verifica quais IDs foram alterados (comparando com o df_edit original)
                ids_alterados = []
                for idx, row_original in df_edit.iterrows():
                    # Encontra a linha correspondente no edited_df (sem a coluna 'Selecionar')
                    row_editado = edited_df[edited_df['id'] == row_original['id']].iloc[0]
                    if (row_original['produto-marca'] != row_editado['produto-marca'] or
                        row_original['produto-descricao'] != row_editado['produto-descricao'] or
                        row_original['validade'] != row_editado['validade']):
                        ids_alterados.append(row_original['id'])
                
                if not ids_alterados:
                    st.info("Nenhuma alteração detectada.")
                else:
                    # Valida os dados alterados
                    validacao_ok = True
                    for idx, row in edited_df.iterrows():
                        if row['id'] in ids_alterados:
                            marca = str(row['produto-marca']).strip()
                            desc = str(row['produto-descricao']).strip()
                            val = row['validade']
                            if not marca:
                                st.error(f"ID {row['id']}: Marca não pode estar vazia.")
                                validacao_ok = False
                            if not desc:
                                st.error(f"ID {row['id']}: Descrição não pode estar vazia.")
                                validacao_ok = False
                            if len(desc) > 100:
                                st.error(f"ID {row['id']}: Descrição excede 100 caracteres.")
                                validacao_ok = False
                            if val is None:
                                st.error(f"ID {row['id']}: Validade é obrigatória.")
                                validacao_ok = False
                    if validacao_ok:
                        # Aplica as atualizações
                        for idx, row in edited_df.iterrows():
                            if row['id'] in ids_alterados:
                                try:
                                    atualizar_registro(
                                        aba_inclusoes,
                                        row['id'],
                                        {
                                            'produto-marca': row['produto-marca'],
                                            'produto-descricao': row['produto-descricao'],
                                            'validade': row['validade'].strftime("%d/%m/%Y")
                                        },
                                        usuario
                                    )
                                except Exception as e:
                                    st.error(f"Erro ao atualizar ID {row['id']}: {e}")
                                    validacao_ok = False
                        if validacao_ok:
                            st.success(f"{len(ids_alterados)} registro(s) atualizado(s) com sucesso. O campo 'registro' foi atualizado para a data/hora atual.")
                            # Limpa a seleção após salvar
                            if f"selecao_{camara_selecionada}_{vaga_selecionada}" in st.session_state:
                                del st.session_state[f"selecao_{camara_selecionada}_{vaga_selecionada}"]
                            time.sleep(1.5)
                            st.rerun()
        
        with col2:
            # Excluir registros selecionados (marcados na coluna 'Selecionar')
            ids_para_excluir = edited_df[edited_df['Selecionar'] == True]['id'].tolist()
            if ids_para_excluir:
                if st.button(f"🗑️ Excluir {len(ids_para_excluir)} selecionado(s)", type="primary", use_container_width=True):
                    with st.spinner("Excluindo registros e gravando log..."):
                        num = excluir_registros_por_ids(aba_inclusoes, aba_log, ids_para_excluir, usuario)
                        if num > 0:
                            exibir_mensagem_centralizada(f"{num} registro(s) excluído(s) com sucesso! Log gravado.")
                            # Limpa a seleção após exclusão
                            if f"selecao_{camara_selecionada}_{vaga_selecionada}" in st.session_state:
                                del st.session_state[f"selecao_{camara_selecionada}_{vaga_selecionada}"]
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("Nenhum registro foi excluído.")
            else:
                st.button("🗑️ Excluir selecionados", disabled=True, use_container_width=True)

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

def renderizar_secao_produtos(aba_inclusoes, aba_log, usuario):
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
            descricao = st.text_input("Descricao do produto", max_chars=100, help="Maximo de 100 caracteres.")
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
            "produto-marca": st.column_config.SelectboxColumn("Marca", help="Selecione a marca do produto", width="medium", options=config.MARCA_OPCOES, required=True),
            "validade": st.column_config.DateColumn("Validade", format="DD/MM/YYYY", required=True)
        }
        st.write("**Produtos neste palete:**")
        edited_df = st.data_editor(df, column_config=column_config, num_rows="dynamic", use_container_width=True, key="produtos_editor")
        colA, colB, colC = st.columns(3)
        with colA:
            if st.button("Salvar alteracoes", use_container_width=True):
                ok, msg = _validar_dataframe(edited_df)
                if not ok:
                    st.error(f"{msg}")
                else:
                    st.session_state.produtos_temp = _converter_edited_df(edited_df)
                    st.rerun()
        with colB:
            if st.button("Finalizar palete", use_container_width=True, type="primary"):
                ok, msg = _validar_dataframe(edited_df)
                if not ok:
                    st.error(f"{msg}")
                else:
                    st.session_state.produtos_temp = _converter_edited_df(edited_df)
                    _finalizar_palete(aba_inclusoes, aba_log, usuario)
        with colC:
            if st.button("Cancelar palete", use_container_width=True):
                st.session_state.produtos_temp = []
                st.session_state.camara = None
                st.session_state.vaga = None
                st.session_state.bloqueado = False
                force_reset()
    else:
        st.info("Nenhum produto adicionado ainda.")

def _finalizar_palete(aba_inclusoes, aba_log, usuario):
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
        salvar_registros(aba_inclusoes, aba_log, registros_para_gravar, usuario)
        exibir_mensagem_centralizada(f"{len(registros_para_gravar)} produto(s) registrado(s) com sucesso!")
        time.sleep(3)
        st.session_state.produtos_temp = []
        st.session_state.camara = None
        st.session_state.vaga = None
        st.session_state.bloqueado = False
        force_reset()
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")