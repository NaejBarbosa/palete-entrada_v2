# app.py - Com botões HTML lado a lado (funciona no mobile)
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

# CSS para o container flex dos botões e estilo
st.markdown("""
<style>
    h1 { text-align: center; font-size: 2.8rem; margin-bottom: 0.5rem; }
    h2 { text-align: center; font-size: 1.5rem; margin-top: 0; color: #2c3e50; }
    .descricao-app { text-align: center; font-size: 1rem; margin-bottom: 1.2rem; color: #555; }
    
    /* Container flexível para os botões */
    .btn-flex-container {
        display: flex;
        justify-content: center;
        gap: 20px;
        flex-wrap: nowrap;
        margin: 20px 0;
    }
    /* Estilo dos botões customizados */
    .custom-btn {
        background-color: #f0f2f6;
        border: 1px solid #d1d5db;
        border-radius: 0.5rem;
        padding: 0.5rem 1.5rem;
        font-size: 1rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
        font-family: inherit;
        min-width: 120px;
        text-align: center;
    }
    .custom-btn-primary {
        background-color: #ff4b4b;
        border-color: #ff4b4b;
        color: white;
    }
    .custom-btn-secondary {
        background-color: #f0f2f6;
        border-color: #d1d5db;
        color: #31333f;
    }
    .custom-btn:hover {
        transform: scale(1.02);
        opacity: 0.9;
    }
    @media (max-width: 640px) {
        .btn-flex-container { gap: 10px; }
        .custom-btn { padding: 0.4rem 1rem; font-size: 0.9rem; min-width: 100px; }
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
if 'modo' not in st.session_state:
    # Verificar se há parâmetro na URL (para os botões HTML)
    modo_param = st.query_params.get("modo", "Cadastrar")
    st.session_state.modo = modo_param if modo_param in ["Cadastrar", "Consultar"] else "Cadastrar"
if 'reset_counter' not in st.session_state:
    st.session_state.reset_counter = 0

# Conexão e dados
sheet = conectar_planilha()
df_existente = carregar_dados_existentes(sheet)

# ------------------------------
# Renderização dos botões HTML customizados
# ------------------------------
# Determina qual botão deve estar ativo (primary)
btn_cadastrar_class = "custom-btn custom-btn-primary" if st.session_state.modo == "Cadastrar" else "custom-btn custom-btn-secondary"
btn_consultar_class = "custom-btn custom-btn-primary" if st.session_state.modo == "Consultar" else "custom-btn custom-btn-secondary"

# Cria os botões em HTML, com JavaScript que atualiza a URL e recarrega
botao_html = f"""
<div class="btn-flex-container">
    <button class="{btn_cadastrar_class}" onclick="setModo('Cadastrar')">📝 Cadastrar</button>
    <button class="{btn_consultar_class}" onclick="setModo('Consultar')">🔍 Consultar</button>
</div>
<script>
    function setModo(modo) {{
        const url = new URL(window.location.href);
        url.searchParams.set('modo', modo);
        window.location.href = url.toString();
    }}
</script>
"""

st.markdown(botao_html, unsafe_allow_html=True)

# ------------------------------
# Renderização condicional conforme o modo
# ------------------------------
if st.session_state.modo == "Consultar":
    renderizar_secao_consulta(df_existente)
else:   # Cadastrar
    renderizar_secao_cadastro(sheet, df_existente)
    renderizar_secao_produtos(sheet)