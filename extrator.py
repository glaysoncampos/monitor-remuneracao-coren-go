import io
import re
import unicodedata

import pdfplumber


CAMPOS_OBRIGATORIOS = {
    "funcionario",
    "cargo",
    "salario_cadastro",
    "proventos",
    "descontos",
    "inss",
    "liquido",
}


def normalizar(texto):
    texto = " ".join(
        str(texto or "")
        .replace("\n", " ")
        .split()
    ).lower()

    return "".join(
        caractere
        for caractere in unicodedata.normalize(
            "NFD",
            texto
        )
        if unicodedata.category(caractere) != "Mn"
    )


def limpar_texto(texto):
    return " ".join(
        str(texto or "")
        .replace("\n", " ")
        .split()
    )


def moeda_para_float(valor):
    texto = limpar_texto(valor)

    if not texto:
        return None

    texto = texto.replace("R$", "").strip()
    texto = texto.replace(".", "")
    texto = texto.replace(",", ".")

    texto = re.sub(
        r"[^0-9.\-]",
        "",
        texto
    )

    if not texto:
        return None

    try:
        return round(float(texto), 2)

    except ValueError:
        return None


def identificar_colunas(linha):
    colunas = {}

    for indice, celula in enumerate(linha):
        texto = normalizar(celula)

        if not texto:
            continue

        if (
            "funcionario" in texto
            or "empregado" in texto
        ):
            colunas["funcionario"] = indice

        elif texto == "cargo":
            colunas["cargo"] = indice

        elif (
            "sal" in texto
            and "cadastro" in texto
        ):
            colunas["salario_cadastro"] = indice

        elif "provento" in texto:
            colunas["proventos"] = indice

        elif "desconto" in texto:
            colunas["descontos"] = indice

        elif texto == "inss":
            colunas["inss"] = indice

        elif (
            "liquido" in texto
            or "líquido" in str(celula or "").lower()
        ):
            colunas["liquido"] = indice

    return colunas


def ler_celula(linha, indice):
    if indice is None:
        return ""

    if indice >= len(linha):
        return ""

    return limpar_texto(
        linha[indice]
    )


def separar_codigo_nome(texto):
    texto = limpar_texto(texto)

    encontrado = re.match(
        r"^\s*(\d+)\s*[-–]\s*(.+)$",
        texto
    )

    if encontrado:
        return (
            encontrado.group(1),
            limpar_texto(
                encontrado.group(2)
            )
        )

    return "", texto


def linha_para_registro(linha, colunas):
    funcionario = ler_celula(
        linha,
        colunas.get("funcionario")
    )

    codigo, nome = separar_codigo_nome(
        funcionario
    )

    if not nome:
        return None

    nome_normalizado = normalizar(nome)

    palavras_ignoradas = (
        "funcionario",
        "mes/ano",
        "conselho regional",
        "folha de pagamento",
        "total",
    )

    if any(
        termo in nome_normalizado
        for termo in palavras_ignoradas
    ):
        return None

    cargo = ler_celula(
        linha,
        colunas.get("cargo")
    )

    salario = moeda_para_float(
        ler_celula(
            linha,
            colunas.get(
                "salario_cadastro"
            )
        )
    )

    proventos = moeda_para_float(
        ler_celula(
            linha,
            colunas.get("proventos")
        )
    )

    descontos = moeda_para_float(
        ler_celula(
            linha,
            colunas.get("descontos")
        )
    )

    inss = moeda_para_float(
        ler_celula(
            linha,
            colunas.get("inss")
        )
    )

    liquido = moeda_para_float(
        ler_celula(
            linha,
            colunas.get("liquido")
        )
    )

    valores = [
        salario,
        proventos,
        descontos,
        inss,
        liquido,
    ]

    if all(
        valor is None
        for valor in valores
    ):
        return None

    if (
        proventos is None
        or descontos is None
        or inss is None
        or liquido is None
    ):
        return None

    return {
        "codigo": codigo,
        "nome": nome,
        "cargo": cargo,
        "salario_cadastro": (
            salario
            if salario is not None
            else 0.0
        ),
        "proventos": proventos,
        "descontos": descontos,
        "inss": inss,
        "liquido": liquido,
    }


def extrair_total_documento(documento):
    candidatos = []

    padrao = re.compile(
        r"R\$\s*"
        r"([\d.]+,\d{2})"
    )

    for pagina in documento.pages:
        texto = pagina.extract_text() or ""

        for linha in texto.splitlines():
            linha_limpa = limpar_texto(
                linha
            )

            encontrados = padrao.findall(
                linha_limpa
            )

            if len(encontrados) == 1:
                valor = moeda_para_float(
                    encontrados[0]
                )

                if valor is not None:
                    candidatos.append(
                        valor
                    )

    if not candidatos:
        return None

    return max(candidatos)


def extrair_remuneracoes(pdf_bytes):
    registros = []
    total_documento = None

    with pdfplumber.open(
        io.BytesIO(pdf_bytes)
    ) as documento:

        total_documento = (
            extrair_total_documento(
                documento
            )
        )

        for pagina in documento.pages:
            tabelas = pagina.extract_tables()

            for tabela in tabelas:
                colunas = None

                for linha in tabela:
                    if not linha:
                        continue

                    cabecalho = identificar_colunas(
                        linha
                    )

                    if (
                        CAMPOS_OBRIGATORIOS
                        .issubset(
                            cabecalho.keys()
                        )
                    ):
                        colunas = cabecalho
                        continue

                    if not colunas:
                        continue

                    registro = linha_para_registro(
                        linha,
                        colunas
                    )

                    if registro:
                        registros.append(
                            registro
                        )

    registros_unicos = {}

    for registro in registros:
        chave = normalizar(
            registro["nome"]
        )

        if not chave:
            continue

        if chave not in registros_unicos:
            registros_unicos[chave] = (
                registro
            )

    resultado = list(
        registros_unicos.values()
    )

    if len(resultado) < 10:
        raise RuntimeError(
            "Poucos empregados foram lidos. "
            "A estrutura do PDF pode ter mudado."
        )

    sem_cargo = [
        registro
        for registro in resultado
        if not registro["cargo"].strip()
    ]

    if sem_cargo:
        raise RuntimeError(
            "Existem empregados sem cargo "
            "identificado. A atualização foi "
            "interrompida para evitar dados "
            "incorretos."
        )

    return {
        "registros": resultado,
        "total_documento": total_documento,
    }
