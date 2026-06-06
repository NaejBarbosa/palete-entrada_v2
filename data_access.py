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

    # Garantir que 'total-caixas' seja inteiro
    if 'total-caixas' in df.columns:
        df['total-caixas'] = pd.to_numeric(df['total-caixas'], errors='coerce').fillna(0).astype(int)

    return df

def obter_proximo_id_global(aba_inclusoes, aba_log):
    """
    Retorna o próximo ID sequencial baseado no maior valor existente
    na coluna A (id) de ambas as abas: inclusoes e log_exclusoes.
    """
    max_id = 0

    # Lê os IDs da aba de inclusões (coluna A, ignorando cabeçalho)
    ids_inclusoes = aba_inclusoes.col_values(1)[1:]  # pula linha 1
    for val in ids_inclusoes:
        try:
            max_id = max(max_id, int(float(val)))
        except (ValueError, TypeError):
            continue

    # Lê os IDs da aba de log (coluna A, ignorando cabeçalho)
    ids_log = aba_log.col_values(1)[1:]
    for val in ids_log:
        try:
            max_id = max(max_id, int(float(val)))
        except (ValueError, TypeError):
            continue

    return max_id + 1 if max_id > 0 else 1

def salvar_registros(aba_inclusoes, aba_log, registros, usuario):
    """Insere registros na aba Inclusoes com ID global (considerando log), timestamp e usuário."""
    tz = pytz.timezone('America/Sao_Paulo')
    for reg in registros:
        proximo_id = obter_proximo_id_global(aba_inclusoes, aba_log)
        timestamp = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")
        aba_inclusoes.append_row([
            proximo_id,
            timestamp,
            reg['camara'],
            reg['camara-vaga'],
            reg['produto-marca'],
            reg['produto-descricao'],
            reg['total-caixas'],
            reg['validade'],
            usuario
        ])

def combina_existe(camara, vaga, df_existente):
    """Verifica se uma combinação câmara/vaga já está cadastrada."""
    if df_existente.empty:
        return False
    return ((df_existente['camara'] == camara) & (df_existente['camara-vaga'] == vaga)).any()

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
        # row[0]=id, [1]=registro, [2]=camara, [3]=vaga, [4]=marca, [5]=desc, [6]=caixas, [7]=validade, [8]=usuario_inclusao
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
            dados[6],          # total-caixas
            dados[7],          # validade
            usuario
        ])

    # Excluir as linhas (do maior número para o menor)
    for linha_num, _ in sorted(linhas_para_excluir, key=lambda x: x[0], reverse=True):
        aba_inclusoes.delete_rows(linha_num)

    return len(linhas_para_excluir)

# ==================== NOVAS FUNÇÕES PARA EDIÇÃO/EXCLUSÃO SELETIVA ====================

def atualizar_registro(aba_inclusoes, id_registro, novos_dados, usuario):
    """
    Atualiza um registro existente na aba 'inclusoes' com base no ID.
    novos_dados: dict com chaves 'produto-marca', 'produto-descricao', 'total-caixas', 'validade'
    O campo 'registro' é atualizado para o timestamp atual.
    """
    tz = pytz.timezone('America/Sao_Paulo')
    timestamp = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")
    
    # Localizar a linha que contém o ID
    coluna_ids = aba_inclusoes.col_values(1)  # coluna A
    for idx, val in enumerate(coluna_ids, start=1):
        if str(val).strip() == str(id_registro):
            linha_num = idx
            break
    else:
        raise ValueError(f"ID {id_registro} não encontrado na aba de inclusões")
    
    # Atualizar as células
    # Mapeamento: col5=marca, col6=desc, col7=caixas, col8=validade, col2=registro
    aba_inclusoes.update_cell(linha_num, 5, novos_dados['produto-marca'])
    aba_inclusoes.update_cell(linha_num, 6, novos_dados['produto-descricao'])
    aba_inclusoes.update_cell(linha_num, 7, novos_dados['total-caixas'])
    aba_inclusoes.update_cell(linha_num, 8, novos_dados['validade'])
    aba_inclusoes.update_cell(linha_num, 2, timestamp)  # atualiza registro

def excluir_registros_por_ids(aba_inclusoes, aba_log, ids, usuario):
    """
    Exclui uma lista de IDs da aba 'inclusoes', movendo cada um para o log.
    Retorna o número de registros efetivamente excluídos.
    """
    if not ids:
        return 0
    
    tz = pytz.timezone('America/Sao_Paulo')
    data_hora_exclusao = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")
    
    # Buscar todas as linhas com seus IDs
    all_values = aba_inclusoes.get_all_values()
    if not all_values:
        return 0
    
    linhas_para_excluir = []  # (linha_num, dados)
    for i, row in enumerate(all_values[1:], start=2):
        if len(row) >= 1 and row[0].strip() in [str(id_) for id_ in ids]:
            linhas_para_excluir.append((i, row))
    
    if not linhas_para_excluir:
        return 0
    
    # Primeiro: gravar no log
    for _, dados in linhas_para_excluir:
        # dados[0]=id, [1]=registro, [2]=camara, [3]=vaga, [4]=marca, [5]=desc, [6]=caixas, [7]=validade, [8]=usuario_inclusao
        aba_log.append_row([
            dados[0],          # id
            data_hora_exclusao,
            dados[2],          # camara
            dados[3],          # vaga
            dados[4],          # marca
            dados[5],          # descricao
            dados[6],          # total-caixas
            dados[7],          # validade
            usuario
        ])
    
    # Depois: excluir as linhas (do maior número para o menor)
    for linha_num, _ in sorted(linhas_para_excluir, key=lambda x: x[0], reverse=True):
        aba_inclusoes.delete_rows(linha_num)
    
    return len(linhas_para_excluir)