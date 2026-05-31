# pdf_generator.py
import io
from datetime import datetime
import pandas as pd
from fpdf import FPDF
import pytz


def quebrar_palavra(palavra, largura_max, pdf):
    """Divide uma palavra longa em partes que cabem na largura máxima."""
    pedacos = []
    restante = palavra
    while restante:
        for i in range(len(restante), 0, -1):
            if pdf.get_string_width(restante[:i]) <= largura_max:
                pedacos.append(restante[:i])
                restante = restante[i:]
                break
        else:
            pedacos.append(restante[0])
            restante = restante[1:]
    return pedacos


def gerar_pdf_tabela(df, titulo="Relatorio de Paletes"):
    """
    Gera um PDF com os dados do DataFrame.
    Retorna os bytes do PDF ou None se o DataFrame estiver vazio.
    """
    if df.empty:
        return None

    LARGURA_PAGINA = 160
    ALTURA_PAGINA = 220
    MARGEM = 8
    ALTURA_LINHA_TEXTO = 4
    MARGEM_INTERNA = 2

    pdf = FPDF('P', 'mm', (LARGURA_PAGINA, ALTURA_PAGINA))
    pdf.set_auto_page_break(True, MARGEM)
    pdf.set_left_margin(MARGEM)
    pdf.set_right_margin(MARGEM)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, titulo, ln=1, align="C")
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 8)
    tz = pytz.timezone('America/Sao_Paulo')
    data_geracao = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")
    pdf.cell(0, 5, f"Gerado: {data_geracao}", ln=1, align="R")
    pdf.cell(0, 5, f"Total: {len(df)} registros", ln=1, align="R")
    pdf.ln(4)

    colunas = list(df.columns)
    if len(colunas) == 6:
        # [registro, camara, camara-vaga, produto-marca, produto-descricao, validade]
        larguras = [22, 18, 22, 26, 38, 18]
    elif len(colunas) == 4:
        larguras = [34, 32, 42, 36]
    else:
        larguras = [28, 24, 20, 36, 36]

    idx_descricao = -1
    if "produto-descricao" in colunas:
        idx_descricao = colunas.index("produto-descricao")

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(80, 80, 80)
    pdf.set_text_color(255, 255, 255)
    for i, col in enumerate(colunas):
        pdf.cell(larguras[i], 6, col, 1, 0, "C", 1)
    pdf.ln()
    pdf.set_text_color(0, 0, 0)

    pdf.set_font("Helvetica", "", 7)
    zebra = False
    for _, row in df.iterrows():
        textos_quebrados = []
        max_linhas = 1
        for i, col in enumerate(colunas):
            valor = str(row[col]) if pd.notna(row[col]) else ""
            largura_util = larguras[i] - 2 * MARGEM_INTERNA
            palavras = valor.split()
            linhas = []
            linha_atual = ""
            for palavra in palavras:
                if pdf.get_string_width(palavra) > largura_util:
                    subs = quebrar_palavra(palavra, largura_util, pdf)
                    for sub in subs:
                        teste = linha_atual + (" " if linha_atual else "") + sub
                        if pdf.get_string_width(teste) <= largura_util:
                            linha_atual = teste
                        else:
                            if linha_atual:
                                linhas.append(linha_atual)
                            linha_atual = sub
                else:
                    teste = linha_atual + (" " if linha_atual else "") + palavra
                    if pdf.get_string_width(teste) <= largura_util:
                        linha_atual = teste
                    else:
                        if linha_atual:
                            linhas.append(linha_atual)
                        linha_atual = palavra
            if linha_atual:
                linhas.append(linha_atual)
            if not linhas:
                linhas = [""]
            textos_quebrados.append(linhas)
            if len(linhas) > max_linhas:
                max_linhas = len(linhas)

        altura_texto = max_linhas * ALTURA_LINHA_TEXTO
        altura_linha = altura_texto + 2 * MARGEM_INTERNA

        if pdf.get_y() + altura_linha > ALTURA_PAGINA - MARGEM:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_fill_color(80, 80, 80)
            pdf.set_text_color(255, 255, 255)
            for i, col in enumerate(colunas):
                pdf.cell(larguras[i], 6, col, 1, 0, "C", 1)
            pdf.ln()
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", "", 7)
            zebra = False

        x0 = pdf.get_x()
        y0 = pdf.get_y()

        # Desenha fundo da linha inteira (todas as células)
        for i, largura in enumerate(larguras):
            pdf.set_xy(x0 + sum(larguras[:i]), y0)
            if zebra:
                pdf.set_fill_color(230, 230, 230)
            else:
                pdf.set_fill_color(255, 255, 255)
            pdf.rect(pdf.get_x(), pdf.get_y(), largura, altura_linha, 'DF')

        # Agora desenha o texto célula por célula
        for i, (largura, linhas) in enumerate(zip(larguras, textos_quebrados)):
            largura_util = largura - 2 * MARGEM_INTERNA
            altura_texto_util = len(linhas) * ALTURA_LINHA_TEXTO
            offset_y = (altura_linha - 2 * MARGEM_INTERNA - altura_texto_util) / 2.0
            x_celula = x0 + sum(larguras[:i]) + MARGEM_INTERNA
            y_texto = y0 + MARGEM_INTERNA + offset_y

            eh_descricao = (i == idx_descricao)
            align = "L" if eh_descricao else "C"

            for j, linha in enumerate(linhas):
                y_atual = y_texto + j * ALTURA_LINHA_TEXTO
                pdf.set_xy(x_celula, y_atual)
                # Usa cell com largura exata e sem borda, alinhado conforme necessário
                pdf.cell(largura_util, ALTURA_LINHA_TEXTO, linha, 0, 0, align)

        pdf.set_xy(x0, y0 + altura_linha)
        zebra = not zebra

    buffer = io.BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()