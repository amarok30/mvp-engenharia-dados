-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 00 · Configuração do catálogo
-- MAGIC
-- MAGIC **Lê:** nada.
-- MAGIC
-- MAGIC **Escreve:** catálogo `mafia_office`, schemas `bronze`, `silver`, `gold` e o Volume `bronze.pouso`.
-- MAGIC
-- MAGIC **Por quê:** o Unity Catalog organiza o lakehouse em catálogo, schema e objeto. Cada camada vira um schema, e o
-- MAGIC Volume é a área de pouso dos arquivos brutos, lidos pelos notebooks 01 e 02.
-- MAGIC
-- MAGIC Tudo usa `IF NOT EXISTS`, então rodar de novo não altera nada.
-- MAGIC
-- MAGIC Depois deste notebook, os arquivos são enviados pela interface (Catalog > mafia_office > bronze > pouso > Upload) os arquivos
-- MAGIC baixados por `scripts/baixar_fontes.sh`, nesta estrutura:
-- MAGIC
-- MAGIC ```
-- MAGIC /Volumes/mafia_office/bronze/pouso/stackoverflow/2022/results.csv   (e schema.csv)
-- MAGIC /Volumes/mafia_office/bronze/pouso/stackoverflow/2023/...
-- MAGIC /Volumes/mafia_office/bronze/pouso/stackoverflow/2024/...
-- MAGIC /Volumes/mafia_office/bronze/pouso/stackoverflow/2025/...
-- MAGIC /Volumes/mafia_office/bronze/pouso/ibge/sidra_9471.json
-- MAGIC /Volumes/mafia_office/bronze/pouso/ibge/sidra_5434.json
-- MAGIC /Volumes/mafia_office/bronze/pouso/referencia/mapa-de-para-arranjo.csv
-- MAGIC ```
-- MAGIC
-- MAGIC Os quatro `results.csv` têm o mesmo nome. Antes do upload, devem ser criadas as pastas
-- MAGIC (*Create directory*) `stackoverflow/2022` a `stackoverflow/2025`, `ibge` e `referencia`. A pasta `exportacao/` é
-- MAGIC criada durante a execução do pipeline.
-- MAGIC
-- MAGIC O de-para fica no Volume, em `referencia/`, para que a carga use o mesmo caminho no compute serverless.

-- COMMAND ----------

CREATE CATALOG IF NOT EXISTS mafia_office
COMMENT 'MVP de Engenharia de Dados: pipeline sobre dados públicos (Stack Overflow Developer Survey e IBGE/SIDRA) com perguntas motivadas pelo Mafia Office. Uso acadêmico, não comercial.';

-- COMMAND ----------

USE CATALOG mafia_office;

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS bronze
COMMENT 'Camada Bronze: dado como a fonte entregou, sem conversão de tipo, sem descarte de coluna, sem limpeza. Acrescenta apenas colunas de auditoria.';

CREATE SCHEMA IF NOT EXISTS silver
COMMENT 'Camada Silver: dado validado, tipado, normalizado e harmonizado entre safras, no grão do registro de origem. Sem agregação e sem modelo estrela.';

CREATE SCHEMA IF NOT EXISTS gold
COMMENT 'Camada Gold: modelo dimensional (fatos de processos distintos ligadas por dimensões conformadas), views por pergunta de negócio e resultado das verificações de qualidade.';

-- COMMAND ----------

CREATE VOLUME IF NOT EXISTS bronze.pouso
COMMENT 'Área de pouso dos arquivos brutos enviados por upload: stackoverflow/{ano}/results.csv e schema.csv, ibge/sidra_9471.json e sidra_5434.json, referencia/mapa-de-para-arranjo.csv.';

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Verificação
-- MAGIC

-- COMMAND ----------

SHOW SCHEMAS IN mafia_office;

-- COMMAND ----------

SHOW VOLUMES IN mafia_office.bronze;
