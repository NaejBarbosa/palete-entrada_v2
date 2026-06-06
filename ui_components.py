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
    colunas_exibir = ['registro', 'camara', 'camara-vaga', 'produto-marca', 'produto-descricao', 'total-caixas', 'validade']
    if filtro_camara != "Todas" and filtro_vaga != "Todas":
        st.write(f"**Registros encontrados para {filtro_camara} / {filtro_vaga}:**")
        if not df_filtrado.empty:
            st.dataframe(
                df_filtrado[colunas_exibir],
                use_container_width=True,
                column_config={
                    "registro": st.column_config.DatetimeColumn("Registro", format="DD/MM/YYYY HH:mm:ss"),
                    "total-caixas": st.column_config.NumberColumn("Caixas", min_value=1, max_value=100),
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
                    "total-caixas": st.column_config.NumberColumn("Caixas", min_value=1, max_value=100),
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
        
        # Carregar ou inicializar o estado do DataFrame de edição (incluindo novas linhas)
        state_key = f"edit_df_{camara_selecionada}_{vaga_selecionada}"
        if state_key not in st.session_state:
            # Cria o DataFrame base com os registros existentes
            df_edit = df_vaga[['id', 'registro', 'produto-marca', 'produto-descricao', 'total-caixas', 'validade']].copy()
            df_edit['registro'] = df_edit['registro'].dt.strftime('%d/%m/%Y %H:%M:%S')
            df_edit['validade'] = pd.to_datetime(df_edit['validade']).dt.date
            st.session_state[state_key] = df_edit
        else:
            df_edit = st.session_state[state_key]
        
        # Adicionar coluna de seleção (checkbox) no início
        if "selecao" not in st.session_state:
            st.session_state.selecao = {state_key: [False] * len(df_edit)}
        if state_key not in st.session_state.selecao:
            st.session_state.selecao[state_key] = [False] * len(df_edit)
        
        df_edit_com_selecao = df_edit.copy()
        df_edit_com_selecao.insert(0, 'Selecionar', st.session_state.selecao[state_key])
        
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
            "total-caixas": st.column_config.NumberColumn(
                "Caixas",
                min_value=1,
                max_value=100,
                step=1,
                required=True
            ),
            "validade": st.column_config.DateColumn(
                "Validade",
                format="DD/MM/YYYY",
                required=True
            )
        }
        
        # Botões: Selecionar todos, Limpar seleção, Adicionar produto
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("☑️ Selecionar todos", use_container_width=True):
                st.session_state.selecao[state_key] = [True] * len(df_edit)
                st.rerun()
        with col2:
            if st.button("⬜ Limpar seleção", use_container_width=True):
                st.session_state.selecao[state_key] = [False] * len(df_edit)
                st.rerun()
        with col3:
            if st.button("➕ Adicionar produto", use_container_width=True):
                # Cria nova linha com ID temporário negativo, registro vazio, campos em branco
                novo_id = -len(df_edit) - 1  # ID temporário único negativo
                nova_linha = pd.DataFrame([{
                    'id': novo_id,
                    'registro': '',
                    'produto-marca': '',
                    'produto-descricao': '',
                    'total-caixas': 1,
                    'validade': None
                }])
                df_edit = pd.concat([df_edit, nova_linha], ignore_index=True)
                st.session_state[state_key] = df_edit
                st.session_state.selecao[state_key] = st.session_state.selecao[state_key] + [False]
                st.rerun()
        
        st.write("**Registros da vaga (edite os campos desejados, marque para excluir ou adicione novos):**")
        
        # Data editor
        edited_df = st.data_editor(
            df_edit_com_selecao,
            column_config=column_config,
            num_rows="fixed",
            use_container_width=True,
            key=f"editor_vaga_{camara_selecionada}_{vaga_selecionada}"
        )
        
        # Atualizar session_state com os dados editados (sem a coluna de seleção)
        if 'Selecionar' in edited_df.columns:
            st.session_state.selecao[state_key] = edited_df['Selecionar'].tolist()
            edited_df_sem_selecao = edited_df.drop(columns=['Selecionar'])
            # Preservar o DataFrame editado (com IDs originais e novos)
            st.session_state[state_key] = edited_df_sem_selecao
        
        # Botões de ação: Salvar edições e Excluir selecionados
        col_salvar, col_excluir = st.columns(2)
        
        with col_salvar:
            if st.button("💾 Salvar edições e novos produtos", use_container_width=True):
                # Separar registros existentes (ID > 0) dos novos (ID <= 0)
                df_atual = st.session_state[state_key].copy()
                df_existentes = df_atual[df_atual['id'] > 0].copy()
                df_novos = df_atual[df_atual['id'] <= 0].copy()
                
                # Validar e atualizar registros existentes (edição)
                ids_alterados = []
                df_original = df_vaga[['id', 'produto-marca', 'produto-descricao', 'total-caixas', 'validade']].copy()
                if not df_original.empty:
                    df_original['validade'] = pd.to_datetime(df_original['validade']).dt.date
                
                for idx, row in df_existentes.iterrows():
                    original = df_original[df_original['id'] == row['id']]
                    if not original.empty:
                        orig = original.iloc[0]
                        if (orig['produto-marca'] != row['produto-marca'] or
                            orig['produto-descricao'] != row['produto-descricao'] or
                            orig['total-caixas'] != row['total-caixas'] or
                            orig['validade'] != row['validade']):
                            ids_alterados.append(row['id'])
                
                validacao_ok = True
                # Validar existentes alterados
                for _, row in df_existentes.iterrows():
                    if row['id'] in ids_alterados:
                        marca = str(row['produto-marca']).strip()
                        desc = str(row['produto-descricao']).strip()
                        caixas = row['total-caixas']
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
                        if caixas is None or caixas < 1 or caixas > 100:
                            st.error(f"ID {row['id']}: Total de caixas deve ser um número entre 1 e 100.")
                            validacao_ok = False
                        if val is None:
                            st.error(f"ID {row['id']}: Validade é obrigatória.")
                            validacao_ok = False
                
                # Validar novos registros
                novos_validos = []
                for _, row in df_novos.iterrows():
                    marca = str(row['produto-marca']).strip()
                    desc = str(row['produto-descricao']).strip()
                    caixas = row['total-caixas']
                    val = row['validade']
                    if not marca:
                        st.error("Novo registro: Marca não pode estar vazia.")
                        validacao_ok = False
                    elif not desc:
                        st.error("Novo registro: Descrição não pode estar vazia.")
                        validacao_ok = False
                    elif len(desc) > 100:
                        st.error(f"Novo registro: Descrição excede 100 caracteres.")
                        validacao_ok = False
                    elif caixas is None or caixas < 1 or caixas > 100:
                        st.error("Novo registro: Total de caixas deve ser um número entre 1 e 100.")
                        validacao_ok = False
                    elif val is None:
                        st.error("Novo registro: Validade é obrigatória.")
                        validacao_ok = False
                    else:
                        novos_validos.append({
                            'produto-marca': marca,
                            'produto-descricao': desc,
                            'total-caixas': int(caixas),
                            'validade': val.strftime("%d/%m/%Y")
                        })
                
                if validacao_ok:
                    # Salvar alterações nos registros existentes
                    for _, row in df_existentes.iterrows():
                        if row['id'] in ids_alterados:
                            try:
                                atualizar_registro(
                                    aba_inclusoes,
                                    row['id'],
                                    {
                                        'produto-marca': row['produto-marca'],
                                        'produto-descricao': row['produto-descricao'],
                                        'total-caixas': row['total-caixas'],
                                        'validade': row['validade'].strftime("%d/%m/%Y")
                                    },
                                    usuario
                                )
                            except Exception as e:
                                st.error(f"Erro ao atualizar ID {row['id']}: {e}")
                                validacao_ok = False
                    
                    # Inserir novos registros
                    if novos_validos and validacao_ok:
                        registros_para_gravar = []
                        for prod in novos_validos:
                            registros_para_gravar.append({
                                "camara": camara_selecionada,
                                "camara-vaga": vaga_selecionada,
                                "produto-marca": prod['produto-marca'],
                                "produto-descricao": prod['produto-descricao'],
                                "total-caixas": prod['total-caixas'],
                                "validade": prod['validade']
                            })
                        try:
                            salvar_registros(aba_inclusoes, aba_log, registros_para_gravar, usuario)
                            st.success(f"{len(registros_para_gravar)} novo(s) produto(s) adicionado(s).")
                        except Exception as e:
                            st.error(f"Erro ao salvar novos produtos: {e}")
                            validacao_ok = False
                    
                    if validacao_ok:
                        msg = f"{len(ids_alterados)} registro(s) atualizado(s)."
                        if novos_validos:
                            msg += f" {len(novos_validos)} novo(s) adicionado(s)."
                        st.success(msg)
                        # Limpar estado e recarregar
                        if state_key in st.session_state:
                            del st.session_state[state_key]
                        if state_key in st.session_state.selecao:
                            del st.session_state.selecao[state_key]
                        time.sleep(1.5)
                        st.rerun()
        
        with col_excluir:
            ids_para_excluir = edited_df[edited_df['Selecionar'] == True]['id'].tolist()
            # Filtrar apenas IDs positivos (existentes no banco)
            ids_para_excluir_existentes = [id_ for id_ in ids_para_excluir if id_ > 0]
            if ids_para_excluir_existentes:
                if st.button(f"🗑️ Excluir {len(ids_para_excluir_existentes)} selecionado(s)", type="primary", use_container_width=True):
                    with st.spinner("Excluindo registros e gravando log..."):
                        num = excluir_registros_por_ids(aba_inclusoes, aba_log, ids_para_excluir_existentes, usuario)
                        if num > 0:
                            exibir_mensagem_centralizada(f"{num} registro(s) excluído(s) com sucesso! Log gravado.")
                            # Limpar estado
                            if state_key in st.session_state:
                                del st.session_state[state_key]
                            if state_key in st.session_state.selecao:
                                del st.session_state.selecao[state_key]
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
        caixas = row.get("total-caixas")
        validade = row.get("validade")
        if pd.isna(validade) or validade == "":
            return False, f"Linha {idx+1}: data de validade e obrigatoria."
        if not marca:
            return False, f"Linha {idx+1}: marca e obrigatoria."
        if not descricao:
            return False, f"Linha {idx+1}: descricao e obrigatoria."
        if len(descricao) > 100:
            return False, f"Linha {idx+1}: a descricao nao pode ter mais de 100 caracteres (atualmente {len(descricao)})."
        if caixas is None or not (1 <= caixas <= 100):
            return False, f"Linha {idx+1}: total de caixas deve ser um número entre 1 e 100."
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
        if p.get("total-caixas") is not None:
            p["total-caixas"] = int(p["total-caixas"])
    return produtos

def renderizar_secao_produtos(aba_inclusoes, aba_log, usuario):
    if not (not st.session_state.bloqueado and st.session_state.camara and st.session_state.vaga):
        if st.session_state.bloqueado and not st.session_state.exibir_gerenciamento:
            st.info("Altere a camara ou vaga para uma combinacao livre.")
        return

    st.subheader("Produtos no Palete")
    st.markdown("**Novo produto**")
    with st.form(key="produto_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            marca = st.selectbox("Produto / Marca", config.MARCA_OPCOES)
        with col2:
            descricao = st.text_input("Descricao do produto", max_chars=100, help="Maximo de 100 caracteres.")
            if descricao:
                st.caption(f"{len(descricao)}/100 caracteres")
        with col3:
            caixas = st.number_input("Total de caixas", min_value=1, max_value=100, step=1, value=1)
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
                    "total-caixas": caixas,
                    "validade": validade.strftime("%d/%m/%Y")
                })
                st.rerun()

    if st.session_state.produtos_temp:
        df = pd.DataFrame(st.session_state.produtos_temp)
        df = df[["produto-marca", "produto-descricao", "total-caixas", "validade"]]
        df["validade"] = pd.to_datetime(df["validade"], format="%d/%m/%Y", errors="coerce")
        column_config = {
            "produto-marca": st.column_config.SelectboxColumn("Marca", help="Selecione a marca do produto", width="medium", options=config.MARCA_OPCOES, required=True),
            "total-caixas": st.column_config.NumberColumn("Caixas", min_value=1, max_value=100, step=1, required=True),
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
            "total-caixas": prod["total-caixas"],
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