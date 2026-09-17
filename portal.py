import re
import unicodedata
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from config import BASE_URL, TARGET_SECTION, TIMEOUT


def normalizar(texto):
    texto = " ".join(str(texto or "").split()).lower()

    return "".join(
        caractere
        for caractere in unicodedata.normalize("NFD", texto)
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

    alvo = normalizar(TARGET_SECTION)

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
            ano = link_ano.get_text(strip=True)

            lista = re.search(
                r"id=([0-9a-f-]{36})",
                link_ano.get("href", ""),
                re.IGNORECASE
            )

            if (
                ano.isdigit()
                and len(ano) == 4
                and lista
            ):
                anos_encontrados.append(
                    (int(ano), lista.group(1))
                )

        if anos_encontrados:
            return max(anos_encontrados)

    raise RuntimeError(
        "Não foi possível localizar automaticamente "
        "a seção Remuneração de Empregados no portal."
    )


def localizar_pdf_mais_recente(conexao, lista_id):
    endereco = (
        f"{BASE_URL}"
        "Publico/Listas/BuscarEntity"
    )

    resposta = conexao.post(
        endereco,
        data={"id": lista_id},
        timeout=TIMEOUT
    )

    resposta.raise_for_status()

    dados = resposta.json().get("data") or {}

    arquivos = [
        item
        for item in dados.get("Itens", [])
        if item.get("Anexo")
    ]

    if not arquivos:
        raise RuntimeError(
            "Nenhum relatório de remuneração "
            "foi encontrado no portal."
        )

    def converter_data(item):
        try:
            return datetime.strptime(
                item.get("DataUpload", ""),
                "%d/%m/%Y"
            )
        except ValueError:
            return datetime.min

    mais_recente = max(
        arquivos,
        key=converter_data
    )

    anexo = mais_recente["Anexo"]

    anexo_id = (
        anexo.get("IdArquivoAnexo")
        or anexo.get("Id")
    )

    if not anexo_id:
        raise RuntimeError(
            "O relatório foi encontrado, mas o "
            "identificador do PDF não foi localizado."
        )

    url_pdf = (
        f"{BASE_URL}"
        "Publico/ArquivosAnexos/Download"
        f"?idArquivoAnexo={anexo_id}"
    )

    return {
        "titulo_lista": dados.get(
            "TituloPagina",
            "Remuneração de Empregados"
        ),
        "nome": anexo.get("Nome"),
        "data_upload": mais_recente.get(
            "DataUpload"
        ),
        "url": url_pdf
    }


def baixar_pdf(conexao, url):
    resposta = conexao.get(
        url,
        timeout=TIMEOUT
    )

    resposta.raise_for_status()

    if not resposta.content.startswith(b"%PDF"):
        raise RuntimeError(
            "O arquivo encontrado não é um PDF válido."
        )

    return resposta.content
