# app.py - Versão corrigida para mobile
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

st.set_page_config(page_title="Registro de Paletes", layout="centered")

st.title("❄️ Perecíveis | 410")
st.markdown(
    '<p class="descricao-app">Controle de paletes das câmaras frias/congeladas da loja 410 do Fort Atacadista.</p>',
    unsafe_allow_html=True
)

# CSS FORÇANDO BOTÕES LADO A LADO NO MOBILE
st.markdown("""
<style>
    h1 { text-align: center; font-size: 2.8rem; margin-bottom: 0.5rem; }
    h2 { text-align: center; font-size: 1.5rem; margin-top: 0; color: #2c3e50; }
    .descricao-app { text-align: center; font-size: 1rem; margin-bottom: 1.2rem; color: #555; }

    /* Força os botões a ficarem lado a lado em qualquer tamanho de tela */
    div[data-testid="column"]:has(button) {
        display: flex !important;
        flex-direction: row !important;
        justify-content: center !important;
        gap: 10px !important;
        flex-wrap: nowrap !important;
    }
    
    /* Cada botão ocupa largura automática, não 100% */
    .stButton button {
        width: auto !important;
        white-space: nowrap !important;
        min-width: 120px !important;
    }
    
    /* No celular, garante que as colunas internas não quebrem */
    @media (max-width: 640px) {
        div[data-testid="column"]:has(button) {
            flex-direction: row !important;
        }
        .stButton button {
            font-size: 14px !important;
            padding: 0.5rem 1rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# Sessão
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
if 'modo' not in st.session_state:
    st.session_state.modo = "Cadastrar"
if 'reset_counter' not in st.session_state:
    st.session_state.reset_counter = 0

sheet = conectar_planilha()
df_existente = carregar_dados_existentes(sheet)

# Botões centralizados e lado a lado (mesma estrutura, mas CSS força)
col_esq, col_centro, col_dir = st.columns([1, 2, 1])
with col_centro:
    btn1, btn2 = st.columns(2)
    with btn1:
        if st.button("📝 Cadastrar", 
                     key="cadastrar_btn",
                     type="primary" if st.session_state.modo == "Cadastrar" else "secondary"):
            st.session_state.modo = "Cadastrar"
            st.rerun()
    with btn2:
        if st.button("🔍 Consultar", 
                     key="consultar_btn",
                     type="primary" if st.session_state.modo == "Consultar" else "secondary"):
            st.session_state.modo = "Consultar"
            st.rerun()

if st.session_state.modo == "Consultar":
    renderizar_secao_consulta(df_existente)
else:
    renderizar_secao_cadastro(sheet, df_existente)
    renderizar_secao_produtos(sheet)