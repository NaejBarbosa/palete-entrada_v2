# app.py - Com abas (Cadastrar / Consultar) - funciona no mobile
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

# Título principal
st.title("❄️ Perecíveis | 410")

# Descrição
st.markdown(
    '<p class="descricao-app">Controle de paletes das câmaras frias/congeladas da loja 410 do Fort Atacadista.</p>',
    unsafe_allow_html=True
)

# CSS mínimo (apenas para título e descrição)
st.markdown("""
<style>
    h1 { text-align: center; font-size: 2.8rem; margin-bottom: 0.5rem; }
    h2 { text-align: center; font-size: 1.5rem; margin-top: 0; color: #2c3e50; }
    .descricao-app { text-align: center; font-size: 1rem; margin-bottom: 1.2rem; color: #555; }
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
if 'reset_counter' not in st.session_state:
    st.session_state.reset_counter = 0

# ------------------------------
# Conexão e carregamento de dados
# ------------------------------
sheet = conectar_planilha()
df_existente = carregar_dados_existentes(sheet)

# ------------------------------
# Abas para Cadastrar e Consultar (lado a lado no mobile)
# ------------------------------
tab_cadastrar, tab_consultar = st.tabs(["📝 Cadastrar", "🔍 Consultar"])

with tab_cadastrar:
    renderizar_secao_cadastro(sheet, df_existente)
    renderizar_secao_produtos(sheet)

with tab_consultar:
    renderizar_secao_consulta(df_existente)