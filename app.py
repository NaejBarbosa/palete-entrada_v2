# app.py - Abas centralizadas com fonte maior
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

# CSS com fonte maior para as abas
st.markdown("""
<style>
    h1 {
        text-align: center;
        font-size: 2.8rem;
        margin-bottom: 0.5rem;
    }
    .descricao-app {
        text-align: center;
        font-size: 1rem;
        margin-bottom: 2rem;
        color: #555;
    }
    
    /* Centralizar abas */
    .stTabs [data-baseweb="tab-list"] {
        display: flex;
        justify-content: center;
        gap: 2rem;
        flex-wrap: wrap;
    }
    
    /* Aumentar fonte dos botões das abas */
    .stTabs [data-baseweb="tab"] {
        flex: 0 1 auto;
        white-space: nowrap;
        font-size: 1.6rem;          /* Aumente ou diminua conforme desejar */
        font-weight: 500;
        padding: 0.5rem 0.8rem;
    }
    
    /* Ajuste fino para mobile */
    @media (max-width: 640px) {
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.8rem;
        }
        .stTabs [data-baseweb="tab"] {
            font-size: 1.1rem;       /* Fonte um pouco menor no celular, ainda maior que o padrão */
        }
    }
</style>
""", unsafe_allow_html=True)

# Inicialização da sessão
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

sheet = conectar_planilha()
df_existente = carregar_dados_existentes(sheet)

# Abas centralizadas
tab_cadastrar, tab_consultar = st.tabs(["📝 Cadastrar", "🔍 Consultar"])

with tab_cadastrar:
    renderizar_secao_cadastro(sheet, df_existente)
    renderizar_secao_produtos(sheet)

with tab_consultar:
    renderizar_secao_consulta(df_existente)