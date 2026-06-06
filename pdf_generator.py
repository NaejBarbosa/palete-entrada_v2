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

def gerar_pdf_tabela(df, titulo="Relatorio de Paletes", usuario="desconhecido"):
    """
    Gera um PDF com os dados do DataFrame.
    Retorna os bytes do PDF ou None se o DataFrame estiver vazio.
    Remove automaticamente a coluna 'id' caso exista.
    """
    # Remove a coluna 'id' se presente
    if 'id' in df.columns:
        df = df.drop(columns=['id'])
    
    if df.empty:
        return None

    LARGURA_PAGINA = 160   # mm
    ALTURA_PAGINA = 220    # mm
    MARGEM = 8             # mm
    ALTURA_LINHA_TEXTO = 4 # mm
    MARGEM_INTERNA = 2     # mm

    # Definição das larguras das colunas (total deve caber dentro da área útil: 160 - 2*8 = 144 mm)
    colunas = list(df.columns)
    if len(colunas) == 7:
        # ordem esperada: registro, camara, camara-vaga, produto-marca, produto-descricao, total-caixas, validade
        larguras = [18, 16, 18, 24, 30, 16, 18]   # soma = 140 mm (folga de 4 mm)
    elif len(colunas) == 6:
        larguras = [22, 18, 22, 26, 38, 18]       # soma = 144 mm
    elif len(colunas) == 4:
        larguras = [34, 32, 42, 36]               # soma = 144 mm
    else:
        larguras = [18, 16, 18, 24, 30, 16, 18]   # fallback para 7 colunas

    largura_total_tabela = sum(larguras)

    # Calcula a posição X inicial para centralizar a tabela dentro da área útil
    area_util_largura = LARGURA_PAGINA - 2 * MARGEM
    x0_central = MARGEM + (area_util_largura - largura_total_tabela) / 2

    pdf = FPDF('P', 'mm', (LARGURA_PAGINA, ALTURA_PAGINA))
    pdf.set_auto_page_break(True, MARGEM)
    pdf.set_left_margin(MARGEM)
    pdf.set_right_margin(MARGEM)
    pdf.add_page()

    # Título
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, titulo, ln=1, align="C")
    pdf.ln(3)

    # Informações de rodapé/cabeçalho
    pdf.set_font("Helvetica", "", 8)
    tz = pytz.timezone('America/Sao_Paulo')
    data_geracao = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")
    pdf.cell(0, 5, f"Gerado: {data_geracao}", ln=1, align="R")
    pdf.cell(0, 5, f"Usuário: {usuario}", ln=1, align="R")
    pdf.cell(0, 5, f"Total: {len(df)} registros", ln=1, align="R")
    pdf.ln(4)

    idx_descricao = -1
    if "produto-descricao" in colunas:
        idx_descricao = colunas.index("produto-descricao")

    # Cabeçalho da tabela (posicionado em x0_central)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(80, 80, 80)
    pdf.set_text_color(255, 255, 255)
    pdf.set_x(x0_central)
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
            
            # Impede quebra de data dentro do campo validade
            if col == "validade" and "/" in valor and len(valor) == 10:
                palavras = [valor]
            else:
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

        # Verifica se precisa de nova página
        if pdf.get_y() + altura_linha > ALTURA_PAGINA - MARGEM:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_fill_color(80, 80, 80)
            pdf.set_text_color(255, 255, 255)
            pdf.set_x(x0_central)
            for i, col in enumerate(colunas):
                pdf.cell(larguras[i], 6, col, 1, 0, "C", 1)
            pdf.ln()
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", "", 7)
            zebra = False

        # Desenha a linha inteira (fundo) a partir de x0_central
        x0_atual = x0_central
        y0_atual = pdf.get_y()
        for i, largura in enumerate(larguras):
            pdf.set_xy(x0_atual + sum(larguras[:i]), y0_atual)
            if zebra:
                pdf.set_fill_color(230, 230, 230)
            else:
                pdf.set_fill_color(255, 255, 255)
            pdf.rect(pdf.get_x(), pdf.get_y(), largura, altura_linha, 'DF')

        # Desenha o texto célula por célula
        for i, (largura, linhas) in enumerate(zip(larguras, textos_quebrados)):
            largura_util = largura - 2 * MARGEM_INTERNA
            altura_texto_util = len(linhas) * ALTURA_LINHA_TEXTO
            offset_y = (altura_linha - 2 * MARGEM_INTERNA - altura_texto_util) / 2.0
            x_celula = x0_atual + sum(larguras[:i]) + MARGEM_INTERNA
            y_texto = y0_atual + MARGEM_INTERNA + offset_y

            eh_descricao = (i == idx_descricao)
            align = "L" if eh_descricao else "C"

            for j, linha in enumerate(linhas):
                y_atual = y_texto + j * ALTURA_LINHA_TEXTO
                pdf.set_xy(x_celula, y_atual)
                pdf.cell(largura_util, ALTURA_LINHA_TEXTO, linha, 0, 0, align)

        pdf.set_xy(x0_atual, y0_atual + altura_linha)
        zebra = not zebra

    buffer = io.BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()