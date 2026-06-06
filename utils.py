# Funções utilitárias (exibição de mensagens, reset, etc.)

import streamlit as st
import uuid

def exibir_mensagem_centralizada(mensagem, quebrar_linha=False):
    """
    Exibe mensagem com a mesma formatação do st.success, centralizada,
    com animação de subir e desaparecer em 3 segundos.
    """
    msg_id = f"msg_{uuid.uuid4().hex}"

    style_base = """
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
        border-radius: 0.5rem;
        padding: 12px 24px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        font-weight: 500;
        font-size: 1rem;
        z-index: 9999;
        text-align: center;
        font-family: inherit;
        animation: fadeOutUp 0.5s ease-in-out 2.5s forwards;
    """

    if quebrar_linha and '<br><br>' in mensagem:
        partes = mensagem.split('<br><br>', 1)
        primeira = partes[0].strip()
        segunda = partes[1].strip() if len(partes) > 1 else ''
        conteudo_html = f'✅ {primeira}'
        if segunda:
            conteudo_html += f'<br><br>{segunda}'
        style_extra = "white-space: normal; max-width: 80vw; word-wrap: break-word;"
    elif quebrar_linha:
        conteudo_html = f'✅ {mensagem}'
        style_extra = "white-space: normal; max-width: 80vw; word-wrap: break-word;"
    else:
        conteudo_html = f'✅ {mensagem}'
        style_extra = "white-space: nowrap;"

    style_completo = style_base + style_extra

    html = f"""
    <div id="{msg_id}" style="{style_completo}">
        {conteudo_html}
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)

def force_reset():
    """Força o reset dos componentes usando session_state (compatível com todas as versões)."""
    st.session_state.reset_counter = st.session_state.get('reset_counter', 0) + 1
    st.rerun()