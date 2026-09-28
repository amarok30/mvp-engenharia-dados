# Databricks notebook source
# MAGIC %md
# MAGIC # 05b · Qualidade por atributo
# MAGIC
# MAGIC **Lê:** as tabelas da Bronze, os perfis da captura e as cinco tabelas da Silver e `gold.verificacoes_qualidade` (notebook 05).
# MAGIC
# MAGIC **Escreve:** `gold.qualidade_por_atributo`, uma linha por coluna da Bronze e da Silver.
# MAGIC
# MAGIC **Por quê:** o notebook 05 organiza a qualidade por problema (C01 a C30). Este notebook mede, para cada coluna da captura e da Silver,
# MAGIC as cinco dimensões de qualidade, com uma leitura por tabela:
# MAGIC
# MAGIC - **completude:** parcela de valores preenchidos;
# MAGIC - **unicidade:** só faz sentido na chave; nas outras colunas é registrada a quantidade de valores distintos;
# MAGIC - **consistência:** parcela dos valores preenchidos que respeita a regra de domínio da coluna. Algumas regras
# MAGIC   cruzam colunas (por exemplo, `trabalhando` = `empregado OR autonomo`); texto livre fica sem regra;
# MAGIC - **acurácia:** só onde existe referência externa (totais do IBGE, contagem publicada pela Stack Overflow). Nas
# MAGIC   outras colunas a linha diz por que não dá para medir;
# MAGIC - **outliers:** regra do intervalo interquartil (fora de Q1 − 1,5 × IQR e Q3 + 1,5 × IQR), só nas colunas de
# MAGIC   medida. Nenhuma linha sai da Silver por ser outlier.
# MAGIC
# MAGIC Este notebook só mede e grava; quem para o pipeline é o 05.
# MAGIC
# MAGIC A gravação usa `mode("overwrite")`, então rodar de novo é seguro.

# COMMAND ----------

from datetime import datetime, timezone
import json
from pathlib import Path
from perfil_captura import perfil_registros

from pyspark.sql import functions as F

CATALOGO = "mafia_office"

# Chave de cada tabela, a mesma das restrições dos notebooks 03 e 04.
CHAVES = {
    "so_respondente": ["safra", "resposta_id"],
    "so_de_para_arranjo": ["safra", "valor_origem"],
    "so_metadados_pergunta": ["safra", "qname"],
    "ibge_teletrabalho_uf": ["uf_codigo", "modalidade_codigo"],
    "ibge_ocupados_uf_atividade": ["uf_codigo", "periodo_codigo", "atividade_codigo"],
}

ARRANJOS = "'Remoto', 'Híbrido', 'Presencial', 'Flexível', 'Não informado'"
PORTES = "'Autônomo', 'Menos de 20', '20 a 99', '100 a 499', '500 a 999', '1.000 a 4.999', '5.000 a 9.999', '10.000 ou mais', 'Não sabe'"
SINAIS = "'-', '..', '...', 'x'"
FAIXAS_CV = "'Exata', 'Ótima', 'Boa', 'Razoável', 'Pouco precisa', 'Imprecisa'"
CLASSIFICAR_CV = (
    "CASE WHEN {cv} = 0 THEN 'Exata' WHEN {cv} <= 5 THEN 'Ótima' WHEN {cv} <= 15 THEN 'Boa' "
    "WHEN {cv} <= 30 THEN 'Razoável' WHEN {cv} <= 50 THEN 'Pouco precisa' ELSE 'Imprecisa' END"
)

# Regra de consistência de cada coluna: (expressão SQL avaliada nas linhas com valor, texto da regra).
# None na expressão quer dizer texto livre, sem regra fechada.
REGRAS = {
    "so_respondente": {
        "safra": ("safra IN (2022, 2023, 2024, 2025)", "safra entre 2022 e 2025"),
        "resposta_id": ("resposta_id > 0", "inteiro positivo"),
        "e_profissional": ("e_profissional IN (true, false)", "booleano"),
        "empregado": ("empregado IN (true, false)", "booleano"),
        "autonomo": ("autonomo IN (true, false)", "booleano"),
        "trabalhando": ("trabalhando = (empregado OR autonomo)", "igual a empregado OU autônomo"),
        "arranjo_trabalho_origem": (None, "texto da fonte; o de-para da safra é conferido na verificação C17"),
        "arranjo_trabalho": (f"arranjo_trabalho IN ({ARRANJOS})", "uma das cinco categorias do de-para"),
        "comparavel_serie": (
            "comparavel_serie = (arranjo_trabalho NOT IN ('Flexível', 'Não informado'))",
            "verdadeiro só para Remoto, Híbrido e Presencial",
        ),
        "pais": ("pais = trim(pais) AND length(pais) > 0", "nome sem espaço nas pontas; lista aberta da pesquisa"),
        "e_brasil": ("e_brasil = (COALESCE(pais, '') = 'Brazil')", "verdadeiro só quando pais é Brazil"),
        "porte_empresa_origem": ("porte_empresa IS NOT NULL", "todo rótulo da fonte tem faixa canônica"),
        "porte_empresa": (f"porte_empresa IN ({PORTES})", "uma das nove faixas canônicas"),
        "porte_ordem": ("porte_ordem BETWEEN 1 AND 9", "ordem de 1 a 9"),
        "perfil_principal": (None, "texto da fonte; lista de perfis muda entre safras"),
        "anos_codando": ("anos_codando BETWEEN 0 AND 50", "0 a 50"),
        "faixa_experiencia": (
            "faixa_experiencia = CASE WHEN anos_codando <= 2 THEN '0–2' WHEN anos_codando <= 5 THEN '3–5' "
            "WHEN anos_codando <= 10 THEN '6–10' WHEN anos_codando <= 20 THEN '11–20' ELSE '21+' END",
            "faixa bate com anos_codando",
        ),
        "remuneracao_usd": ("remuneracao_usd >= 0", "não negativa"),
        "remuneracao_outlier": (
            "remuneracao_outlier = COALESCE(remuneracao_usd < 1000 OR remuneracao_usd > 1000000, false)",
            "verdadeiro só fora de 1 mil a 1 milhão de dólares",
        ),
        "satisfacao_trabalho": (
            "satisfacao_trabalho BETWEEN 0 AND 10 AND safra >= 2024",
            "0 a 10, e só em 2024 e 2025, quando a pergunta existe",
        ),
        "_ingerido_em": ("_ingerido_em IS NOT NULL", "data e hora da carga"),
    },
    "so_de_para_arranjo": {
        "safra": ("safra IN (2022, 2023, 2024, 2025)", "2022 a 2025; nulo vale para todas as safras"),
        "valor_origem": (None, "rótulo literal da pesquisa"),
        "valor_canonico": (f"valor_canonico IN ({ARRANJOS})", "uma das cinco categorias"),
        "entra_serie_historica": (
            "entra_serie_historica = (valor_canonico IN ('Remoto', 'Híbrido', 'Presencial'))",
            "verdadeiro só para Remoto, Híbrido e Presencial",
        ),
        "observacao": (None, "texto livre"),
    },
    "so_metadados_pergunta": {
        "safra": ("safra IN (2022, 2023, 2024, 2025)", "2022 a 2025"),
        "qname": ("qname = trim(qname) AND qname NOT LIKE '% %'", "identificador sem espaço"),
        "texto_pergunta": (None, "texto livre"),
        "tipo": (None, "código de tipo da fonte"),
        "presente_na_safra": ("presente_na_safra = (texto_pergunta IS NOT NULL)", "verdadeiro só quando há texto"),
    },
    "ibge_teletrabalho_uf": {
        "nivel_territorial": ("nivel_territorial IN ('pais', 'uf')", "pais ou uf"),
        "uf_codigo": (
            "(nivel_territorial = 'pais' AND uf_codigo = '1') OR (nivel_territorial = 'uf' AND uf_codigo RLIKE '^[1-5][0-9]$')",
            "1 para o Brasil; dois dígitos para UF",
        ),
        "uf_nome": (None, "nome do território"),
        "ano": ("ano = 2022", "2022"),
        "modalidade_codigo": (
            "modalidade_codigo IN ('59803', '59804', '59805', '59806', '59807', '59808')",
            "seis códigos da classificação c1675",
        ),
        "modalidade": (None, "rótulo do IBGE"),
        "pessoas_mil": ("pessoas_mil >= 0", "não negativo"),
        "pessoas_mil_sinal": (f"pessoas_mil_sinal IN ({SINAIS})", "um dos sinais do IBGE"),
        "cv_pessoas": ("cv_pessoas >= 0", "não negativo"),
        "cv_pessoas_sinal": (f"cv_pessoas_sinal IN ({SINAIS})", "um dos sinais do IBGE"),
        "cv_pessoas_classificacao": (
            f"cv_pessoas_classificacao = {CLASSIFICAR_CV.format(cv='cv_pessoas')}",
            "faixa bate com cv_pessoas",
        ),
        "percentual": ("percentual BETWEEN 0 AND 100", "0 a 100"),
        "percentual_sinal": (f"percentual_sinal IN ({SINAIS})", "um dos sinais do IBGE"),
        "cv_percentual": ("cv_percentual >= 0", "não negativo"),
        "cv_percentual_sinal": (f"cv_percentual_sinal IN ({SINAIS})", "um dos sinais do IBGE"),
        "cv_classificacao": (
            f"cv_classificacao = {CLASSIFICAR_CV.format(cv='cv_percentual')}",
            "faixa bate com cv_percentual",
        ),
        "estimativa_confiavel": ("estimativa_confiavel = (cv_percentual <= 15)", "verdadeiro só com CV até 15%"),
        "disponivel_no_nivel": (
            "disponivel_no_nivel = NOT (nivel_territorial = 'uf' AND modalidade_codigo IN ('59807', '59808'))",
            "falso só para 59807 e 59808 por UF",
        ),
        "e_experimental": ("e_experimental = true", "sempre verdadeiro"),
    },
    "ibge_ocupados_uf_atividade": {
        "uf_codigo": ("uf_codigo RLIKE '^[1-5][0-9]$'", "dois dígitos"),
        "uf_nome": (None, "nome da UF"),
        "ano": ("ano >= 2012", "2012 em diante"),
        "trimestre": ("trimestre BETWEEN 1 AND 4", "1 a 4"),
        "periodo_codigo": (
            "periodo_codigo = concat(CAST(ano AS STRING), lpad(CAST(trimestre AS STRING), 2, '0'))",
            "AAAATT, igual a ano e trimestre",
        ),
        "atividade_codigo": ("atividade_codigo RLIKE '^[0-9]+$'", "código numérico da classificação c888"),
        "atividade_nome": (None, "rótulo do IBGE"),
        "e_proxy_tecnologia": ("e_proxy_tecnologia = (atividade_codigo = '56624')", "verdadeiro só para 56624"),
        "pessoas_mil": ("pessoas_mil >= 0", "não negativo"),
        "pessoas_mil_sinal": (f"pessoas_mil_sinal IN ({SINAIS})", "um dos sinais do IBGE"),
    },
}

# Acurácia: só onde existe referência externa. (verificação que mede, o que é comparado); sem verificação, o motivo.
ACURACIA = {
    ("ibge_teletrabalho_uf", "pessoas_mil"): ("C14", "total do Brasil comparado com o publicado pelo IBGE"),
    ("ibge_teletrabalho_uf", "percentual"): ("C14", "taxas do Brasil comparadas com as publicadas pelo IBGE"),
    ("ibge_ocupados_uf_atividade", "pessoas_mil"): ("C24", "total comparado com a soma dos grupamentos publicada"),
    ("so_respondente", "resposta_id"): ("C16", "linhas de 2025 comparadas com as respostas publicadas na metodologia"),
    ("so_respondente", "remuneracao_usd"): ("C11", "estatísticas da captura de 2024 comparadas com os valores esperados; não comprova a remuneração individual; extremos descritos na C19"),
    ("so_respondente", "e_brasil"): ("C12", "respondentes do Brasil comparados com a contagem esperada"),
}
SEM_REFERENCIA = {
    "so_respondente": "não mensurável: resposta autodeclarada, sem fonte de verdade por pessoa",
    "so_de_para_arranjo": "não se aplica: tabela de referência do projeto, versionada no Git",
    "so_metadados_pergunta": "não mensurável: o próprio schema.csv é a fonte",
    "ibge_teletrabalho_uf": "não mensurável: estimativa amostral; a precisão está no CV",
    "ibge_ocupados_uf_atividade": "não mensurável: estimativa amostral",
}
# Outliers só em colunas de medida. Chave, código, ano e ordem de faixa são números, mas IQR neles não faz sentido.
MEDIDAS = {
    "so_respondente": ["anos_codando", "remuneracao_usd", "satisfacao_trabalho"],
    "ibge_teletrabalho_uf": ["pessoas_mil", "cv_pessoas", "percentual", "cv_percentual"],
    "ibge_ocupados_uf_atividade": ["pessoas_mil"],
}

# COMMAND ----------

verificacoes = {
    linha["verificacao_id"]: linha["resultado"]
    for linha in spark.table(f"{CATALOGO}.gold.verificacoes_qualidade").select("verificacao_id", "resultado").collect()
}

linhas_perfil = []
for tabela, regras in REGRAS.items():
    nome = f"{CATALOGO}.silver.{tabela}"
    df = spark.table(nome)
    tipos = dict(df.dtypes)
    colunas = df.columns
    faltando = set(colunas) ^ set(regras)
    if faltando:
        raise AssertionError(f"{tabela}: colunas sem regra ou regra sem coluna: {sorted(faltando)}")

    # Uma leitura por tabela: nulos, distintos e violações de regra de todas as colunas.
    agregados = [F.count(F.lit(1)).alias("_total")]
    for posicao, coluna in enumerate(colunas):
        agregados.append(F.sum(F.col(f"`{coluna}`").isNull().cast("int")).alias(f"n{posicao}"))
        agregados.append(F.countDistinct(F.col(f"`{coluna}`")).alias(f"d{posicao}"))
        expressao = regras[coluna][0]
        if expressao:
            agregados.append(
                F.sum((F.col(f"`{coluna}`").isNotNull() & ~F.coalesce(F.expr(expressao), F.lit(False))).cast("int")).alias(f"v{posicao}")
            )
    resumo = df.agg(*agregados).first().asDict()
    total = resumo["_total"]

    chave = CHAVES[tabela]
    repetidas = df.groupBy(*chave).count().filter("count > 1").agg(F.sum(F.col("count") - 1)).first()[0] or 0

    for posicao, coluna in enumerate(colunas):
        nulos = resumo[f"n{posicao}"]
        preenchidos = total - nulos
        expressao, texto_regra = regras[coluna]
        violacoes = resumo.get(f"v{posicao}")
        consistencia = None if expressao is None or not preenchidos else round(100 * (preenchidos - violacoes) / preenchidos, 2)
        if coluna in chave:
            unicidade = f"parte da chave ({', '.join(chave)}): {repetidas} combinações repetidas"
        else:
            distintos = resumo[f"d{posicao}"]
            rotulo = "valor distinto" if distintos == 1 else "valores distintos"
            unicidade = f"não se aplica (não é chave); {distintos:,} {rotulo}".replace(",", ".")
        if (tabela, coluna) in ACURACIA:
            verificacao, comparacao = ACURACIA[(tabela, coluna)]
            acuracia = f"{verificacao} {verificacoes.get(verificacao, 'sem resultado')}: {comparacao}"
        else:
            acuracia = SEM_REFERENCIA[tabela]

        outliers = limite_inf = limite_sup = None
        if coluna in MEDIDAS.get(tabela, []) and preenchidos:
            q1, q3 = df.select(F.percentile_approx(F.col(coluna).cast("double"), [0.25, 0.75], 10000)).first()[0]
            iqr = q3 - q1
            limite_inf, limite_sup = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            outliers = df.filter((F.col(coluna) < limite_inf) | (F.col(coluna) > limite_sup)).count()

        linhas_perfil.append(
            (
                f"silver.{tabela}", coluna, posicao + 1, tipos[coluna], total, nulos,
                round(100 * preenchidos / total, 2) if total else None,
                unicidade, texto_regra, violacoes, consistencia, acuracia,
                outliers, None if limite_inf is None else float(limite_inf), None if limite_sup is None else float(limite_sup),
            )
        )

# A captura é avaliada antes de harmonização. O perfil das respostas foi medido
# no notebook 01; as tabelas auxiliares e colunas de ingestão são medidas aqui.
perfis_captura = {}
pasta_perfis = Path("/Volumes/mafia_office/bronze/pouso/exportacao/perfil-captura")
for item in spark.catalog.listTables(f"{CATALOGO}.bronze"):
    if item.isTemporary or item.tableType == "VIEW":
        continue
    tabela = item.name
    bruto = spark.table(f"{CATALOGO}.bronze.{tabela}")
    tipos = dict(bruto.dtypes)
    arquivo = pasta_perfis / f"{tabela}.json"
    medido = json.loads(arquivo.read_text(encoding="utf-8")) if tabela.startswith("so_pesquisa_") else {}
    restantes = [c for c in bruto.columns if c not in medido]
    if restantes:
        medido.update(perfil_registros(
            (linha.asDict() for linha in bruto.select(*restantes).toLocalIterator()), restantes
        ))
    perfis_captura[tabela] = medido
    for posicao, coluna in enumerate(bruto.columns, 1):
        m = medido[coluna]
        total = m["linhas"]
        acuracia = m["acuracia"]
        if not tabela.startswith("so_pesquisa_"):
            acuracia = "fidelidade à captura; os totais e relações da fonte são conferidos nas regras C14, C23 e C24 quando aplicáveis"
        linhas_perfil.append((
            f"bronze.{tabela}", coluna, posicao, tipos[coluna], total, m["nulos"],
            round(100 * (total - m["nulos"]) / total, 2) if total else None,
            m["unicidade"], m["regra_consistencia"], m["fora_da_regra"], m["consistencia_pct"], acuracia,
            m["outliers_iqr"], m["limite_inf_iqr"], m["limite_sup_iqr"],
        ))
destino_dominios = pasta_perfis.parent / "dominios-captura.json"
destino_dominios.write_text(json.dumps(perfis_captura, ensure_ascii=False, indent=2), encoding="utf-8")

perfil = spark.createDataFrame(
    linhas_perfil,
    "tabela STRING, coluna STRING, posicao INT, tipo STRING, linhas BIGINT, nulos BIGINT, completude_pct DOUBLE, "
    "unicidade STRING, regra_consistencia STRING, fora_da_regra BIGINT, consistencia_pct DOUBLE, acuracia STRING, "
    "outliers_iqr BIGINT, limite_inf_iqr DOUBLE, limite_sup_iqr DOUBLE",
).withColumn("executado_em", F.lit(datetime.now(timezone.utc)).cast("timestamp"))

perfil.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"{CATALOGO}.gold.qualidade_por_atributo"
)
print(f"ok: gold.qualidade_por_atributo com {perfil.count()} atributos da Bronze e da Silver")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Evidência: atributos que não passam 100% na regra

# COMMAND ----------

display(
    spark.sql(
        f"""
        SELECT tabela, coluna, completude_pct, regra_consistencia, fora_da_regra, consistencia_pct, outliers_iqr
        FROM {CATALOGO}.gold.qualidade_por_atributo
        WHERE consistencia_pct < 100 OR completude_pct < 100 OR outliers_iqr > 0
        ORDER BY tabela, posicao
        """
    )
)
