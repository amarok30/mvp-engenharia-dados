-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 06 · Gold: dimensões
-- MAGIC
-- MAGIC **Lê:** `silver.so_respondente`, `silver.so_de_para_arranjo`, `silver.ibge_teletrabalho_uf`,
-- MAGIC `silver.ibge_ocupados_uf_atividade`.
-- MAGIC
-- MAGIC **Escreve:** sete dimensões em `gold`: `dim_periodo`, `dim_geografia`, `dim_arranjo_trabalho`, `dim_porte_empresa`,
-- MAGIC `dim_perfil_dev`, `dim_modalidade_ibge`, `dim_atividade_economica`.
-- MAGIC
-- MAGIC **Por quê:** é aqui que o dado vira modelo dimensional. São três fatos de processos diferentes (resposta à
-- MAGIC pesquisa, estimativa de teletrabalho, estimativa de ocupação) ligados por duas dimensões conformadas,
-- MAGIC `dim_periodo` e `dim_geografia`, definidas uma vez e usadas pelos três.
-- MAGIC
-- MAGIC `dim_arranjo_trabalho` (Stack Overflow: remoto, híbrido, presencial, flexível) e `dim_modalidade_ibge` (IBGE:
-- MAGIC trabalho remoto, teletrabalho, no domicílio, fora do domicílio) ficam separadas. As definições são diferentes, e
-- MAGIC juntar as duas numa dimensão só daria um número que não existe.
-- MAGIC
-- MAGIC Membros especiais: toda dimensão tem a linha `-1 / Desconhecido`, usada quando a busca na dimensão falha.
-- MAGIC `dim_geografia` e `dim_porte_empresa` também têm `-2 / Não informado`, para quem deixou o campo em branco. A regra
-- MAGIC de não ter FK nula no fato é do Kimball Group; os valores `-1` e `-2` são convenção do projeto. Separar os dois casos
-- MAGIC deixa a verificação C15 exigir zero linhas em `-1`.
-- MAGIC
-- MAGIC Chaves substitutas determinísticas, para que rodar de novo gere as mesmas chaves:
-- MAGIC - `dim_periodo`: `ano × 10` para ano (2022 vira 20220) e `ano × 10 + trimestre` para trimestre (2022T4 vira 20224).
-- MAGIC - `dim_arranjo_trabalho` e `dim_porte_empresa`: a ordem canônica da categoria (1 a 9).
-- MAGIC - `dim_geografia`, `dim_perfil_dev`, `dim_modalidade_ibge` e `dim_atividade_economica`: `xxhash64` da chave natural,
-- MAGIC   levado para inteiro não negativo. Com `ROW_NUMBER()`, um membro novo (um país novo em 2026, por exemplo) mudaria
-- MAGIC   todas as chaves. Os membros -1 e -2 são negativos e não colidem com o hash. A checagem no fim do notebook para a
-- MAGIC   execução se duas chaves naturais gerarem o mesmo hash.
-- MAGIC
-- MAGIC Decisões:
-- MAGIC - `dim_geografia` usa o nome do país em inglês, como vem da pesquisa, e `pais_nome = 'Brazil'` nas UFs. Assim o
-- MAGIC   Brasil das duas fontes se encontra sem traduzir nomes de país.
-- MAGIC - `uf_sigla` e `regiao` vêm de uma tabela de referência embutida (o primeiro dígito do código é a grande região),
-- MAGIC   porque a API não devolve esses atributos.
-- MAGIC - `dim_porte_empresa.faixa_min` fica nulo em `Menos de 20`, porque 2025 não informa o piso da faixa fundida.
-- MAGIC - `dim_perfil_dev` recebe `Não informado` quando `perfil` ou `faixa_experiencia` é nulo, porque o par é a chave
-- MAGIC   natural; `-1` fica só para falha de busca.
-- MAGIC - `dim_modalidade_ibge.e_teletrabalho` é verdadeiro para `c1675` 59805 a 59808 (teletrabalho e seus recortes por
-- MAGIC   local). 59803 é o total e 59804 é trabalho remoto, conceito mais amplo.
-- MAGIC - `dim_modalidade_ibge.modalidade_pai_codigo` guarda a hierarquia medida na verificação C23: 59804 está contido em
-- MAGIC   59803, 59805 em 59804, e 59806, 59807 e 59808 em 59805, com 59806 e 59807 sobrepostos em 59808. Modalidades não se
-- MAGIC   somam.
-- MAGIC - `dim_atividade_economica.e_total` (47946) e `e_subgrupamento` (60031, Indústria de transformação, contida em 47948,
-- MAGIC   Indústria geral) vêm da verificação C24; somas de ocupação excluem os dois.
-- MAGIC - `dim_modalidade_ibge` tem `modalidade_codigo` para filtrar por código, não por texto.
-- MAGIC
-- MAGIC Tudo com `CREATE OR REPLACE TABLE ... AS SELECT`, então rodar de novo é seguro.

-- COMMAND ----------

USE CATALOG mafia_office;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Antes de recriar as dimensões
-- MAGIC
-- MAGIC Os fatos têm chave estrangeira para as dimensões (notebook 07), e o Unity Catalog não deixa recriar uma
-- MAGIC dimensão referenciada. Por isso tiro só as chaves estrangeiras. Os fatos continuam existindo, com o histórico do
-- MAGIC Delta, e o 07 recria as chaves.

-- COMMAND ----------

-- MAGIC %python
-- MAGIC CHAVES_ESTRANGEIRAS = {
-- MAGIC     "fato_resposta_pesquisa": ["fk_resposta_periodo", "fk_resposta_geografia", "fk_resposta_arranjo_trabalho",
-- MAGIC                                "fk_resposta_porte_empresa", "fk_resposta_perfil_dev"],
-- MAGIC     "fato_teletrabalho_uf": ["fk_teletrabalho_periodo", "fk_teletrabalho_geografia", "fk_teletrabalho_modalidade_ibge"],
-- MAGIC     "fato_ocupacao_uf_atividade": ["fk_ocupacao_periodo", "fk_ocupacao_geografia", "fk_ocupacao_atividade_economica"],
-- MAGIC }
-- MAGIC for fato, chaves in CHAVES_ESTRANGEIRAS.items():
-- MAGIC     if spark.catalog.tableExists(f"mafia_office.gold.{fato}"):
-- MAGIC         for chave in chaves:
-- MAGIC             spark.sql(f"ALTER TABLE mafia_office.gold.{fato} DROP CONSTRAINT IF EXISTS {chave}")

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## `dim_periodo` (conformada)

-- COMMAND ----------

CREATE OR REPLACE TABLE gold.dim_periodo AS
WITH anos AS (
  SELECT DISTINCT safra AS ano FROM silver.so_respondente
  UNION
  SELECT DISTINCT ano FROM silver.ibge_teletrabalho_uf
),
trimestres AS (
  SELECT DISTINCT ano, trimestre FROM silver.ibge_ocupados_uf_atividade
)
SELECT CAST(ano * 10 AS INT) AS periodo_chave, 'ano' AS tipo_periodo, CAST(ano AS INT) AS ano,
       CAST(NULL AS INT) AS trimestre, CAST(ano AS STRING) AS rotulo
FROM anos
UNION ALL
SELECT CAST(ano * 10 + trimestre AS INT), 'trimestre', CAST(ano AS INT), CAST(trimestre AS INT),
       CONCAT(CAST(ano AS STRING), 'T', CAST(trimestre AS STRING))
FROM trimestres
UNION ALL
SELECT -1, 'Desconhecido', CAST(NULL AS INT), CAST(NULL AS INT), 'Desconhecido';

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## `dim_geografia` (conformada)

-- COMMAND ----------

CREATE OR REPLACE TABLE gold.dim_geografia AS
WITH referencia_uf AS (
  SELECT * FROM VALUES ('11','RO'), ('12','AC'), ('13','AM'), ('14','RR'), ('15','PA'), ('16','AP'), ('17','TO'),
         ('21','MA'), ('22','PI'), ('23','CE'), ('24','RN'), ('25','PB'), ('26','PE'), ('27','AL'), ('28','SE'), ('29','BA'),
         ('31','MG'), ('32','ES'), ('33','RJ'), ('35','SP'),
         ('41','PR'), ('42','SC'), ('43','RS'),
         ('50','MS'), ('51','MT'), ('52','GO'), ('53','DF')
  AS t(codigo, uf_sigla)
),
referencia_regiao AS (
  SELECT * FROM VALUES ('1','Norte'), ('2','Nordeste'), ('3','Sudeste'), ('4','Sul'), ('5','Centro-Oeste')
  AS t(digito, regiao)
),
ufs AS (
  SELECT uf_codigo AS codigo, MIN(uf_nome) AS nome
  FROM (
    SELECT uf_codigo, uf_nome FROM silver.ibge_ocupados_uf_atividade
    UNION ALL
    SELECT uf_codigo, uf_nome FROM silver.ibge_teletrabalho_uf WHERE nivel_territorial = 'uf'
  )
  GROUP BY uf_codigo
),
paises AS (
  SELECT DISTINCT pais AS codigo FROM silver.so_respondente WHERE pais IS NOT NULL
  UNION
  SELECT 'Brazil'
),
base AS (
  SELECT 'pais' AS nivel, codigo, codigo AS nome, codigo AS pais_nome,
         CAST(NULL AS STRING) AS uf_sigla, CAST(NULL AS STRING) AS regiao
  FROM paises
  UNION ALL
  SELECT 'uf', u.codigo, u.nome, 'Brazil', r.uf_sigla, g.regiao
  FROM ufs u
  LEFT JOIN referencia_uf r ON r.codigo = u.codigo
  LEFT JOIN referencia_regiao g ON g.digito = SUBSTRING(u.codigo, 1, 1)
)
SELECT CAST(pmod(xxhash64(nivel, codigo), 9223372036854775807) AS BIGINT) AS geo_chave, nivel, codigo, nome, pais_nome, uf_sigla, regiao
FROM base
UNION ALL
SELECT -1, 'Desconhecido', 'Desconhecido', 'Desconhecido', 'Desconhecido', CAST(NULL AS STRING), CAST(NULL AS STRING)
UNION ALL
SELECT -2, 'pais', 'Não informado', 'Não informado', 'Não informado', CAST(NULL AS STRING), CAST(NULL AS STRING);

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## `dim_arranjo_trabalho`

-- COMMAND ----------

CREATE OR REPLACE TABLE gold.dim_arranjo_trabalho AS
WITH categorias AS (
  SELECT valor_canonico AS arranjo, BOOL_AND(entra_serie_historica) AS entra_serie_historica
  FROM silver.so_de_para_arranjo
  GROUP BY valor_canonico
)
SELECT CAST(ordem AS INT) AS arranjo_chave, arranjo, entra_serie_historica, CAST(ordem AS INT) AS ordem
FROM (
  SELECT arranjo, entra_serie_historica,
         CASE arranjo WHEN 'Remoto' THEN 1 WHEN 'Híbrido' THEN 2 WHEN 'Presencial' THEN 3
                      WHEN 'Flexível' THEN 4 WHEN 'Não informado' THEN 5 END AS ordem
  FROM categorias
)
UNION ALL
SELECT -1, 'Desconhecido', false, 99;

-- COMMAND ----------

-- Guarda: categoria do de-para sem ordem canônica ficaria com chave nula.
SELECT CASE WHEN COUNT(*) > 0
            THEN raise_error('dim_arranjo_trabalho: categoria do de-para sem ordem canônica; atualize o CASE acima')
            ELSE 'ok: todas as categorias com ordem' END AS verificacao
FROM gold.dim_arranjo_trabalho WHERE arranjo_chave IS NULL;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## `dim_porte_empresa`

-- COMMAND ----------

CREATE OR REPLACE TABLE gold.dim_porte_empresa AS
SELECT CAST(ordem AS INT) AS porte_chave, porte, CAST(ordem AS INT) AS ordem,
       CAST(faixa_min AS INT) AS faixa_min, CAST(faixa_max AS INT) AS faixa_max
FROM VALUES
  ('Autônomo',        1, 1,     1),
  ('Menos de 20',     2, NULL,  19),
  ('20 a 99',         3, 20,    99),
  ('100 a 499',       4, 100,   499),
  ('500 a 999',       5, 500,   999),
  ('1.000 a 4.999',   6, 1000,  4999),
  ('5.000 a 9.999',   7, 5000,  9999),
  ('10.000 ou mais',  8, 10000, NULL),
  ('Não sabe',        9, NULL,  NULL)
AS t(porte, ordem, faixa_min, faixa_max)
UNION ALL
SELECT -1, 'Desconhecido', 99, CAST(NULL AS INT), CAST(NULL AS INT)
UNION ALL
SELECT -2, 'Não informado', 98, CAST(NULL AS INT), CAST(NULL AS INT);

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## `dim_perfil_dev`

-- COMMAND ----------

CREATE OR REPLACE TABLE gold.dim_perfil_dev AS
WITH perfis AS (
  SELECT DISTINCT
    COALESCE(perfil_principal, 'Não informado') AS perfil,
    COALESCE(faixa_experiencia, 'Não informado') AS faixa_experiencia
  FROM silver.so_respondente
)
SELECT CAST(pmod(xxhash64(perfil, faixa_experiencia), 9223372036854775807) AS BIGINT) AS perfil_chave, perfil, faixa_experiencia
FROM perfis
UNION ALL
SELECT -1, 'Desconhecido', 'Desconhecido';

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## `dim_modalidade_ibge`

-- COMMAND ----------

CREATE OR REPLACE TABLE gold.dim_modalidade_ibge AS
WITH modalidades AS (
  SELECT modalidade_codigo, MIN(modalidade) AS modalidade
  FROM silver.ibge_teletrabalho_uf
  GROUP BY modalidade_codigo
)
SELECT CAST(pmod(xxhash64(modalidade_codigo), 9223372036854775807) AS BIGINT) AS modalidade_chave,
       modalidade,
       modalidade_codigo IN ('59805', '59806', '59807', '59808') AS e_teletrabalho,
       modalidade_codigo,
       CASE modalidade_codigo
         WHEN '59804' THEN '59803'
         WHEN '59805' THEN '59804'
         WHEN '59806' THEN '59805'
         WHEN '59807' THEN '59805'
         WHEN '59808' THEN '59805'
       END AS modalidade_pai_codigo
FROM modalidades
UNION ALL
SELECT -1, 'Desconhecido', false, 'Desconhecido', CAST(NULL AS STRING);

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## `dim_atividade_economica`

-- COMMAND ----------

CREATE OR REPLACE TABLE gold.dim_atividade_economica AS
WITH atividades AS (
  SELECT atividade_codigo AS codigo, MIN(atividade_nome) AS nome, BOOL_OR(e_proxy_tecnologia) AS e_proxy_tecnologia
  FROM silver.ibge_ocupados_uf_atividade
  GROUP BY atividade_codigo
)
SELECT CAST(pmod(xxhash64(codigo), 9223372036854775807) AS BIGINT) AS atividade_chave, codigo, nome, e_proxy_tecnologia,
       codigo = '47946' AS e_total,
       codigo = '60031' AS e_subgrupamento
FROM atividades
UNION ALL
SELECT -1, 'Desconhecido', 'Desconhecido', false, false, false;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Checagem: chave natural única, chave substituta única e membro `-1` em todas
-- MAGIC

-- COMMAND ----------

WITH resumo AS (
  SELECT 'dim_periodo' AS dimensao, COUNT(*) AS linhas, COUNT_IF(periodo_chave = -1) AS membro_desconhecido,
         COUNT(*) - COUNT(DISTINCT periodo_chave) AS chaves_repetidas, 0 AS colisoes_hash FROM gold.dim_periodo
  UNION ALL
  SELECT 'dim_geografia', COUNT(*), COUNT_IF(geo_chave = -1), COUNT(*) - COUNT(DISTINCT nivel, codigo), COUNT(*) - COUNT(DISTINCT geo_chave) FROM gold.dim_geografia
  UNION ALL
  SELECT 'dim_arranjo_trabalho', COUNT(*), COUNT_IF(arranjo_chave = -1), COUNT(*) - COUNT(DISTINCT arranjo), COUNT(*) - COUNT(DISTINCT arranjo_chave) FROM gold.dim_arranjo_trabalho
  UNION ALL
  SELECT 'dim_porte_empresa', COUNT(*), COUNT_IF(porte_chave = -1), COUNT(*) - COUNT(DISTINCT porte), COUNT(*) - COUNT(DISTINCT porte_chave) FROM gold.dim_porte_empresa
  UNION ALL
  SELECT 'dim_perfil_dev', COUNT(*), COUNT_IF(perfil_chave = -1), COUNT(*) - COUNT(DISTINCT perfil, faixa_experiencia), COUNT(*) - COUNT(DISTINCT perfil_chave) FROM gold.dim_perfil_dev
  UNION ALL
  SELECT 'dim_modalidade_ibge', COUNT(*), COUNT_IF(modalidade_chave = -1), COUNT(*) - COUNT(DISTINCT modalidade_codigo), COUNT(*) - COUNT(DISTINCT modalidade_chave) FROM gold.dim_modalidade_ibge
  UNION ALL
  SELECT 'dim_atividade_economica', COUNT(*), COUNT_IF(atividade_chave = -1), COUNT(*) - COUNT(DISTINCT codigo), COUNT(*) - COUNT(DISTINCT atividade_chave) FROM gold.dim_atividade_economica
)
SELECT *,
       CASE WHEN membro_desconhecido <> 1 OR chaves_repetidas <> 0 OR colisoes_hash <> 0
            THEN raise_error(CONCAT('Dimensão inválida: ', dimensao)) END AS falha
FROM resumo
ORDER BY dimensao;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Chave primária de cada dimensão
-- MAGIC
-- MAGIC No Unity Catalog, chave primária e chave estrangeira são informativas: o Databricks não bloqueia uma escrita que
-- MAGIC as viole, mas usa as restrições no otimizador (com `RELY`) e no diagrama do Catalog Explorer. Quem garante a
-- MAGIC unicidade é a checagem acima. O `NOT NULL` da coluna da chave o Delta aplica em toda escrita.

-- COMMAND ----------

ALTER TABLE gold.dim_periodo ALTER COLUMN periodo_chave SET NOT NULL;
ALTER TABLE gold.dim_periodo ADD CONSTRAINT pk_dim_periodo PRIMARY KEY (periodo_chave) RELY;

ALTER TABLE gold.dim_geografia ALTER COLUMN geo_chave SET NOT NULL;
ALTER TABLE gold.dim_geografia ADD CONSTRAINT pk_dim_geografia PRIMARY KEY (geo_chave) RELY;

ALTER TABLE gold.dim_arranjo_trabalho ALTER COLUMN arranjo_chave SET NOT NULL;
ALTER TABLE gold.dim_arranjo_trabalho ADD CONSTRAINT pk_dim_arranjo_trabalho PRIMARY KEY (arranjo_chave) RELY;

ALTER TABLE gold.dim_porte_empresa ALTER COLUMN porte_chave SET NOT NULL;
ALTER TABLE gold.dim_porte_empresa ADD CONSTRAINT pk_dim_porte_empresa PRIMARY KEY (porte_chave) RELY;

ALTER TABLE gold.dim_perfil_dev ALTER COLUMN perfil_chave SET NOT NULL;
ALTER TABLE gold.dim_perfil_dev ADD CONSTRAINT pk_dim_perfil_dev PRIMARY KEY (perfil_chave) RELY;

ALTER TABLE gold.dim_modalidade_ibge ALTER COLUMN modalidade_chave SET NOT NULL;
ALTER TABLE gold.dim_modalidade_ibge ADD CONSTRAINT pk_dim_modalidade_ibge PRIMARY KEY (modalidade_chave) RELY;

ALTER TABLE gold.dim_atividade_economica ALTER COLUMN atividade_chave SET NOT NULL;
ALTER TABLE gold.dim_atividade_economica ADD CONSTRAINT pk_dim_atividade_economica PRIMARY KEY (atividade_chave) RELY;
