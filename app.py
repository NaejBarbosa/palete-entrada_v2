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

# Descrição com fonte personalizada
st.markdown(
    '<p class="descricao-app">Controle de paletes das câmaras frias/congeladas da loja 410 do Fort Atacadista.</p>',
    unsafe_allow_html=True
)

# ------------------------------
# CSS (sem forçar largura dos botões)
# ------------------------------
st.markdown("""
<style>
    /* Centraliza e ajusta proporção do título principal (h1) */
    h1 {
        text-align: center;
        font-size: 2.8rem;
        margin-bottom: 0.5rem;
    }
    /* Centraliza subtítulos (se houver) */
    h2 {
        text-align: center;
        font-size: 1.5rem;
        margin-top: 0;
        color: #2c3e50;
    }
    /* Estilo da descrição */
    .descricao-app {
        text-align: center;
        font-size: 1rem;
        margin-bottom: 1.2rem;
        color: #555;
    }
    /* NÃO definir largura para botões */
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
if 'modo' not in st.session_state:
    st.session_state.modo = "Cadastrar"   # padrão
if 'reset_counter' not in st.session_state:
    st.session_state.reset_counter = 0    # controle de reset dos selects

# ------------------------------
# Conexão e carregamento de dados
# ------------------------------
sheet = conectar_planilha()
df_existente = carregar_dados_existentes(sheet)

# ------------------------------
# Botões Cadastrar / Consultar lado a lado (sem CSS conflitante)
# ------------------------------
# Cria 3 colunas: margem esquerda, conteúdo, margem direita
col_esq, col_meio, col_dir = st.columns([1, 2, 1])
with col_meio:
    # Duas colunas internas para os botões
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("📝 Cadastrar", 
                     key="btn_cadastrar",
                     type="primary" if st.session_state.modo == "Cadastrar" else "secondary"):
            st.session_state.modo = "Cadastrar"
            st.rerun()
    with btn_col2:
        if st.button("🔍 Consultar", 
                     key="btn_consultar",
                     type="primary" if st.session_state.modo == "Consultar" else "secondary"):
            st.session_state.modo = "Consultar"
            st.rerun()

# ------------------------------
# Renderização condicional conforme o modo
# ------------------------------
if st.session_state.modo == "Consultar":
    renderizar_secao_consulta(df_existente)
else:   # Cadastrar
    renderizar_secao_cadastro(sheet, df_existente)
    renderizar_secao_produtos(sheet)