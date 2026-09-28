# Databricks notebook source
# MAGIC %md
# MAGIC # 08b · Modelo: Remoto por safra, controlando composição
# MAGIC
# MAGIC **Lê:** `gold.fato_resposta_pesquisa` e as dimensões `dim_periodo`, `dim_geografia`, `dim_arranjo_trabalho` e
# MAGIC `dim_perfil_dev`.
# MAGIC
# MAGIC **Escreve:** `gold.analise_q1d_modelo_logistico`, uma linha por termo do modelo e por contraste entre safras.
# MAGIC
# MAGIC **Por quê:** a Q1c padroniza a série do remoto por um fator só (vínculo). O indicador Brasil/resto, a faixa de experiência e o
# MAGIC vínculo mudam de composição entre safras ao mesmo tempo. Por isso, é ajustada uma regressão logística de `Remoto`
# MAGIC (contra Híbrido e Presencial, na série comparável) sobre safra, vínculo, Brasil e faixa de experiência, na base
# MAGIC de quem trabalha. O coeficiente de cada safra mede a diferença no logaritmo das chances de remoto com esses três fatores constantes. O vínculo
# MAGIC entra em três categorias (empregado, autônomo, ambos); "ambos" só existe de 2022 a 2024.
# MAGIC
# MAGIC O modelo controla só a composição observada. Não corrige viés de seleção, quem não respondeu em 2025 continua
# MAGIC fora e a mudança de questionário de 2025 continua valendo. Os intervalos cobrem só o erro aleatório.
# MAGIC
# MAGIC Método: GLM binomial com ligação logit (statsmodels), ajustado sobre a tabela agregada (remotos e total por safra ×
# MAGIC vínculo × Brasil × faixa), o que equivale ao ajuste linha a linha. Referências: 2022, empregado, fora do Brasil,
# MAGIC faixa 0–2. Se a dispersão de Pearson passar de 1, a covariância é escalada pela dispersão (quase-binomial).
# MAGIC
# MAGIC Leitura da razão de chances: 0,80 quer dizer que as *odds* de estar remoto (remotos ÷ não remotos) ficaram 20%
# MAGIC menores, não a proporção. Com 43% de remotos, odds 20% menores dão cerca de 38%.
# MAGIC
# MAGIC A gravação usa `CREATE OR REPLACE TABLE`, então rodar de novo é seguro.
# MAGIC
# MAGIC O ambiente serverless padrão não traz `statsmodels`; a célula seguinte instala o pacote na sessão.

# COMMAND ----------

# MAGIC %pip install statsmodels==0.15.0 --quiet

# COMMAND ----------

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm
from pyspark.sql import functions as F

CATALOGO = "mafia_office"
REFERENCIAS = {"safra": "2022", "vinculo": "Empregado", "faixa_experiencia": "0–2"}

# COMMAND ----------

# Base: quem trabalha, série comparável (Remoto, Híbrido, Presencial), país informado. Uma linha por combinação, com
# o total e os remotos, o que basta para o GLM binomial.
celulas = (
    spark.table(f"{CATALOGO}.gold.fato_resposta_pesquisa").alias("f")
    .join(spark.table(f"{CATALOGO}.gold.dim_periodo").alias("p"), F.col("f.periodo_chave") == F.col("p.periodo_chave"))
    .join(spark.table(f"{CATALOGO}.gold.dim_geografia").alias("g"), F.col("f.geo_chave") == F.col("g.geo_chave"))
    .join(spark.table(f"{CATALOGO}.gold.dim_arranjo_trabalho").alias("a"), F.col("f.arranjo_chave") == F.col("a.arranjo_chave"))
    .join(spark.table(f"{CATALOGO}.gold.dim_perfil_dev").alias("pf"), F.col("f.perfil_chave") == F.col("pf.perfil_chave"))
    .filter(F.col("f.trabalhando") & F.col("a.entra_serie_historica") & ~F.col("f.geo_chave").isin(-1, -2))
    .filter(F.col("pf.faixa_experiencia") != "Não informado")
    .select(
        F.col("p.ano").cast("string").alias("safra"),
        F.when(F.col("f.empregado") & F.col("f.autonomo"), "Ambos")
         .when(F.col("f.empregado"), "Empregado")
         .otherwise("Autônomo").alias("vinculo"),
        (F.col("g.codigo") == "Brazil").cast("int").alias("brasil"),
        F.col("pf.faixa_experiencia"),
        F.col("f.qtd_respondentes").alias("n"),
        F.when(F.col("a.arranjo") == "Remoto", F.col("f.qtd_respondentes")).otherwise(F.lit(0)).alias("remotos"),
    )
    .groupBy("safra", "vinculo", "brasil", "faixa_experiencia")
    .agg(F.sum("n").alias("n"), F.sum("remotos").alias("remotos"))
    .toPandas()
)
celulas["n"] = celulas["n"].astype(int)
celulas["remotos"] = celulas["remotos"].astype(int)
print(f"{len(celulas)} células; {int(celulas['n'].sum())} respondentes; {int(celulas['remotos'].sum())} remotos")

# COMMAND ----------

# Matriz do modelo: dummies com a referência declarada em REFERENCIAS removida de cada fator.
X = pd.DataFrame({"intercepto": 1.0}, index=celulas.index)
for fator, ref in REFERENCIAS.items():
    niveis = sorted(celulas[fator].unique())
    assert ref in niveis, f"referência {ref} ausente em {fator}: {niveis}"
    for nivel in niveis:
        if nivel != ref:
            X[f"{fator}={nivel}"] = (celulas[fator] == nivel).astype(float)
X["brasil"] = celulas["brasil"].astype(float)

endog = np.column_stack([celulas["remotos"], celulas["n"] - celulas["remotos"]])
# Com mais de 200 mil respondentes em pouco mais de cem células, qualquer falta de ajuste aparece como superdispersão
# (variância observada maior que a do modelo binomial). A dispersão de Pearson é calculada (qui-quadrado sobre graus de
# liberdade) e, se ela passar de 1, a matriz de covariância é multiplicada por ela (quase-binomial). A escala é aplicada explicitamente: com a resposta em duas colunas (remotos, não remotos), o scale="X2" do statsmodels não dá a mesma dispersão.
modelo = sm.GLM(endog, X, family=sm.families.Binomial()).fit()
DISPERSAO_PEARSON = float(modelo.pearson_chi2 / modelo.df_resid)
ESCALA = max(1.0, DISPERSAO_PEARSON)
print(f"dispersão de Pearson: {DISPERSAO_PEARSON:.2f} ({'erros-padrão corrigidos' if ESCALA > 1 else 'sem correção'})")
print("Inferência: coeficientes abaixo com covariância corrigida pela dispersão de Pearson.")

# COMMAND ----------

# Uma linha por termo, com razão de chances e intervalo de 95%; depois os contrastes entre safras consecutivas, cuja
# variância vem da matriz de covariância dos coeficientes.
cov = modelo.cov_params() * ESCALA
linhas = []
for termo in X.columns:
    if termo == "intercepto":
        continue
    fator, _, categoria = termo.partition("=")
    b, ep = float(modelo.params[termo]), float(cov.loc[termo, termo]) ** 0.5
    linhas.append((fator if categoria else "brasil", categoria or "Brasil", REFERENCIAS.get(fator, "fora do Brasil"),
                   "termo", b, ep, float(2 * norm.sf(abs(b / ep)))))
for atual, anterior in (("2023", "2022"), ("2024", "2023"), ("2025", "2024"), ("2024", "2022")):
    ta, tb = f"safra={atual}", f"safra={anterior}"
    if tb == f"safra={REFERENCIAS['safra']}":
        b, var = float(modelo.params[ta]), float(cov.loc[ta, ta])
    else:
        b = float(modelo.params[ta] - modelo.params[tb])
        var = float(cov.loc[ta, ta] + cov.loc[tb, tb] - 2 * cov.loc[ta, tb])
    ep = var ** 0.5
    z = b / ep
    linhas.append(("safra", atual, anterior, "contraste", b, ep, float(2 * norm.sf(abs(z)))))

resultado = pd.DataFrame(linhas, columns=["fator", "categoria", "referencia", "tipo", "coeficiente", "erro_padrao", "p_valor"])
resultado["razao_de_chances"] = np.exp(resultado["coeficiente"])
resultado["ic95_inf"] = np.exp(resultado["coeficiente"] - 1.96 * resultado["erro_padrao"])
resultado["ic95_sup"] = np.exp(resultado["coeficiente"] + 1.96 * resultado["erro_padrao"])
resultado["n_celulas"] = len(celulas)
resultado["n_respondentes"] = int(celulas["n"].sum())
resultado["remotos"] = int(celulas["remotos"].sum())
resultado["dispersao_pearson"] = round(DISPERSAO_PEARSON, 2)
for c in ("coeficiente", "erro_padrao", "razao_de_chances", "ic95_inf", "ic95_sup"):
    resultado[c] = resultado[c].round(4)
# P-valores pequenos mantêm precisão; zero não representa probabilidade exata.
print(resultado.to_string(index=False))

# COMMAND ----------

spark.createDataFrame(resultado).createOrReplaceTempView("_modelo_11")
spark.sql(
    f"""
    CREATE OR REPLACE TABLE {CATALOGO}.gold.analise_q1d_modelo_logistico
    COMMENT 'Q1d: regressão logística de Remoto (série comparável, base trabalhando) sobre safra, vínculo, Brasil e faixa de experiência; uma linha por termo e por contraste entre safras. Controla composição observada; não corrige seleção.'
    AS SELECT fator, categoria, referencia, tipo, coeficiente, erro_padrao, razao_de_chances, ic95_inf, ic95_sup, p_valor,
              n_celulas, n_respondentes, remotos, dispersao_pearson
       FROM _modelo_11
    """
)
# Comentários de coluna: notebook 09, junto com os das demais tabelas Gold.

# COMMAND ----------

display(spark.sql(f"SELECT * FROM {CATALOGO}.gold.analise_q1d_modelo_logistico ORDER BY tipo DESC, fator, categoria"))
