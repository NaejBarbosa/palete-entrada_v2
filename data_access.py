# data_access.py
import pandas as pd
from datetime import datetime
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import config

def conectar_planilha():
    """Retorna (client, aba_inclusoes, aba_log). Cria abas se não existirem."""
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(config.SHEET_ID)

    # Aba de inclusões
    try:
        aba_inclusoes = sheet.worksheet("Inclusoes")
    except gspread.WorksheetNotFound:
        aba_inclusoes = sheet.add_worksheet(title="Inclusoes", rows=1000, cols=7)
        aba_inclusoes.append_row(config.COLUNAS_INCLUSOES)

    # Aba de log de exclusões
    try:
        aba_log = sheet.worksheet("log_exclusoes")
    except gspread.WorksheetNotFound:
        aba_log = sheet.add_worksheet(title="log_exclusoes", rows=1000, cols=7)
        aba_log.append_row(config.COLUNAS_LOG_EXCLUSAO)

    return client, aba_inclusoes, aba_log

def carregar_dados_existentes(aba_inclusoes):
    """Carrega todos os registros da aba Inclusoes e retorna DataFrame."""
    dados = aba_inclusoes.get_all_records()
    df = pd.DataFrame(dados)

    # Conversão da coluna 'registro'
    if 'registro' in df.columns:
        df['registro'] = (
            df['registro']
            .astype(str)
            .str.replace("'", "", regex=False)
            .str.strip()
        )
        df['registro'] = pd.to_datetime(df['registro'], dayfirst=True, errors='coerce')
        if df['registro'].dtype != 'datetime64[ns]':
            df['registro'] = pd.to_datetime(df['registro'], errors='coerce')

    # Conversão da coluna 'validade'
    if 'validade' in df.columns:
        df['validade'] = (
            df['validade']
            .astype(str)
            .str.replace("'", "", regex=False)
            .str.strip()
        )
        df['validade'] = pd.to_datetime(df['validade'], dayfirst=True, errors='coerce')
        if df['validade'].dtype != 'datetime64[ns]':
            df['validade'] = pd.to_datetime(df['validade'], errors='coerce')

    return df

def combina_existe(camara, vaga, df_existente):
    """Verifica se uma combinação câmara/vaga já está cadastrada."""
    if df_existente.empty:
        return False
    return ((df_existente['camara'] == camara) & (df_existente['camara-vaga'] == vaga)).any()

def salvar_registros(aba_inclusoes, registros, usuario):
    """Insere registros na aba Inclusoes com timestamp e usuário."""
    tz = pytz.timezone('America/Sao_Paulo')
    for reg in registros:
        timestamp = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")
        aba_inclusoes.append_row([
            timestamp,
            reg['camara'],
            reg['camara-vaga'],
            reg['produto-marca'],
            reg['produto-descricao'],
            reg['validade'],
            usuario
        ])

def excluir_registros_vaga(aba_inclusoes, aba_log, camara, vaga, usuario):
    """
    Remove todos os registros da combinação na aba Inclusoes.
    Para cada registro removido, insere um registro detalhado na aba log_exclusoes.
    Retorna o número de registros excluídos.
    """
    all_values = aba_inclusoes.get_all_values()
    if not all_values:
        return 0

    linhas_para_excluir = []  # (num_linha, dados_do_registro)
    for i, row in enumerate(all_values[1:], start=2):
        if len(row) >= 3 and row[1] == camara and row[2] == vaga:
            # row[0]=registro, [1]=camara, [2]=vaga, [3]=marca, [4]=desc, [5]=validade, [6]=usuario_inclusao
            linhas_para_excluir.append((i, row))

    if not linhas_para_excluir:
        return 0

    tz = pytz.timezone('America/Sao_Paulo')
    data_hora_exclusao = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")

    # Para cada registro excluído, grava no log
    for _, dados in linhas_para_excluir:
        aba_log.append_row([
            data_hora_exclusao,
            dados[1],   # camara
            dados[2],   # vaga
            dados[3],   # marca
            dados[4],   # descricao
            dados[5],   # validade
            usuario
        ])

    # Excluir as linhas (do maior número para o menor)
    for linha_num, _ in sorted(linhas_para_excluir, key=lambda x: x[0], reverse=True):
        aba_inclusoes.delete_rows(linha_num)

    return len(linhas_para_excluir)