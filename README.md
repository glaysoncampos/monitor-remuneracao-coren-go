# monitor-remuneracao-coren-go
# Monitor de Remuneração dos Empregados do Coren-GO

Monitor automático criado para acompanhar a página de **Remuneração de Empregados** do Portal da Transparência do Conselho Regional de Enfermagem de Goiás.

## Objetivo

O sistema identifica automaticamente o relatório mais recente de remuneração publicado no Portal Implanta, baixa o PDF, extrai os dados, valida os valores e publica um painel HTML no GitHub Pages.

## Painel

Acesse:

https://glaysoncampos.github.io/monitor-remuneracao-coren-go/

## Fonte dos dados

Portal da Transparência do Coren-GO.

Seção monitorada:

**Remuneração de Empregados**

Ano inicial configurado:

**2026**

## Funcionamento automático

O monitor utiliza:

- Python
- GitHub Actions
- GitHub Pages
- pdfplumber
- requests
- BeautifulSoup

O workflow é executado automaticamente todos os dias às **07h30 no horário de Brasília**.

Também pode ser executado manualmente pela aba **Actions** do GitHub.

## Regra para identificar o relatório mais recente

O monitor primeiro identifica a data de upload mais recente.

Caso existam dois ou mais relatórios publicados na mesma data, o sistema utiliza o **mês e o ano de referência presentes no nome do arquivo** como critério de desempate.

Exemplo:

- Remuneração 07/2026, upload 17/09/2026
- Remuneração 08/2026, upload 17/09/2026

Nesse caso, o monitor seleciona automaticamente **08/2026**.

## Dados extraídos

Para cada empregado são extraídos:

- Funcionário
- Cargo
- Salário de cadastro
- Proventos
- Descontos
- INSS
- Valor líquido

## Indicadores do painel

O painel apresenta:

- Folha líquida total
- Quantidade de empregados
- Total de proventos
- Total de descontos
- Total de INSS
- Média líquida
- Maior remuneração líquida
- Menor remuneração líquida
- Ranking das maiores remunerações
- Valores consolidados por cargo
- Tabela detalhada por empregado

## Gráfico por cargo

O painel permite analisar os valores consolidados por cargo utilizando diferentes métricas:

- Líquido
- Proventos
- Salário de cadastro
- Descontos
- INSS

## Validações de segurança

O projeto possui validações para evitar a publicação de informações incorretas.

Entre elas:

- identificação das colunas pelo cabeçalho da tabela
- validação do vínculo entre funcionário, cargo e valores
- identificação por nome, sem depender exclusivamente do código numérico do empregado
- bloqueio da atualização quando existirem empregados sem cargo identificado
- bloqueio quando a estrutura do PDF não puder ser interpretada com segurança
- validação do total líquido calculado contra o total apresentado no PDF
- utilização de hash SHA-256 para identificar o PDF processado

## Arquivos principais

`config.py`

Configurações gerais do projeto.

`portal.py`

Localiza a seção correta no Portal Implanta, identifica o ano mais recente e seleciona o PDF correto.

`extrator.py`

Responsável pela leitura e validação da tabela de remuneração.

`monitor.py`

Coordena o processamento, calcula os indicadores e gera os arquivos utilizados pelo painel.

`docs/dados.json`

Base estruturada utilizada pelo painel.

`docs/remuneracoes.csv`

Arquivo CSV com os dados extraídos.

`docs/index.html`

Painel publicado no GitHub Pages.

`.github/workflows/monitor.yml`

Automação responsável pela execução diária e publicação do painel.

## Validação inicial

O primeiro relatório validado pelo projeto foi:

**Remuneração dos Empregados, Agosto de 2026**

Data de upload:

**17/09/2026**

Resultados validados:

- 53 empregados
- Folha líquida: R$ 633.060,35
- Proventos: R$ 818.782,68
- Descontos: R$ 145.750,70
- INSS: R$ 41.071,63
- Média líquida: R$ 11.944,53

O total líquido extraído pelo sistema foi conferido com o total apresentado no próprio PDF.

## Atualização do painel

Quando um novo relatório é publicado no Portal da Transparência:

1. O GitHub Actions executa o monitor.
2. O sistema identifica o relatório mais recente.
3. O PDF é baixado.
4. Os dados são extraídos e validados.
5. O arquivo `dados.json` é atualizado.
6. O CSV é atualizado.
7. O GitHub Pages publica automaticamente o novo painel.

## Status

**Projeto funcional e automatizado.**

Última validação manual: **17/09/2026**.
