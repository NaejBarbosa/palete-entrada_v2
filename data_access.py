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

    # Lista os nomes de todas as abas (preservando a capitalização original)
    nomes_abas = [ws.title for ws in sheet.worksheets()]

    # ---- Aba de inclusões (case‑insensitive, esperamos "inclusoes" com i minúsculo) ----
    aba_inclusoes = None
    for nome in nomes_abas:
        if nome.lower() == "inclusoes":
            aba_inclusoes = sheet.worksheet(nome)
            break
    if aba_inclusoes is None:
        # Cria a aba com o nome padronizado (minúsculo)
        aba_inclusoes = sheet.add_worksheet(title="inclusoes", rows=1000, cols=len(config.COLUNAS_INCLUSOES))
        aba_inclusoes.append_row(config.COLUNAS_INCLUSOES)
    else:
        # Garante que os cabeçalhos estão corretos (apenas adiciona colunas faltantes no final)
        _garantir_cabecalho(aba_inclusoes, config.COLUNAS_INCLUSOES)

    # ---- Aba de log de exclusões (case‑insensitive) ----
    aba_log = None
    for nome in nomes_abas:
        if nome.lower() == "log_exclusoes":
            aba_log = sheet.worksheet(nome)
            break
    if aba_log is None:
        aba_log = sheet.add_worksheet(title="log_exclusoes", rows=1000, cols=len(config.COLUNAS_LOG_EXCLUSAO))
        aba_log.append_row(config.COLUNAS_LOG_EXCLUSAO)
    else:
        _garantir_cabecalho(aba_log, config.COLUNAS_LOG_EXCLUSAO)

    return client, aba_inclusoes, aba_log

def _garantir_cabecalho(worksheet, colunas_esperadas):
    """Verifica se a primeira linha tem as colunas esperadas. Se faltar alguma, adiciona no final."""
    header = worksheet.row_values(1)
    # Adiciona colunas faltantes no final
    for i, col in enumerate(colunas_esperadas):
        if i >= len(header) or header[i] != col:
            # Encontra a posição onde deveria estar, mas se não existir, adiciona ao final
            if col not in header:
                worksheet.add_cols(1)
                worksheet.update_cell(1, len(header)+1, col)
                header.append(col)

def carregar_dados_existentes(aba_inclusoes):
    """Carrega todos os registros da aba Inclusoes e retorna DataFrame."""
    dados = aba_inclusoes.get_all_records()
    df = pd.DataFrame(dados)

    # Conversão da coluna 'id' para inteiro
    if 'id' in df.columns:
        df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)

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

def obter_proximo_id(aba_inclusoes):
    """Retorna o próximo ID sequencial baseado no maior valor existente na coluna A (id)."""
    # Pega todos os valores da coluna A (índice 1)
    ids = aba_inclusoes.col_values(1)[1:]  # pula cabeçalho
    if not ids:
        return 1
    # Converte para inteiros, ignora não numéricos
    ids_int = []
    for val in ids:
        try:
            ids_int.append(int(float(val)))
        except (ValueError, TypeError):
            continue
    if not ids_int:
        return 1
    return max(ids_int) + 1

def combina_existe(camara, vaga, df_existente):
    """Verifica se uma combinação câmara/vaga já está cadastrada."""
    if df_existente.empty:
        return False
    return ((df_existente['camara'] == camara) & (df_existente['camara-vaga'] == vaga)).any()

def salvar_registros(aba_inclusoes, registros, usuario):
    """Insere registros na aba Inclusoes com ID, timestamp e usuário."""
    tz = pytz.timezone('America/Sao_Paulo')
    for reg in registros:
        proximo_id = obter_proximo_id(aba_inclusoes)
        timestamp = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")
        aba_inclusoes.append_row([
            proximo_id,
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
    Para cada registro removido, insere um registro detalhado na aba log_exclusoes,
    incluindo o mesmo ID.
    Retorna o número de registros excluídos.
    """
    all_values = aba_inclusoes.get_all_values()
    if not all_values:
        return 0

    linhas_para_excluir = []  # (num_linha, dados_do_registro)
    for i, row in enumerate(all_values[1:], start=2):
        # row[0]=id, [1]=registro, [2]=camara, [3]=vaga, [4]=marca, [5]=desc, [6]=validade, [7]=usuario_inclusao
        if len(row) >= 4 and row[2] == camara and row[3] == vaga:
            linhas_para_excluir.append((i, row))

    if not linhas_para_excluir:
        return 0

    tz = pytz.timezone('America/Sao_Paulo')
    data_hora_exclusao = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")

    # Para cada registro excluído, grava no log (incluindo o ID)
    for _, dados in linhas_para_excluir:
        aba_log.append_row([
            dados[0],          # id
            data_hora_exclusao,
            dados[2],          # camara
            dados[3],          # vaga
            dados[4],          # marca
            dados[5],          # descricao
            dados[6],          # validade
            usuario
        ])

    # Excluir as linhas (do maior número para o menor)
    for linha_num, _ in sorted(linhas_para_excluir, key=lambda x: x[0], reverse=True):
        aba_inclusoes.delete_rows(linha_num)

    return len(linhas_para_excluir)