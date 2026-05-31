# app.py
import streamlit as st
import time
from data_access import conectar_planilha, carregar_dados_existentes
from ui_components import (
    renderizar_secao_consulta,
    renderizar_secao_cadastro,
    renderizar_secao_produtos
)
from utils import exibir_mensagem_centralizada, force_reset

st.set_page_config(page_title="Registro de Paletes", layout="centered")

# ==================== LOGIN ====================
def verificar_login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
        st.session_state.usuario = None

    if not st.session_state.autenticado:
        st.title("🔐 Acesso Restrito")
        with st.form("login_form"):
            user = st.text_input("Usuário")
            pwd = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar")
            if submitted:
                creds = st.secrets["usuarios"]
                if user in creds and creds[user] == pwd:
                    st.session_state.autenticado = True
                    st.session_state.usuario = user
                    st.rerun()
                else:
                    st.error("Usuário ou senha inválidos")
        st.stop()

verificar_login()
# ==============================================

# Conexão com a planilha (agora com duas abas)
client, aba_inclusoes, aba_log = conectar_planilha()
df_existente = carregar_dados_existentes(aba_inclusoes)

st.title("❄️ Perecíveis | 410")

st.markdown(
    '<p class="descricao-app">Controle de paletes das câmaras frias/ congeladas da loja 410 do Fort Atacadista.</p>',
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
        color: #A9A9A9;
    }
    .stTabs [data-baseweb="tab-list"] {
        display: flex;
        justify-content: center;
        gap: 2rem;
        flex-wrap: wrap;
    }
    .stTabs [data-baseweb="tab"] {
        flex: 0 1 auto;
        white-space: nowrap;
        font-size: 1.6rem;
        font-weight: 500;
        padding: 0.5rem 0.8rem;
    }
    @media (max-width: 640px) {
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.8rem;
        }
        .stTabs [data-baseweb="tab"] {
            font-size: 1.1rem;
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

# Sidebar com informações do usuário logado
with st.sidebar:
    st.markdown(f"**👤 Usuário:** {st.session_state.usuario}")
    if st.button("🚪 Sair"):
        for key in ["autenticado", "usuario"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# Abas centralizadas
tab_cadastrar, tab_consultar = st.tabs(["📝 Cadastrar", "🔍 Consultar"])

with tab_cadastrar:
    renderizar_secao_cadastro(aba_inclusoes, aba_log, df_existente, client, st.session_state.usuario)
    renderizar_secao_produtos(aba_inclusoes, st.session_state.usuario)

with tab_consultar:
    renderizar_secao_consulta(df_existente)