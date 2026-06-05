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

    # Lista os nomes de todas as abas
    nomes_abas = [ws.title for ws in sheet.worksheets()]

    # ---- Aba de inclusões ----
    aba_inclusoes = None
    for nome in nomes_abas:
        if nome.lower() == "inclusoes":
            aba_inclusoes = sheet.worksheet(nome)
            break
    if aba_inclusoes is None:
        aba_inclusoes = sheet.add_worksheet(title="inclusoes", rows=1000, cols=len(config.COLUNAS_INCLUSOES))
        aba_inclusoes.append_row(config.COLUNAS_INCLUSOES)
    else:
        _garantir_cabecalho(aba_inclusoes, config.COLUNAS_INCLUSOES)

    # ---- Aba de log de exclusões ----
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
    """Adiciona colunas faltantes no final, sem alterar a ordem existente."""
    header = worksheet.row_values(1)
    for col in colunas_esperadas:
        if col not in header:
            worksheet.add_cols(1)
            worksheet.update_cell(1, len(header) + 1, col)
            header.append(col)

def _get_header_map(worksheet):
    """Retorna um dicionário {nome_coluna: índice} baseado na primeira linha."""
    header = worksheet.row_values(1)
    return {col: idx for idx, col in enumerate(header) if col}

def _inserir_linha_mapeada(worksheet, valores_dict):
    """
    Insere uma linha na worksheet alinhando os valores de acordo com o cabeçalho atual.
    valores_dict: dicionário com chave = nome da coluna, valor = conteúdo.
    """
    header_map = _get_header_map(worksheet)
    num_colunas = len(worksheet.row_values(1))
    linha = [""] * num_colunas
    
    for col_nome, valor in valores_dict.items():
        if col_nome in header_map:
            linha[header_map[col_nome]] = valor
    worksheet.append_row(linha)

def obter_proximo_id(aba_inclusoes):
    """
    Retorna o próximo ID sequencial baseado na coluna 'id' (independente da posição).
    """
    header_map = _get_header_map(aba_inclusoes)
    if 'id' not in header_map:
        # Se não existe coluna id, cria (caso de planilha muito antiga)
        _garantir_cabecalho(aba_inclusoes, config.COLUNAS_INCLUSOES)
        header_map = _get_header_map(aba_inclusoes)
    
    col_idx = header_map['id'] + 1  # gspread é 1-indexado
    ids = aba_inclusoes.col_values(col_idx)[1:]  # pula cabeçalho
    if not ids:
        return 1
    ids_int = []
    for val in ids:
        try:
            ids_int.append(int(float(val)))
        except (ValueError, TypeError):
            continue
    if not ids_int:
        return 1
    return max(ids_int) + 1

def carregar_dados_existentes(aba_inclusoes):
    """Carrega todos os registros da aba Inclusoes e retorna DataFrame."""
    try:
        all_values = aba_inclusoes.get_all_values()
        if not all_values or len(all_values) < 2:
            return pd.DataFrame(columns=config.COLUNAS_INCLUSOES)
        
        header = all_values[0]
        data = all_values[1:]
        
        # Completa cabeçalho se necessário
        if len(header) < len(config.COLUNAS_INCLUSOES):
            header += [f"col_extra_{i}" for i in range(len(config.COLUNAS_INCLUSOES) - len(header))]
        
        df = pd.DataFrame(data, columns=header[:len(config.COLUNAS_INCLUSOES)])
        
        # Garante todas as colunas esperadas
        for col in config.COLUNAS_INCLUSOES:
            if col not in df.columns:
                df[col] = None
        
        # Converte tipos
        if 'id' in df.columns:
            df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
        if 'registro' in df.columns:
            df['registro'] = pd.to_datetime(df['registro'], dayfirst=True, errors='coerce')
        if 'validade' in df.columns:
            df['validade'] = pd.to_datetime(df['validade'], dayfirst=True, errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {type(e).__name__} - {str(e)}")
        return pd.DataFrame(columns=config.COLUNAS_INCLUSOES)

def combina_existe(camara, vaga, df_existente):
    if df_existente.empty:
        return False
    return ((df_existente['camara'] == camara) & (df_existente['camara-vaga'] == vaga)).any()

def salvar_registros(aba_inclusoes, registros, usuario):
    """Insere registros na aba Inclusoes com ID, timestamp e usuário (mapeado)."""
    tz = pytz.timezone('America/Sao_Paulo')
    for reg in registros:
        proximo_id = obter_proximo_id(aba_inclusoes)
        timestamp = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")
        valores = {
            "id": proximo_id,
            "registro": timestamp,
            "camara": reg['camara'],
            "camara-vaga": reg['camara-vaga'],
            "produto-marca": reg['produto-marca'],
            "produto-descricao": reg['produto-descricao'],
            "validade": reg['validade'],
            "usuario-inclusao": usuario
        }
        _inserir_linha_mapeada(aba_inclusoes, valores)

def excluir_registros_vaga(aba_inclusoes, aba_log, camara, vaga, usuario):
    """
    Remove todos os registros da combinação na aba Inclusoes.
    Para cada registro removido, insere um registro detalhado na aba log_exclusoes,
    mapeando pelos nomes das colunas.
    """
    all_values = aba_inclusoes.get_all_values()
    if not all_values or len(all_values) < 2:
        return 0

    # Mapeamento de índices das colunas na aba inclusoes
    header_inclusoes = all_values[0]
    col_id_idx = None
    col_camara_idx = None
    col_vaga_idx = None
    col_marca_idx = None
    col_desc_idx = None
    col_validade_idx = None
    for idx, col in enumerate(header_inclusoes):
        if col == 'id':
            col_id_idx = idx
        elif col == 'camara':
            col_camara_idx = idx
        elif col == 'camara-vaga':
            col_vaga_idx = idx
        elif col == 'produto-marca':
            col_marca_idx = idx
        elif col == 'produto-descricao':
            col_desc_idx = idx
        elif col == 'validade':
            col_validade_idx = idx
    
    if any(v is None for v in [col_camara_idx, col_vaga_idx]):
        return 0
    
    linhas_para_excluir = []  # (num_linha, dados)
    for i, row in enumerate(all_values[1:], start=2):
        if len(row) > max(col_camara_idx, col_vaga_idx) and row[col_camara_idx] == camara and row[col_vaga_idx] == vaga:
            linhas_para_excluir.append((i, row))
    
    if not linhas_para_excluir:
        return 0
    
    tz = pytz.timezone('America/Sao_Paulo')
    data_hora_exclusao = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")
    
    for _, dados in linhas_para_excluir:
        valores_log = {
            "id": dados[col_id_idx] if col_id_idx is not None and len(dados) > col_id_idx else "",
            "data_hora_exclusao": data_hora_exclusao,
            "camara": dados[col_camara_idx] if len(dados) > col_camara_idx else "",
            "camara-vaga": dados[col_vaga_idx] if len(dados) > col_vaga_idx else "",
            "produto-marca": dados[col_marca_idx] if col_marca_idx is not None and len(dados) > col_marca_idx else "",
            "produto-descricao": dados[col_desc_idx] if col_desc_idx is not None and len(dados) > col_desc_idx else "",
            "validade": dados[col_validade_idx] if col_validade_idx is not None and len(dados) > col_validade_idx else "",
            "usuario-exclusao": usuario
        }
        _inserir_linha_mapeada(aba_log, valores_log)
    
    for linha_num, _ in sorted(linhas_para_excluir, key=lambda x: x[0], reverse=True):
        aba_inclusoes.delete_rows(linha_num)
    
    return len(linhas_para_excluir)