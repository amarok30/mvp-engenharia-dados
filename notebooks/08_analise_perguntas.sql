-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 08 · Análise: uma view por pergunta
-- MAGIC
-- MAGIC **Lê:** tabelas fato e dimensões da Gold.
-- MAGIC
-- MAGIC **Escreve:** nove views (uma por pergunta, mais `gold.vw_q1_remoto_por_vinculo`, sensibilidade da Q1), de
-- MAGIC `gold.vw_q1_evolucao_arranjo` a `gold.vw_q8_mercado_brasil`, com comentário de tabela e de coluna.
-- MAGIC
-- MAGIC **Por quê:** cada pergunta de negócio vira uma view com a pergunta e as premissas no comentário. Assim a resposta
-- MAGIC pode ser consultada sem abrir este notebook, e cada coluna fica documentada no catálogo.
-- MAGIC
-- MAGIC ## Regras das views da pesquisa (Q1 a Q5)
-- MAGIC
-- MAGIC - **Base: quem trabalha** (`trabalhando` = empregado ou autônomo). A pergunta de arranjo não se aplica a estudante,
-- MAGIC   aposentado ou desempregado; pela verificação C02, de 2022 a 2024 o nulo de `RemoteWork` é quase todo desses
-- MAGIC   grupos. Em 2025, 19,8% de quem trabalha também não informou o arranjo. A Q1 mostra também a base de todos os que
-- MAGIC   informaram o arranjo, como sensibilidade.
-- MAGIC - **Percentuais sobre quem informou o arranjo.** `Não informado` e os membros especiais ficam fora.
-- MAGIC - **Mudança no questionário de 2025.** A opção `Your choice` (Flexível) só existe em 2025, e as duas opções de
-- MAGIC   híbrido foram fundidas. Comparações entre safras usam a série comparável (Remoto, Híbrido e Presencial, sem
-- MAGIC   Flexível no denominador). Como não sei como esses respondentes se dividiriam nas opções antigas, a Q1 também
-- MAGIC   mostra limites de sensibilidade para Remoto.
-- MAGIC - **Incerteza.** Proporções têm intervalo de Wilson de 95%. O intervalo mede só o erro aleatório; a pesquisa é
-- MAGIC   autosselecionada, e isso nenhum intervalo corrige.
-- MAGIC - **n** aparece em toda linha.
-- MAGIC
-- MAGIC ## Decisões
-- MAGIC
-- MAGIC - Q3 compara o Brasil com o resto do mundo (sem o Brasil), para ter grupos independentes. País em branco fica fora
-- MAGIC   dos dois grupos.
-- MAGIC - Q4: os gráficos usam só combinações com `n_serie_comparavel >= 100`, sempre com o intervalo de 95%. Abaixo disso a
-- MAGIC   margem passa de 10 pontos. A view mantém todas as combinações.
-- MAGIC - Q5: média com erro padrão, distribuição em três faixas (0 a 4, 5 a 7, 8 a 10) e média padronizada por faixa de
-- MAGIC   experiência. Numa escala de 0 a 10 a mediana tende a empatar; a padronização tira o efeito da composição por
-- MAGIC   experiência. A regra de usar mediana vale para remuneração, por causa da cauda extrema.
-- MAGIC - Q7: a variação anual é calculada sobre a média móvel de quatro trimestres, para reduzir o ruído de UF pequena (a
-- MAGIC   5434 não traz CV).
-- MAGIC - Q8: cenários com taxa publicada (`/d/m`) e cenário da pesquisa. Os detalhes estão no comentário da view.
-- MAGIC
-- MAGIC As razões usam `try_divide`: com ANSI ligado (padrão no serverless), `/` por zero interrompe a consulta.
-- MAGIC
-- MAGIC Depois de cada view há uma consulta pronta para o gráfico. A visualização é criada no resultado (botão `+`), com o
-- MAGIC tipo indicado no comentário, e a imagem vai para `docs/img/`.
-- MAGIC
-- MAGIC Tudo com `CREATE OR REPLACE VIEW`, então rodar de novo é seguro.

-- COMMAND ----------

USE CATALOG mafia_office;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Q1 · Evolução do arranjo de trabalho no mundo, 2022 a 2025

-- COMMAND ----------

-- Q1: Como evoluiu a distribuição entre trabalho remoto, híbrido e presencial de 2022 a 2025 no mundo?
-- Fonte: Stack Overflow Developer Survey. Duas bases: trabalhando (principal) e todos_informados (sensibilidade).
-- pct_serie_comparavel: Remoto, Híbrido e Presencial, sem Flexível no denominador; é a série lida entre safras.
-- 2022 a 2024 usam o mesmo questionário; 2025 mudou e é lido junto dos limites da consulta Q1b.
-- Intervalo de Wilson de 95% sobre a série comparável.
CREATE OR REPLACE VIEW gold.vw_q1_evolucao_arranjo (
  safra COMMENT 'Ano da pesquisa. Domínio: 2022 a 2025. Linhagem: gold.dim_periodo.ano pela periodo_chave da fato.',
  base COMMENT 'trabalhando (empregado ou autônomo, base principal) ou todos_informados (sensibilidade). Domínio: trabalhando, todos_informados. Linhagem: constante de cada bloco do UNION ALL; trabalhando filtra fato.trabalhando.',
  arranjo COMMENT 'Arranjo harmonizado: Remoto, Híbrido, Presencial, Flexível (só 2025). Domínio: Remoto, Híbrido, Presencial, Flexível. Linhagem: gold.dim_arranjo_trabalho.arranjo.',
  ordem COMMENT 'Ordem de exibição do arranjo. Domínio: 1 a 4. Linhagem: gold.dim_arranjo_trabalho.ordem.',
  entra_serie_historica COMMENT 'true para Remoto, Híbrido e Presencial. Domínio: true, false. Linhagem: gold.dim_arranjo_trabalho.entra_serie_historica.',
  respondentes COMMENT 'Respondentes da base com o arranjo. Domínio: inteiro não negativo. Linhagem: SUM(gold.fato_resposta_pesquisa.qtd_respondentes) por safra, base e arranjo.',
  n_informados COMMENT 'Respondentes da base que informaram o arranjo, incluindo Flexível. Domínio: inteiro positivo. Linhagem: SUM(respondentes) por safra e base.',
  pct_sobre_informados COMMENT 'respondentes / n_informados × 100. Domínio: 0 a 100, uma casa. Linhagem: respondentes / n_informados × 100, arredondado.',
  n_serie_comparavel COMMENT 'Respondentes da base em Remoto, Híbrido ou Presencial. Domínio: inteiro positivo. Linhagem: SUM(respondentes) com entra_serie_historica, por safra e base.',
  pct_serie_comparavel COMMENT 'respondentes / n_serie_comparavel × 100; nulo para Flexível. Domínio: 0 a 100, uma casa; nulo em Flexível. Linhagem: respondentes / n_serie_comparavel × 100.',
  ic95_inf COMMENT 'Limite inferior do intervalo de Wilson de 95% de pct_serie_comparavel; só erro aleatório. Domínio: 0 a 100, uma casa. Linhagem: fórmula de Wilson sobre respondentes e n_serie_comparavel.',
  ic95_sup COMMENT 'Limite superior do intervalo de Wilson de 95% de pct_serie_comparavel; só erro aleatório. Domínio: 0 a 100, uma casa. Linhagem: fórmula de Wilson sobre respondentes e n_serie_comparavel.'
)
COMMENT 'Q1: Como evoluiu a distribuição entre trabalho remoto, híbrido e presencial de 2022 a 2025 no mundo? Série comparável sem Flexível; 2025 com quebra de instrumento; bases trabalhando e todos_informados. Origem: gold.fato_resposta_pesquisa com dim_periodo e dim_arranjo_trabalho.'
AS
WITH respostas AS (
  SELECT p.ano AS safra, f.trabalhando, a.arranjo, a.ordem, a.entra_serie_historica, f.qtd_respondentes
  FROM gold.fato_resposta_pesquisa f
  JOIN gold.dim_periodo p ON p.periodo_chave = f.periodo_chave
  JOIN gold.dim_arranjo_trabalho a ON a.arranjo_chave = f.arranjo_chave
  WHERE a.arranjo NOT IN ('Não informado', 'Desconhecido')
),
por_base AS (
  SELECT safra, 'trabalhando' AS base, arranjo, ordem, entra_serie_historica, SUM(qtd_respondentes) AS respondentes
  FROM respostas WHERE trabalhando
  GROUP BY safra, arranjo, ordem, entra_serie_historica
  UNION ALL
  SELECT safra, 'todos_informados', arranjo, ordem, entra_serie_historica, SUM(qtd_respondentes)
  FROM respostas
  GROUP BY safra, arranjo, ordem, entra_serie_historica
),
com_bases AS (
  SELECT *,
         SUM(respondentes) OVER (PARTITION BY safra, base) AS n_informados,
         SUM(CASE WHEN entra_serie_historica THEN respondentes END) OVER (PARTITION BY safra, base) AS n_serie_comparavel
  FROM por_base
),
wilson AS (
  SELECT *,
         CASE WHEN entra_serie_historica THEN try_divide(respondentes, n_serie_comparavel) END AS p,
         try_divide(3.8416, n_serie_comparavel) AS z2_n  -- z² / n, com z = 1,96
  FROM com_bases
)
SELECT
  safra, base, arranjo, ordem, entra_serie_historica, respondentes, n_informados,
  ROUND(100 * try_divide(respondentes, n_informados), 1) AS pct_sobre_informados,
  n_serie_comparavel,
  ROUND(100 * p, 1) AS pct_serie_comparavel,
  ROUND(100 * try_divide(p + z2_n / 2 - 1.96 * SQRT(try_divide(p * (1 - p), n_serie_comparavel) + POWER(z2_n, 2) / (4 * 3.8416)), 1 + z2_n), 1) AS ic95_inf,
  ROUND(100 * try_divide(p + z2_n / 2 + 1.96 * SQRT(try_divide(p * (1 - p), n_serie_comparavel) + POWER(z2_n, 2) / (4 * 3.8416)), 1 + z2_n), 1) AS ic95_sup
FROM wilson;

-- COMMAND ----------

-- Gráfico Q1a: barras empilhadas 100%, eixo X = safra, série = arranjo, valor = pct_serie_comparavel, base = trabalhando.
SELECT safra, base, arranjo, respondentes, n_serie_comparavel, pct_serie_comparavel, ic95_inf, ic95_sup, pct_sobre_informados
FROM gold.vw_q1_evolucao_arranjo
ORDER BY base DESC, safra, ordem;

-- COMMAND ----------

-- Tabela Q1b: limites de sensibilidade para Remoto. Limite inferior: Flexível conta como não remoto. Limite superior:
-- Flexível conta como remoto. Nas safras sem Flexível os dois limites coincidem.
SELECT
  safra,
  base,
  MAX(n_informados) AS n_informados,
  MAX(CASE WHEN arranjo = 'Remoto' THEN pct_serie_comparavel END) AS remoto_serie_comparavel,
  ROUND(100 * try_divide(SUM(CASE WHEN arranjo = 'Remoto' THEN respondentes ELSE 0 END), MAX(n_informados)), 1) AS remoto_limite_inferior,
  ROUND(100 * try_divide(SUM(CASE WHEN arranjo IN ('Remoto', 'Flexível') THEN respondentes ELSE 0 END), MAX(n_informados)), 1) AS remoto_limite_superior
FROM gold.vw_q1_evolucao_arranjo
GROUP BY safra, base
ORDER BY base DESC, safra;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### Q1c · A não resposta de 2025 e a tendência do remoto
-- MAGIC
-- MAGIC Em 2025, 19,8% de quem trabalha não informou o arranjo (C02), contra no máximo 0,1% antes, e o nulo se concentra
-- MAGIC em autônomos (C26). Autônomos são mais remotos que empregados, então a não resposta muda a composição da base
-- MAGIC informada. Esta view separa a série por vínculo, padroniza a composição pela de 2024 e dá limites para os nulos.
-- MAGIC
-- MAGIC O próprio vínculo também mudou: `Employment` é multi-resposta de 2022 a 2024 e resposta única em 2025. Quem marcou
-- MAGIC empregado e autônomo ao mesmo tempo (duplos) não tem equivalente em 2025, então a view calcula tudo nas duas
-- MAGIC classificações possíveis dos duplos e considera o intervalo entre elas.

-- COMMAND ----------

-- Q1c: a variação do remoto entre 2024 e 2025 sobrevive à não resposta concentrada em autônomos?
-- Fonte: Stack Overflow Developer Survey. Base: trabalhando. Série comparável (Remoto, Híbrido, Presencial).
-- classificacao_duplos: 'duplos como Empregado' (empregado = true vira Empregado) ou 'duplos como Autônomo'
-- (autonomo = true vira Autônomo). Em 2025 não há duplos e as duas classificações coincidem.
-- Padronização direta: pct_remoto de cada vínculo na safra × peso do vínculo na série comparável de 2024, na mesma
-- classificação. Limites dos nulos: nulos como não remotos e como remotos, sobre série comparável + nulos, supondo que
-- nenhum nulo seria Flexível.
CREATE OR REPLACE VIEW gold.vw_q1_remoto_por_vinculo (
  safra COMMENT 'Ano da pesquisa. Domínio: 2022 a 2025. Linhagem: gold.dim_periodo.ano.',
  classificacao_duplos COMMENT 'Como quem marcou empregado e autônomo (2022 a 2024) é classificado: duplos como Empregado ou duplos como Autônomo. Domínio: duplos como Empregado, duplos como Autônomo. Linhagem: constante de cada bloco da view.',
  vinculo COMMENT 'Empregado, Autônomo ou Todos (quem trabalha), segundo classificacao_duplos. Domínio: Empregado, Autônomo, Todos. Linhagem: gold.fato_resposta_pesquisa.empregado e autonomo, conforme classificacao_duplos; Todos soma os dois.',
  trabalhando COMMENT 'Respondentes que trabalham, no vínculo. Domínio: inteiro positivo (contagem). Linhagem: SUM(gold.fato_resposta_pesquisa.qtd_respondentes) com trabalhando verdadeiro.',
  respondentes_duplos COMMENT 'Respondentes do vínculo que marcaram empregado e autônomo; 0 em 2025, quando Employment é resposta única. Domínio: inteiro não negativo. Linhagem: SUM de qtd_respondentes com empregado e autonomo verdadeiros.',
  nulos_arranjo COMMENT 'Respondentes do vínculo sem arranjo informado. Domínio: inteiro não negativo. Linhagem: SUM de qtd_respondentes com arranjo Não informado.',
  pct_nulo_arranjo COMMENT 'nulos_arranjo / trabalhando × 100. Domínio: 0 a 100, uma casa. Linhagem: nulos_arranjo / trabalhando × 100.',
  n_serie_comparavel COMMENT 'Respondentes do vínculo em Remoto, Híbrido ou Presencial. Domínio: inteiro positivo. Linhagem: SUM de qtd_respondentes com entra_serie_historica.',
  remotos COMMENT 'Respondentes do vínculo em Remoto. Domínio: inteiro não negativo. Linhagem: SUM de qtd_respondentes com arranjo Remoto.',
  pct_remoto COMMENT 'remotos / n_serie_comparavel × 100. Domínio: 0 a 100, uma casa. Linhagem: remotos / n_serie_comparavel × 100.',
  ic95_inf COMMENT 'Limite inferior do intervalo de Wilson de 95% de pct_remoto; só erro aleatório. Domínio: 0 a 100, uma casa. Linhagem: fórmula de Wilson sobre remotos e n_serie_comparavel.',
  ic95_sup COMMENT 'Limite superior do intervalo de Wilson de 95% de pct_remoto; só erro aleatório. Domínio: 0 a 100, uma casa. Linhagem: fórmula de Wilson sobre remotos e n_serie_comparavel.',
  peso_vinculo COMMENT 'Participação do vínculo na série comparável da safra × 100; nulo em Todos. Domínio: 0 a 100, uma casa; nulo em Todos. Linhagem: n_serie_comparavel do vínculo / n_serie_comparavel de Todos × 100.',
  pct_remoto_padronizado_2024 COMMENT 'Só em Todos: soma por vínculo de pct_remoto da safra × peso do vínculo em 2024, na mesma classificação; remove o efeito de composição por vínculo. Domínio: 0 a 100, uma casa; nulo fora de Todos. Linhagem: SUM(pct_remoto da safra × peso_vinculo de 2024) / 100.',
  remoto_limite_inf_nulos COMMENT 'Só em Todos: remotos / (n_serie_comparavel + nulos_arranjo) × 100, com os nulos como não remotos e nenhum como Flexível. Domínio: 0 a 100, uma casa; nulo fora de Todos. Linhagem: remotos / (n_serie_comparavel + nulos_arranjo) × 100.',
  remoto_limite_sup_nulos COMMENT 'Só em Todos: (remotos + nulos_arranjo) / (n_serie_comparavel + nulos_arranjo) × 100, com os nulos como remotos e nenhum como Flexível. Domínio: 0 a 100, uma casa; nulo fora de Todos. Linhagem: (remotos + nulos_arranjo) / (n_serie_comparavel + nulos_arranjo) × 100.'
)
COMMENT 'Q1c: sensibilidade da série de Remoto à não resposta de 2025. Série por vínculo nas duas classificações de quem marcou empregado e autônomo, padronizada pela composição de 2024 e com limites para os nulos. Base trabalhando, série comparável. Origem: gold.fato_resposta_pesquisa com dim_periodo e dim_arranjo_trabalho.'
AS
WITH respostas AS (
  SELECT p.ano AS safra, f.empregado, f.autonomo, a.arranjo, a.entra_serie_historica, f.qtd_respondentes
  FROM gold.fato_resposta_pesquisa f
  JOIN gold.dim_periodo p ON p.periodo_chave = f.periodo_chave
  JOIN gold.dim_arranjo_trabalho a ON a.arranjo_chave = f.arranjo_chave
  WHERE f.trabalhando
),
-- As duas classificações saem de um CROSS JOIN com VALUES. Com UNION ALL e um literal por ramo, o Spark local
-- devolveu um valor errado numa subconsulta; com o CROSS JOIN o resultado ficou certo.
classificadas AS (
  SELECT r.safra, r.empregado, r.autonomo, r.arranjo, r.entra_serie_historica, r.qtd_respondentes,
         c.classificacao_duplos,
         CASE
           WHEN c.classificacao_duplos = 'duplos como Empregado'
             THEN CASE WHEN r.empregado THEN 'Empregado' ELSE 'Autônomo' END
           ELSE CASE WHEN r.autonomo THEN 'Autônomo' ELSE 'Empregado' END
         END AS vinculo
  FROM respostas r
  CROSS JOIN (VALUES ('duplos como Empregado'), ('duplos como Autônomo')) AS c(classificacao_duplos)
),
por_vinculo AS (
  SELECT safra, classificacao_duplos, vinculo,
         SUM(qtd_respondentes) AS trabalhando,
         SUM(CASE WHEN empregado AND autonomo THEN qtd_respondentes ELSE 0 END) AS respondentes_duplos,
         SUM(CASE WHEN arranjo = 'Não informado' THEN qtd_respondentes ELSE 0 END) AS nulos_arranjo,
         SUM(CASE WHEN entra_serie_historica THEN qtd_respondentes ELSE 0 END) AS n_serie_comparavel,
         SUM(CASE WHEN arranjo = 'Remoto' THEN qtd_respondentes ELSE 0 END) AS remotos
  FROM classificadas
  GROUP BY safra, classificacao_duplos, vinculo
),
pesos AS (
  SELECT safra, classificacao_duplos, vinculo,
         try_divide(n_serie_comparavel, SUM(n_serie_comparavel) OVER (PARTITION BY safra, classificacao_duplos)) AS peso
  FROM por_vinculo
),
padronizado AS (
  SELECT v.safra, v.classificacao_duplos, SUM(try_divide(v.remotos, v.n_serie_comparavel) * p2024.peso) AS p_padronizado
  FROM por_vinculo v
  JOIN pesos p2024
    ON p2024.vinculo = v.vinculo AND p2024.classificacao_duplos = v.classificacao_duplos AND p2024.safra = 2024
  GROUP BY v.safra, v.classificacao_duplos
),
unido AS (
  SELECT safra, classificacao_duplos, vinculo, trabalhando, respondentes_duplos, nulos_arranjo, n_serie_comparavel, remotos
  FROM por_vinculo
  UNION ALL
  SELECT safra, classificacao_duplos, 'Todos' AS vinculo, SUM(trabalhando) AS trabalhando,
         SUM(respondentes_duplos) AS respondentes_duplos, SUM(nulos_arranjo) AS nulos_arranjo,
         SUM(n_serie_comparavel) AS n_serie_comparavel, SUM(remotos) AS remotos
  FROM por_vinculo
  GROUP BY safra, classificacao_duplos
),
wilson AS (
  SELECT *,
         try_divide(remotos, n_serie_comparavel) AS p,
         try_divide(3.8416, n_serie_comparavel) AS z2_n  -- z² / n, com z = 1,96
  FROM unido
)
SELECT
  w.safra, w.classificacao_duplos, w.vinculo, w.trabalhando, w.respondentes_duplos, w.nulos_arranjo,
  ROUND(100 * try_divide(w.nulos_arranjo, w.trabalhando), 1) AS pct_nulo_arranjo,
  w.n_serie_comparavel, w.remotos,
  ROUND(100 * w.p, 1) AS pct_remoto,
  ROUND(100 * try_divide(w.p + w.z2_n / 2 - 1.96 * SQRT(try_divide(w.p * (1 - w.p), w.n_serie_comparavel) + POWER(w.z2_n, 2) / (4 * 3.8416)), 1 + w.z2_n), 1) AS ic95_inf,
  ROUND(100 * try_divide(w.p + w.z2_n / 2 + 1.96 * SQRT(try_divide(w.p * (1 - w.p), w.n_serie_comparavel) + POWER(w.z2_n, 2) / (4 * 3.8416)), 1 + w.z2_n), 1) AS ic95_sup,
  ROUND(100 * pe.peso, 1) AS peso_vinculo,
  CASE WHEN w.vinculo = 'Todos' THEN ROUND(100 * pd.p_padronizado, 1) END AS pct_remoto_padronizado_2024,
  CASE WHEN w.vinculo = 'Todos'
       THEN ROUND(100 * try_divide(w.remotos, w.n_serie_comparavel + w.nulos_arranjo), 1) END AS remoto_limite_inf_nulos,
  CASE WHEN w.vinculo = 'Todos'
       THEN ROUND(100 * try_divide(w.remotos + w.nulos_arranjo, w.n_serie_comparavel + w.nulos_arranjo), 1) END AS remoto_limite_sup_nulos
FROM wilson w
LEFT JOIN pesos pe
  ON pe.safra = w.safra AND pe.classificacao_duplos = w.classificacao_duplos AND pe.vinculo = w.vinculo
LEFT JOIN padronizado pd ON pd.safra = w.safra AND pd.classificacao_duplos = w.classificacao_duplos;

-- COMMAND ----------

-- Tabela Q1c: Remoto por vínculo e série padronizada, nas duas classificações dos duplos.
SELECT safra, classificacao_duplos, vinculo, trabalhando, respondentes_duplos, pct_nulo_arranjo, n_serie_comparavel,
       pct_remoto, ic95_inf, ic95_sup, peso_vinculo, pct_remoto_padronizado_2024, remoto_limite_inf_nulos,
       remoto_limite_sup_nulos
FROM gold.vw_q1_remoto_por_vinculo
ORDER BY safra, classificacao_duplos DESC, CASE vinculo WHEN 'Todos' THEN 0 WHEN 'Empregado' THEN 1 ELSE 2 END;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Q2 · Arranjo de trabalho por porte da empresa

-- COMMAND ----------

-- Q2: O arranjo de trabalho varia com o porte da empresa?
-- Fonte: Stack Overflow Developer Survey. Base: trabalhando, com arranjo e porte informados.
-- Porte canônico: 2022 a 2024 tinham 2 to 9 e 10 to 19; 2025 funde em Less than 20. As três viram Menos de 20.
-- Autônomo (Just me) não é porte de empresa e misturaria trabalho por conta própria com a associação entre porte e
-- arranjo: e_autonomo permite ler com e sem essa faixa. Percentual calculado dentro de cada porte e safra.
CREATE OR REPLACE VIEW gold.vw_q2_arranjo_por_porte (
  safra COMMENT 'Ano da pesquisa. Domínio: 2022 a 2025. Linhagem: gold.dim_periodo.ano.',
  porte COMMENT 'Faixa canônica de porte da empresa. Domínio: nove faixas de porte. Linhagem: gold.dim_porte_empresa.porte.',
  porte_ordem COMMENT 'Ordem crescente de porte (1 a 9). Domínio: 1 a 9. Linhagem: gold.dim_porte_empresa.ordem.',
  e_autonomo COMMENT 'true na faixa Autônomo (Just me), que convém excluir ao comparar portes. Domínio: true, false. Linhagem: porte igual a Autônomo.',
  arranjo COMMENT 'Arranjo harmonizado. Domínio: Remoto, Híbrido, Presencial, Flexível. Linhagem: gold.dim_arranjo_trabalho.arranjo.',
  arranjo_ordem COMMENT 'Ordem de exibição do arranjo. Domínio: 1 a 4. Linhagem: gold.dim_arranjo_trabalho.ordem.',
  respondentes COMMENT 'Respondentes trabalhando com o porte e o arranjo. Domínio: inteiro não negativo. Linhagem: SUM(gold.fato_resposta_pesquisa.qtd_respondentes) por safra, porte e arranjo.',
  n_porte COMMENT 'Respondentes trabalhando no porte que informaram o arranjo. Domínio: inteiro positivo. Linhagem: SUM(respondentes) por safra e porte.',
  pct_no_porte COMMENT 'respondentes / n_porte × 100. Domínio: 0 a 100, uma casa. Linhagem: respondentes / n_porte × 100.'
)
COMMENT 'Q2: O arranjo de trabalho varia com o porte da empresa? Base trabalhando; percentual dentro do porte; Menos de 20 funde as faixas de 2 a 19; e_autonomo separa Just me. Origem: gold.fato_resposta_pesquisa com dim_periodo, dim_porte_empresa e dim_arranjo_trabalho.'
AS
WITH respostas AS (
  SELECT p.ano AS safra, pt.porte, pt.ordem AS porte_ordem, a.arranjo, a.ordem AS arranjo_ordem,
         SUM(f.qtd_respondentes) AS respondentes
  FROM gold.fato_resposta_pesquisa f
  JOIN gold.dim_periodo p ON p.periodo_chave = f.periodo_chave
  JOIN gold.dim_arranjo_trabalho a ON a.arranjo_chave = f.arranjo_chave
  JOIN gold.dim_porte_empresa pt ON pt.porte_chave = f.porte_chave
  WHERE f.trabalhando
    AND a.arranjo NOT IN ('Não informado', 'Desconhecido')
    AND pt.porte_chave > 0
  GROUP BY p.ano, pt.porte, pt.ordem, a.arranjo, a.ordem
)
SELECT
  safra, porte, porte_ordem, porte = 'Autônomo' AS e_autonomo, arranjo, arranjo_ordem, respondentes,
  SUM(respondentes) OVER (PARTITION BY safra, porte) AS n_porte,
  ROUND(100 * try_divide(respondentes, SUM(respondentes) OVER (PARTITION BY safra, porte)), 1) AS pct_no_porte
FROM respostas;

-- COMMAND ----------

-- Gráfico Q2: barras empilhadas 100%, eixo X = porte (ordenado por porte_ordem), série = arranjo, safra 2025, sem Autônomo
-- e sem Não sabe.
SELECT safra, porte, arranjo, respondentes, n_porte, pct_no_porte
FROM gold.vw_q2_arranjo_por_porte
WHERE safra = 2025 AND NOT e_autonomo AND porte <> 'Não sabe'
ORDER BY porte_ordem, arranjo_ordem;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Q3 · Brasil comparado ao resto do mundo

-- COMMAND ----------

-- Q3: Como o Brasil se compara à média global na adoção de trabalho remoto?
-- Fonte: Stack Overflow Developer Survey. Base: trabalhando. Só agregado nacional: a subamostra brasileira cai de
-- 2.109 respondentes (2022) para 825 (2025); em 2025, 634 brasileiros que trabalham informaram o arranjo e 586 estão na
-- série comparável. Não desagrego o Brasil por UF, porte ou perfil. Resto do mundo exclui o Brasil (grupos
-- independentes) e quem não informou país.
-- Série comparável sem Flexível e intervalo de Wilson de 95%; o intervalo não cobre viés de seleção.
CREATE OR REPLACE VIEW gold.vw_q3_brasil_x_resto_mundo (
  safra COMMENT 'Ano da pesquisa. Domínio: 2022 a 2025. Linhagem: gold.dim_periodo.ano.',
  grupo COMMENT 'Brasil ou Resto do mundo (todos os países exceto o Brasil). Domínio: Brasil, Resto do mundo. Linhagem: gold.dim_geografia.codigo igual ou diferente de Brazil.',
  arranjo COMMENT 'Arranjo harmonizado. Domínio: Remoto, Híbrido, Presencial, Flexível. Linhagem: gold.dim_arranjo_trabalho.arranjo.',
  ordem COMMENT 'Ordem de exibição do arranjo. Domínio: 1 a 4. Linhagem: gold.dim_arranjo_trabalho.ordem.',
  entra_serie_historica COMMENT 'true para Remoto, Híbrido e Presencial. Domínio: true, false. Linhagem: gold.dim_arranjo_trabalho.entra_serie_historica.',
  respondentes COMMENT 'Respondentes trabalhando do grupo com o arranjo. Domínio: inteiro não negativo. Linhagem: SUM(gold.fato_resposta_pesquisa.qtd_respondentes) por safra, grupo e arranjo.',
  n_informados COMMENT 'Respondentes trabalhando do grupo que informaram o arranjo, incluindo Flexível. Domínio: inteiro positivo. Linhagem: SUM(respondentes) por safra e grupo.',
  n_serie_comparavel COMMENT 'Respondentes trabalhando do grupo em Remoto, Híbrido ou Presencial. Domínio: inteiro positivo. Linhagem: SUM(respondentes) com entra_serie_historica, por safra e grupo.',
  pct_serie_comparavel COMMENT 'respondentes / n_serie_comparavel × 100; nulo para Flexível. Domínio: 0 a 100, uma casa; nulo em Flexível. Linhagem: respondentes / n_serie_comparavel × 100.',
  ic95_inf COMMENT 'Limite inferior do intervalo de Wilson de 95%; só erro aleatório. Domínio: 0 a 100, uma casa. Linhagem: fórmula de Wilson sobre respondentes e n_serie_comparavel.',
  ic95_sup COMMENT 'Limite superior do intervalo de Wilson de 95%; só erro aleatório. Domínio: 0 a 100, uma casa. Linhagem: fórmula de Wilson sobre respondentes e n_serie_comparavel.'
)
COMMENT 'Q3: Como o Brasil se compara à média global na adoção de trabalho remoto? Base trabalhando; Brasil × resto do mundo; só agregado nacional; série comparável com intervalo de Wilson. Origem: gold.fato_resposta_pesquisa com dim_periodo, dim_geografia e dim_arranjo_trabalho.'
AS
WITH respostas AS (
  SELECT p.ano AS safra,
         CASE WHEN g.codigo = 'Brazil' THEN 'Brasil' ELSE 'Resto do mundo' END AS grupo,
         a.arranjo, a.ordem, a.entra_serie_historica, f.qtd_respondentes
  FROM gold.fato_resposta_pesquisa f
  JOIN gold.dim_periodo p ON p.periodo_chave = f.periodo_chave
  JOIN gold.dim_geografia g ON g.geo_chave = f.geo_chave
  JOIN gold.dim_arranjo_trabalho a ON a.arranjo_chave = f.arranjo_chave
  WHERE f.trabalhando
    AND f.geo_chave NOT IN (-1, -2)
    AND a.arranjo NOT IN ('Não informado', 'Desconhecido')
),
agregado AS (
  SELECT safra, grupo, arranjo, ordem, entra_serie_historica, SUM(qtd_respondentes) AS respondentes
  FROM respostas
  GROUP BY safra, grupo, arranjo, ordem, entra_serie_historica
),
com_bases AS (
  SELECT *,
         SUM(respondentes) OVER (PARTITION BY safra, grupo) AS n_informados,
         SUM(CASE WHEN entra_serie_historica THEN respondentes END) OVER (PARTITION BY safra, grupo) AS n_serie_comparavel
  FROM agregado
),
wilson AS (
  SELECT *,
         CASE WHEN entra_serie_historica THEN try_divide(respondentes, n_serie_comparavel) END AS p,
         try_divide(3.8416, n_serie_comparavel) AS z2_n
  FROM com_bases
)
SELECT
  safra, grupo, arranjo, ordem, entra_serie_historica, respondentes, n_informados, n_serie_comparavel,
  ROUND(100 * p, 1) AS pct_serie_comparavel,
  ROUND(100 * try_divide(p + z2_n / 2 - 1.96 * SQRT(try_divide(p * (1 - p), n_serie_comparavel) + POWER(z2_n, 2) / (4 * 3.8416)), 1 + z2_n), 1) AS ic95_inf,
  ROUND(100 * try_divide(p + z2_n / 2 + 1.96 * SQRT(try_divide(p * (1 - p), n_serie_comparavel) + POWER(z2_n, 2) / (4 * 3.8416)), 1 + z2_n), 1) AS ic95_sup
FROM wilson;

-- COMMAND ----------

-- Gráfico Q3: linhas com barra de erro, eixo X = safra, série = grupo, valor = pct_serie_comparavel, filtro arranjo =
-- Remoto; ic95_inf e ic95_sup como barras de erro; n_serie_comparavel no rótulo.
SELECT safra, grupo, arranjo, respondentes, n_serie_comparavel, pct_serie_comparavel, ic95_inf, ic95_sup
FROM gold.vw_q3_brasil_x_resto_mundo
WHERE entra_serie_historica
ORDER BY safra, grupo, ordem;

-- COMMAND ----------

-- Sensibilidade Q3: 2024 e 2025 agregadas. A subamostra brasileira de 2025 é fina (586 na série comparável); somar as
-- duas safras dobra a base e mostra se a diferença Brasil × resto do mundo se mantém. Como o questionário mudou em
-- 2025, o agregado é só sensibilidade, não série.
WITH agregado AS (
  SELECT grupo, SUM(respondentes) AS remotos, SUM(n_serie_comparavel) AS n
  FROM (SELECT DISTINCT safra, grupo, arranjo, respondentes, n_serie_comparavel FROM gold.vw_q3_brasil_x_resto_mundo)
  WHERE safra IN (2024, 2025) AND arranjo = 'Remoto'
  GROUP BY grupo
),
wilson AS (SELECT *, try_divide(remotos, n) AS p, try_divide(3.8416, n) AS z2_n FROM agregado)
SELECT grupo, remotos, n AS n_serie_comparavel, ROUND(100 * p, 1) AS pct_remoto_2024_2025,
       ROUND(100 * try_divide(p + z2_n / 2 - 1.96 * SQRT(try_divide(p * (1 - p), n) + POWER(z2_n, 2) / (4 * 3.8416)), 1 + z2_n), 1) AS ic95_inf,
       ROUND(100 * try_divide(p + z2_n / 2 + 1.96 * SQRT(try_divide(p * (1 - p), n) + POWER(z2_n, 2) / (4 * 3.8416)), 1 + z2_n), 1) AS ic95_sup
FROM wilson
ORDER BY grupo;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Q4 · Perfis e faixas de experiência que concentram trabalho remoto

-- COMMAND ----------

-- Q4: Que perfis profissionais e faixas de experiência concentram trabalho remoto?
-- Fonte: Stack Overflow Developer Survey. Base: trabalhando.
-- Perfil = perfil_principal: em 2022 DevType é multi-resposta e o perfil é o primeiro item listado; de 2023 a 2025 é
-- resposta única. Perfis de 2022 não se comparam aos das safras seguintes.
-- Experiência = anos codando (YearsCode, inclui anos de estudo; não é experiência profissional), censurado em 0 e 50.
-- pct_remoto_comparavel = Remoto sobre a série comparável (sem Flexível), com intervalo de Wilson de 95%.
CREATE OR REPLACE VIEW gold.vw_q4_perfil_remoto (
  safra COMMENT 'Ano da pesquisa. Domínio: 2022 a 2025. Linhagem: gold.dim_periodo.ano.',
  perfil COMMENT 'Perfil profissional (primeiro item em 2022; resposta única de 2023 a 2025). Domínio: rótulos de DevType da safra. Linhagem: gold.dim_perfil_dev.perfil.',
  faixa_experiencia COMMENT 'Faixa de anos codando (inclui anos de estudo). Domínio: 0–2, 3–5, 6–10, 11–20, 21+, Não informado. Linhagem: gold.dim_perfil_dev.faixa_experiencia.',
  n_informados COMMENT 'Respondentes trabalhando do perfil e faixa que informaram o arranjo. Domínio: inteiro positivo. Linhagem: SUM(gold.fato_resposta_pesquisa.qtd_respondentes) com arranjo informado.',
  n_serie_comparavel COMMENT 'Respondentes trabalhando do perfil e faixa em Remoto, Híbrido ou Presencial. Domínio: inteiro não negativo. Linhagem: SUM de qtd_respondentes com entra_serie_historica.',
  remotos COMMENT 'Respondentes trabalhando do perfil e faixa em Remoto. Domínio: inteiro não negativo. Linhagem: SUM de qtd_respondentes com arranjo Remoto.',
  hibridos COMMENT 'Respondentes trabalhando do perfil e faixa em Híbrido. Domínio: inteiro não negativo. Linhagem: SUM de qtd_respondentes com arranjo Híbrido.',
  pct_remoto_comparavel COMMENT 'remotos / n_serie_comparavel × 100. Domínio: 0 a 100, uma casa. Linhagem: remotos / n_serie_comparavel × 100.',
  pct_hibrido_comparavel COMMENT 'hibridos / n_serie_comparavel × 100. Domínio: 0 a 100, uma casa. Linhagem: hibridos / n_serie_comparavel × 100.',
  pct_nao_presencial_comparavel COMMENT 'Remoto mais Híbrido sobre a série comparável: o público do Mafia Office. Domínio: 0 a 100, uma casa. Linhagem: (remotos + hibridos) / n_serie_comparavel × 100.',
  ic95_inf COMMENT 'Limite inferior do intervalo de Wilson de 95%; só erro aleatório. Domínio: 0 a 100, uma casa. Linhagem: fórmula de Wilson sobre remotos e n_serie_comparavel.',
  ic95_sup COMMENT 'Limite superior do intervalo de Wilson de 95%; só erro aleatório. Domínio: 0 a 100, uma casa. Linhagem: fórmula de Wilson sobre remotos e n_serie_comparavel.'
)
COMMENT 'Q4: Que perfis profissionais e faixas de experiência concentram trabalho remoto? Base trabalhando; Remoto sobre a série comparável, com intervalo de Wilson; perfis de 2022 não comparáveis. Origem: gold.fato_resposta_pesquisa com dim_periodo, dim_arranjo_trabalho e dim_perfil_dev.'
AS
WITH agregado AS (
  SELECT
    p.ano AS safra,
    pf.perfil,
    pf.faixa_experiencia,
    SUM(f.qtd_respondentes) AS n_informados,
    SUM(CASE WHEN a.entra_serie_historica THEN f.qtd_respondentes ELSE 0 END) AS n_serie_comparavel,
    SUM(CASE WHEN a.arranjo = 'Remoto' THEN f.qtd_respondentes ELSE 0 END) AS remotos,
    SUM(CASE WHEN a.arranjo = 'Híbrido' THEN f.qtd_respondentes ELSE 0 END) AS hibridos
  FROM gold.fato_resposta_pesquisa f
  JOIN gold.dim_periodo p ON p.periodo_chave = f.periodo_chave
  JOIN gold.dim_arranjo_trabalho a ON a.arranjo_chave = f.arranjo_chave
  JOIN gold.dim_perfil_dev pf ON pf.perfil_chave = f.perfil_chave
  WHERE f.trabalhando
    AND a.arranjo NOT IN ('Não informado', 'Desconhecido')
    AND pf.perfil NOT IN ('Não informado', 'Desconhecido')
  GROUP BY p.ano, pf.perfil, pf.faixa_experiencia
),
wilson AS (
  SELECT *, try_divide(remotos, n_serie_comparavel) AS p, try_divide(3.8416, n_serie_comparavel) AS z2_n
  FROM agregado
)
SELECT
  safra, perfil, faixa_experiencia, n_informados, n_serie_comparavel, remotos, hibridos,
  ROUND(100 * p, 1) AS pct_remoto_comparavel,
  ROUND(100 * try_divide(hibridos, n_serie_comparavel), 1) AS pct_hibrido_comparavel,
  ROUND(100 * try_divide(remotos + hibridos, n_serie_comparavel), 1) AS pct_nao_presencial_comparavel,
  ROUND(100 * try_divide(p + z2_n / 2 - 1.96 * SQRT(try_divide(p * (1 - p), n_serie_comparavel) + POWER(z2_n, 2) / (4 * 3.8416)), 1 + z2_n), 1) AS ic95_inf,
  ROUND(100 * try_divide(p + z2_n / 2 + 1.96 * SQRT(try_divide(p * (1 - p), n_serie_comparavel) + POWER(z2_n, 2) / (4 * 3.8416)), 1 + z2_n), 1) AS ic95_sup
FROM wilson;

-- COMMAND ----------

-- Gráfico Q4a: barras horizontais com barra de erro, perfis em 2025 (todas as faixas somadas), n_serie_comparavel >= 100.
WITH perfil AS (
  SELECT perfil, SUM(n_serie_comparavel) AS n, SUM(remotos) AS remotos
  FROM gold.vw_q4_perfil_remoto
  WHERE safra = 2025
  GROUP BY perfil
),
wilson AS (SELECT *, try_divide(remotos, n) AS p, try_divide(3.8416, n) AS z2_n FROM perfil)
SELECT perfil, n AS n_serie_comparavel, remotos,
       ROUND(100 * p, 1) AS pct_remoto_comparavel,
       ROUND(100 * try_divide(p + z2_n / 2 - 1.96 * SQRT(try_divide(p * (1 - p), n) + POWER(z2_n, 2) / (4 * 3.8416)), 1 + z2_n), 1) AS ic95_inf,
       ROUND(100 * try_divide(p + z2_n / 2 + 1.96 * SQRT(try_divide(p * (1 - p), n) + POWER(z2_n, 2) / (4 * 3.8416)), 1 + z2_n), 1) AS ic95_sup
FROM wilson
WHERE n >= 100
ORDER BY pct_remoto_comparavel DESC;

-- COMMAND ----------

-- Sensibilidade Q4: perfis com 2024 e 2025 agregadas (resposta única nas duas safras), n_serie_comparavel >= 100.
-- Mostra se a ordenação dos perfis de 2025 se mantém com base maior.
WITH perfil AS (
  SELECT perfil, SUM(n_serie_comparavel) AS n, SUM(remotos) AS remotos
  FROM gold.vw_q4_perfil_remoto
  WHERE safra IN (2024, 2025)
  GROUP BY perfil
),
wilson AS (SELECT *, try_divide(remotos, n) AS p, try_divide(3.8416, n) AS z2_n FROM perfil)
SELECT perfil, n AS n_serie_comparavel, remotos,
       ROUND(100 * p, 1) AS pct_remoto_2024_2025,
       ROUND(100 * try_divide(p + z2_n / 2 - 1.96 * SQRT(try_divide(p * (1 - p), n) + POWER(z2_n, 2) / (4 * 3.8416)), 1 + z2_n), 1) AS ic95_inf,
       ROUND(100 * try_divide(p + z2_n / 2 + 1.96 * SQRT(try_divide(p * (1 - p), n) + POWER(z2_n, 2) / (4 * 3.8416)), 1 + z2_n), 1) AS ic95_sup
FROM wilson
WHERE n >= 100
ORDER BY pct_remoto_2024_2025 DESC;

-- COMMAND ----------

-- Gráfico Q4b: barras agrupadas, eixo X = faixa de experiência, valor = pct_remoto_comparavel, série = safra; só
-- combinações com n_serie_comparavel >= 100.
WITH faixa AS (
  SELECT safra, faixa_experiencia, SUM(n_serie_comparavel) AS n, SUM(remotos) AS remotos
  FROM gold.vw_q4_perfil_remoto
  WHERE faixa_experiencia <> 'Não informado'
  GROUP BY safra, faixa_experiencia
)
SELECT safra, faixa_experiencia, n AS n_serie_comparavel, remotos, ROUND(100 * try_divide(remotos, n), 1) AS pct_remoto_comparavel
FROM faixa
WHERE n >= 100
ORDER BY safra,
         CASE faixa_experiencia WHEN '0–2' THEN 1 WHEN '3–5' THEN 2 WHEN '6–10' THEN 3 WHEN '11–20' THEN 4 ELSE 5 END;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Q5 · Arranjo de trabalho e satisfação

-- COMMAND ----------

-- Q5: Existe relação entre arranjo de trabalho e satisfação declarada com o emprego?
-- Fonte: Stack Overflow Developer Survey, só 2024 e 2025 (JobSat não existe em 2022 e 2023). Base: trabalhando.
-- JobSat mede satisfação geral com o emprego, não o problema de colaboração remota que o produto resolve. A Q5 só
-- olha se o arranjo se associa à satisfação geral. É associação descritiva, não causal.
-- satisfacao_media_padronizada: média ponderada pela distribuição de faixa de experiência de toda a base da safra
-- (padronização direta), para que diferenças de composição por experiência não se confundam com o arranjo. Se um
-- arranjo não tem alguma faixa, os pesos das faixas presentes são renormalizados.
CREATE OR REPLACE VIEW gold.vw_q5_arranjo_satisfacao (
  safra COMMENT 'Ano da pesquisa (2024 ou 2025). Domínio: 2024, 2025. Linhagem: gold.dim_periodo.ano.',
  arranjo COMMENT 'Arranjo harmonizado. Domínio: Remoto, Híbrido, Presencial, Flexível. Linhagem: gold.dim_arranjo_trabalho.arranjo.',
  ordem COMMENT 'Ordem de exibição do arranjo. Domínio: 1 a 4. Linhagem: gold.dim_arranjo_trabalho.ordem.',
  n_com_satisfacao COMMENT 'Respondentes trabalhando com arranjo e satisfação informados. Domínio: inteiro positivo. Linhagem: COUNT(*) das linhas de gold.fato_resposta_pesquisa com satisfacao_trabalho preenchida.',
  satisfacao_media COMMENT 'Média de JobSat (0 a 10). Domínio: 0 a 10, duas casas. Linhagem: AVG(gold.fato_resposta_pesquisa.satisfacao_trabalho).',
  erro_padrao_media COMMENT 'Desvio padrão amostral dividido pela raiz de n; só erro aleatório. Domínio: real positivo, três casas. Linhagem: STDDEV_SAMP(satisfacao_trabalho) / SQRT(n).',
  desvio_padrao COMMENT 'Desvio padrão amostral de JobSat no arranjo; referência para ler o tamanho das diferenças entre médias. Domínio: real positivo, duas casas. Linhagem: STDDEV_SAMP(satisfacao_trabalho).',
  satisfacao_media_padronizada COMMENT 'Média padronizada pela distribuição de faixa de experiência da safra. Domínio: 0 a 10, duas casas. Linhagem: média por faixa de experiência ponderada pelo peso da faixa na safra.',
  satisfacao_p25 COMMENT 'Primeiro quartil de JobSat. Domínio: 0 a 10. Linhagem: PERCENTILE_CONT(0.25) de satisfacao_trabalho.',
  satisfacao_mediana COMMENT 'Mediana de JobSat. Domínio: 0 a 10. Linhagem: PERCENTILE_CONT(0.50) de satisfacao_trabalho.',
  satisfacao_p75 COMMENT 'Terceiro quartil de JobSat. Domínio: 0 a 10. Linhagem: PERCENTILE_CONT(0.75) de satisfacao_trabalho.',
  pct_0_a_4 COMMENT 'Percentual com JobSat de 0 a 4. Domínio: 0 a 100, uma casa. Linhagem: parcela com satisfacao_trabalho até 4 × 100.',
  pct_5_a_7 COMMENT 'Percentual com JobSat de 5 a 7. Domínio: 0 a 100, uma casa. Linhagem: parcela com satisfacao_trabalho acima de 4 e até 7 × 100.',
  pct_8_a_10 COMMENT 'Percentual com JobSat de 8 a 10. Domínio: 0 a 100, uma casa. Linhagem: parcela com satisfacao_trabalho acima de 7 × 100.'
)
COMMENT 'Q5: Existe relação entre arranjo de trabalho e satisfação declarada com o emprego? 2024 e 2025; base trabalhando; média com erro padrão, média padronizada por experiência e distribuição; associação, não causa. Origem: gold.fato_resposta_pesquisa com dim_periodo, dim_arranjo_trabalho e dim_perfil_dev.'
AS
WITH respostas AS (
  SELECT p.ano AS safra, a.arranjo, a.ordem, pf.faixa_experiencia, f.satisfacao_trabalho AS satisfacao
  FROM gold.fato_resposta_pesquisa f
  JOIN gold.dim_periodo p ON p.periodo_chave = f.periodo_chave
  JOIN gold.dim_arranjo_trabalho a ON a.arranjo_chave = f.arranjo_chave
  JOIN gold.dim_perfil_dev pf ON pf.perfil_chave = f.perfil_chave
  WHERE p.ano IN (2024, 2025)
    AND f.trabalhando
    AND f.satisfacao_trabalho IS NOT NULL
    AND a.arranjo NOT IN ('Não informado', 'Desconhecido')
),
resumo AS (
  SELECT
    safra, arranjo, ordem,
    COUNT(*) AS n,
    AVG(satisfacao) AS media,
    try_divide(STDDEV_SAMP(satisfacao), SQRT(COUNT(*))) AS erro_padrao,
    STDDEV_SAMP(satisfacao) AS desvio_padrao,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY satisfacao) AS p25,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY satisfacao) AS p50,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY satisfacao) AS p75,
    AVG(CASE WHEN satisfacao <= 4 THEN 1.0 ELSE 0.0 END) AS faixa_baixa,
    AVG(CASE WHEN satisfacao > 4 AND satisfacao <= 7 THEN 1.0 ELSE 0.0 END) AS faixa_media,
    AVG(CASE WHEN satisfacao > 7 THEN 1.0 ELSE 0.0 END) AS faixa_alta
  FROM respostas
  GROUP BY safra, arranjo, ordem
),
media_por_estrato AS (
  SELECT safra, arranjo, faixa_experiencia, AVG(satisfacao) AS media_estrato
  FROM respostas
  GROUP BY safra, arranjo, faixa_experiencia
),
peso_estrato AS (
  SELECT safra, faixa_experiencia, try_divide(COUNT(*), SUM(COUNT(*)) OVER (PARTITION BY safra)) AS peso
  FROM respostas
  GROUP BY safra, faixa_experiencia
),
padronizada AS (
  SELECT e.safra, e.arranjo, try_divide(SUM(e.media_estrato * w.peso), SUM(w.peso)) AS media_padronizada
  FROM media_por_estrato e
  JOIN peso_estrato w ON w.safra = e.safra AND w.faixa_experiencia = e.faixa_experiencia
  GROUP BY e.safra, e.arranjo
)
SELECT
  r.safra, r.arranjo, r.ordem, r.n AS n_com_satisfacao,
  ROUND(r.media, 2) AS satisfacao_media,
  ROUND(r.erro_padrao, 3) AS erro_padrao_media,
  ROUND(r.desvio_padrao, 2) AS desvio_padrao,
  ROUND(pd.media_padronizada, 2) AS satisfacao_media_padronizada,
  r.p25 AS satisfacao_p25, r.p50 AS satisfacao_mediana, r.p75 AS satisfacao_p75,
  ROUND(100 * r.faixa_baixa, 1) AS pct_0_a_4,
  ROUND(100 * r.faixa_media, 1) AS pct_5_a_7,
  ROUND(100 * r.faixa_alta, 1) AS pct_8_a_10
FROM resumo r
JOIN padronizada pd ON pd.safra = r.safra AND pd.arranjo = r.arranjo;

-- COMMAND ----------

-- Gráfico Q5: barras agrupadas com barra de erro (1,96 × erro padrão), eixo X = arranjo, valor = satisfacao_media,
-- série = safra; a tabela traz a média padronizada e a distribuição.
SELECT safra, arranjo, n_com_satisfacao, satisfacao_media, erro_padrao_media, desvio_padrao, satisfacao_media_padronizada,
       satisfacao_mediana, pct_0_a_4, pct_5_a_7, pct_8_a_10
FROM gold.vw_q5_arranjo_satisfacao
ORDER BY safra, ordem;

-- COMMAND ----------

-- Tamanho de efeito da Q5: Remoto e Híbrido contra Presencial, em pontos da escala, em desvios-padrão (d de Cohen com
-- desvio-padrão agrupado dos dois arranjos), bruto e depois de padronizar por experiência, e em pontos percentuais de
-- nota 8 a 10.
WITH pares AS (
  SELECT r.safra, r.arranjo,
         r.satisfacao_media - p.satisfacao_media AS diferenca,
         r.satisfacao_media_padronizada - p.satisfacao_media_padronizada AS diferenca_padronizada,
         SQRT(try_divide((r.n_com_satisfacao - 1) * POWER(r.desvio_padrao, 2) + (p.n_com_satisfacao - 1) * POWER(p.desvio_padrao, 2),
                         r.n_com_satisfacao + p.n_com_satisfacao - 2)) AS desvio_agrupado,
         r.pct_8_a_10 - p.pct_8_a_10 AS diferenca_pct_8_a_10
  FROM gold.vw_q5_arranjo_satisfacao r
  JOIN gold.vw_q5_arranjo_satisfacao p ON p.safra = r.safra AND p.arranjo = 'Presencial'
  WHERE r.arranjo IN ('Remoto', 'Híbrido')
)
SELECT safra, arranjo,
       ROUND(diferenca, 2) AS diferenca_pontos,
       ROUND(diferenca_padronizada, 2) AS diferenca_padronizada_pontos,
       ROUND(try_divide(diferenca, desvio_agrupado), 2) AS d_cohen,
       ROUND(try_divide(diferenca_padronizada, desvio_agrupado), 2) AS d_cohen_padronizado,
       ROUND(diferenca_pct_8_a_10, 1) AS diferenca_pct_8_a_10
FROM pares
ORDER BY safra, arranjo DESC;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Q6 · Tamanho e distribuição geográfica do teletrabalho no Brasil

-- COMMAND ----------

-- Q6: Qual o tamanho e a distribuição geográfica do teletrabalho no Brasil?
-- Fonte: IBGE, PNAD Contínua anual, tabela SIDRA 9471 (4º trimestre de 2022, estatísticas experimentais segundo o SIDRA).
-- Não foi localizada edição posterior com esse recorte.
-- Brasil vem da linha nacional publicada (com CV próprio), não da soma das UFs.
-- pessoas_mil é qualificado pelo CV de pessoas (4091); percentual, pelo CV do percentual (12966). Percentual sobre o
-- total de ocupados do território. Modalidades não se somam (verificação C23): filtre um código por vez.
-- Intervalo de 95% aproximado do percentual: percentual × (1 ± 1,96 × CV / 100).
CREATE OR REPLACE VIEW gold.vw_q6_teletrabalho_uf (
  nivel COMMENT 'pais (Brasil) ou uf. Domínio: pais, uf. Linhagem: gold.dim_geografia.nivel.',
  uf_sigla COMMENT 'Sigla da UF; nulo no Brasil. Domínio: 27 siglas de UF; nulo no Brasil. Linhagem: gold.dim_geografia.uf_sigla.',
  territorio COMMENT 'Nome do território. Domínio: Brasil e as 27 UFs. Linhagem: gold.dim_geografia.nome.',
  regiao COMMENT 'Grande região; nulo no Brasil. Domínio: Norte, Nordeste, Sudeste, Sul, Centro-Oeste; nulo no Brasil. Linhagem: gold.dim_geografia.regiao.',
  modalidade_codigo COMMENT 'Código c1675 (59803 a 59808). Domínio: 59803 a 59808. Linhagem: gold.dim_modalidade_ibge.modalidade_codigo.',
  modalidade COMMENT 'Nome da modalidade conforme o IBGE. Domínio: rótulos da classificação c1675. Linhagem: gold.dim_modalidade_ibge.modalidade.',
  modalidade_pai_codigo COMMENT 'Modalidade que contém esta (hierarquia da verificação C23). Domínio: código c1675 ou nulo no Total. Linhagem: gold.dim_modalidade_ibge.modalidade_pai_codigo.',
  e_teletrabalho COMMENT 'true para teletrabalho (59805) e seus recortes por local. Domínio: true, false. Linhagem: gold.dim_modalidade_ibge.e_teletrabalho.',
  pessoas_mil COMMENT 'Pessoas ocupadas na modalidade, em mil. Domínio: real não negativo. Linhagem: gold.fato_teletrabalho_uf.pessoas_mil.',
  cv_pessoas COMMENT 'CV de pessoas_mil, em %. Domínio: real não negativo. Linhagem: gold.fato_teletrabalho_uf.cv_pessoas.',
  cv_pessoas_classificacao COMMENT 'Faixa de CV adotada no projeto sobre cv_pessoas, publicado pelo IBGE. Domínio: Exata, Ótima, Boa, Razoável, Pouco precisa, Imprecisa. Linhagem: gold.fato_teletrabalho_uf.cv_pessoas_classificacao.',
  leitura_pessoas COMMENT 'Uso de pessoas_mil segundo a faixa adotada: Sustenta conclusão, Usar com ressalva, Só transparência. Domínio: Sustenta conclusão, Usar com ressalva, Só transparência. Linhagem: CASE sobre cv_pessoas_classificacao.',
  percentual COMMENT 'Percentual do total de ocupados do território. Domínio: 0 a 100. Linhagem: gold.fato_teletrabalho_uf.percentual.',
  cv_percentual COMMENT 'CV do percentual, em %. Domínio: real não negativo. Linhagem: gold.fato_teletrabalho_uf.cv_percentual.',
  cv_classificacao COMMENT 'Faixa de CV adotada no projeto sobre cv_percentual, publicado pelo IBGE. Domínio: Exata, Ótima, Boa, Razoável, Pouco precisa, Imprecisa. Linhagem: gold.fato_teletrabalho_uf.cv_classificacao.',
  leitura_percentual COMMENT 'Uso do percentual segundo a faixa adotada. Domínio: Sustenta conclusão, Usar com ressalva, Só transparência. Linhagem: CASE sobre cv_classificacao.',
  ic95_percentual_inf COMMENT 'Limite inferior aproximado de 95% do percentual, truncado em 0. Domínio: 0 a 100. Linhagem: GREATEST(0, percentual × (1 − 1,96 × cv_percentual / 100)).',
  ic95_percentual_sup COMMENT 'Limite superior aproximado de 95% do percentual. Domínio: real não negativo. Linhagem: percentual × (1 + 1,96 × cv_percentual / 100).'
)
COMMENT 'Q6: Qual o tamanho e a distribuição geográfica do teletrabalho no Brasil? PNAD Contínua anual 2022 (4º trimestre), estatísticas experimentais; Brasil pela linha nacional; sem as categorias que o IBGE declara disponíveis só para Brasil e Grande Região; cada medida com seu CV e a faixa adotada; modalidades não se somam. Origem: gold.fato_teletrabalho_uf com dim_geografia e dim_modalidade_ibge.'
AS
SELECT
  g.nivel, g.uf_sigla, g.nome AS territorio, g.regiao,
  m.modalidade_codigo, m.modalidade, m.modalidade_pai_codigo, m.e_teletrabalho,
  f.pessoas_mil, f.cv_pessoas, f.cv_pessoas_classificacao,
  CASE
    WHEN f.cv_pessoas_classificacao IN ('Exata', 'Ótima', 'Boa') THEN 'Sustenta conclusão'
    WHEN f.cv_pessoas_classificacao = 'Razoável' THEN 'Usar com ressalva'
    WHEN f.cv_pessoas_classificacao IN ('Pouco precisa', 'Imprecisa') THEN 'Só transparência'
    ELSE 'CV não publicado'
  END AS leitura_pessoas,
  f.percentual, f.cv_percentual, f.cv_classificacao,
  CASE
    WHEN f.cv_classificacao IN ('Exata', 'Ótima', 'Boa') THEN 'Sustenta conclusão'
    WHEN f.cv_classificacao = 'Razoável' THEN 'Usar com ressalva'
    WHEN f.cv_classificacao IN ('Pouco precisa', 'Imprecisa') THEN 'Só transparência'
    ELSE 'CV não publicado'
  END AS leitura_percentual,
  ROUND(GREATEST(0, f.percentual * (1 - 1.96 * f.cv_percentual / 100)), 2) AS ic95_percentual_inf,
  ROUND(f.percentual * (1 + 1.96 * f.cv_percentual / 100), 2) AS ic95_percentual_sup
FROM gold.fato_teletrabalho_uf f
JOIN gold.dim_geografia g ON g.geo_chave = f.geo_chave
JOIN gold.dim_modalidade_ibge m ON m.modalidade_chave = f.modalidade_chave
-- 59807 e 59808 por UF ficam fora: o IBGE declara essas categorias só para Brasil e Grande Região (C28).
WHERE f.disponivel_no_nivel;

-- COMMAND ----------

-- Gráfico Q6: barras horizontais por UF com barra de erro, valor = percentual, filtro modalidade_codigo = 59805
-- (teletrabalho), cor = leitura_percentual. A primeira linha traz o Brasil para referência.
SELECT nivel, uf_sigla, territorio, regiao, pessoas_mil, cv_pessoas_classificacao, percentual,
       ic95_percentual_inf, ic95_percentual_sup, cv_classificacao, leitura_percentual
FROM gold.vw_q6_teletrabalho_uf
WHERE modalidade_codigo = '59805'
ORDER BY CASE nivel WHEN 'pais' THEN 0 ELSE 1 END, percentual DESC;

-- COMMAND ----------

-- Tabela Q6: tamanho nacional por modalidade, com a hierarquia.
SELECT modalidade_codigo, modalidade, modalidade_pai_codigo, pessoas_mil, cv_pessoas, cv_pessoas_classificacao,
       percentual, cv_percentual, cv_classificacao
FROM gold.vw_q6_teletrabalho_uf
WHERE nivel = 'pais'
ORDER BY modalidade_codigo;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Q7 · População ocupada no setor proxy de tecnologia por UF

-- COMMAND ----------

-- Q7: Como evoluiu a população ocupada no setor proxy de tecnologia por UF?
-- Fonte: IBGE, PNAD Contínua, tabela SIDRA 5434, trimestral, sem CV publicado na consulta.
-- PREMISSA: o proxy é o grupamento 56624 (Informação, comunicação e atividades financeiras, imobiliárias,
-- profissionais e administrativas). É mais amplo que TI e inclui serviços administrativos: a tendência do proxy não
-- identifica a tendência de TI.
-- media_movel_4t: média dos últimos quatro trimestres (só com janela completa). variacao_anual_media_movel_pct compara
-- com a média móvel de quatro trimestres antes, o que remove sazonalidade e reduz o ruído de UF pequena.
-- A 5434 é consultada só no nível UF: o Brasil é soma das UFs.
CREATE OR REPLACE VIEW gold.vw_q7_ocupacao_proxy_tecnologia_uf (
  uf_sigla COMMENT 'Sigla da UF. Domínio: 27 siglas de UF. Linhagem: gold.dim_geografia.uf_sigla.',
  uf_nome COMMENT 'Nome da UF. Domínio: 27 UFs. Linhagem: gold.dim_geografia.nome.',
  regiao COMMENT 'Grande região. Domínio: Norte, Nordeste, Sudeste, Sul, Centro-Oeste. Linhagem: gold.dim_geografia.regiao.',
  ano COMMENT 'Ano do trimestre. Domínio: 2012 em diante. Linhagem: gold.dim_periodo.ano.',
  trimestre COMMENT 'Trimestre (1 a 4). Domínio: 1 a 4. Linhagem: gold.dim_periodo.trimestre.',
  periodo COMMENT 'Rótulo AAAATn. Domínio: AAAATn, como 2022T4. Linhagem: gold.dim_periodo.rotulo.',
  pessoas_mil COMMENT 'Ocupados no grupamento 56624, em mil. Domínio: real não negativo. Linhagem: gold.fato_ocupacao_uf_atividade.pessoas_mil com atividade 56624.',
  media_movel_4t COMMENT 'Média de pessoas_mil nos últimos quatro trimestres; nulo sem janela completa. Domínio: real não negativo; nulo nos três primeiros trimestres. Linhagem: AVG(pessoas_mil) na janela dos quatro trimestres até o atual, por UF.',
  media_movel_4t_ano_anterior COMMENT 'media_movel_4t quatro trimestres antes. Domínio: real não negativo ou nulo. Linhagem: LAG(media_movel_4t, 4) por UF.',
  variacao_anual_media_movel_pct COMMENT 'Variação percentual de media_movel_4t contra o ano anterior. Domínio: real, uma casa; nulo sem ano anterior. Linhagem: (media_movel_4t / media_movel_4t_ano_anterior − 1) × 100.'
)
COMMENT 'Q7: Como evoluiu a população ocupada no setor proxy de tecnologia por UF? Proxy = grupamento 56624, mais amplo que TI (premissa); variação anual sobre média móvel de quatro trimestres. Origem: gold.fato_ocupacao_uf_atividade com dim_periodo, dim_geografia e dim_atividade_economica.'
AS
WITH proxy AS (
  SELECT g.uf_sigla, g.nome AS uf_nome, g.regiao, p.ano, p.trimestre, p.rotulo AS periodo, f.pessoas_mil
  FROM gold.fato_ocupacao_uf_atividade f
  JOIN gold.dim_periodo p ON p.periodo_chave = f.periodo_chave
  JOIN gold.dim_geografia g ON g.geo_chave = f.geo_chave
  JOIN gold.dim_atividade_economica a ON a.atividade_chave = f.atividade_chave
  WHERE a.e_proxy_tecnologia
),
movel AS (
  SELECT *,
         CASE WHEN COUNT(pessoas_mil) OVER janela = 4 THEN AVG(pessoas_mil) OVER janela END AS media_movel_4t
  FROM proxy
  WINDOW janela AS (PARTITION BY uf_sigla ORDER BY ano, trimestre ROWS BETWEEN 3 PRECEDING AND CURRENT ROW)
)
SELECT
  atual.uf_sigla, atual.uf_nome, atual.regiao, atual.ano, atual.trimestre, atual.periodo, atual.pessoas_mil,
  ROUND(atual.media_movel_4t, 1) AS media_movel_4t,
  ROUND(anterior.media_movel_4t, 1) AS media_movel_4t_ano_anterior,
  ROUND(100 * try_divide(atual.media_movel_4t - anterior.media_movel_4t, anterior.media_movel_4t), 1) AS variacao_anual_media_movel_pct
FROM movel atual
LEFT JOIN movel anterior
  ON anterior.uf_sigla = atual.uf_sigla
 AND anterior.ano = atual.ano - 1
 AND anterior.trimestre = atual.trimestre;

-- COMMAND ----------

-- Gráfico Q7a: linhas, eixo X = periodo, valores = soma das UFs (Brasil) trimestral e em média móvel.
SELECT ano, trimestre, periodo,
       SUM(pessoas_mil) AS pessoas_mil_brasil,
       SUM(media_movel_4t) AS media_movel_4t_brasil
FROM gold.vw_q7_ocupacao_proxy_tecnologia_uf
GROUP BY ano, trimestre, periodo
ORDER BY ano, trimestre;

-- COMMAND ----------

-- Gráfico Q7b: barras por UF no último trimestre disponível, com variação anual da média móvel.
SELECT uf_sigla, uf_nome, regiao, periodo, pessoas_mil, media_movel_4t, variacao_anual_media_movel_pct
FROM gold.vw_q7_ocupacao_proxy_tecnologia_uf
WHERE ano * 10 + trimestre = (SELECT MAX(ano * 10 + trimestre) FROM gold.vw_q7_ocupacao_proxy_tecnologia_uf)
ORDER BY pessoas_mil DESC;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Q8 · Estimativa de mercado endereçável no Brasil

-- COMMAND ----------

-- Q8: Cruzando as duas fontes, qual a estimativa de mercado endereçável no Brasil?
-- É uma estimativa de ordem de grandeza, em pessoas, não uma medição. Mercado aqui é população potencial de usuários
-- (assentos), não receita nem número de empresas.
-- Base de aplicação: ocupados no grupamento proxy 56624 no 4º trimestre de 2022 (tabela 5434).
-- Cenários de taxa:
--   A. taxa de teletrabalho (c1675 = 59805), publicada pelo IBGE para o total de ocupados.
--   B. taxa de trabalho remoto (c1675 = 59804), conceito mais amplo, publicada pelo IBGE.
--   C. taxa da pesquisa: Remoto + Híbrido entre brasileiros trabalhando que informaram o arranjo, safra 2022. Amostra
--      autosselecionada de desenvolvedores, só no agregado nacional. Serve de teste: mostra se a taxa dos
--      desenvolvedores, aplicada ao grupamento inteiro, passaria do teto lógico.
-- Teto lógico: ninguém fora do trabalho remoto (c1675 = 59804) entra no mercado, então nenhuma estimativa pode passar
-- do total de pessoas em trabalho remoto do território. excede_teto_logico marca a violação. Nos cenários A e B o
-- teto não pode ser violado por construção (proxy × remoto ÷ ocupados, com proxy menor que o total de ocupados); o
-- teste só é informativo no cenário C.
-- Premissas:
--   1. A e B aplicam ao setor proxy uma taxa medida sobre todos os ocupados, embora a fonte não abra teletrabalho por
--      setor. Se o setor proxy tiver taxa maior que a média dos ocupados, A e B ficam abaixo do valor real; a fonte não
--      permite medir essa diferença.
--   2. O proxy é mais amplo que TI.
--   3. O teletrabalho é estatística experimental e de 2022; a ocupação usada é do mesmo período.
--   4. As tabelas 9471 e 5434 têm universos ligeiramente diferentes no mesmo trimestre (verificação C25); a Q8 só aplica
--      razões entre elas, nunca soma níveis.
--   5. A taxa usada é o percentual publicado com precisão máxima (/d/m), não uma razão de valores arredondados.
--   6. Incerteza propagada: estimativa_ic95_inf_mil e estimativa_ic95_sup_mil aplicam ao proxy a taxa × (1 ± 1,96 × CV
--      da taxa / 100). Só a precisão amostral da taxa do IBGE entra; a 5434 não publica CV na consulta usada, então o
--      proxy entra sem incerteza, e a transferência da taxa média ao setor (premissa 1) não é quantificável. No método
--      "soma das estimativas por UF" os limites são somados, o que supõe erros perfeitamente correlacionados entre UFs
--      e produz um intervalo conservador (mais largo). O cenário C não tem CV e fica sem intervalo.
-- Cruzamento pela dimensão conformada dim_geografia (e pelo ano em dim_periodo), agregando cada fato separadamente
-- antes de combinar (drill-across). As taxonomias de arranjo (pesquisa) e de modalidade (IBGE) não são cruzadas; a taxa
-- da pesquisa entra como número, com a premissa escrita.
CREATE OR REPLACE VIEW gold.vw_q8_mercado_brasil (
  nivel COMMENT 'uf ou pais (Brasil). Domínio: pais, uf. Linhagem: gold.dim_geografia.nivel.',
  uf_sigla COMMENT 'Sigla da UF; BR no Brasil. Domínio: 27 siglas de UF ou BR. Linhagem: gold.dim_geografia.uf_sigla; BR fixo no Brasil.',
  territorio COMMENT 'Nome do território. Domínio: Brasil e as 27 UFs. Linhagem: gold.dim_geografia.nome.',
  regiao COMMENT 'Grande região; nulo no Brasil. Domínio: cinco grandes regiões; nulo no Brasil. Linhagem: gold.dim_geografia.regiao.',
  cenario COMMENT 'A (teletrabalho IBGE), B (trabalho remoto IBGE) ou C (Remoto + Híbrido na pesquisa, teste de transferência). Domínio: A, B, C. Linhagem: constante de cada bloco da view.',
  metodo COMMENT 'Como a estimativa foi agregada. Domínio: taxa nacional × proxy do Brasil, soma das estimativas por UF, taxa da UF × proxy da UF, taxa da pesquisa × proxy do Brasil. Linhagem: constante de cada bloco da view.',
  taxa_pct COMMENT 'Taxa aplicada ao proxy, em %. Domínio: 0 a 100. Linhagem: gold.fato_teletrabalho_uf.percentual (A: 59805, B: 59804); em C, Remoto + Híbrido de brasileiros em fato_resposta_pesquisa 2022.',
  taxa_cv_classificacao COMMENT 'Faixa adotada para o CV da taxa publicado pelo IBGE; nulo no cenário C, que não tem CV. Domínio: seis faixas de CV ou nulo. Linhagem: gold.fato_teletrabalho_uf.cv_classificacao.',
  taxa_cv_pct COMMENT 'CV da taxa publicado pelo IBGE, em %; nulo no cenário C e no método soma das UFs. Domínio: real não negativo ou nulo. Linhagem: gold.fato_teletrabalho_uf.cv_percentual.',
  proxy_mil COMMENT 'Ocupados no grupamento 56624 em 2022T4, em mil. Domínio: real positivo. Linhagem: gold.fato_ocupacao_uf_atividade.pessoas_mil com atividade 56624 em 2022T4.',
  estimativa_mil COMMENT 'proxy_mil × taxa_pct / 100, em mil pessoas. Domínio: real não negativo, uma casa. Linhagem: proxy_mil × taxa_pct / 100.',
  estimativa_ic95_inf_mil COMMENT 'proxy_mil × taxa_pct × (1 − 1,96 × CV / 100) / 100; só a precisão amostral da taxa do IBGE; nulo no cenário C. Domínio: real não negativo ou nulo. Linhagem: proxy_mil × taxa_pct × (1 − 1,96 × taxa_cv_pct / 100) / 100.',
  estimativa_ic95_sup_mil COMMENT 'proxy_mil × taxa_pct × (1 + 1,96 × CV / 100) / 100; só a precisão amostral da taxa do IBGE; nulo no cenário C. Domínio: real não negativo ou nulo. Linhagem: proxy_mil × taxa_pct × (1 + 1,96 × taxa_cv_pct / 100) / 100.',
  teto_logico_mil COMMENT 'Pessoas em trabalho remoto (59804) no território, em mil: limite superior de qualquer estimativa. Domínio: real positivo. Linhagem: gold.fato_teletrabalho_uf.pessoas_mil da modalidade 59804 no território.',
  excede_teto_logico COMMENT 'true quando estimativa_mil passa de teto_logico_mil, o que invalida o cenário. Só pode ocorrer no cenário C. Domínio: true, false. Linhagem: estimativa_mil maior que teto_logico_mil.'
)
COMMENT 'Q8: Qual a estimativa de mercado endereçável no Brasil? Ordem de grandeza em pessoas: proxy 56624 em 2022T4 × taxa de teletrabalho (A), de trabalho remoto (B) ou da pesquisa (C, teste de transferência); teto lógico = total em trabalho remoto. Origem: gold.fato_ocupacao_uf_atividade, gold.fato_teletrabalho_uf e gold.fato_resposta_pesquisa, com as dimensões.'
AS
WITH proxy_uf AS (
  SELECT f.geo_chave, f.pessoas_mil AS proxy_mil
  FROM gold.fato_ocupacao_uf_atividade f
  JOIN gold.dim_periodo p ON p.periodo_chave = f.periodo_chave
  JOIN gold.dim_atividade_economica a ON a.atividade_chave = f.atividade_chave
  WHERE p.tipo_periodo = 'trimestre' AND p.ano = 2022 AND p.trimestre = 4 AND a.e_proxy_tecnologia
),
proxy_brasil AS (
  SELECT SUM(proxy_mil) AS proxy_mil FROM proxy_uf
),
teto AS (
  SELECT f.geo_chave, g.nivel, f.pessoas_mil AS teto_logico_mil
  FROM gold.fato_teletrabalho_uf f
  JOIN gold.dim_modalidade_ibge m ON m.modalidade_chave = f.modalidade_chave
  JOIN gold.dim_geografia g ON g.geo_chave = f.geo_chave
  WHERE m.modalidade_codigo = '59804'
),
teto_brasil AS (
  SELECT teto_logico_mil FROM teto WHERE nivel = 'pais'
),
taxas_ibge AS (
  SELECT
    f.geo_chave,
    g.nivel,
    CASE m.modalidade_codigo WHEN '59805' THEN 'A' ELSE 'B' END AS cenario,
    f.percentual AS taxa_pct,
    f.cv_classificacao AS taxa_cv_classificacao,
    f.cv_percentual AS taxa_cv_pct
  FROM gold.fato_teletrabalho_uf f
  JOIN gold.dim_modalidade_ibge m ON m.modalidade_chave = f.modalidade_chave
  JOIN gold.dim_geografia g ON g.geo_chave = f.geo_chave
  WHERE m.modalidade_codigo IN ('59804', '59805')
),
por_uf AS (
  SELECT 'uf' AS nivel, g.uf_sigla, g.nome AS territorio, g.regiao, t.cenario,
         'taxa da UF × proxy da UF' AS metodo, t.taxa_pct, t.taxa_cv_classificacao, t.taxa_cv_pct, x.proxy_mil,
         x.proxy_mil * t.taxa_pct / 100 AS estimativa_mil,
         x.proxy_mil * t.taxa_pct * (1 - 1.96 * t.taxa_cv_pct / 100) / 100 AS estimativa_inf,
         x.proxy_mil * t.taxa_pct * (1 + 1.96 * t.taxa_cv_pct / 100) / 100 AS estimativa_sup
  FROM proxy_uf x
  JOIN taxas_ibge t ON t.geo_chave = x.geo_chave AND t.nivel = 'uf'
  JOIN gold.dim_geografia g ON g.geo_chave = x.geo_chave
),
taxa_survey AS (
  SELECT 100 * try_divide(
           SUM(CASE WHEN a.arranjo IN ('Remoto', 'Híbrido') THEN f.qtd_respondentes ELSE 0 END),
           SUM(f.qtd_respondentes)
         ) AS taxa_pct
  FROM gold.fato_resposta_pesquisa f
  JOIN gold.dim_periodo p ON p.periodo_chave = f.periodo_chave
  JOIN gold.dim_geografia g ON g.geo_chave = f.geo_chave
  JOIN gold.dim_arranjo_trabalho a ON a.arranjo_chave = f.arranjo_chave
  WHERE p.ano = 2022
    AND g.nivel = 'pais' AND g.codigo = 'Brazil'
    AND f.trabalhando
    AND a.arranjo NOT IN ('Não informado', 'Desconhecido')
)
SELECT u.nivel, u.uf_sigla, u.territorio, u.regiao, u.cenario, u.metodo, ROUND(u.taxa_pct, 2) AS taxa_pct,
       u.taxa_cv_classificacao, ROUND(u.taxa_cv_pct, 2) AS taxa_cv_pct, u.proxy_mil, ROUND(u.estimativa_mil, 1) AS estimativa_mil,
       ROUND(u.estimativa_inf, 1) AS estimativa_ic95_inf_mil, ROUND(u.estimativa_sup, 1) AS estimativa_ic95_sup_mil,
       tt.teto_logico_mil, u.estimativa_mil > tt.teto_logico_mil AS excede_teto_logico
FROM por_uf u
JOIN gold.dim_geografia g ON g.nivel = 'uf' AND g.uf_sigla = u.uf_sigla
JOIN teto tt ON tt.geo_chave = g.geo_chave
UNION ALL
SELECT 'pais', 'BR', 'Brasil', CAST(NULL AS STRING), u.cenario, 'soma das estimativas por UF',
       CAST(NULL AS DOUBLE), CAST(NULL AS STRING), CAST(NULL AS DOUBLE), SUM(u.proxy_mil), ROUND(SUM(u.estimativa_mil), 1),
       ROUND(SUM(u.estimativa_inf), 1), ROUND(SUM(u.estimativa_sup), 1),
       MAX(tb.teto_logico_mil), SUM(u.estimativa_mil) > MAX(tb.teto_logico_mil)
FROM por_uf u
CROSS JOIN teto_brasil tb
GROUP BY u.cenario
UNION ALL
SELECT 'pais', 'BR', 'Brasil', CAST(NULL AS STRING), t.cenario, 'taxa nacional × proxy do Brasil (soma das UFs)',
       ROUND(t.taxa_pct, 2), t.taxa_cv_classificacao, ROUND(t.taxa_cv_pct, 2), b.proxy_mil, ROUND(b.proxy_mil * t.taxa_pct / 100, 1),
       ROUND(b.proxy_mil * t.taxa_pct * (1 - 1.96 * t.taxa_cv_pct / 100) / 100, 1),
       ROUND(b.proxy_mil * t.taxa_pct * (1 + 1.96 * t.taxa_cv_pct / 100) / 100, 1),
       tb.teto_logico_mil, b.proxy_mil * t.taxa_pct / 100 > tb.teto_logico_mil
FROM taxas_ibge t
CROSS JOIN proxy_brasil b
CROSS JOIN teto_brasil tb
WHERE t.nivel = 'pais'
UNION ALL
SELECT 'pais', 'BR', 'Brasil', CAST(NULL AS STRING), 'C', 'taxa da pesquisa (Brasil, 2022) × proxy do Brasil',
       ROUND(s.taxa_pct, 2), CAST(NULL AS STRING), CAST(NULL AS DOUBLE), b.proxy_mil, ROUND(b.proxy_mil * s.taxa_pct / 100, 1),
       CAST(NULL AS DOUBLE), CAST(NULL AS DOUBLE),
       tb.teto_logico_mil, b.proxy_mil * s.taxa_pct / 100 > tb.teto_logico_mil
FROM taxa_survey s
CROSS JOIN proxy_brasil b
CROSS JOIN teto_brasil tb;

-- COMMAND ----------

-- Tabela Q8: Brasil por cenário e método (a ordem de grandeza) e UFs do cenário A ordenadas pela estimativa.
SELECT nivel, uf_sigla, territorio, cenario, metodo, taxa_pct, taxa_cv_classificacao, taxa_cv_pct, proxy_mil, estimativa_mil,
       estimativa_ic95_inf_mil, estimativa_ic95_sup_mil, teto_logico_mil, excede_teto_logico
FROM gold.vw_q8_mercado_brasil
WHERE nivel = 'pais' OR cenario = 'A'
ORDER BY CASE nivel WHEN 'pais' THEN 0 ELSE 1 END, cenario, estimativa_mil DESC;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Apoio à qualidade: distribuição da remuneração por safra (verificação C19)
-- MAGIC
-- MAGIC O gráfico usa quantis agregados: o gráfico sai de cinco números por safra. Os valores estão no
-- MAGIC câmbio de cada safra, então não se comparam entre anos sem ressalva.

-- COMMAND ----------

-- Gráfico C19: caixa construída com p01, p25, p50, p75 e p99 por safra, em escala logarítmica.
SELECT
  safra,
  COUNT(remuneracao_usd) AS n_com_remuneracao,
  COUNT_IF(remuneracao_outlier) AS outliers_marcados,
  PERCENTILE_CONT(0.01) WITHIN GROUP (ORDER BY remuneracao_usd) AS p01,
  PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY remuneracao_usd) AS p25,
  PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY remuneracao_usd) AS p50,
  PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY remuneracao_usd) AS p75,
  PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY remuneracao_usd) AS p99
FROM gold.fato_resposta_pesquisa
WHERE remuneracao_usd IS NOT NULL
GROUP BY safra
ORDER BY safra;
