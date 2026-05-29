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
st.title("❄️ Entrada de Paletes | Perecíveis")

# ------------------------------
# CSS mínimo (apenas aparência, sem scroll)
# ------------------------------
st.markdown("""
<style>
    /* Seus estilos CSS personalizados aqui */
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
    st.session_state.check_consulta = False

# ------------------------------
# Conexão e carregamento de dados
# ------------------------------
sheet = conectar_planilha()
df_existente = carregar_dados_existentes(sheet)

# ------------------------------
# Renderização das seções
# ------------------------------
consulta_ativa = renderizar_secao_consulta(df_existente)
renderizar_secao_cadastro(sheet, df_existente)
renderizar_secao_produtos(sheet)