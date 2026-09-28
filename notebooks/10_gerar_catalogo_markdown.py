# Databricks notebook source
# MAGIC %md
# MAGIC # 10 · Gerar o catálogo em Markdown
# MAGIC
# MAGIC **Lê:** `mafia_office.information_schema.tables` e `mafia_office.information_schema.columns`, schemas `bronze`,
# MAGIC `silver` e `gold`, e `gold.qualidade_por_atributo`.
# MAGIC
# MAGIC **Escreve:** `catalogo-de-dados.md`, `catalogo-bronze.md` e `qualidade-por-atributo.md` na pasta do widget
# MAGIC `destino` (padrão: pasta `exportacao/` do Volume). O histórico das verificações é gravado nos notebooks 05 e 07.
# MAGIC
# MAGIC **Por quê:** o catálogo em Markdown é gerado a partir dos comentários do Unity Catalog (notebook 09), e não
# MAGIC escrito à mão. Assim ele acompanha o catálogo do Databricks e pode ser lido no GitHub sem abrir o workspace.
# MAGIC
# MAGIC Toda coluna precisa ter comentário com `Domínio:` e `Linhagem:`. Se faltar, o notebook para antes de gravar.
# MAGIC
# MAGIC Os arquivos exportados pelo Catalog Explorer (Volume `bronze.pouso`, pasta `exportacao/`) são copiados para
# MAGIC `docs/`. O catálogo também é impresso no fim do notebook.
# MAGIC
# MAGIC A coluna "Nulos" mostra a contagem real, feita com uma consulta agregada por tabela, e não a nulidade declarada no
# MAGIC schema (tabelas criadas por CTAS aceitam nulo em todas as colunas). Na Bronze, tudo é texto e o vazio chega como
# MAGIC `NA`, então ali a contagem soma nulo, `NA` e texto vazio. Views não são medidas.
# MAGIC
# MAGIC A saída usa o Volume porque a escrita funciona no serverless sem depender de
# MAGIC onde os notebooks foram importados.
# MAGIC
# MAGIC Os arquivos são sobrescritos a cada execução; com os mesmos comentários, só muda a data de geração no cabeçalho.

# COMMAND ----------

import os
from datetime import datetime, timezone

CATALOGO = "mafia_office"
SCHEMAS = ["silver", "gold"]

dbutils.widgets.text(
    "destino",
    "/Volumes/mafia_office/bronze/pouso/exportacao/catalogo-de-dados.md",
    "Arquivo de saída",
)
DESTINO = dbutils.widgets.get("destino")

# COMMAND ----------

tabelas = spark.sql(
    f"""
    SELECT table_schema, table_name, table_type, comment
    FROM {CATALOGO}.information_schema.tables
    WHERE table_schema IN ('bronze', 'silver', 'gold')
    ORDER BY table_schema DESC, table_type, table_name
    """
).collect()

colunas = spark.sql(
    f"""
    SELECT table_schema, table_name, column_name, ordinal_position, full_data_type, is_nullable, comment
    FROM {CATALOGO}.information_schema.columns
    WHERE table_schema IN ('bronze', 'silver', 'gold')
    ORDER BY table_schema, table_name, ordinal_position
    """
).collect()

if not tabelas:
    raise ValueError("Nenhuma tabela encontrada em bronze, silver e gold. Rode os notebooks 00 a 09 antes.")

# Para antes de gravar se faltar comentário. Isso acontece quando um notebook de 01 a 07 roda depois do 09, porque
# recriar a tabela apaga os comentários.
sem_comentario = [
    f"{c['table_schema']}.{c['table_name']}.{c['column_name']}" for c in colunas if not (c["comment"] or "").strip()
]
sem_comentario += [f"{t['table_schema']}.{t['table_name']}" for t in tabelas if not (t["comment"] or "").strip()]
if sem_comentario:
    raise ValueError(
        f"{len(sem_comentario)} objetos sem comentário (exemplos: {sem_comentario[:5]}). Reexecute o notebook 09 e depois este."
    )

# Cada campo precisa de descrição, tipo, domínio e linhagem. O tipo vem do information_schema; a descrição, o domínio
# e a linhagem precisam estar no comentário.
sem_dominio_ou_linhagem = [
    f"{c['table_schema']}.{c['table_name']}.{c['column_name']}"
    for c in colunas
    if "Domínio:" not in (c["comment"] or "") or "Linhagem:" not in (c["comment"] or "")
]
if sem_dominio_ou_linhagem:
    raise ValueError(
        f"{len(sem_dominio_ou_linhagem)} colunas sem Domínio: ou Linhagem: no comentário "
        f"(exemplos: {sem_dominio_ou_linhagem[:5]}). Corrija o comentário e reexecute."
    )

colunas_por_tabela: dict[tuple[str, str], list] = {}
for coluna in colunas:
    colunas_por_tabela.setdefault((coluna["table_schema"], coluna["table_name"]), []).append(coluna)

# COMMAND ----------


def celula(texto: str | None) -> str:
    """Escapa o que quebraria a tabela Markdown."""
    if texto is None or not str(texto).strip():
        return "_sem comentário_"
    return str(texto).replace("|", "\\|").replace("\n", " ").strip()


def contar_nulos(schema: str, tabela: str, nomes: list[str]) -> dict[str, tuple[int, int]]:
    """Uma varredura por tabela: total de linhas e nulos por coluna. Na Bronze, NA e texto vazio contam como nulo."""
    if schema == "bronze":
        condicao = "`{nome}` IS NULL OR trim(CAST(`{nome}` AS STRING)) IN ('NA', '')"
    else:
        condicao = "`{nome}` IS NULL"
    expressoes = ", ".join(
        f"COUNT_IF({condicao.format(nome=nome)}) AS `n_{indice}`" for indice, nome in enumerate(nomes)
    )
    linha = spark.sql(f"SELECT COUNT(*) AS total, {expressoes} FROM {CATALOGO}.{schema}.{tabela}").first()
    return {nome: (linha[f"n_{indice}"], linha["total"]) for indice, nome in enumerate(nomes)}


def secao_tabela(tabela, numero_quadro: int) -> list[str]:
    nome = f"{tabela['table_schema']}.{tabela['table_name']}"
    tipo = "view" if tabela["table_type"] == "VIEW" else "tabela"
    linhas = [
        f"### `{nome}`",
        "",
        f"*{tipo}* · {celula(tabela['comment'])}",
        "",
        f"**Quadro {numero_quadro} - Atributos de `{nome}`**",
        "",
        "| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |",
        "|---|---|---|---|---|",
    ]
    colunas_tabela = colunas_por_tabela.get((tabela["table_schema"], tabela["table_name"]), [])
    nulos = (
        {}
        if tipo == "view"
        else contar_nulos(tabela["table_schema"], tabela["table_name"], [c["column_name"] for c in colunas_tabela])
    )
    # Numeração pela ordem da consulta (já ordenada por ordinal_position), sem depender da base 0 ou 1.
    for posicao, coluna in enumerate(colunas_tabela, 1):
        if coluna["column_name"] in nulos:
            quantidade, total = nulos[coluna["column_name"]]
            texto_nulos = f"{quantidade:,} de {total:,}".replace(",", ".")
        else:
            texto_nulos = "n/a (view)"
        linhas.append(
            f"| {posicao} | `{coluna['column_name']}` | `{coluna['full_data_type']}` | {texto_nulos} | "
            f"{celula(coluna['comment'])} |"
        )
    linhas += ["", f"Fonte: o autor ({datetime.now(timezone.utc).year}), com base nos metadados e nas contagens do pipeline.", ""]
    return linhas


gerado_em = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
documento = [
    "# Catálogo de dados",
    "",
    f"> Arquivo **gerado** pelo notebook `notebooks/10_gerar_catalogo_markdown.py` a partir de "
    f"`{CATALOGO}.information_schema` em {gerado_em}. Não edite à mão: altere os `COMMENT ON` em "
    "`notebooks/09_catalogo_comentarios.sql`, reexecute o 09 e depois o 10.",
    "",
    "Cada descrição de coluna segue o padrão **o que é · domínio · linhagem**. A linhagem coluna a coluna entre as "
    "camadas também está em [`linhagem.md`](linhagem.md), escrita à mão e independente da aba de linhagem do Unity "
    "Catalog.",
    "",
    "## Sumário",
    "",
]
for schema in SCHEMAS:
    documento.append(f"- **{schema}**")
    for tabela in tabelas:
        if tabela["table_schema"] == schema:
            documento.append(f"  - `{schema}.{tabela['table_name']}`")
documento.append("")

numero_quadro = 0
for schema in SCHEMAS:
    documento += [f"## Schema `{schema}`", ""]
    for tabela in tabelas:
        if tabela["table_schema"] == schema:
            numero_quadro += 1
            documento += secao_tabela(tabela, numero_quadro)

conteudo = "\n".join(documento)

# Catálogo da Bronze em arquivo separado: são mais de 500 colunas, quase todas perguntas da pesquisa, e no arquivo
# principal elas esconderiam a Silver e a Gold.
bronze = [
    "# Catálogo de dados · camada Bronze",
    "",
    f"> Arquivo **gerado** pelo notebook `notebooks/10_gerar_catalogo_markdown.py` a partir de "
    f"`{CATALOGO}.information_schema` em {gerado_em}. Os comentários das colunas são gravados na própria carga "
    "(notebooks 01 e 02): o texto de cada pergunta vem do `schema.csv` da safra e o rótulo de cada campo do SIDRA "
    "vem do cabeçalho da resposta da API. A Bronze guarda o texto como veio da fonte. Como tudo é texto e o vazio "
    "chega como `NA`, a coluna Nulos soma nulo, `NA` e texto vazio.",
    "",
]
numero_quadro = 0
for tabela in tabelas:
    if tabela["table_schema"] == "bronze":
        numero_quadro += 1
        bronze += secao_tabela(tabela, numero_quadro)
conteudo_bronze = "\n".join(bronze)
DESTINO_BRONZE = os.path.join(os.path.dirname(DESTINO), "catalogo-bronze.md")

# COMMAND ----------

os.makedirs(os.path.dirname(DESTINO), exist_ok=True)
with open(DESTINO, "w", encoding="utf-8") as arquivo:
    arquivo.write(conteudo)
with open(DESTINO_BRONZE, "w", encoding="utf-8") as arquivo:
    arquivo.write(conteudo_bronze)
print(f"ok: {DESTINO_BRONZE}")

print(f"ok: {DESTINO} com {len(tabelas)} objetos e {len(colunas)} colunas")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Qualidade por atributo em Markdown

# COMMAND ----------


def numero(valor, casas: int = 1) -> str:
    if valor is None:
        return "n/a"
    if isinstance(valor, float):
        return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{valor:,}".replace(",", ".")


perfil = spark.sql(f"SELECT * FROM {CATALOGO}.gold.qualidade_por_atributo ORDER BY tabela, posicao").collect()
qualidade = [
    "# Qualidade por atributo",
    "",
    f"> Arquivo **gerado** pelo notebook `notebooks/10_gerar_catalogo_markdown.py` a partir de "
    f"`{CATALOGO}.gold.qualidade_por_atributo` (notebook 05b) em {gerado_em}.",
    "",
    "Uma linha por coluna da Bronze e da Silver, nas cinco dimensões de qualidade. Completude é a parcela de valores "
    "preenchidos. Unicidade só se aplica à chave da tabela. Consistência é a parcela dos valores preenchidos que respeita "
    "a regra de domínio da coluna, inclusive regras entre colunas. Acurácia só é medida onde existe referência externa. "
    "Outliers usam a regra do intervalo interquartil (1,5 × IQR) nas colunas de medida; chaves e códigos ficam de fora.",
    "",
]
tabela_atual = None
numero_tabela = 0
fonte_qualidade = f"Fonte: o autor ({datetime.now(timezone.utc).year}), com base no perfil calculado no notebook 05b."
for linha in perfil:
    if linha["tabela"] != tabela_atual:
        if tabela_atual is not None:
            qualidade += ["", fonte_qualidade]
        numero_tabela += 1
        tabela_atual = linha["tabela"]
        qualidade += [
            "",
            f"## `{tabela_atual}`",
            "",
            f"**Tabela {numero_tabela} - Qualidade dos atributos de `{tabela_atual}`**",
            "",
            "| Coluna | Completude | Unicidade | Consistência | Acurácia | Outliers |",
            "|---|---|---|---|---|---|",
        ]
    completude = f"{numero(linha['completude_pct'])}% ({numero(linha['nulos'])} nulos)"
    consistencia = (
        f"{numero(linha['consistencia_pct'])}% · {celula(linha['regra_consistencia'])}"
        if linha["consistencia_pct"] is not None
        else celula(linha["regra_consistencia"])
    )
    outliers = (
        f"{numero(linha['outliers_iqr'])} fora de [{numero(linha['limite_inf_iqr'], 2)}; {numero(linha['limite_sup_iqr'], 2)}]"
        if linha["outliers_iqr"] is not None
        else "sem regra de extremos nesta etapa; chaves, códigos e campos textuais ficam fora do IQR"
    )
    qualidade.append(
        f"| `{linha['coluna']}` | {completude} | {celula(linha['unicidade'])} | {consistencia} | "
        f"{celula(linha['acuracia'])} | {outliers} |"
    )
if tabela_atual is not None:
    qualidade += ["", fonte_qualidade, ""]
DESTINO_QUALIDADE = os.path.join(os.path.dirname(DESTINO), "qualidade-por-atributo.md")
with open(DESTINO_QUALIDADE, "w", encoding="utf-8") as arquivo:
    arquivo.write("\n".join(qualidade) + "\n")
print(f"ok: {DESTINO_QUALIDADE} com {len(perfil)} atributos")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Histórico das verificações já persistidas
# MAGIC
# MAGIC Uma execução pode ter histórico parcial. O estado de sucesso ou falha é consultado no Jobs.

# COMMAND ----------

display(
    spark.sql(
        f"""
        SELECT job_run_id, MIN(executado_em) AS executado_em, COUNT(*) AS verificacoes,
               COUNT_IF(resultado = 'reprovado') AS reprovadas
        FROM {CATALOGO}.gold.verificacoes_qualidade_historico
        GROUP BY job_run_id ORDER BY executado_em DESC
        """
    )
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Conteúdo gerado
# MAGIC

# COMMAND ----------

print(conteudo)
