# app.py
# Ponto de entrada principal da aplicação

import streamlit as st
import time

from config import CAMARAS, VAGAS, MARCA_OPCOES
from data_access import conectar_planilha, carregar_dados_existentes
from ui_components import (
    renderizar_secao_consulta,
    renderizar_secao_cadastro,
    renderizar_secao_produtos
)
from utils import exibir_mensagem_centralizada, force_reset

# ------------------------------
# Configuração da página
# ------------------------------
st.set_page_config(page_title="Registro de Paletes", layout="centered")

# Título principal modificado
st.title("❄️ Perecíveis | 410")

# Descrição com fonte personalizada (tamanho = 1rem)
st.markdown(
    '<p class="descricao-app">Controle de paletes das câmaras frias/congeladas da loja 410 do Fort Atacadista.</p>',
    unsafe_allow_html=True
)

# ------------------------------
# CSS mínimo (aparência, centralização, radio)
# ------------------------------
st.markdown("""
<style>
    /* Centraliza e ajusta proporção do título principal (h1) */
    h1 {
        text-align: center;
        font-size: 2.8rem;
        margin-bottom: 0.5rem;
    }
    /* Centraliza e ajusta proporção do subtítulo (h2) */
    h2 {
        text-align: center;
        font-size: 1.5rem;
        margin-top: 0;
        color: #2c3e50;
    }
    /* Estilo da descrição (mesmo tamanho do texto do checkbox) */
    .descricao-app {
        text-align: center;
        font-size: 1rem;
        margin-bottom: 1.2rem;
        color: #555;
    }
    /* Centraliza os botões de rádio na horizontal */
    div[data-testid="stHorizontalRadio"] {
        justify-content: center;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------
# Inicialização da sessão
# ------------------------------
if 'produtos_temp' not in st.session_state:
    st.session_state.produtos_temp = []
if 'camara' not in st.session_state:
    st.session_state.camara = None
if 'vaga' not in st.session_state:
    st.session_state.vaga = None
if 'bloqueado' not in st.session_state:
    st.session_state.bloqueado = False
if 'exibir_gerenciamento' not in st.session_state:
    st.session_state.exibir_gerenciamento = False
if 'check_consulta' not in st.session_state:
    st.session_state.check_consulta = False   # mantido por compatibilidade, mas não é mais usado

# ------------------------------
# Conexão e carregamento de dados
# ------------------------------
sheet = conectar_planilha()
df_existente = carregar_dados_existentes(sheet)

# ------------------------------
# Botões de seleção (Cadastrar / Consultar)
# ------------------------------
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    modo = st.radio(
        "Selecione o modo",
        options=["Cadastrar", "Consultar"],
        index=0,
        horizontal=True,
        key="modo_operacao"
    )

# ------------------------------
# Renderização condicional
# ------------------------------
if modo == "Consultar":
    renderizar_secao_consulta(df_existente)
else:
    renderizar_secao_cadastro(sheet, df_existente)
    renderizar_secao_produtos(sheet)