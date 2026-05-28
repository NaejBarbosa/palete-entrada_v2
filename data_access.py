# data_access.py
# Módulo responsável por toda a comunicação com o Google Sheets

import pandas as pd
from datetime import datetime
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import config

def conectar_planilha():
    """Estabelece conexão com a planilha do Google Sheets e garante cabeçalhos corretos."""
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(config.SHEET_ID).sheet1

    header = sheet.row_values(1)
    if not header:
        sheet.append_row(config.COLUNAS_CORRETAS)
    elif header != config.COLUNAS_CORRETAS:
        if "registro" not in header:
            sheet.insert_cols(1)
            sheet.update_cell(1, 1, "registro")

    return sheet

def carregar_dados_existentes(sheet):
    """Carrega todos os registros da planilha e retorna um DataFrame."""
    dados = sheet.get_all_records()
    df = pd.DataFrame(dados)

    # ✅ CORREÇÃO: converte a coluna 'validade' para datetime
    if 'validade' in df.columns:
        df['validade'] = pd.to_datetime(
            df['validade'],
            format='%d/%m/%Y',   # formato usado na planilha
            errors='coerce'      # valores inválidos viram NaT
        )

    return df

def combina_existe(camara, vaga, df_existente):
    """Verifica se uma combinação câmara/vaga já está cadastrada."""
    if df_existente.empty:
        return False
    return ((df_existente['camara'] == camara) & (df_existente['camara-vaga'] == vaga)).any()

def salvar_registros(sheet, registros):
    """Salva uma lista de registros na planilha."""
    tz = pytz.timezone('America/Sao_Paulo')
    for reg in registros:
        timestamp = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")
        sheet.append_row([
            timestamp,
            reg['camara'],
            reg['camara-vaga'],
            reg['produto-marca'],
            reg['produto-descricao'],
            reg['validade']
        ])

def excluir_registros_vaga(sheet, camara, vaga):
    """Exclui todos os registros de uma determinada combinação câmara/vaga."""
    all_values = sheet.get_all_values()
    if not all_values:
        return 0
    rows_to_delete = []
    for i, row in enumerate(all_values[1:], start=2):
        if len(row) >= 3 and row[1] == camara and row[2] == vaga:
            rows_to_delete.append(i)
    for row_num in sorted(rows_to_delete, reverse=True):
        sheet.delete_rows(row_num)
    return len(rows_to_delete)