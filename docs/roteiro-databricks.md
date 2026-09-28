# Roteiro de execução no Databricks

Passo a passo para reproduzir o pipeline no Databricks Free Edition. O procedimento reproduz o fluxo da execução documentada.

A Free Edition tem cota de uso diária. Se ela estourar, o compute fica parado até o dia seguinte. As cargas
analíticas substituem as tabelas inteiras, enquanto o histórico atualiza os resultados da execução por chave. Depois
da liberação da cota, a retomada usa o recurso Repair run do job, a partir da tarefa interrompida.

## 1 Baixar e conferir os arquivos

```bash
bash scripts/baixar_fontes.sh
shasum -a 256 dados/stackoverflow/*/*.csv dados/ibge/*.json
```

Compare os sha256 com os de [`evidencias/EXTRACAO.txt`](../evidencias/EXTRACAO.txt). Se algum for diferente, os
arquivos são de outra extração, e as contagens esperadas pelos notebooks não valem para eles. Se um `results.csv` tiver
134 bytes, é o ponteiro do Git LFS: rode o script de novo.

## 2 Ligar o repositório ao workspace

1. Em *Settings › Linked accounts*, conecte a conta do GitHub.
2. Em *Workspace › Create › Git folder*, informe `https://github.com/amarok30/mvp-engenharia-dados`.
3. Rode o notebook `notebooks/00_setup_catalogo` com compute **Serverless**. Ele cria o catálogo `mafia_office`, os
   schemas `bronze`, `silver` e `gold` e o Volume `bronze.pouso`.

## 3 Enviar os arquivos para o Volume

Pela interface, crie as pastas no Volume (*Create directory*) e envie cada arquivo para a sua:

**Quadro 1 - Enviar os arquivos para o Volume**

| Pasta no Volume | Arquivos |
|---|---|
| `stackoverflow/2022` a `stackoverflow/2025` | `results.csv` e `schema.csv` de cada safra |
| `ibge` | `sidra_9471.json` e `sidra_5434.json` |
| `referencia` | `docs/mapa-de-para-arranjo.csv` |

Fonte: elaborado pelo autor (2026), com base nas fontes e regras indicadas no texto.

Ou, com a CLI do Databricks:

```bash
databricks fs cp -r --overwrite dados/stackoverflow dbfs:/Volumes/mafia_office/bronze/pouso/stackoverflow
databricks fs cp -r --overwrite dados/ibge dbfs:/Volumes/mafia_office/bronze/pouso/ibge
databricks fs cp --overwrite docs/mapa-de-para-arranjo.csv dbfs:/Volumes/mafia_office/bronze/pouso/referencia/
```

## 4 Criar e rodar o job

Na primeira vez:

```bash
databricks jobs create --json @jobs/pipeline.json
databricks jobs run-now <id_do_job>
```

Para atualizar um job que já existe:

```bash
jq '{job_id: <id_do_job>, new_settings: .}' jobs/pipeline.json > /tmp/job.json
databricks jobs reset --json @/tmp/job.json
```

O job lê os notebooks direto da branch `main` do GitHub e passa o id da execução no parâmetro `job_run_id`. As duas
fontes seguem em paralelo até a Silver. O gatilho por chegada de arquivo na pasta `stackoverflow/` do Volume fica
pausado; sua ativação exige primeiro atualizar os mapas e as regras para a safra 2026.

Se uma tarefa falhar, as seguintes não rodam. Corrija e use *Repair run* a partir da tarefa que falhou. Se a Silver
tiver sido gravada com problema, volte a versão anterior:

```sql
DESCRIBE HISTORY mafia_office.silver.so_respondente;
RESTORE TABLE mafia_office.silver.so_respondente TO VERSION AS OF <versão>;
```

Recriar uma tabela apaga os comentários dela. Se rodar sozinho qualquer notebook de 01 a 07, rode depois o 09 e o 10.

## 5 Exportar o que vai para o repositório

**Quadro 2 - Exportar o que vai para o repositório**

| O quê | Como | Destino |
|---|---|---|
| Catálogo e qualidade por atributo em Markdown | Baixar `catalogo-de-dados.md`, `catalogo-bronze.md` e `qualidade-por-atributo.md` da pasta `exportacao/` do Volume | `docs/` |
| Domínios da captura | Baixar `dominios-captura.json` da pasta `exportacao/` do Volume | `docs/dominios-captura.json` |
| Views da Gold | Exportar cada view como CSV | `evidencias/views/` |
| Verificações | `SELECT * FROM mafia_office.gold.verificacoes_qualidade ORDER BY verificacao_id`, exportado como CSV | `evidencias/verificacoes-qualidade.csv` |
| Linhagem de tabela | Consulta 1 abaixo, exportada como CSV | `evidencias/linhagem-unity-catalog.csv` |
| Linhagem de coluna | Consulta 2 abaixo, exportada como CSV | `evidencias/linhagem-colunas-unity-catalog.csv` |
| Tags | Consulta 3 abaixo, exportada como CSV | `evidencias/tags-unity-catalog.csv` |
| Tarefas da execução | Consulta 4 abaixo, exportada como CSV | `evidencias/execucao-job.csv` |
| Notebooks com saída | `databricks jobs export-run <id_da_tarefa> --views-to-export CODE` para cada tarefa da execução final | `docs/notebooks-html/` |
| Gráficos | `python3 scripts/gerar_graficos.py` | `docs/img/` |

Fonte: elaborado pelo autor (2026), com base nas fontes e regras indicadas no texto.

```sql
-- 1. Linhagem entre tabelas do catálogo, desde a data da execução final
SELECT source_table_full_name, target_table_full_name, entity_type, entity_id, event_time
FROM system.access.table_lineage
WHERE target_table_catalog = 'mafia_office' AND event_date >= '<data da execução>'
ORDER BY target_table_full_name, source_table_full_name;

-- 2. Linhagem entre colunas
SELECT source_table_full_name, source_column_name, target_table_full_name, target_column_name, entity_type, event_time
FROM system.access.column_lineage
WHERE target_table_catalog = 'mafia_office' AND event_date >= '<data da execução>'
ORDER BY target_table_full_name, target_column_name;

-- 3. Tags de tabela, view e coluna
SELECT 'tabela' AS objeto, schema_name, table_name, NULL AS column_name, tag_name, tag_value
FROM mafia_office.information_schema.table_tags
UNION ALL
SELECT 'coluna', schema_name, table_name, column_name, tag_name, tag_value
FROM mafia_office.information_schema.column_tags
ORDER BY schema_name, table_name, column_name, tag_name;

-- 4. Duração de cada tarefa da execução final
SELECT task_key, period_start_time, period_end_time, result_state
FROM system.lakeflow.job_task_run_timeline
WHERE job_run_id = <id_da_execução>
ORDER BY period_start_time;
```

## 6 Conferir que rodar de novo dá o mesmo resultado

Rode o job duas vezes seguidas. Depois:

```sql
DESCRIBE HISTORY mafia_office.gold.fato_resposta_pesquisa;

-- n é a versão mais recente; o esperado é zero linhas nas duas consultas
SELECT * FROM mafia_office.gold.fato_resposta_pesquisa VERSION AS OF <n>
EXCEPT ALL
SELECT * FROM mafia_office.gold.fato_resposta_pesquisa VERSION AS OF <n - 1>;

SELECT * FROM mafia_office.gold.fato_resposta_pesquisa VERSION AS OF <n - 1>
EXCEPT ALL
SELECT * FROM mafia_office.gold.fato_resposta_pesquisa VERSION AS OF <n>;
```

## 7 Capturas de tela

As capturas ficam em `evidencias/`. As nove capturas finais de 27 set. 2026 estão identificadas, com seus hashes, no [manifesto da execução](../evidencias/execucao-validada.json). As demais imagens ilustram a configuração do ambiente. Os recortes preservam os títulos, eixos, legendas e conteúdo dos painéis, sem os menus e avisos externos da interface.

**Quadro 3 - Prints**

| Arquivo | O que mostrar |
|---|---|
| `print-01-catalogo.png` | Catalog Explorer com `mafia_office` aberto nos schemas bronze, silver e gold |
| `print-02-volume.png` | Volume `pouso` com as pastas |
| `print-03-diagrama.png` | Diagrama de relacionamento da `fato_resposta_pesquisa` (*View relationships*) |
| `print-04-comentarios.png` | Uma tabela da Gold com a descrição das colunas e as tags |
| `print-05-linhagem.png` | Aba de linhagem da `fato_resposta_pesquisa`, numa captura só |
| `print-06-job.png` | Lista da execução final com as treze tarefas concluídas e o painel *Run details* aberto, com o id e a data |
| `print-07-verificacoes.png` | `SELECT resultado, COUNT(*) FROM mafia_office.gold.verificacoes_qualidade GROUP BY resultado` no SQL Editor |
| `print-08-dashboard.png` | Recorte da página Q1 a Q4: evolução do arranjo e modelo ajustado |
| `print-09-git.png` | Pasta Git ligada ao repositório |
| `print-10-dashboard-q5-q8.png` | Recorte da página Q5 a Q8: satisfação e premissas dos cenários |
| `print-11-dashboard-cenarios.png` | Série da Q7 e tabela dos cenários da Q8 |
| `print-14-dashboard-qualidade.png` | Resumo das 32 verificações e detalhe das primeiras regras |
| `print-15-dashboard-q2-q3.png` | Q3 à esquerda: Brasil e resto do mundo; Q2 à direita: arranjo por porte em 2025 |
| `print-16-dashboard-q4.png` | Os seis perfis mais e os seis menos remotos em 2025 |
| `print-17-dashboard-q6.png` | Teletrabalho por UF em 2022, com cores pela precisão do coeficiente de variação |
| `print-12-qualidade-atributo.png` (opcional) | `SELECT * FROM mafia_office.gold.qualidade_por_atributo` no SQL Editor |
| `print-13-historico-delta.png` (opcional) | `DESCRIBE HISTORY mafia_office.gold.fato_resposta_pesquisa`, com duas execuções seguidas |

Fonte: elaborado pelo autor (2026), com base nas fontes e regras indicadas no texto.

## 8 Validação local e testes

Os testes de transformação usam as mesmas funções da Silver executadas pelos notebooks.
Para rodar a suíte no ambiente Python com Spark e Delta:

```bash
python -m pytest testes/ -q
```

O executor [`testes/validacao_local.py`](../testes/validacao_local.py) verifica a integração sobre os arquivos baixados:

```bash
python testes/validacao_local.py
```

O ambiente local usa Java 17 e Python com as dependências abaixo. Com o ambiente virtual ativo:

```bash
python -m pip install pyspark==3.5.5 delta-spark==3.3.2 sqlparse pytest statsmodels==0.15.0 pandas numpy scipy matplotlib
```

Spark e Delta executam as transformações; statsmodels e suas dependências executam o modelo da Q1.
Matplotlib é usado na geração das figuras. O Java 17 precisa estar disponível no PATH ou no JAVA_HOME.
A variável `VALIDACAO_BASE` permite usar outra pasta para dados temporários. O executor traduz catálogo, Volume e
metadados para o Spark local. Células Python e SQL são executadas; texto Markdown é ignorado. Permissões, tags,
PK/FK informativas e o job são verificados apenas no Databricks.

A validação executa o pipeline duas vezes e compara contagens e hashes do conteúdo analítico. Timestamps de execução
e tabelas históricas ficam fora dessa comparação por variarem por desenho. Também repete o notebook 05 depois do 07
para verificar a preservação de C15. Qualquer divergência torna o comando malsucedido.

O [workflow opcional](../.github/workflows/verificacoes.yml) está configurado para acionamento manual. O GitHub Actions
não é requisito para reproduzir o MVP: os testes podem ser executados localmente e o pipeline, no Databricks.
Uma execução impedida por limite da conta não comprova aprovação nem reprovação dos testes. As evidências da entrega
devem registrar os testes efetivamente executados e o estado do job na nuvem.
