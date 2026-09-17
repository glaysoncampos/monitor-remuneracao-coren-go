import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from config import OUTPUT_DIR
from extrator import extrair_remuneracoes
from portal import (
    baixar_pdf,
    criar_conexao,
    descobrir_lista_mais_nova,
    localizar_pdf_mais_recente,
)


def somar(registros, campo):
    return round(
        sum(
            float(item.get(campo, 0) or 0)
            for item in registros
        ),
        2,
    )


def calcular_indicadores(registros):
    total_empregados = len(registros)

    total_salario = somar(
        registros,
        "salario_cadastro"
    )

    total_proventos = somar(
        registros,
        "proventos"
    )

    total_descontos = somar(
        registros,
        "descontos"
    )

    total_inss = somar(
        registros,
        "inss"
    )

    total_liquido = somar(
        registros,
        "liquido"
    )

    media_liquida = round(
        total_liquido / total_empregados,
        2,
    ) if total_empregados else 0

    maior = max(
        registros,
        key=lambda item: item["liquido"]
    )

    menor = min(
        registros,
        key=lambda item: item["liquido"]
    )

    return {
        "total_empregados": total_empregados,
        "total_salario_cadastro": total_salario,
        "total_proventos": total_proventos,
        "total_descontos": total_descontos,
        "total_inss": total_inss,
        "total_liquido": total_liquido,
        "media_liquida": media_liquida,
        "maior_remuneracao": {
            "nome": maior["nome"],
            "cargo": maior["cargo"],
            "valor": maior["liquido"],
        },
        "menor_remuneracao": {
            "nome": menor["nome"],
            "cargo": menor["cargo"],
            "valor": menor["liquido"],
        },
    }


def calcular_por_cargo(registros):
    cargos = defaultdict(
        lambda: {
            "quantidade": 0,
            "salario_cadastro": 0.0,
            "proventos": 0.0,
            "descontos": 0.0,
            "inss": 0.0,
            "liquido": 0.0,
        }
    )

    for item in registros:
        cargo = item["cargo"].strip()

        dados = cargos[cargo]

        dados["quantidade"] += 1
        dados["salario_cadastro"] += (
            item["salario_cadastro"]
        )
        dados["proventos"] += (
            item["proventos"]
        )
        dados["descontos"] += (
            item["descontos"]
        )
        dados["inss"] += (
            item["inss"]
        )
        dados["liquido"] += (
            item["liquido"]
        )

    resultado = []

    for cargo, valores in cargos.items():
        resultado.append({
            "cargo": cargo,
            "quantidade": valores[
                "quantidade"
            ],
            "salario_cadastro": round(
                valores["salario_cadastro"],
                2,
            ),
            "proventos": round(
                valores["proventos"],
                2,
            ),
            "descontos": round(
                valores["descontos"],
                2,
            ),
            "inss": round(
                valores["inss"],
                2,
            ),
            "liquido": round(
                valores["liquido"],
                2,
            ),
        })

    resultado.sort(
        key=lambda item: item["liquido"],
        reverse=True,
    )

    return resultado


def salvar_csv(registros):
    arquivo = OUTPUT_DIR / "remuneracoes.csv"

    campos = [
        "codigo",
        "nome",
        "cargo",
        "salario_cadastro",
        "proventos",
        "descontos",
        "inss",
        "liquido",
    ]

    with arquivo.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as csvfile:

        escritor = csv.DictWriter(
            csvfile,
            fieldnames=campos,
            delimiter=";",
        )

        escritor.writeheader()

        for registro in registros:
            escritor.writerow(registro)


def main():
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    conexao = criar_conexao()

    ano, lista_id = (
        descobrir_lista_mais_nova(
            conexao
        )
    )

    relatorio = (
        localizar_pdf_mais_recente(
            conexao,
            lista_id,
        )
    )

    pdf_bytes = baixar_pdf(
        conexao,
        relatorio["url"],
    )

    hash_pdf = hashlib.sha256(
        pdf_bytes
    ).hexdigest()

    extraido = extrair_remuneracoes(
        pdf_bytes
    )

    registros = extraido["registros"]

    total_documento = (
        extraido["total_documento"]
    )

    indicadores = calcular_indicadores(
        registros
    )

    total_liquido = indicadores[
        "total_liquido"
    ]

    if total_documento is not None:
        diferenca = abs(
            total_documento
            - total_liquido
        )

        if diferenca > 0.05:
            raise RuntimeError(
                "O total líquido calculado não "
                "confere com o total apresentado "
                "no PDF. "
                f"PDF: R$ {total_documento:.2f} | "
                f"Calculado: R$ {total_liquido:.2f}"
            )

    dados = {
        "ano": ano,
        "fonte": relatorio,
        "hash_pdf": hash_pdf,
        "atualizado_em": datetime.now(
            ZoneInfo(
                "America/Sao_Paulo"
            )
        ).isoformat(),
        "indicadores": indicadores,
        "por_cargo": calcular_por_cargo(
            registros
        ),
        "registros": registros,
    }

    arquivo_json = (
        OUTPUT_DIR / "dados.json"
    )

    arquivo_json.write_text(
        json.dumps(
            dados,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    salvar_csv(registros)

    print(
        "Monitor atualizado com sucesso."
    )

    print(
        f"Ano: {ano}"
    )

    print(
        "Relatório: "
        f"{relatorio['nome']}"
    )

    print(
        "Data de upload: "
        f"{relatorio['data_upload']}"
    )

    print(
        "Empregados: "
        f"{indicadores['total_empregados']}"
    )

    print(
        "Total líquido: "
        f"R$ {total_liquido:,.2f}"
    )


if __name__ == "__main__":
    main()
