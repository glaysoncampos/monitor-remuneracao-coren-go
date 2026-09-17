import re
import unicodedata
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from config import BASE_URL, TARGET_SECTION, TIMEOUT


def normalizar(texto):
    texto = " ".join(
        str(texto or "").split()
    ).lower()

    return "".join(
        caractere
        for caractere in unicodedata.normalize(
            "NFD",
            texto
        )
        if unicodedata.category(caractere) != "Mn"
    )


def criar_conexao():
    conexao = requests.Session()

    conexao.headers.update({
        "User-Agent": (
            "MonitorRemuneracaoCorenGO/1.0 "
            "(auditoria de dados publicos)"
        )
    })

    return conexao


def descobrir_lista_mais_nova(conexao):
    resposta = conexao.get(
        BASE_URL,
        timeout=TIMEOUT
    )

    resposta.raise_for_status()

    pagina = BeautifulSoup(
        resposta.text,
        "html.parser"
    )

    alvo = normalizar(
        TARGET_SECTION
    )

    for item_menu in pagina.select("li"):
        link_principal = item_menu.find(
            "a",
            recursive=False
        )

        if not link_principal:
            continue

        titulo = normalizar(
            link_principal.get_text(
                " ",
                strip=True
            )
        )

        if alvo not in titulo:
            continue

        anos_encontrados = []

        for link_ano in item_menu.select(
            "a[href*='publico/Listas?id=']"
        ):
            ano = link_ano.get_text(
                strip=True
            )

            lista = re.search(
                r"id=([0-9a-f-]{36})",
                link_ano.get(
                    "href",
                    ""
                ),
                re.IGNORECASE
            )

            if (
                ano.isdigit()
                and len(ano) == 4
                and lista
            ):
                anos_encontrados.append(
                    (
                        int(ano),
                        lista.group(1)
                    )
                )

        if anos_encontrados:
            return max(
                anos_encontrados
            )

    raise RuntimeError(
        "Não foi possível localizar "
        "automaticamente a seção "
        "Remuneração de Empregados."
    )


def extrair_mes_ano(nome_arquivo):
    texto = normalizar(
        nome_arquivo
    )

    padroes = [
        r"(\d{1,2})\s*[-_/ ]\s*(20\d{2})",
        r"(20\d{2})\s*[-_/ ]\s*(\d{1,2})",
    ]

    encontrado = re.search(
        padroes[0],
        texto
    )

    if encontrado:
        mes = int(
            encontrado.group(1)
        )

        ano = int(
            encontrado.group(2)
        )

        if 1 <= mes <= 12:
            return ano, mes

    encontrado = re.search(
        padroes[1],
        texto
    )

    if encontrado:
        ano = int(
            encontrado.group(1)
        )

        mes = int(
            encontrado.group(2)
        )

        if 1 <= mes <= 12:
            return ano, mes

    meses = {
        "janeiro": 1,
        "fevereiro": 2,
        "marco": 3,
        "abril": 4,
        "maio": 5,
        "junho": 6,
        "julho": 7,
        "agosto": 8,
        "setembro": 9,
        "outubro": 10,
        "novembro": 11,
        "dezembro": 12,
    }

    for nome_mes, numero_mes in meses.items():
        if nome_mes not in texto:
            continue

        ano_encontrado = re.search(
            r"(20\d{2})",
            texto
        )

        if ano_encontrado:
            return (
                int(
                    ano_encontrado.group(1)
                ),
                numero_mes
            )

    return 0, 0


def localizar_pdf_mais_recente(
    conexao,
    lista_id
):
    endereco = (
        f"{BASE_URL}"
        "Publico/Listas/BuscarEntity"
    )

    resposta = conexao.post(
        endereco,
        data={
            "id": lista_id
        },
        timeout=TIMEOUT
    )

    resposta.raise_for_status()

    dados = (
        resposta.json()
        .get("data")
        or {}
    )

    arquivos = [
        item
        for item in dados.get(
            "Itens",
            []
        )
        if item.get("Anexo")
    ]

    if not arquivos:
        raise RuntimeError(
            "Nenhum relatório de "
            "remuneração foi encontrado."
        )

    def chave_ordenacao(item):
        try:
            data_upload = (
                datetime.strptime(
                    item.get(
                        "DataUpload",
                        ""
                    ),
                    "%d/%m/%Y"
                )
            )

        except ValueError:
            data_upload = (
                datetime.min
            )

        anexo = (
            item.get("Anexo")
            or {}
        )

        nome_arquivo = (
            anexo.get("Nome")
            or item.get("Nome")
            or ""
        )

        ano_referencia, mes = (
            extrair_mes_ano(
                nome_arquivo
            )
        )

        return (
            data_upload,
            ano_referencia,
            mes
        )

    mais_recente = max(
        arquivos,
        key=chave_ordenacao
    )

    anexo = (
        mais_recente[
            "Anexo"
        ]
    )

    anexo_id = (
        anexo.get(
            "IdArquivoAnexo"
        )
        or anexo.get("Id")
    )

    if not anexo_id:
        raise RuntimeError(
            "O relatório foi encontrado, "
            "mas o identificador do PDF "
            "não foi localizado."
        )

    url_pdf = (
        f"{BASE_URL}"
        "Publico/ArquivosAnexos/"
        "Download"
        f"?idArquivoAnexo={anexo_id}"
    )

    return {
        "titulo_lista": dados.get(
            "TituloPagina",
            "Remuneração de Empregados"
        ),
        "nome": anexo.get(
            "Nome"
        ),
        "data_upload": (
            mais_recente.get(
                "DataUpload"
            )
        ),
        "url": url_pdf
    }


def baixar_pdf(
    conexao,
    url
):
    resposta = conexao.get(
        url,
        timeout=TIMEOUT
    )

    resposta.raise_for_status()

    if not resposta.content.startswith(
        b"%PDF"
    ):
        raise RuntimeError(
            "O arquivo encontrado "
            "não é um PDF válido."
        )

    return resposta.content
