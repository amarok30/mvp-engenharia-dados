-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 07 · Gold: fatos
-- MAGIC
-- MAGIC **Lê:** `silver.so_respondente`, `silver.ibge_teletrabalho_uf`, `silver.ibge_ocupados_uf_atividade` e as sete
-- MAGIC dimensões do notebook 06.
-- MAGIC
-- MAGIC **Escreve:** `gold.fato_resposta_pesquisa`, `gold.fato_teletrabalho_uf`, `gold.fato_ocupacao_uf_atividade` e as
-- MAGIC linhas `C15.*` de `gold.verificacoes_qualidade` e do histórico por execução.
-- MAGIC
-- MAGIC **Por quê:** cada fato registra um processo diferente, com grão próprio. As duas fontes não se somam (uma é
-- MAGIC resposta individual autosselecionada, a outra é estimativa populacional ponderada), então ficam em fatos separados.
-- MAGIC
-- MAGIC ## Grão de cada fato
-- MAGIC
-- MAGIC - **`fato_resposta_pesquisa`**: uma linha por respondente da Stack Overflow Developer Survey em uma safra.
-- MAGIC - **`fato_teletrabalho_uf`**: uma linha por território (Brasil ou UF) e modalidade de trabalho remoto ou
-- MAGIC   teletrabalho, na estimativa da PNAD Contínua de 2022 (4º trimestre).
-- MAGIC - **`fato_ocupacao_uf_atividade`**: uma linha por UF, trimestre e grupamento de atividade econômica, na estimativa
-- MAGIC   de pessoas ocupadas da PNAD Contínua.
-- MAGIC
-- MAGIC O carregamento usa `LEFT JOIN` em cada dimensão, sem FK nula. Campo em branco na fonte vai para `-2 / Não informado` (país e
-- MAGIC porte); valor sem par na dimensão vai para `-1 / Desconhecido`. Nenhuma linha se perde.
-- MAGIC
-- MAGIC Verificação C15: o `COUNT(*)` da Silver tem de ser igual ao do fato depois dos `JOIN`. Chave natural repetida numa
-- MAGIC dimensão aumentaria o fato; um `JOIN` interno diminuiria. Também são exigidas zero linhas em `-1` e chave primária única.
-- MAGIC Qualquer falha para o notebook.
-- MAGIC
-- MAGIC Decisões:
-- MAGIC - `safra` e `resposta_id` ficam no fato como dimensões degeneradas, para rastrear até a Silver. Uma
-- MAGIC   `dim_respondente` teria o mesmo grão do fato.
-- MAGIC - `e_profissional`, `empregado`, `autonomo`, `trabalhando` e `remuneracao_outlier` ficam no fato como atributos
-- MAGIC   degenerados; `trabalhando` define a base das views Q1 a Q5. Uma dimensão lixo (junk) só acrescentaria um `JOIN`.
-- MAGIC - `cv_classificacao` e `estimativa_confiavel` ficam no fato de teletrabalho porque descrevem a precisão daquela
-- MAGIC   estimativa.
-- MAGIC
-- MAGIC Tudo com `CREATE OR REPLACE TABLE ... AS SELECT` e `MERGE` por `verificacao_id`, então rodar de novo é seguro.

-- COMMAND ----------

USE CATALOG mafia_office;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## `fato_resposta_pesquisa`

-- COMMAND ----------

CREATE OR REPLACE TABLE gold.fato_resposta_pesquisa AS
SELECT
  COALESCE(p.periodo_chave, -1)  AS periodo_chave,
  COALESCE(g.geo_chave, CASE WHEN r.pais IS NULL THEN -2 ELSE -1 END) AS geo_chave,
  COALESCE(a.arranjo_chave, -1)  AS arranjo_chave,
  COALESCE(pt.porte_chave, CASE WHEN r.porte_empresa_origem IS NULL THEN -2 ELSE -1 END) AS porte_chave,
  COALESCE(pf.perfil_chave, -1)  AS perfil_chave,
  r.safra,
  r.resposta_id,
  r.e_profissional,
  r.empregado,
  r.autonomo,
  r.trabalhando,
  r.remuneracao_outlier,
  1                           AS qtd_respondentes,
  r.remuneracao_usd,
  r.satisfacao_trabalho,
  r.anos_codando
FROM silver.so_respondente r
LEFT JOIN gold.dim_periodo p
  ON p.tipo_periodo = 'ano' AND p.ano = r.safra
LEFT JOIN gold.dim_geografia g
  ON g.nivel = 'pais' AND g.codigo = r.pais
LEFT JOIN gold.dim_arranjo_trabalho a
  ON a.arranjo = r.arranjo_trabalho
LEFT JOIN gold.dim_porte_empresa pt
  ON pt.porte = r.porte_empresa
LEFT JOIN gold.dim_perfil_dev pf
  ON pf.perfil = COALESCE(r.perfil_principal, 'Não informado')
 AND pf.faixa_experiencia = COALESCE(r.faixa_experiencia, 'Não informado');

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## `fato_teletrabalho_uf`

-- COMMAND ----------

CREATE OR REPLACE TABLE gold.fato_teletrabalho_uf AS
SELECT
  COALESCE(p.periodo_chave, -1)    AS periodo_chave,
  COALESCE(g.geo_chave, -1)        AS geo_chave,
  COALESCE(m.modalidade_chave, -1) AS modalidade_chave,
  t.pessoas_mil,
  t.pessoas_mil_sinal,
  t.cv_pessoas,
  t.cv_pessoas_sinal,
  t.cv_pessoas_classificacao,
  t.percentual,
  t.percentual_sinal,
  t.cv_percentual,
  t.cv_percentual_sinal,
  t.cv_classificacao,
  t.estimativa_confiavel,
  t.disponivel_no_nivel
FROM silver.ibge_teletrabalho_uf t
LEFT JOIN gold.dim_periodo p
  ON p.tipo_periodo = 'ano' AND p.ano = t.ano
LEFT JOIN gold.dim_geografia g
  ON (t.nivel_territorial = 'pais' AND g.nivel = 'pais' AND g.codigo = 'Brazil')
  OR (t.nivel_territorial = 'uf' AND g.nivel = 'uf' AND g.codigo = t.uf_codigo)
LEFT JOIN gold.dim_modalidade_ibge m
  ON m.modalidade_codigo = t.modalidade_codigo;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## `fato_ocupacao_uf_atividade`

-- COMMAND ----------

CREATE OR REPLACE TABLE gold.fato_ocupacao_uf_atividade AS
SELECT
  COALESCE(p.periodo_chave, -1)   AS periodo_chave,
  COALESCE(g.geo_chave, -1)       AS geo_chave,
  COALESCE(a.atividade_chave, -1) AS atividade_chave,
  o.pessoas_mil,
  o.pessoas_mil_sinal
FROM silver.ibge_ocupados_uf_atividade o
LEFT JOIN gold.dim_periodo p
  ON p.tipo_periodo = 'trimestre' AND p.ano = o.ano AND p.trimestre = o.trimestre
LEFT JOIN gold.dim_geografia g
  ON g.nivel = 'uf' AND g.codigo = o.uf_codigo
LEFT JOIN gold.dim_atividade_economica a
  ON a.codigo = o.atividade_codigo;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## C15: preservação de contagem e ausência de FK nula

-- COMMAND ----------

CREATE TABLE IF NOT EXISTS gold.verificacoes_qualidade (
  verificacao_id STRING,
  camada STRING,
  tabela STRING,
  atributo STRING,
  dimensao_qualidade STRING,
  dimensao_dama STRING,
  resultado STRING,
  valor_medido STRING,
  linhas_afetadas BIGINT,
  classificacao STRING,
  tipo_regra STRING,
  severidade STRING,
  tratamento STRING,
  executado_em TIMESTAMP
)
USING DELTA;

-- COMMAND ----------

CREATE OR REPLACE TEMP VIEW _contagens_fatos AS
SELECT 'C15.1' AS verificacao_id,
       'silver.so_respondente → gold.fato_resposta_pesquisa' AS tabela,
       (SELECT COUNT(*) FROM silver.so_respondente) AS linhas_silver,
       (SELECT COUNT(*) FROM gold.fato_resposta_pesquisa) AS linhas_fato,
       (SELECT COUNT_IF(periodo_chave = -1 OR geo_chave = -1 OR arranjo_chave = -1 OR porte_chave = -1 OR perfil_chave = -1)
          FROM gold.fato_resposta_pesquisa) AS linhas_com_desconhecido,
       (SELECT COUNT_IF(periodo_chave IS NULL OR geo_chave IS NULL OR arranjo_chave IS NULL OR porte_chave IS NULL OR perfil_chave IS NULL)
          FROM gold.fato_resposta_pesquisa) AS linhas_fk_nula,
       (SELECT COUNT(*) - COUNT(DISTINCT safra, resposta_id) FROM gold.fato_resposta_pesquisa) AS linhas_chave_repetida
UNION ALL
SELECT 'C15.2',
       'silver.ibge_teletrabalho_uf → gold.fato_teletrabalho_uf',
       (SELECT COUNT(*) FROM silver.ibge_teletrabalho_uf),
       (SELECT COUNT(*) FROM gold.fato_teletrabalho_uf),
       (SELECT COUNT_IF(periodo_chave = -1 OR geo_chave = -1 OR modalidade_chave = -1) FROM gold.fato_teletrabalho_uf),
       (SELECT COUNT_IF(periodo_chave IS NULL OR geo_chave IS NULL OR modalidade_chave IS NULL) FROM gold.fato_teletrabalho_uf),
       (SELECT COUNT(*) - COUNT(DISTINCT periodo_chave, geo_chave, modalidade_chave) FROM gold.fato_teletrabalho_uf)
UNION ALL
SELECT 'C15.3',
       'silver.ibge_ocupados_uf_atividade → gold.fato_ocupacao_uf_atividade',
       (SELECT COUNT(*) FROM silver.ibge_ocupados_uf_atividade),
       (SELECT COUNT(*) FROM gold.fato_ocupacao_uf_atividade),
       (SELECT COUNT_IF(periodo_chave = -1 OR geo_chave = -1 OR atividade_chave = -1) FROM gold.fato_ocupacao_uf_atividade),
       (SELECT COUNT_IF(periodo_chave IS NULL OR geo_chave IS NULL OR atividade_chave IS NULL) FROM gold.fato_ocupacao_uf_atividade),
       (SELECT COUNT(*) - COUNT(DISTINCT periodo_chave, geo_chave, atividade_chave) FROM gold.fato_ocupacao_uf_atividade);

-- COMMAND ----------

CREATE OR REPLACE TEMP VIEW _verificacoes_07 AS
  SELECT
    verificacao_id,
    'gold' AS camada,
    tabela,
    'COUNT(*), chave primária e chaves estrangeiras' AS atributo,
    'Integridade' AS dimensao_qualidade,
    'Completude' AS dimensao_dama,
    CASE WHEN linhas_silver = linhas_fato AND linhas_fk_nula = 0 AND linhas_com_desconhecido = 0 AND linhas_chave_repetida = 0
         THEN 'aprovado' ELSE 'reprovado' END AS resultado,
    CONCAT('medido: silver ', linhas_silver, ', fato ', linhas_fato,
           ', linhas com alguma FK -1 ', linhas_com_desconhecido, ', linhas com FK nula ', linhas_fk_nula,
           ', linhas com chave primária repetida ', linhas_chave_repetida,
           ' | esperado: contagens idênticas, 0 FK nula, 0 FK -1 (membro -2 Não informado é permitido) e chave primária única') AS valor_medido,
    CAST(ABS(linhas_silver - linhas_fato) AS BIGINT) AS linhas_afetadas,
    'guarda_defensiva' AS classificacao,
    'regra' AS tipo_regra,
    'alta' AS severidade,
    'Membros -1 e -2 nas dimensões e LEFT JOIN com COALESCE; chave natural única verificada no notebook 06.' AS tratamento,
    current_timestamp() AS executado_em
  FROM _contagens_fatos;

-- COMMAND ----------

-- MAGIC %python
-- MAGIC from historico_qualidade import persistir_historico
-- MAGIC
-- MAGIC dbutils.widgets.text("job_run_id", "manual", "Id da execução do job")
-- MAGIC job_run_id = persistir_historico(
-- MAGIC     spark, spark.table("_verificacoes_07"), dbutils.widgets.get("job_run_id")
-- MAGIC )

-- COMMAND ----------

MERGE INTO gold.verificacoes_qualidade AS t
USING _verificacoes_07 AS s
ON t.verificacao_id = s.verificacao_id
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
WHEN NOT MATCHED BY SOURCE AND t.camada = 'gold' THEN DELETE;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Chaves primárias e estrangeiras dos fatos
-- MAGIC
-- MAGIC A chave primária de cada fato é o próprio grão: `(safra, resposta_id)` na pesquisa e a combinação das chaves de
-- MAGIC dimensão nas duas tabelas do IBGE. As chaves estrangeiras fazem o Catalog Explorer desenhar o diagrama de
-- MAGIC relacionamento. São informativas; quem garante a integridade é a C15, logo acima.

-- COMMAND ----------

ALTER TABLE gold.fato_resposta_pesquisa ALTER COLUMN arranjo_chave SET NOT NULL;
ALTER TABLE gold.fato_resposta_pesquisa ALTER COLUMN geo_chave SET NOT NULL;
ALTER TABLE gold.fato_resposta_pesquisa ALTER COLUMN perfil_chave SET NOT NULL;
ALTER TABLE gold.fato_resposta_pesquisa ALTER COLUMN periodo_chave SET NOT NULL;
ALTER TABLE gold.fato_resposta_pesquisa ALTER COLUMN porte_chave SET NOT NULL;
ALTER TABLE gold.fato_resposta_pesquisa ALTER COLUMN resposta_id SET NOT NULL;
ALTER TABLE gold.fato_resposta_pesquisa ALTER COLUMN safra SET NOT NULL;
ALTER TABLE gold.fato_resposta_pesquisa DROP CONSTRAINT IF EXISTS pk_fato_resposta_pesquisa;
ALTER TABLE gold.fato_resposta_pesquisa ADD CONSTRAINT pk_fato_resposta_pesquisa PRIMARY KEY (safra, resposta_id) RELY;
ALTER TABLE gold.fato_resposta_pesquisa DROP CONSTRAINT IF EXISTS fk_resposta_periodo;
ALTER TABLE gold.fato_resposta_pesquisa ADD CONSTRAINT fk_resposta_periodo FOREIGN KEY (periodo_chave) REFERENCES gold.dim_periodo (periodo_chave);
ALTER TABLE gold.fato_resposta_pesquisa DROP CONSTRAINT IF EXISTS fk_resposta_geografia;
ALTER TABLE gold.fato_resposta_pesquisa ADD CONSTRAINT fk_resposta_geografia FOREIGN KEY (geo_chave) REFERENCES gold.dim_geografia (geo_chave);
ALTER TABLE gold.fato_resposta_pesquisa DROP CONSTRAINT IF EXISTS fk_resposta_arranjo_trabalho;
ALTER TABLE gold.fato_resposta_pesquisa ADD CONSTRAINT fk_resposta_arranjo_trabalho FOREIGN KEY (arranjo_chave) REFERENCES gold.dim_arranjo_trabalho (arranjo_chave);
ALTER TABLE gold.fato_resposta_pesquisa DROP CONSTRAINT IF EXISTS fk_resposta_porte_empresa;
ALTER TABLE gold.fato_resposta_pesquisa ADD CONSTRAINT fk_resposta_porte_empresa FOREIGN KEY (porte_chave) REFERENCES gold.dim_porte_empresa (porte_chave);
ALTER TABLE gold.fato_resposta_pesquisa DROP CONSTRAINT IF EXISTS fk_resposta_perfil_dev;
ALTER TABLE gold.fato_resposta_pesquisa ADD CONSTRAINT fk_resposta_perfil_dev FOREIGN KEY (perfil_chave) REFERENCES gold.dim_perfil_dev (perfil_chave);

ALTER TABLE gold.fato_teletrabalho_uf ALTER COLUMN geo_chave SET NOT NULL;
ALTER TABLE gold.fato_teletrabalho_uf ALTER COLUMN modalidade_chave SET NOT NULL;
ALTER TABLE gold.fato_teletrabalho_uf ALTER COLUMN periodo_chave SET NOT NULL;
ALTER TABLE gold.fato_teletrabalho_uf DROP CONSTRAINT IF EXISTS pk_fato_teletrabalho_uf;
ALTER TABLE gold.fato_teletrabalho_uf ADD CONSTRAINT pk_fato_teletrabalho_uf PRIMARY KEY (periodo_chave, geo_chave, modalidade_chave) RELY;
ALTER TABLE gold.fato_teletrabalho_uf DROP CONSTRAINT IF EXISTS fk_teletrabalho_periodo;
ALTER TABLE gold.fato_teletrabalho_uf ADD CONSTRAINT fk_teletrabalho_periodo FOREIGN KEY (periodo_chave) REFERENCES gold.dim_periodo (periodo_chave);
ALTER TABLE gold.fato_teletrabalho_uf DROP CONSTRAINT IF EXISTS fk_teletrabalho_geografia;
ALTER TABLE gold.fato_teletrabalho_uf ADD CONSTRAINT fk_teletrabalho_geografia FOREIGN KEY (geo_chave) REFERENCES gold.dim_geografia (geo_chave);
ALTER TABLE gold.fato_teletrabalho_uf DROP CONSTRAINT IF EXISTS fk_teletrabalho_modalidade_ibge;
ALTER TABLE gold.fato_teletrabalho_uf ADD CONSTRAINT fk_teletrabalho_modalidade_ibge FOREIGN KEY (modalidade_chave) REFERENCES gold.dim_modalidade_ibge (modalidade_chave);

ALTER TABLE gold.fato_ocupacao_uf_atividade ALTER COLUMN atividade_chave SET NOT NULL;
ALTER TABLE gold.fato_ocupacao_uf_atividade ALTER COLUMN geo_chave SET NOT NULL;
ALTER TABLE gold.fato_ocupacao_uf_atividade ALTER COLUMN periodo_chave SET NOT NULL;
ALTER TABLE gold.fato_ocupacao_uf_atividade DROP CONSTRAINT IF EXISTS pk_fato_ocupacao_uf_atividade;
ALTER TABLE gold.fato_ocupacao_uf_atividade ADD CONSTRAINT pk_fato_ocupacao_uf_atividade PRIMARY KEY (periodo_chave, geo_chave, atividade_chave) RELY;
ALTER TABLE gold.fato_ocupacao_uf_atividade DROP CONSTRAINT IF EXISTS fk_ocupacao_periodo;
ALTER TABLE gold.fato_ocupacao_uf_atividade ADD CONSTRAINT fk_ocupacao_periodo FOREIGN KEY (periodo_chave) REFERENCES gold.dim_periodo (periodo_chave);
ALTER TABLE gold.fato_ocupacao_uf_atividade DROP CONSTRAINT IF EXISTS fk_ocupacao_geografia;
ALTER TABLE gold.fato_ocupacao_uf_atividade ADD CONSTRAINT fk_ocupacao_geografia FOREIGN KEY (geo_chave) REFERENCES gold.dim_geografia (geo_chave);
ALTER TABLE gold.fato_ocupacao_uf_atividade DROP CONSTRAINT IF EXISTS fk_ocupacao_atividade_economica;
ALTER TABLE gold.fato_ocupacao_uf_atividade ADD CONSTRAINT fk_ocupacao_atividade_economica FOREIGN KEY (atividade_chave) REFERENCES gold.dim_atividade_economica (atividade_chave);

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Regras de domínio nos fatos
-- MAGIC
-- MAGIC As mesmas faixas da Silver, gravadas também nos fatos.

-- COMMAND ----------

ALTER TABLE gold.fato_resposta_pesquisa DROP CONSTRAINT IF EXISTS ck_fato_resposta_qtd;
ALTER TABLE gold.fato_resposta_pesquisa ADD CONSTRAINT ck_fato_resposta_qtd CHECK (qtd_respondentes = 1);
ALTER TABLE gold.fato_resposta_pesquisa DROP CONSTRAINT IF EXISTS ck_fato_resposta_satisfacao;
ALTER TABLE gold.fato_resposta_pesquisa ADD CONSTRAINT ck_fato_resposta_satisfacao CHECK (satisfacao_trabalho IS NULL OR satisfacao_trabalho BETWEEN 0 AND 10);
ALTER TABLE gold.fato_resposta_pesquisa DROP CONSTRAINT IF EXISTS ck_fato_resposta_anos_codando;
ALTER TABLE gold.fato_resposta_pesquisa ADD CONSTRAINT ck_fato_resposta_anos_codando CHECK (anos_codando IS NULL OR anos_codando BETWEEN 0 AND 50);
ALTER TABLE gold.fato_resposta_pesquisa DROP CONSTRAINT IF EXISTS ck_fato_resposta_remuneracao;
ALTER TABLE gold.fato_resposta_pesquisa ADD CONSTRAINT ck_fato_resposta_remuneracao CHECK (remuneracao_usd IS NULL OR remuneracao_usd >= 0);
ALTER TABLE gold.fato_teletrabalho_uf DROP CONSTRAINT IF EXISTS ck_fato_teletrabalho_percentual;
ALTER TABLE gold.fato_teletrabalho_uf ADD CONSTRAINT ck_fato_teletrabalho_percentual CHECK (percentual IS NULL OR percentual BETWEEN 0 AND 100);
ALTER TABLE gold.fato_teletrabalho_uf DROP CONSTRAINT IF EXISTS ck_fato_teletrabalho_pessoas;
ALTER TABLE gold.fato_teletrabalho_uf ADD CONSTRAINT ck_fato_teletrabalho_pessoas CHECK (pessoas_mil IS NULL OR pessoas_mil >= 0);
ALTER TABLE gold.fato_ocupacao_uf_atividade DROP CONSTRAINT IF EXISTS ck_fato_ocupacao_pessoas;
ALTER TABLE gold.fato_ocupacao_uf_atividade ADD CONSTRAINT ck_fato_ocupacao_pessoas CHECK (pessoas_mil IS NULL OR pessoas_mil >= 0);

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Resultado da C15
-- MAGIC

-- COMMAND ----------

SELECT *,
       CASE WHEN linhas_silver <> linhas_fato OR linhas_fk_nula <> 0 OR linhas_com_desconhecido <> 0 OR linhas_chave_repetida <> 0
            THEN raise_error(CONCAT('Integridade referencial falhou em ', verificacao_id, ': ', tabela)) END AS falha
FROM _contagens_fatos
ORDER BY verificacao_id;
