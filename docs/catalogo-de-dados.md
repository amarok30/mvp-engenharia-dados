# Catálogo de dados

> Arquivo **gerado** pelo notebook `notebooks/10_gerar_catalogo_markdown.py` a partir de `mafia_office.information_schema` em 2026-09-27 18:50 UTC. Não edite à mão: altere os `COMMENT ON` em `notebooks/09_catalogo_comentarios.sql`, reexecute o 09 e depois o 10.

Cada descrição de coluna segue o padrão **o que é · domínio · linhagem**. A linhagem coluna a coluna entre as camadas também está em [`linhagem.md`](linhagem.md), escrita à mão e independente da aba de linhagem do Unity Catalog.

## Sumário

- **silver**
  - `silver.ibge_ocupados_uf_atividade`
  - `silver.ibge_teletrabalho_uf`
  - `silver.so_de_para_arranjo`
  - `silver.so_metadados_pergunta`
  - `silver.so_respondente`
- **gold**
  - `gold.analise_q1d_modelo_logistico`
  - `gold.dim_arranjo_trabalho`
  - `gold.dim_atividade_economica`
  - `gold.dim_geografia`
  - `gold.dim_modalidade_ibge`
  - `gold.dim_perfil_dev`
  - `gold.dim_periodo`
  - `gold.dim_porte_empresa`
  - `gold.fato_ocupacao_uf_atividade`
  - `gold.fato_resposta_pesquisa`
  - `gold.fato_teletrabalho_uf`
  - `gold.qualidade_por_atributo`
  - `gold.verificacoes_qualidade`
  - `gold.verificacoes_qualidade_historico`
  - `gold.vw_q1_evolucao_arranjo`
  - `gold.vw_q1_remoto_por_vinculo`
  - `gold.vw_q2_arranjo_por_porte`
  - `gold.vw_q3_brasil_x_resto_mundo`
  - `gold.vw_q4_perfil_remoto`
  - `gold.vw_q5_arranjo_satisfacao`
  - `gold.vw_q6_teletrabalho_uf`
  - `gold.vw_q7_ocupacao_proxy_tecnologia_uf`
  - `gold.vw_q8_mercado_brasil`

## Schema `silver`

### `silver.ibge_ocupados_uf_atividade`

*tabela* · Grão: UF × trimestre × grupamento de atividade no trabalho principal. Pessoas de 14 anos ou mais ocupadas, PNAD Contínua. Origem: bronze.ibge_sidra_5434 sem o cabeçalho d[0].

**Quadro 1 - Atributos de `silver.ibge_ocupados_uf_atividade`**

| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |
|---|---|---|---|---|
| 1 | `uf_codigo` | `string` | 0 de 20.358 | Código IBGE da UF. Domínio: dois dígitos, 27 UFs. Linhagem: DnC da dimensão territorial. |
| 2 | `uf_nome` | `string` | 0 de 20.358 | Nome da UF. Domínio: 27 UFs. Linhagem: DnN da dimensão territorial. |
| 3 | `ano` | `int` | 0 de 20.358 | Ano do trimestre. Domínio: 2012 em diante. Linhagem: quatro primeiros caracteres de periodo_codigo. |
| 4 | `trimestre` | `int` | 0 de 20.358 | Trimestre do ano. Domínio: 1 a 4. Linhagem: dois últimos caracteres de periodo_codigo. |
| 5 | `periodo_codigo` | `string` | 0 de 20.358 | Código de período do SIDRA. Domínio: AAAATT (ex.: 202204). Linhagem: DnC da dimensão de período, sem transformação. |
| 6 | `atividade_codigo` | `string` | 0 de 20.358 | Código do grupamento de atividade (classificação c888). Domínio: 13 códigos, incluindo 47946 Total, que soma os demais. Linhagem: DnC da classificação. |
| 7 | `atividade_nome` | `string` | 0 de 20.358 | Nome do grupamento de atividade conforme o IBGE. Domínio: rótulos da classificação c888. Linhagem: DnN da classificação. |
| 8 | `e_proxy_tecnologia` | `boolean` | 0 de 20.358 | Marca o grupamento usado como proxy de tecnologia. Domínio: true só para 56624 (Informação, comunicação e atividades financeiras, imobiliárias, profissionais e administrativas). Linhagem: atividade_codigo igual a 56624. Premissa: mais amplo que TI. |
| 9 | `pessoas_mil` | `double` | 0 de 20.358 | Estimativa de pessoas ocupadas, em mil. Domínio: real não negativo; 0 quando o sinal é -; nulo quando o sinal é .., ... ou x. Linhagem: campo V da variável 4090. Não somar grupamentos livremente: 47946 é o Total e 60031 está contido em 47948 (verificação C24). |
| 10 | `pessoas_mil_sinal` | `string` | 19.449 de 20.358 | Sinal convencional do IBGE na célula (Normas de apresentação tabular). Domínio: nulo quando a célula traz número; - (zero não resultante de arredondamento, valor 0); .. (não se aplica); ... (não disponível); x (omitido por sigilo); nos três últimos o valor é nulo. Linhagem: campo V da variável 4090. |

Fonte: o autor (2026), com base nos metadados e nas contagens do pipeline.

### `silver.ibge_teletrabalho_uf`

*tabela* · Grão: território (Brasil ou UF) × modalidade de trabalho remoto ou teletrabalho, 2022 (4º trimestre). Módulo de teletrabalho divulgado para 2022; não foi localizada edição posterior com esse recorte, então não há série. Origem: bronze.ibge_sidra_9471 sem o cabeçalho d[0], variáveis pivotadas.

**Quadro 2 - Atributos de `silver.ibge_teletrabalho_uf`**

| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |
|---|---|---|---|---|
| 1 | `nivel_territorial` | `string` | 0 de 168 | Nível do território. Domínio: pais (Brasil), uf. Linhagem: campo NC do SIDRA (1 para Brasil, 3 para UF). |
| 2 | `uf_codigo` | `string` | 0 de 168 | Código IBGE do território. Domínio: 1 para Brasil; dois dígitos para UF. Linhagem: campo DnC da dimensão territorial, identificada pelo rótulo do cabeçalho. |
| 3 | `uf_nome` | `string` | 0 de 168 | Nome do território. Domínio: Brasil e as 27 UFs. Linhagem: campo DnN da dimensão territorial. |
| 4 | `ano` | `int` | 0 de 168 | Ano de referência. Domínio: 2022 (PNAD Contínua anual, 4º trimestre, segundo a nota da tabela 9471). Linhagem: quatro primeiros caracteres do código de período do SIDRA. |
| 5 | `modalidade_codigo` | `string` | 0 de 168 | Código da classificação c1675. Domínio: 59803 Total, 59804 Realizou trabalho remoto, 59805 Realizou teletrabalho, 59806 Teletrabalho no domicílio, 59807 Fora do domicílio, 59808 No domicílio e fora. Linhagem: DnC da classificação. |
| 6 | `modalidade` | `string` | 0 de 168 | Nome da modalidade conforme o IBGE. Domínio: rótulos da classificação c1675. Linhagem: DnN da classificação. Teletrabalho do IBGE não é o Remoto autodeclarado da pesquisa. |
| 7 | `pessoas_mil` | `double` | 0 de 168 | Estimativa de pessoas de 14 anos ou mais ocupadas na modalidade, em mil. Domínio: real não negativo; nulo quando pessoas_mil_sinal é .., ... ou x. Linhagem: campo V da variável 4090, pivotado. Modalidades não se somam (verificação C23). |
| 8 | `pessoas_mil_sinal` | `string` | 168 de 168 | Sinal convencional do IBGE na célula (Normas de apresentação tabular). Domínio: nulo quando a célula traz número; - (zero não resultante de arredondamento, valor 0); .. (não se aplica); ... (não disponível); x (omitido por sigilo); nos três últimos o valor é nulo. Linhagem: campo V da variável 4090. |
| 9 | `cv_pessoas` | `double` | 0 de 168 | Coeficiente de variação de pessoas_mil, em %. Domínio: real não negativo. Linhagem: campo V da variável 4091, pivotado. |
| 10 | `cv_pessoas_sinal` | `string` | 168 de 168 | Sinal convencional do IBGE na célula (Normas de apresentação tabular). Domínio: nulo quando a célula traz número; - (zero não resultante de arredondamento, valor 0); .. (não se aplica); ... (não disponível); x (omitido por sigilo); nos três últimos o valor é nulo. Linhagem: campo V da variável 4091. |
| 11 | `cv_pessoas_classificacao` | `string` | 0 de 168 | Faixa de CV adotada no projeto sobre o cv_pessoas publicado pelo IBGE (convenção, não classificação do IBGE). Domínio: Exata, Ótima, Boa, Razoável, Pouco precisa, Imprecisa; nulo sem CV. Linhagem: derivada de cv_pessoas. |
| 12 | `percentual` | `double` | 0 de 168 | Percentual publicado pelo IBGE para a modalidade. Domínio: 0 a 100. Linhagem: campo V da variável 12965, com precisão máxima (/d/m), pivotado. |
| 13 | `percentual_sinal` | `string` | 168 de 168 | Sinal convencional do IBGE na célula (Normas de apresentação tabular). Domínio: nulo quando a célula traz número; - (zero não resultante de arredondamento, valor 0); .. (não se aplica); ... (não disponível); x (omitido por sigilo); nos três últimos o valor é nulo. Linhagem: campo V da variável 12965. |
| 14 | `cv_percentual` | `double` | 0 de 168 | Coeficiente de variação do percentual, em %. Domínio: real não negativo; 0 no Total, publicado com o sinal - (zero não resultante de arredondamento). Linhagem: campo V da variável 12966, com precisão máxima (/d/m), pivotado. |
| 15 | `cv_percentual_sinal` | `string` | 140 de 168 | Sinal convencional do IBGE na célula (Normas de apresentação tabular). Domínio: nulo quando a célula traz número; - (zero não resultante de arredondamento, valor 0); .. (não se aplica); ... (não disponível); x (omitido por sigilo); nos três últimos o valor é nulo. Linhagem: campo V da variável 12966. |
| 16 | `cv_classificacao` | `string` | 0 de 168 | Faixa de CV adotada no projeto sobre o cv_percentual publicado pelo IBGE (convenção, não classificação do IBGE). Domínio: Exata (0), Ótima (até 5), Boa (mais de 5 até 15), Razoável (mais de 15 até 30), Pouco precisa (mais de 30 até 50), Imprecisa (mais de 50); nulo sem CV. Linhagem: derivada de cv_percentual. |
| 17 | `estimativa_confiavel` | `boolean` | 0 de 168 | CV publicado pelo IBGE; o limiar de 15% é critério do projeto. Domínio: true quando cv_percentual até 15 (Exata, Ótima ou Boa), false acima, nulo sem CV. Linhagem: derivada de cv_percentual. |
| 18 | `disponivel_no_nivel` | `boolean` | 0 de 168 | Indica se o IBGE declara a categoria disponível no nível territorial da linha. Domínio: false para 59807 e 59808 por UF (a nota da tabela 9471 as declara só para Brasil e Grande Região), true nas demais. Linhagem: nivel_territorial e modalidade_codigo; medido na verificação C28. |
| 19 | `e_experimental` | `boolean` | 0 de 168 | Marca estatística experimental do IBGE. Domínio: sempre true. Linhagem: constante; o nome da tabela 9471 no SIDRA termina em Estatísticas experimentais. |

Fonte: o autor (2026), com base nos metadados e nas contagens do pipeline.

### `silver.so_de_para_arranjo`

*tabela* · De-para versionado do arranjo de trabalho, uma linha por valor de origem em cada safra, incluindo o nulo. 15 linhas. Origem: docs/mapa-de-para-arranjo.csv no Git, enviado ao Volume bronze.pouso/referencia.

**Quadro 3 - Atributos de `silver.so_de_para_arranjo`**

| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |
|---|---|---|---|---|
| 1 | `safra` | `int` | 1 de 15 | Safra em que o rótulo existe. Domínio: 2022 a 2025; nulo significa todas as safras (linha do valor nulo). Linhagem: coluna safra do CSV, com todas convertido para nulo. |
| 2 | `valor_origem` | `string` | 1 de 15 | Rótulo literal de RemoteWork na safra. Domínio: opções da pesquisa; nulo representa resposta ausente. Linhagem: coluna valor_origem do CSV, campo vazio lido como nulo. |
| 3 | `valor_canonico` | `string` | 0 de 15 | Categoria harmonizada. Domínio: Remoto, Híbrido, Presencial, Flexível, Não informado. Linhagem: coluna valor_canonico do CSV versionado no Git. |
| 4 | `entra_serie_historica` | `boolean` | 0 de 15 | Indica se o rótulo entra na série comparável 2022 a 2025. Domínio: true, false. Linhagem: coluna do CSV convertida para BOOLEAN. |
| 5 | `observacao` | `string` | 6 de 15 | Justificativa do mapeamento, incluindo perda de granularidade em 2025 e ausência de equivalente para Your choice. Domínio: texto livre. Linhagem: coluna observacao do CSV. |

Fonte: o autor (2026), com base nos metadados e nas contagens do pipeline.

### `silver.so_metadados_pergunta`

*tabela* · Uma linha por pergunta (qname) em cada safra, inclusive quando a pergunta não existia. Mostra que o texto de RemoteWork é o mesmo nas quatro safras, embora as opções tenham mudado. Origem: bronze.so_esquema.

**Quadro 4 - Atributos de `silver.so_metadados_pergunta`**

| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |
|---|---|---|---|---|
| 1 | `safra` | `int` | 0 de 864 | Safra. Domínio: 2022 a 2025. Linhagem: _safra de bronze.so_esquema, completada por produto cartesiano com as quatro safras. |
| 2 | `qname` | `string` | 0 de 864 | Nome curto da pergunta, igual ao nome de coluna do results.csv quando a pergunta é de resposta única. Domínio: identificador sem espaço, 383 distintos nas quatro safras. Linhagem: qname de bronze.so_esquema. |
| 3 | `texto_pergunta` | `string` | 481 de 864 | Texto da pergunta. Domínio: texto; nulo quando a pergunta não existia na safra. Linhagem: question de bronze.so_esquema; se o qname se repete na safra (subperguntas de 2025), o menor texto em ordem alfabética. |
| 4 | `tipo` | `string` | 481 de 864 | Tipo da pergunta segundo a pesquisa. Domínio: códigos do schema.csv. Linhagem: type de bronze.so_esquema, menor valor por (safra, qname). |
| 5 | `presente_na_safra` | `boolean` | 0 de 864 | Indica se a pergunta existia na safra. Domínio: true, false. Linhagem: texto_pergunta não nulo. Distingue ausência estrutural de não resposta. |

Fonte: o autor (2026), com base nos metadados e nas contagens do pipeline.

### `silver.so_respondente`

*tabela* · Grão: um respondente da Stack Overflow Developer Survey em uma safra. Chave (safra, resposta_id). 277.080 linhas (2022 a 2025). Representação validada e não agregada; sem modelo estrela. Origem: bronze.so_pesquisa_2022 a 2025.

**Quadro 5 - Atributos de `silver.so_respondente`**

| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |
|---|---|---|---|---|
| 1 | `safra` | `int` | 0 de 277.080 | Ano da edição da pesquisa. Domínio: 2022, 2023, 2024, 2025. Linhagem: coluna de auditoria _safra da tabela bronze.so_pesquisa_{ano}. |
| 2 | `resposta_id` | `bigint` | 0 de 277.080 | Identificador da resposta dentro da safra. Domínio: inteiro positivo, único por safra e repetido entre safras (a chave exige a safra). Linhagem: ResponseId, convertido de STRING para BIGINT. |
| 3 | `e_profissional` | `boolean` | 0 de 277.080 | Indica desenvolvedor de profissão. Domínio: true, false, nulo quando MainBranch ausente. Linhagem: MainBranch igual a I am a developer by profession, após normalização Unicode. |
| 4 | `empregado` | `boolean` | 0 de 277.080 | Indica vínculo empregatício. Domínio: true, false. Linhagem: Employment; algum item é Employed (2025, resposta única) ou começa com Employed, (2022 a 2024: full-time ou part-time, multi-resposta). Freelancer e autônomo ficam false. |
| 5 | `autonomo` | `boolean` | 0 de 277.080 | Indica trabalho autônomo. Domínio: true, false. Linhagem: algum item de Employment é Independent contractor, freelancer, or self-employed (rótulo igual nas quatro safras). |
| 6 | `trabalhando` | `boolean` | 0 de 277.080 | Indica quem trabalha, população à qual a pergunta de arranjo se aplica e base das views Q1 a Q5. Domínio: true, false. Linhagem: empregado OR autonomo. |
| 7 | `arranjo_trabalho_origem` | `string` | 0 de 277.080 | Resposta original sobre situação de trabalho, cópia fiel, nunca sobrescrita. Domínio: rótulos da safra (ver silver.so_de_para_arranjo) ou NA. Linhagem: RemoteWork sem transformação. Não equivale a teletrabalho do IBGE. |
| 8 | `arranjo_trabalho` | `string` | 0 de 277.080 | Arranjo de trabalho harmonizado entre safras. Domínio: Remoto, Híbrido, Presencial, Flexível, Não informado. Linhagem: RemoteWork (NA e vazio viram nulo) mapeado por JOIN com silver.so_de_para_arranjo por (safra, valor); valor sem mapeamento derruba o notebook 03. Conceito autodeclarado da pesquisa, não comparável ao teletrabalho do IBGE. |
| 9 | `comparavel_serie` | `boolean` | 0 de 277.080 | Indica se o arranjo entra na série 2022 a 2025. Domínio: true, false. Linhagem: arranjo_trabalho fora de Flexível e Não informado. |
| 10 | `pais` | `string` | 22.969 de 277.080 | País declarado pelo respondente, nome em inglês. Domínio: nomes da lista da pesquisa; nulo quando ausente. Linhagem: Country com NA e vazio para nulo, normalização Unicode e trim. |
| 11 | `e_brasil` | `boolean` | 0 de 277.080 | Indica respondente do Brasil. Domínio: true, false. Linhagem: pais igual a Brazil. Subamostra pequena (825 em 2025): usar só no agregado nacional. |
| 12 | `porte_empresa_origem` | `string` | 79.340 de 277.080 | Porte da empresa como declarado. Domínio: rótulos da safra (10 em 2022 a 2024, 9 em 2025). Linhagem: OrgSize com NA e vazio para nulo e normalização Unicode (apóstrofo U+2019 para ASCII). |
| 13 | `porte_empresa` | `string` | 79.340 de 277.080 | Faixa canônica de porte. Domínio: Autônomo, Menos de 20, 20 a 99, 100 a 499, 500 a 999, 1.000 a 4.999, 5.000 a 9.999, 10.000 ou mais, Não sabe; nulo se rótulo não mapeado. Linhagem: porte_empresa_origem por mapa fixo; 2 to 9 e 10 to 19 (2022 a 2024) e Less than 20 (2025) viram Menos de 20. |
| 14 | `porte_ordem` | `int` | 79.340 de 277.080 | Ordem da faixa de porte para ordenação. Domínio: 1 a 9. Linhagem: mesmo mapa de porte_empresa. |
| 15 | `perfil_principal` | `string` | 35.781 de 277.080 | Perfil profissional principal. Domínio: rótulos de DevType da safra; nulo quando ausente. Linhagem: primeiro item de DevType antes do ; (multi-resposta só em 2022; resposta única de 2023 a 2025, e em 2025 a pergunta inclui o emprego de mais tempo no último ano), com trim. Perfis de 2022 não se comparam aos seguintes. |
| 16 | `anos_codando` | `int` | 15.403 de 277.080 | Anos programando, incluindo anos de estudo (não é experiência profissional). Domínio: 0 a 50, censurado nas pontas. Linhagem: YearsCode; Less than 1 year vira 0; More than 50 years (2022 a 2024) e valores numéricos acima de 50 (2025, sem teto na fonte) viram 50; negativo ou não numérico vira nulo. |
| 17 | `faixa_experiencia` | `string` | 15.403 de 277.080 | Faixa de anos codando. Domínio: 0–2, 3–5, 6–10, 11–20, 21+; nulo quando anos_codando nulo. Linhagem: derivada de anos_codando. |
| 18 | `remuneracao_usd` | `double` | 143.608 de 277.080 | Remuneração anual convertida para dólar pela própria Stack Overflow. Domínio: real não negativo. Linhagem: ConvertedCompYearly para DOUBLE. Usa o câmbio da safra: comparar anos mistura efeito câmbio e efeito salário. Resumir por mediana. |
| 19 | `remuneracao_outlier` | `boolean` | 0 de 277.080 | Marca remuneração implausível, sem remover a linha. Domínio: true quando remuneracao_usd fora de [1.000; 1.000.000], false caso contrário ou nulo. Linhagem: derivada de remuneracao_usd. |
| 20 | `satisfacao_trabalho` | `double` | 221.284 de 277.080 | Satisfação declarada com o emprego. Domínio: 0 a 10; nulo em 2022 e 2023 (pergunta inexistente, ausência estrutural). Linhagem: JobSat para DOUBLE; fora de 0 a 10 vira nulo. |
| 21 | `_ingerido_em` | `timestamp` | 0 de 277.080 | Momento da ingestão na Bronze. Domínio: data e hora UTC da carga. Linhagem: coluna de auditoria _ingerido_em da Bronze, propagada. |

Fonte: o autor (2026), com base nos metadados e nas contagens do pipeline.

## Schema `gold`

### `gold.analise_q1d_modelo_logistico`

*tabela* · Q1d: regressão logística de Remoto (série comparável, base trabalhando) sobre safra, vínculo, Brasil e faixa de experiência; uma linha por termo e por contraste entre safras. Controla composição observada; não corrige seleção. Escrita pelo notebook 08b.

**Quadro 6 - Atributos de `gold.analise_q1d_modelo_logistico`**

| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |
|---|---|---|---|---|
| 1 | `fator` | `string` | 0 de 14 | Fator do modelo. Domínio: safra, vinculo, brasil, faixa_experiencia. Linhagem: nome do bloco de colunas na matriz do modelo do notebook 08b. |
| 2 | `categoria` | `string` | 0 de 14 | Categoria do fator a que o coeficiente se refere. Domínio: safras 2023 a 2025; Autônomo e Ambos; Brasil; faixas de experiência exceto 0–2. Linhagem: rótulo da coluna na matriz do modelo do notebook 08b. |
| 3 | `referencia` | `string` | 0 de 14 | Categoria de referência do coeficiente (a que fica com chance 1). Domínio: 2022, Empregado, fora do Brasil, 0–2; nos contrastes, a safra anterior. Linhagem: categoria omitida de cada fator na matriz do modelo do notebook 08b. |
| 4 | `tipo` | `string` | 0 de 14 | termo (coeficiente contra a referência global) ou contraste (diferença entre duas safras). Domínio: termo, contraste. Linhagem: termo vem direto do GLM; contraste é a diferença entre dois coeficientes de safra no notebook 08b. |
| 5 | `coeficiente` | `double` | 0 de 14 | Coeficiente na escala logit. Domínio: real, em geral entre −3 e 3. Linhagem: GLM binomial do statsmodels sobre as células agregadas por safra, vínculo, Brasil e faixa. |
| 6 | `erro_padrao` | `double` | 0 de 14 | Erro padrão do coeficiente; só erro aleatório. Domínio: real positivo. Linhagem: raiz da diagonal da matriz de covariância do GLM, multiplicada pela raiz da dispersão de Pearson. |
| 7 | `razao_de_chances` | `double` | 0 de 14 | exp(coeficiente): razão de chances (odds) de Remoto contra a referência, a composição constante; 0,80 quer dizer odds 20% menores, não proporção 20% menor. Domínio: real positivo. Linhagem: derivada de coeficiente. |
| 8 | `ic95_inf` | `double` | 0 de 14 | Limite inferior do intervalo de 95% da razão de chances. Domínio: real positivo. Linhagem: exp(coeficiente − 1,96 × erro_padrao). |
| 9 | `ic95_sup` | `double` | 0 de 14 | Limite superior do intervalo de 95% da razão de chances. Domínio: real positivo. Linhagem: exp(coeficiente + 1,96 × erro_padrao). |
| 10 | `p_valor` | `double` | 0 de 14 | p-valor bilateral do teste de Wald. Domínio: 0 a 1. Linhagem: teste de Wald do GLM, ou do contraste, no notebook 08b. |
| 11 | `n_celulas` | `bigint` | 0 de 14 | Combinações de safra × vínculo × Brasil × faixa usadas no ajuste. Domínio: inteiro de 1 a 160 (4 safras × 4 vínculos × 2 × 5 faixas). Linhagem: número de linhas da tabela agregada do notebook 08b. |
| 12 | `n_respondentes` | `bigint` | 0 de 14 | Respondentes na base do modelo (trabalhando, série comparável, país e faixa informados). Domínio: inteiro positivo. Linhagem: soma de gold.fato_resposta_pesquisa.qtd_respondentes na base do modelo. |
| 13 | `remotos` | `bigint` | 0 de 14 | Respondentes em Remoto na base do modelo. Domínio: inteiro de 0 a n_respondentes. Linhagem: soma de gold.fato_resposta_pesquisa.qtd_respondentes com arranjo Remoto. |
| 14 | `dispersao_pearson` | `double` | 0 de 14 | Dispersão de Pearson do modelo binomial (qui-quadrado de Pearson sobre graus de liberdade); acima de 1, os erros-padrão foram corrigidos por ela. Domínio: real positivo, igual em todas as linhas. Linhagem: pearson_chi2 / df_resid do GLM binomial do notebook 08b. |

Fonte: o autor (2026), com base nos metadados e nas contagens do pipeline.

### `gold.dim_arranjo_trabalho`

*tabela* · Dimensão do arranjo de trabalho autodeclarado na pesquisa. Não conformada com dim_modalidade_ibge, porque os conceitos são diferentes. Origem: silver.so_de_para_arranjo.

**Quadro 7 - Atributos de `gold.dim_arranjo_trabalho`**

| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |
|---|---|---|---|---|
| 1 | `arranjo_chave` | `int` | 0 de 6 | Chave substituta igual à ordem canônica. Domínio: 1 a 5; -1 desconhecido. Linhagem: ordem fixa no notebook 06. |
| 2 | `arranjo` | `string` | 0 de 6 | Categoria harmonizada. Domínio: Remoto, Híbrido, Presencial, Flexível, Não informado, Desconhecido. Linhagem: valor_canonico do de-para. |
| 3 | `entra_serie_historica` | `boolean` | 0 de 6 | Indica categoria comparável entre 2022 e 2025. Domínio: true para Remoto, Híbrido e Presencial. Linhagem: entra_serie_historica do de-para (conjunção por categoria). |
| 4 | `ordem` | `int` | 0 de 6 | Ordem de exibição. Domínio: 1 a 5; 99 no membro -1. Linhagem: fixa no notebook 06. |

Fonte: o autor (2026), com base nos metadados e nas contagens do pipeline.

### `gold.dim_atividade_economica`

*tabela* · Dimensão de grupamento de atividade no trabalho principal (classificação c888). Origem: silver.ibge_ocupados_uf_atividade.

**Quadro 8 - Atributos de `gold.dim_atividade_economica`**

| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |
|---|---|---|---|---|
| 1 | `atividade_chave` | `bigint` | 0 de 14 | Chave substituta estável. Domínio: inteiro não negativo, xxhash64 de codigo; -1 desconhecido. Linhagem: gerada no notebook 06; a mesma chave natural gera sempre a mesma chave em qualquer recarga. |
| 2 | `codigo` | `string` | 0 de 14 | Código do grupamento. Domínio: códigos da c888. Linhagem: silver.ibge_ocupados_uf_atividade.atividade_codigo. |
| 3 | `nome` | `string` | 0 de 14 | Nome do grupamento conforme o IBGE. Domínio: rótulos da c888. Linhagem: atividade_nome (menor valor por código). |
| 4 | `e_proxy_tecnologia` | `boolean` | 0 de 14 | Marca o proxy de tecnologia. Domínio: true só para 56624. Linhagem: silver.ibge_ocupados_uf_atividade.e_proxy_tecnologia. Premissa: mais amplo que TI. |
| 5 | `e_total` | `boolean` | 0 de 14 | Marca o grupamento Total, que soma os demais. Domínio: true só para 47946. Linhagem: regra sobre codigo, verificada pela verificação C24. |
| 6 | `e_subgrupamento` | `boolean` | 0 de 14 | Marca grupamento contido em outro. Domínio: true só para 60031 (Indústria de transformação, contida em 47948, Indústria geral). Linhagem: regra sobre codigo, verificada pela verificação C24. |

Fonte: o autor (2026), com base nos metadados e nas contagens do pipeline.

### `gold.dim_geografia`

*tabela* · Dimensão conformada de geografia, usada pelas três tabelas fato. Países da pesquisa (nome em inglês) e UFs do IBGE, com o Brasil conformado como Brazil nas duas fontes. Membros especiais: -1 Desconhecido (falha de busca na dimensão) e -2 Não informado (país em branco na pesquisa).

**Quadro 9 - Atributos de `gold.dim_geografia`**

| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |
|---|---|---|---|---|
| 1 | `geo_chave` | `bigint` | 0 de 224 | Chave substituta estável. Domínio: inteiro não negativo, xxhash64 de (nivel, codigo); -1 Desconhecido; -2 Não informado (país em branco na pesquisa). Linhagem: gerada no notebook 06; a mesma chave natural gera sempre a mesma chave em qualquer recarga. |
| 2 | `nivel` | `string` | 0 de 224 | Nível territorial. Domínio: pais, uf, Desconhecido. Linhagem: pais vem de silver.so_respondente.pais; uf vem das tabelas Silver do IBGE. |
| 3 | `codigo` | `string` | 0 de 224 | Chave natural. Domínio: nome do país em inglês para nivel pais; código IBGE de dois dígitos para nivel uf. Linhagem: silver.so_respondente.pais e uf_codigo das tabelas IBGE; a linha Brasil (NC 1) do IBGE é associada a Brazil. |
| 4 | `nome` | `string` | 0 de 224 | Nome do território. Domínio: nome do país em inglês ou nome da UF em português. Linhagem: pais da pesquisa ou uf_nome do IBGE (menor valor por código). |
| 5 | `pais_nome` | `string` | 0 de 224 | País a que o território pertence. Domínio: nome do país em inglês; Brazil para todas as UFs. Linhagem: pais da pesquisa; constante Brazil para UFs, para conformar as fontes. |
| 6 | `uf_sigla` | `string` | 197 de 224 | Sigla da UF. Domínio: 27 siglas; nulo para países. Linhagem: tabela de referência código IBGE para sigla, embutida no notebook 06. |
| 7 | `regiao` | `string` | 197 de 224 | Grande região do Brasil. Domínio: Norte, Nordeste, Sudeste, Sul, Centro-Oeste; nulo para países. Linhagem: primeiro dígito do código IBGE da UF. |

Fonte: o autor (2026), com base nos metadados e nas contagens do pipeline.

### `gold.dim_modalidade_ibge`

*tabela* · Dimensão de modalidade de trabalho remoto e teletrabalho do IBGE (classificação c1675). Não conformada com dim_arranjo_trabalho, porque os conceitos são diferentes. Origem: silver.ibge_teletrabalho_uf.

**Quadro 10 - Atributos de `gold.dim_modalidade_ibge`**

| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |
|---|---|---|---|---|
| 1 | `modalidade_chave` | `bigint` | 0 de 7 | Chave substituta estável. Domínio: inteiro não negativo, xxhash64 de modalidade_codigo; -1 desconhecido. Linhagem: gerada no notebook 06; a mesma chave natural gera sempre a mesma chave em qualquer recarga. |
| 2 | `modalidade` | `string` | 0 de 7 | Nome da modalidade conforme o IBGE. Domínio: rótulos da c1675. Linhagem: silver.ibge_teletrabalho_uf.modalidade. |
| 3 | `e_teletrabalho` | `boolean` | 0 de 7 | Indica teletrabalho ou recorte de teletrabalho por local. Domínio: true para 59805 a 59808; false para 59803 (Total) e 59804 (trabalho remoto, conceito mais amplo). Linhagem: regra sobre modalidade_codigo. Não somar as linhas com true: 59806 e 59807 se sobrepõem em 59808. |
| 4 | `modalidade_codigo` | `string` | 0 de 7 | Código da classificação c1675. Domínio: 59803 a 59808. Linhagem: silver.ibge_teletrabalho_uf.modalidade_codigo. |
| 5 | `modalidade_pai_codigo` | `string` | 2 de 7 | Modalidade que contém esta. Domínio: 59803 para 59804; 59804 para 59805; 59805 para 59806, 59807 e 59808; nulo para 59803. Linhagem: hierarquia fixa no notebook 06, verificada no dado pela verificação C23 (59806 + 59807 - 59808 = 59805). |

Fonte: o autor (2026), com base nos metadados e nas contagens do pipeline.

### `gold.dim_perfil_dev`

*tabela* · Dimensão de perfil profissional: combinação de perfil principal e faixa de experiência. Origem: silver.so_respondente.

**Quadro 11 - Atributos de `gold.dim_perfil_dev`**

| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |
|---|---|---|---|---|
| 1 | `perfil_chave` | `bigint` | 0 de 300 | Chave substituta estável. Domínio: inteiro não negativo, xxhash64 de (perfil, faixa_experiencia); -1 desconhecido. Linhagem: gerada no notebook 06; a mesma chave natural gera sempre a mesma chave em qualquer recarga. |
| 2 | `perfil` | `string` | 0 de 300 | Perfil profissional principal. Domínio: rótulos de DevType; Não informado quando ausente. Linhagem: silver.so_respondente.perfil_principal (primeiro item de DevType). |
| 3 | `faixa_experiencia` | `string` | 0 de 300 | Faixa de anos codando. Domínio: 0–2, 3–5, 6–10, 11–20, 21+, Não informado. Linhagem: silver.so_respondente.faixa_experiencia. |

Fonte: o autor (2026), com base nos metadados e nas contagens do pipeline.

### `gold.dim_periodo`

*tabela* · Dimensão conformada de período, usada pelas três tabelas fato. Uma linha por ano (pesquisa e teletrabalho) e por trimestre (ocupação), mais o membro -1. Origem: silver.so_respondente, silver.ibge_teletrabalho_uf, silver.ibge_ocupados_uf_atividade.

**Quadro 12 - Atributos de `gold.dim_periodo`**

| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |
|---|---|---|---|---|
| 1 | `periodo_chave` | `int` | 0 de 63 | Chave substituta determinística. Domínio: ano × 10 para ano (20220), ano × 10 + trimestre para trimestre (20224), -1 desconhecido. Linhagem: calculada de ano e trimestre. |
| 2 | `tipo_periodo` | `string` | 0 de 63 | Granularidade do período. Domínio: ano, trimestre, Desconhecido. Linhagem: fonte que originou a linha. |
| 3 | `ano` | `int` | 1 de 63 | Ano. Domínio: inteiro de quatro dígitos; nulo no membro -1. Linhagem: safra da pesquisa, ano da 9471 e ano da 5434. |
| 4 | `trimestre` | `int` | 5 de 63 | Trimestre. Domínio: 1 a 4; nulo em períodos anuais e no membro -1. Linhagem: trimestre da 5434. |
| 5 | `rotulo` | `string` | 0 de 63 | Rótulo legível. Domínio: AAAA ou AAAATn (ex.: 2022T4). Linhagem: derivado de ano e trimestre. |

Fonte: o autor (2026), com base nos metadados e nas contagens do pipeline.

### `gold.dim_porte_empresa`

*tabela* · Dimensão de porte da empresa em nove faixas canônicas, harmonizando a fusão de faixas de 2025. Membros especiais: -1 Desconhecido (rótulo sem mapeamento) e -2 Não informado (porte em branco). Origem: mapa fixo equivalente ao do notebook 03.

**Quadro 13 - Atributos de `gold.dim_porte_empresa`**

| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |
|---|---|---|---|---|
| 1 | `porte_chave` | `int` | 0 de 11 | Chave substituta igual à ordem da faixa. Domínio: 1 a 9; -1 Desconhecido (rótulo sem mapeamento); -2 Não informado. Linhagem: fixa no notebook 06. |
| 2 | `porte` | `string` | 0 de 11 | Faixa canônica. Domínio: Autônomo, Menos de 20, 20 a 99, 100 a 499, 500 a 999, 1.000 a 4.999, 5.000 a 9.999, 10.000 ou mais, Não sabe, Não informado, Desconhecido. Linhagem: silver.so_respondente.porte_empresa. |
| 3 | `ordem` | `int` | 0 de 11 | Ordem crescente de porte. Domínio: 1 a 9; 98 no membro -2; 99 no membro -1. Linhagem: silver.so_respondente.porte_ordem. |
| 4 | `faixa_min` | `int` | 4 de 11 | Menor número de empregados da faixa. Domínio: inteiro; nulo em Menos de 20 (2025 não informa o piso), Não sabe, Não informado e Desconhecido. Linhagem: rótulos da pesquisa. |
| 5 | `faixa_max` | `int` | 4 de 11 | Maior número de empregados da faixa. Domínio: inteiro; nulo em 10.000 ou mais, Não sabe, Não informado e Desconhecido. Linhagem: rótulos da pesquisa. |

Fonte: o autor (2026), com base nos metadados e nas contagens do pipeline.

### `gold.fato_ocupacao_uf_atividade`

*tabela* · Grão: UF × trimestre × grupamento de atividade econômica. Estimativa de pessoas ocupadas da PNAD Contínua. Origem: silver.ibge_ocupados_uf_atividade.

**Quadro 14 - Atributos de `gold.fato_ocupacao_uf_atividade`**

| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |
|---|---|---|---|---|
| 1 | `periodo_chave` | `int` | 0 de 20.358 | FK para dim_periodo (tipo trimestre). Domínio: chaves de dim_periodo; -1 se a busca na dimensão falhar. Linhagem: ano e trimestre. |
| 2 | `geo_chave` | `bigint` | 0 de 20.358 | FK para dim_geografia (nivel uf). Domínio: chaves de dim_geografia; -1 se a busca na dimensão falhar. Linhagem: uf_codigo. |
| 3 | `atividade_chave` | `bigint` | 0 de 20.358 | FK para dim_atividade_economica. Domínio: chaves da dimensão; -1 se a busca na dimensão falhar. Linhagem: atividade_codigo. |
| 4 | `pessoas_mil` | `double` | 0 de 20.358 | Medida semiaditiva: pessoas ocupadas em mil. Soma entre UFs no mesmo trimestre e grupamento; não somar grupamentos (o grupamento 47946 Total contém os demais) nem trimestres. Domínio: real não negativo; nulo quando pessoas_mil_sinal é .., ... ou x. Linhagem: variável 4090 da tabela 5434. |
| 5 | `pessoas_mil_sinal` | `string` | 19.449 de 20.358 | Sinal convencional do IBGE na célula (Normas de apresentação tabular). Domínio: nulo quando a célula traz número; - (zero não resultante de arredondamento, valor 0); .. (não se aplica); ... (não disponível); x (omitido por sigilo); nos três últimos o valor é nulo. Linhagem: silver.ibge_ocupados_uf_atividade.pessoas_mil_sinal. |

Fonte: o autor (2026), com base nos metadados e nas contagens do pipeline.

### `gold.fato_resposta_pesquisa`

*tabela* · Grão: um respondente da Stack Overflow Developer Survey em uma safra. Amostra autosselecionada, sem peso amostral: contagens descrevem quem respondeu, não a população. Origem: silver.so_respondente.

**Quadro 15 - Atributos de `gold.fato_resposta_pesquisa`**

| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |
|---|---|---|---|---|
| 1 | `periodo_chave` | `int` | 0 de 277.080 | FK para dim_periodo (tipo ano). Domínio: chaves de dim_periodo; -1 se a busca na dimensão falhar. Linhagem: safra. |
| 2 | `geo_chave` | `bigint` | 0 de 277.080 | FK para dim_geografia (nivel pais). Domínio: chaves de dim_geografia; -2 quando o país está em branco; -1 se a busca na dimensão falhar (a verificação C15 exige zero). Linhagem: silver.so_respondente.pais. |
| 3 | `arranjo_chave` | `int` | 0 de 277.080 | FK para dim_arranjo_trabalho. Domínio: 1 a 5; -1 se a busca na dimensão falhar. Linhagem: silver.so_respondente.arranjo_trabalho. |
| 4 | `porte_chave` | `int` | 0 de 277.080 | FK para dim_porte_empresa. Domínio: 1 a 9; -2 quando o porte está em branco; -1 se o rótulo não tiver mapeamento (a verificação C15 exige zero). Linhagem: silver.so_respondente.porte_empresa e porte_empresa_origem. |
| 5 | `perfil_chave` | `bigint` | 0 de 277.080 | FK para dim_perfil_dev. Domínio: chaves de dim_perfil_dev; -1 se a busca na dimensão falhar. Linhagem: perfil_principal e faixa_experiencia, com nulo como Não informado. |
| 6 | `safra` | `int` | 0 de 277.080 | Dimensão degenerada: safra da pesquisa. Domínio: 2022 a 2025. Linhagem: silver.so_respondente.safra. |
| 7 | `resposta_id` | `bigint` | 0 de 277.080 | Dimensão degenerada: identificador da resposta na safra; com safra, rastreia a linha até a Silver e a Bronze. Domínio: inteiro positivo. Linhagem: silver.so_respondente.resposta_id. |
| 8 | `e_profissional` | `boolean` | 0 de 277.080 | Atributo degenerado: desenvolvedor de profissão. Domínio: true, false, nulo. Linhagem: silver.so_respondente.e_profissional. |
| 9 | `empregado` | `boolean` | 0 de 277.080 | Atributo degenerado: vínculo empregatício. Domínio: true, false. Linhagem: silver.so_respondente.empregado. |
| 10 | `autonomo` | `boolean` | 0 de 277.080 | Atributo degenerado: trabalho autônomo. Domínio: true, false. Linhagem: silver.so_respondente.autonomo. |
| 11 | `trabalhando` | `boolean` | 0 de 277.080 | Atributo degenerado: empregado ou autônomo; base das views Q1 a Q5. Domínio: true, false. Linhagem: silver.so_respondente.trabalhando. |
| 12 | `remuneracao_outlier` | `boolean` | 0 de 277.080 | Atributo degenerado: remuneração fora de [1.000; 1.000.000] USD. Domínio: true, false. Linhagem: silver.so_respondente.remuneracao_outlier. |
| 13 | `qtd_respondentes` | `int` | 0 de 277.080 | Medida aditiva de contagem. Domínio: sempre 1. Linhagem: constante no notebook 07. |
| 14 | `remuneracao_usd` | `double` | 143.608 de 277.080 | Medida não aditiva: remuneração anual em USD no câmbio da safra. Domínio: real não negativo ou nulo. Linhagem: silver.so_respondente.remuneracao_usd. Resumir por mediana. |
| 15 | `satisfacao_trabalho` | `double` | 221.284 de 277.080 | Medida não aditiva: satisfação com o emprego. Domínio: 0 a 10; nulo em 2022 e 2023. Linhagem: silver.so_respondente.satisfacao_trabalho. |
| 16 | `anos_codando` | `int` | 15.403 de 277.080 | Medida não aditiva: anos programando, incluindo anos de estudo. Domínio: 0 a 50, censurado nas pontas. Linhagem: silver.so_respondente.anos_codando. |

Fonte: o autor (2026), com base nos metadados e nas contagens do pipeline.

### `gold.fato_teletrabalho_uf`

*tabela* · Grão: território (Brasil ou UF) × modalidade de trabalho remoto ou teletrabalho, 2022 (4º trimestre). Estimativa populacional ponderada da PNAD Contínua anual, estatísticas experimentais segundo o SIDRA. Origem: silver.ibge_teletrabalho_uf.

**Quadro 16 - Atributos de `gold.fato_teletrabalho_uf`**

| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |
|---|---|---|---|---|
| 1 | `periodo_chave` | `int` | 0 de 168 | FK para dim_periodo (tipo ano, 2022). Domínio: chaves de dim_periodo; -1 se a busca na dimensão falhar. Linhagem: silver.ibge_teletrabalho_uf.ano. |
| 2 | `geo_chave` | `bigint` | 0 de 168 | FK para dim_geografia: nivel pais Brazil para a linha nacional, nivel uf para UFs. Domínio: chaves de dim_geografia; -1 se a busca na dimensão falhar. Linhagem: nivel_territorial e uf_codigo. |
| 3 | `modalidade_chave` | `bigint` | 0 de 168 | FK para dim_modalidade_ibge. Domínio: chaves de dim_modalidade_ibge; -1 se a busca na dimensão falhar. Linhagem: modalidade_codigo. |
| 4 | `pessoas_mil` | `double` | 0 de 168 | Medida semiaditiva: pessoas ocupadas em mil. Soma entre UFs dentro de uma modalidade; não somar modalidades (Total contém as demais; teletrabalho está contido em trabalho remoto; 59806 e 59807 se sobrepõem). Domínio: real não negativo. Linhagem: variável 4090. |
| 5 | `pessoas_mil_sinal` | `string` | 168 de 168 | Sinal convencional do IBGE na célula (Normas de apresentação tabular). Domínio: nulo quando a célula traz número; - (zero não resultante de arredondamento, valor 0); .. (não se aplica); ... (não disponível); x (omitido por sigilo); nos três últimos o valor é nulo. Linhagem: silver.ibge_teletrabalho_uf.pessoas_mil_sinal. |
| 6 | `cv_pessoas` | `double` | 0 de 168 | Coeficiente de variação de pessoas_mil, em %. Domínio: real não negativo. Linhagem: variável 4091. |
| 7 | `cv_pessoas_sinal` | `string` | 168 de 168 | Sinal convencional do IBGE na célula (Normas de apresentação tabular). Domínio: nulo quando a célula traz número; - (zero não resultante de arredondamento, valor 0); .. (não se aplica); ... (não disponível); x (omitido por sigilo); nos três últimos o valor é nulo. Linhagem: silver.ibge_teletrabalho_uf.cv_pessoas_sinal. |
| 8 | `cv_pessoas_classificacao` | `string` | 0 de 168 | Faixa de CV adotada no projeto sobre o cv_pessoas publicado pelo IBGE. Domínio: Exata, Ótima, Boa, Razoável, Pouco precisa, Imprecisa. Linhagem: silver.ibge_teletrabalho_uf.cv_pessoas_classificacao. |
| 9 | `percentual` | `double` | 0 de 168 | Medida não aditiva: percentual publicado. Domínio: 0 a 100. Linhagem: variável 12965. |
| 10 | `percentual_sinal` | `string` | 168 de 168 | Sinal convencional do IBGE na célula (Normas de apresentação tabular). Domínio: nulo quando a célula traz número; - (zero não resultante de arredondamento, valor 0); .. (não se aplica); ... (não disponível); x (omitido por sigilo); nos três últimos o valor é nulo. Linhagem: silver.ibge_teletrabalho_uf.percentual_sinal. |
| 11 | `cv_percentual` | `double` | 0 de 168 | Coeficiente de variação do percentual, em %. Domínio: real não negativo. Linhagem: variável 12966. |
| 12 | `cv_percentual_sinal` | `string` | 140 de 168 | Sinal convencional do IBGE na célula (Normas de apresentação tabular). Domínio: nulo quando a célula traz número; - (zero não resultante de arredondamento, valor 0); .. (não se aplica); ... (não disponível); x (omitido por sigilo); nos três últimos o valor é nulo. Linhagem: silver.ibge_teletrabalho_uf.cv_percentual_sinal. |
| 13 | `cv_classificacao` | `string` | 0 de 168 | Faixa de CV adotada no projeto sobre o cv_percentual publicado pelo IBGE. Domínio: Exata, Ótima, Boa, Razoável, Pouco precisa, Imprecisa. Linhagem: silver.ibge_teletrabalho_uf.cv_classificacao. |
| 14 | `estimativa_confiavel` | `boolean` | 0 de 168 | CV publicado pelo IBGE; o limiar de 15% é critério do projeto. Domínio: true, false, nulo. Linhagem: silver.ibge_teletrabalho_uf.estimativa_confiavel. |
| 15 | `disponivel_no_nivel` | `boolean` | 0 de 168 | Indica se o IBGE declara a categoria disponível no nível territorial da linha. Domínio: false para 59807 e 59808 por UF, true nas demais. Linhagem: silver.ibge_teletrabalho_uf.disponivel_no_nivel (verificação C28). |

Fonte: o autor (2026), com base nos metadados e nas contagens do pipeline.

### `gold.qualidade_por_atributo`

*tabela* · Qualidade de cada coluna da Bronze e da Silver nas cinco dimensões de qualidade: completude, unicidade, consistência, acurácia e outliers. Uma linha por coluna. Escrita pelo notebook 05b.

**Quadro 17 - Atributos de `gold.qualidade_por_atributo`**

| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |
|---|---|---|---|---|
| 1 | `tabela` | `string` | 0 de 580 | Tabela medida. Domínio: tabelas bronze.* e silver.*. Linhagem: perfil da captura e lista REGRAS do notebook 05b. |
| 2 | `coluna` | `string` | 0 de 580 | Coluna medida. Domínio: nomes de coluna da tabela. Linhagem: schema da tabela medida. |
| 3 | `posicao` | `int` | 0 de 580 | Posição da coluna na tabela, a partir de 1. Domínio: inteiro positivo. Linhagem: ordem do schema da tabela medida. |
| 4 | `tipo` | `string` | 0 de 580 | Tipo da coluna. Domínio: tipos do Spark (string, int, bigint, double, boolean, timestamp). Linhagem: dtypes da tabela medida. |
| 5 | `linhas` | `bigint` | 0 de 580 | Linhas da tabela. Domínio: inteiro não negativo. Linhagem: contagem da tabela medida. |
| 6 | `nulos` | `bigint` | 0 de 580 | Valores ausentes; na Bronze inclui NA e vazio. Domínio: 0 até linhas. Linhagem: perfil da captura ou soma de coluna IS NULL na Silver. |
| 7 | `completude_pct` | `double` | 0 de 580 | Completude: parcela de valores preenchidos, em %. Domínio: 0 a 100. Linhagem: (linhas − nulos) / linhas × 100. |
| 8 | `unicidade` | `string` | 0 de 580 | Unicidade: combinações repetidas da chave, nas colunas da chave; nas demais, registra a ausência de requisito e, na Silver, a contagem de valores distintos. Domínio: texto. Linhagem: ResponseId repetido por safra em perfil_captura.py para a Bronze; GROUP BY da chave e COUNT(DISTINCT coluna) na Silver. |
| 9 | `regra_consistencia` | `string` | 0 de 580 | Regra de domínio da coluna, em português. Domínio: texto; texto livre quando a coluna não tem regra fechada. Linhagem: DOMINIOS e validações de perfil_captura.py na Bronze; lista REGRAS do notebook 05b na Silver. |
| 10 | `fora_da_regra` | `bigint` | 505 de 580 | Valores preenchidos que violam a regra. Domínio: inteiro não negativo; nulo quando não há regra. Linhagem: contadores de formato e plausibilidade de perfil_captura.py na Bronze; soma de NOT regra nas linhas preenchidas da Silver. |
| 11 | `consistencia_pct` | `double` | 508 de 580 | Consistência: parcela dos valores preenchidos dentro da regra, em %. Domínio: 0 a 100; nulo sem regra. Linhagem: (preenchidos − fora_da_regra) / preenchidos × 100. |
| 12 | `acuracia` | `string` | 0 de 580 | Acurácia: verificação que compara a coluna com referência externa e o resultado dela, ou o motivo de não ser mensurável. Domínio: texto. Linhagem: justificativas do perfil de captura produzido no 01 e complementado no 05b; listas ACURACIA e SEM_REFERENCIA do 05b e resultado das verificações na Silver. |
| 13 | `outliers_iqr` | `bigint` | 555 de 580 | Outliers: valores fora de Q1 − 1,5 × IQR e Q3 + 1,5 × IQR. Domínio: inteiro não negativo; nulo sem regra de extremos definida. Linhagem: quantis interpolados na captura; percentile_approx na Silver. |
| 14 | `limite_inf_iqr` | `double` | 555 de 580 | Limite inferior da regra do IQR. Domínio: real; nulo sem regra de extremos definida. Linhagem: Q1 − 1,5 × (Q3 − Q1). |
| 15 | `limite_sup_iqr` | `double` | 555 de 580 | Limite superior da regra do IQR. Domínio: real; nulo sem regra de extremos definida. Linhagem: Q3 + 1,5 × (Q3 − Q1). |
| 16 | `executado_em` | `timestamp` | 0 de 580 | Momento do cálculo. Domínio: data e hora UTC. Linhagem: relógio do notebook 05b. |

Fonte: o autor (2026), com base nos metadados e nas contagens do pipeline.

### `gold.verificacoes_qualidade`

*tabela* · Resultado persistido das verificações de qualidade, uma linha por verificação. Escrita pelos notebooks 05 (camadas bronze e silver) e 07 (camada gold, C15) com MERGE por verificacao_id.

**Quadro 18 - Atributos de `gold.verificacoes_qualidade`**

| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |
|---|---|---|---|---|
| 1 | `verificacao_id` | `string` | 0 de 32 | Identificador da verificação. Domínio: C01 a C30 (C15 gravado como C15.1 a C15.3, um por tabela fato). Linhagem: primeiro argumento de registrar() no notebook 05; C15.1 a C15.3 no notebook 07. |
| 2 | `camada` | `string` | 0 de 32 | Camada em que a medição foi feita. Domínio: bronze, silver, gold. Linhagem: segundo argumento de registrar() no notebook 05; gold no MERGE do notebook 07. |
| 3 | `tabela` | `string` | 0 de 32 | Tabela ou tabelas medidas. Domínio: nomes schema.tabela. Linhagem: argumento tabela de registrar() no notebook 05 e coluna tabela de _contagens_fatos no 07. |
| 4 | `atributo` | `string` | 0 de 32 | Campo ou aspecto medido, com o nome da fonte quando existe. Domínio: texto livre. Linhagem: argumento atributo de registrar() no notebook 05; texto fixo no 07. |
| 5 | `dimensao_qualidade` | `string` | 0 de 32 | Dimensão de qualidade da verificação. Domínio: Completude, Consistência, Unicidade, Acurácia, Integridade, Validade, Outliers, Estrutural, Tempestividade. Linhagem: argumento dimensao_qualidade de registrar() no notebook 05; Integridade no 07. |
| 6 | `dimensao_dama` | `string` | 0 de 32 | Dimensão entre as seis primárias da DAMA UK que de fato se aplica (formulação de Black e Van Nederpelt, 2020). Domínio: Completude, Unicidade, Tempestividade, Validade, Acurácia, Consistência, ou Não se aplica com o motivo (limite amostral, precisão amostral). Linhagem: argumento dimensao_dama de registrar() no notebook 05; Completude no 07. |
| 7 | `resultado` | `string` | 0 de 32 | Resultado da verificação. Domínio: aprovado, reprovado, conferir, explicado, medido, registrado. Linhagem: comparação entre medido e esperado no notebook 05; regra de _contagens_fatos no 07. |
| 8 | `valor_medido` | `string` | 0 de 32 | Valor medido e valor esperado declarado. Domínio: texto no formato medido: ... \| esperado: .... Linhagem: argumentos medido e esperado de registrar() no notebook 05; CONCAT das contagens no 07. |
| 9 | `linhas_afetadas` | `bigint` | 5 de 32 | Quantidade de linhas envolvidas no achado. Domínio: inteiro não negativo ou nulo quando não se aplica. Linhagem: argumento linhas_afetadas de registrar() no notebook 05; diferença de contagens no 07. |
| 10 | `classificacao` | `string` | 0 de 32 | Natureza do achado. Domínio: problema_real (característica da fonte que muda a análise), guarda_defensiva (proteção contra erro de código ou mudança da fonte). Linhagem: argumento classificacao de registrar() no notebook 05; guarda_defensiva no 07. |
| 11 | `tipo_regra` | `string` | 0 de 32 | Tipo da verificação. Domínio: regra (vale para qualquer carga), referencia_externa (compara com número publicado pela fonte), retrato_da_extracao (compara com o que foi medido nos arquivos de 13/09/2026 e funciona como teste de regressão). Linhagem: dicionário TIPO_REGRA do notebook 05; C15 é regra. |
| 12 | `severidade` | `string` | 0 de 32 | Impacto potencial na análise. Domínio: alta, média, baixa. Linhagem: argumento severidade de registrar() no notebook 05; alta no 07. |
| 13 | `tratamento` | `string` | 0 de 32 | O que o pipeline faz com o achado. Domínio: texto livre. Linhagem: argumento tratamento de registrar() no notebook 05; texto fixo no 07. |
| 14 | `executado_em` | `timestamp` | 0 de 32 | Momento da execução da verificação. Domínio: data e hora UTC. Linhagem: relógio do notebook no momento da execução. |

Fonte: o autor (2026), com base nos metadados e nas contagens do pipeline.

### `gold.verificacoes_qualidade_historico`

*tabela* · Resultados produzidos por etapa e execução. Os notebooks 05 e 07 gravam por MERGE antes de interromper por reprovação, com chave (job_run_id, verificacao_id). Uma repetição atualiza a tentativa mais recente; etapas não executadas não são copiadas. O histórico pode ser parcial; o estado completo consta no Databricks Jobs.

**Quadro 19 - Atributos de `gold.verificacoes_qualidade_historico`**

| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |
|---|---|---|---|---|
| 1 | `job_run_id` | `string` | 0 de 192 | Identificador da execução que produziu o resultado. Domínio: número do run do Databricks ou manual-UUID em execução interativa. Linhagem: parâmetro job_run_id do job, preenchido com {{job.run_id}}, ou UUID gerado por persistir_historico. |
| 2 | `verificacao_id` | `string` | 0 de 192 | Identificador da verificação. Domínio: C01 a C30 (C15 como C15.1 a C15.3). Linhagem: campo verificacao_id dos resultados produzidos no notebook 05 ou 07, recebido por persistir_historico. |
| 3 | `camada` | `string` | 0 de 192 | Camada medida. Domínio: bronze, silver, gold. Linhagem: campo camada dos resultados produzidos no notebook 05 ou 07, recebido por persistir_historico. |
| 4 | `tabela` | `string` | 0 de 192 | Tabela ou tabelas medidas. Domínio: nomes schema.tabela. Linhagem: campo tabela dos resultados produzidos no notebook 05 ou 07, recebido por persistir_historico. |
| 5 | `atributo` | `string` | 0 de 192 | Campo ou aspecto medido. Domínio: texto livre. Linhagem: campo atributo dos resultados produzidos no notebook 05 ou 07, recebido por persistir_historico. |
| 6 | `dimensao_qualidade` | `string` | 0 de 192 | Dimensão de qualidade da verificação. Domínio: Completude, Consistência, Unicidade, Acurácia, Integridade, Validade, Outliers, Estrutural, Tempestividade. Linhagem: campo dimensao_qualidade dos resultados produzidos no notebook 05 ou 07, recebido por persistir_historico. |
| 7 | `dimensao_dama` | `string` | 0 de 192 | Dimensão da DAMA que de fato se aplica. Domínio: seis dimensões da DAMA ou Não se aplica com o motivo. Linhagem: campo dimensao_dama dos resultados produzidos no notebook 05 ou 07, recebido por persistir_historico. |
| 8 | `resultado` | `string` | 0 de 192 | Resultado na execução. Domínio: aprovado, reprovado, conferir, explicado, medido, registrado. Linhagem: campo resultado dos resultados produzidos no notebook 05 ou 07, recebido por persistir_historico. |
| 9 | `valor_medido` | `string` | 0 de 192 | Valor medido e esperado na execução. Domínio: texto no formato medido \| esperado. Linhagem: campo valor_medido dos resultados produzidos no notebook 05 ou 07, recebido por persistir_historico. |
| 10 | `linhas_afetadas` | `bigint` | 30 de 192 | Linhas envolvidas no achado. Domínio: inteiro não negativo ou nulo. Linhagem: campo linhas_afetadas dos resultados produzidos no notebook 05 ou 07, recebido por persistir_historico. |
| 11 | `classificacao` | `string` | 0 de 192 | Natureza do achado. Domínio: problema_real, guarda_defensiva. Linhagem: campo classificacao dos resultados produzidos no notebook 05 ou 07, recebido por persistir_historico. |
| 12 | `tipo_regra` | `string` | 0 de 192 | Tipo da verificação. Domínio: regra, referencia_externa, retrato_da_extracao. Linhagem: campo tipo_regra dos resultados produzidos no notebook 05 ou 07, recebido por persistir_historico. |
| 13 | `severidade` | `string` | 0 de 192 | Impacto potencial. Domínio: alta, média, baixa. Linhagem: campo severidade dos resultados produzidos no notebook 05 ou 07, recebido por persistir_historico. |
| 14 | `tratamento` | `string` | 0 de 192 | O que o pipeline faz com o achado. Domínio: texto livre. Linhagem: campo tratamento dos resultados produzidos no notebook 05 ou 07, recebido por persistir_historico. |
| 15 | `executado_em` | `timestamp` | 0 de 192 | Momento em que a verificação rodou. Domínio: data e hora UTC. Linhagem: campo executado_em dos resultados produzidos no notebook 05 ou 07, recebido por persistir_historico. |

Fonte: o autor (2026), com base nos metadados e nas contagens do pipeline.

### `gold.vw_q1_evolucao_arranjo`

*view* · Q1: Como evoluiu a distribuição entre trabalho remoto, híbrido e presencial de 2022 a 2025 no mundo? Série comparável sem Flexível; 2025 com quebra de instrumento; bases trabalhando e todos_informados. Origem: gold.fato_resposta_pesquisa com dim_periodo e dim_arranjo_trabalho.

**Quadro 20 - Atributos de `gold.vw_q1_evolucao_arranjo`**

| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |
|---|---|---|---|---|
| 1 | `safra` | `int` | n/a (view) | Ano da pesquisa. Domínio: 2022 a 2025. Linhagem: gold.dim_periodo.ano pela periodo_chave da fato. |
| 2 | `base` | `string` | n/a (view) | trabalhando (empregado ou autônomo, base principal) ou todos_informados (sensibilidade). Domínio: trabalhando, todos_informados. Linhagem: constante de cada bloco do UNION ALL; trabalhando filtra fato.trabalhando. |
| 3 | `arranjo` | `string` | n/a (view) | Arranjo harmonizado: Remoto, Híbrido, Presencial, Flexível (só 2025). Domínio: Remoto, Híbrido, Presencial, Flexível. Linhagem: gold.dim_arranjo_trabalho.arranjo. |
| 4 | `ordem` | `int` | n/a (view) | Ordem de exibição do arranjo. Domínio: 1 a 4. Linhagem: gold.dim_arranjo_trabalho.ordem. |
| 5 | `entra_serie_historica` | `boolean` | n/a (view) | true para Remoto, Híbrido e Presencial. Domínio: true, false. Linhagem: gold.dim_arranjo_trabalho.entra_serie_historica. |
| 6 | `respondentes` | `bigint` | n/a (view) | Respondentes da base com o arranjo. Domínio: inteiro não negativo. Linhagem: SUM(gold.fato_resposta_pesquisa.qtd_respondentes) por safra, base e arranjo. |
| 7 | `n_informados` | `bigint` | n/a (view) | Respondentes da base que informaram o arranjo, incluindo Flexível. Domínio: inteiro positivo. Linhagem: SUM(respondentes) por safra e base. |
| 8 | `pct_sobre_informados` | `double` | n/a (view) | respondentes / n_informados × 100. Domínio: 0 a 100, uma casa. Linhagem: respondentes / n_informados × 100, arredondado. |
| 9 | `n_serie_comparavel` | `bigint` | n/a (view) | Respondentes da base em Remoto, Híbrido ou Presencial. Domínio: inteiro positivo. Linhagem: SUM(respondentes) com entra_serie_historica, por safra e base. |
| 10 | `pct_serie_comparavel` | `double` | n/a (view) | respondentes / n_serie_comparavel × 100; nulo para Flexível. Domínio: 0 a 100, uma casa; nulo em Flexível. Linhagem: respondentes / n_serie_comparavel × 100. |
| 11 | `ic95_inf` | `double` | n/a (view) | Limite inferior do intervalo de Wilson de 95% de pct_serie_comparavel; só erro aleatório. Domínio: 0 a 100, uma casa. Linhagem: fórmula de Wilson sobre respondentes e n_serie_comparavel. |
| 12 | `ic95_sup` | `double` | n/a (view) | Limite superior do intervalo de Wilson de 95% de pct_serie_comparavel; só erro aleatório. Domínio: 0 a 100, uma casa. Linhagem: fórmula de Wilson sobre respondentes e n_serie_comparavel. |

Fonte: o autor (2026), com base nos metadados e nas contagens do pipeline.

### `gold.vw_q1_remoto_por_vinculo`

*view* · Q1c: sensibilidade da série de Remoto à não resposta de 2025. Série por vínculo nas duas classificações de quem marcou empregado e autônomo, padronizada pela composição de 2024 e com limites para os nulos. Base trabalhando, série comparável. Origem: gold.fato_resposta_pesquisa com dim_periodo e dim_arranjo_trabalho.

**Quadro 21 - Atributos de `gold.vw_q1_remoto_por_vinculo`**

| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |
|---|---|---|---|---|
| 1 | `safra` | `int` | n/a (view) | Ano da pesquisa. Domínio: 2022 a 2025. Linhagem: gold.dim_periodo.ano. |
| 2 | `classificacao_duplos` | `string` | n/a (view) | Como quem marcou empregado e autônomo (2022 a 2024) é classificado: duplos como Empregado ou duplos como Autônomo. Domínio: duplos como Empregado, duplos como Autônomo. Linhagem: constante de cada bloco da view. |
| 3 | `vinculo` | `string` | n/a (view) | Empregado, Autônomo ou Todos (quem trabalha), segundo classificacao_duplos. Domínio: Empregado, Autônomo, Todos. Linhagem: gold.fato_resposta_pesquisa.empregado e autonomo, conforme classificacao_duplos; Todos soma os dois. |
| 4 | `trabalhando` | `bigint` | n/a (view) | Respondentes que trabalham, no vínculo. Domínio: inteiro positivo (contagem). Linhagem: SUM(gold.fato_resposta_pesquisa.qtd_respondentes) com trabalhando verdadeiro. |
| 5 | `respondentes_duplos` | `bigint` | n/a (view) | Respondentes do vínculo que marcaram empregado e autônomo; 0 em 2025, quando Employment é resposta única. Domínio: inteiro não negativo. Linhagem: SUM de qtd_respondentes com empregado e autonomo verdadeiros. |
| 6 | `nulos_arranjo` | `bigint` | n/a (view) | Respondentes do vínculo sem arranjo informado. Domínio: inteiro não negativo. Linhagem: SUM de qtd_respondentes com arranjo Não informado. |
| 7 | `pct_nulo_arranjo` | `double` | n/a (view) | nulos_arranjo / trabalhando × 100. Domínio: 0 a 100, uma casa. Linhagem: nulos_arranjo / trabalhando × 100. |
| 8 | `n_serie_comparavel` | `bigint` | n/a (view) | Respondentes do vínculo em Remoto, Híbrido ou Presencial. Domínio: inteiro positivo. Linhagem: SUM de qtd_respondentes com entra_serie_historica. |
| 9 | `remotos` | `bigint` | n/a (view) | Respondentes do vínculo em Remoto. Domínio: inteiro não negativo. Linhagem: SUM de qtd_respondentes com arranjo Remoto. |
| 10 | `pct_remoto` | `double` | n/a (view) | remotos / n_serie_comparavel × 100. Domínio: 0 a 100, uma casa. Linhagem: remotos / n_serie_comparavel × 100. |
| 11 | `ic95_inf` | `double` | n/a (view) | Limite inferior do intervalo de Wilson de 95% de pct_remoto; só erro aleatório. Domínio: 0 a 100, uma casa. Linhagem: fórmula de Wilson sobre remotos e n_serie_comparavel. |
| 12 | `ic95_sup` | `double` | n/a (view) | Limite superior do intervalo de Wilson de 95% de pct_remoto; só erro aleatório. Domínio: 0 a 100, uma casa. Linhagem: fórmula de Wilson sobre remotos e n_serie_comparavel. |
| 13 | `peso_vinculo` | `double` | n/a (view) | Participação do vínculo na série comparável da safra × 100; nulo em Todos. Domínio: 0 a 100, uma casa; nulo em Todos. Linhagem: n_serie_comparavel do vínculo / n_serie_comparavel de Todos × 100. |
| 14 | `pct_remoto_padronizado_2024` | `double` | n/a (view) | Só em Todos: soma por vínculo de pct_remoto da safra × peso do vínculo em 2024, na mesma classificação; remove o efeito de composição por vínculo. Domínio: 0 a 100, uma casa; nulo fora de Todos. Linhagem: SUM(pct_remoto da safra × peso_vinculo de 2024) / 100. |
| 15 | `remoto_limite_inf_nulos` | `double` | n/a (view) | Só em Todos: remotos / (n_serie_comparavel + nulos_arranjo) × 100, com os nulos como não remotos e nenhum como Flexível. Domínio: 0 a 100, uma casa; nulo fora de Todos. Linhagem: remotos / (n_serie_comparavel + nulos_arranjo) × 100. |
| 16 | `remoto_limite_sup_nulos` | `double` | n/a (view) | Só em Todos: (remotos + nulos_arranjo) / (n_serie_comparavel + nulos_arranjo) × 100, com os nulos como remotos e nenhum como Flexível. Domínio: 0 a 100, uma casa; nulo fora de Todos. Linhagem: (remotos + nulos_arranjo) / (n_serie_comparavel + nulos_arranjo) × 100. |

Fonte: o autor (2026), com base nos metadados e nas contagens do pipeline.

### `gold.vw_q2_arranjo_por_porte`

*view* · Q2: O arranjo de trabalho varia com o porte da empresa? Base trabalhando; percentual dentro do porte; Menos de 20 funde as faixas de 2 a 19; e_autonomo separa Just me. Origem: gold.fato_resposta_pesquisa com dim_periodo, dim_porte_empresa e dim_arranjo_trabalho.

**Quadro 22 - Atributos de `gold.vw_q2_arranjo_por_porte`**

| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |
|---|---|---|---|---|
| 1 | `safra` | `int` | n/a (view) | Ano da pesquisa. Domínio: 2022 a 2025. Linhagem: gold.dim_periodo.ano. |
| 2 | `porte` | `string` | n/a (view) | Faixa canônica de porte da empresa. Domínio: nove faixas de porte. Linhagem: gold.dim_porte_empresa.porte. |
| 3 | `porte_ordem` | `int` | n/a (view) | Ordem crescente de porte (1 a 9). Domínio: 1 a 9. Linhagem: gold.dim_porte_empresa.ordem. |
| 4 | `e_autonomo` | `boolean` | n/a (view) | true na faixa Autônomo (Just me), que convém excluir ao comparar portes. Domínio: true, false. Linhagem: porte igual a Autônomo. |
| 5 | `arranjo` | `string` | n/a (view) | Arranjo harmonizado. Domínio: Remoto, Híbrido, Presencial, Flexível. Linhagem: gold.dim_arranjo_trabalho.arranjo. |
| 6 | `arranjo_ordem` | `int` | n/a (view) | Ordem de exibição do arranjo. Domínio: 1 a 4. Linhagem: gold.dim_arranjo_trabalho.ordem. |
| 7 | `respondentes` | `bigint` | n/a (view) | Respondentes trabalhando com o porte e o arranjo. Domínio: inteiro não negativo. Linhagem: SUM(gold.fato_resposta_pesquisa.qtd_respondentes) por safra, porte e arranjo. |
| 8 | `n_porte` | `bigint` | n/a (view) | Respondentes trabalhando no porte que informaram o arranjo. Domínio: inteiro positivo. Linhagem: SUM(respondentes) por safra e porte. |
| 9 | `pct_no_porte` | `double` | n/a (view) | respondentes / n_porte × 100. Domínio: 0 a 100, uma casa. Linhagem: respondentes / n_porte × 100. |

Fonte: o autor (2026), com base nos metadados e nas contagens do pipeline.

### `gold.vw_q3_brasil_x_resto_mundo`

*view* · Q3: Como o Brasil se compara à média global na adoção de trabalho remoto? Base trabalhando; Brasil × resto do mundo; só agregado nacional; série comparável com intervalo de Wilson. Origem: gold.fato_resposta_pesquisa com dim_periodo, dim_geografia e dim_arranjo_trabalho.

**Quadro 23 - Atributos de `gold.vw_q3_brasil_x_resto_mundo`**

| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |
|---|---|---|---|---|
| 1 | `safra` | `int` | n/a (view) | Ano da pesquisa. Domínio: 2022 a 2025. Linhagem: gold.dim_periodo.ano. |
| 2 | `grupo` | `string` | n/a (view) | Brasil ou Resto do mundo (todos os países exceto o Brasil). Domínio: Brasil, Resto do mundo. Linhagem: gold.dim_geografia.codigo igual ou diferente de Brazil. |
| 3 | `arranjo` | `string` | n/a (view) | Arranjo harmonizado. Domínio: Remoto, Híbrido, Presencial, Flexível. Linhagem: gold.dim_arranjo_trabalho.arranjo. |
| 4 | `ordem` | `int` | n/a (view) | Ordem de exibição do arranjo. Domínio: 1 a 4. Linhagem: gold.dim_arranjo_trabalho.ordem. |
| 5 | `entra_serie_historica` | `boolean` | n/a (view) | true para Remoto, Híbrido e Presencial. Domínio: true, false. Linhagem: gold.dim_arranjo_trabalho.entra_serie_historica. |
| 6 | `respondentes` | `bigint` | n/a (view) | Respondentes trabalhando do grupo com o arranjo. Domínio: inteiro não negativo. Linhagem: SUM(gold.fato_resposta_pesquisa.qtd_respondentes) por safra, grupo e arranjo. |
| 7 | `n_informados` | `bigint` | n/a (view) | Respondentes trabalhando do grupo que informaram o arranjo, incluindo Flexível. Domínio: inteiro positivo. Linhagem: SUM(respondentes) por safra e grupo. |
| 8 | `n_serie_comparavel` | `bigint` | n/a (view) | Respondentes trabalhando do grupo em Remoto, Híbrido ou Presencial. Domínio: inteiro positivo. Linhagem: SUM(respondentes) com entra_serie_historica, por safra e grupo. |
| 9 | `pct_serie_comparavel` | `double` | n/a (view) | respondentes / n_serie_comparavel × 100; nulo para Flexível. Domínio: 0 a 100, uma casa; nulo em Flexível. Linhagem: respondentes / n_serie_comparavel × 100. |
| 10 | `ic95_inf` | `double` | n/a (view) | Limite inferior do intervalo de Wilson de 95%; só erro aleatório. Domínio: 0 a 100, uma casa. Linhagem: fórmula de Wilson sobre respondentes e n_serie_comparavel. |
| 11 | `ic95_sup` | `double` | n/a (view) | Limite superior do intervalo de Wilson de 95%; só erro aleatório. Domínio: 0 a 100, uma casa. Linhagem: fórmula de Wilson sobre respondentes e n_serie_comparavel. |

Fonte: o autor (2026), com base nos metadados e nas contagens do pipeline.

### `gold.vw_q4_perfil_remoto`

*view* · Q4: Que perfis profissionais e faixas de experiência concentram trabalho remoto? Base trabalhando; Remoto sobre a série comparável, com intervalo de Wilson; perfis de 2022 não comparáveis. Origem: gold.fato_resposta_pesquisa com dim_periodo, dim_arranjo_trabalho e dim_perfil_dev.

**Quadro 24 - Atributos de `gold.vw_q4_perfil_remoto`**

| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |
|---|---|---|---|---|
| 1 | `safra` | `int` | n/a (view) | Ano da pesquisa. Domínio: 2022 a 2025. Linhagem: gold.dim_periodo.ano. |
| 2 | `perfil` | `string` | n/a (view) | Perfil profissional (primeiro item em 2022; resposta única de 2023 a 2025). Domínio: rótulos de DevType da safra. Linhagem: gold.dim_perfil_dev.perfil. |
| 3 | `faixa_experiencia` | `string` | n/a (view) | Faixa de anos codando (inclui anos de estudo). Domínio: 0–2, 3–5, 6–10, 11–20, 21+, Não informado. Linhagem: gold.dim_perfil_dev.faixa_experiencia. |
| 4 | `n_informados` | `bigint` | n/a (view) | Respondentes trabalhando do perfil e faixa que informaram o arranjo. Domínio: inteiro positivo. Linhagem: SUM(gold.fato_resposta_pesquisa.qtd_respondentes) com arranjo informado. |
| 5 | `n_serie_comparavel` | `bigint` | n/a (view) | Respondentes trabalhando do perfil e faixa em Remoto, Híbrido ou Presencial. Domínio: inteiro não negativo. Linhagem: SUM de qtd_respondentes com entra_serie_historica. |
| 6 | `remotos` | `bigint` | n/a (view) | Respondentes trabalhando do perfil e faixa em Remoto. Domínio: inteiro não negativo. Linhagem: SUM de qtd_respondentes com arranjo Remoto. |
| 7 | `hibridos` | `bigint` | n/a (view) | Respondentes trabalhando do perfil e faixa em Híbrido. Domínio: inteiro não negativo. Linhagem: SUM de qtd_respondentes com arranjo Híbrido. |
| 8 | `pct_remoto_comparavel` | `double` | n/a (view) | remotos / n_serie_comparavel × 100. Domínio: 0 a 100, uma casa. Linhagem: remotos / n_serie_comparavel × 100. |
| 9 | `pct_hibrido_comparavel` | `double` | n/a (view) | hibridos / n_serie_comparavel × 100. Domínio: 0 a 100, uma casa. Linhagem: hibridos / n_serie_comparavel × 100. |
| 10 | `pct_nao_presencial_comparavel` | `double` | n/a (view) | Remoto mais Híbrido sobre a série comparável: o público do Mafia Office. Domínio: 0 a 100, uma casa. Linhagem: (remotos + hibridos) / n_serie_comparavel × 100. |
| 11 | `ic95_inf` | `double` | n/a (view) | Limite inferior do intervalo de Wilson de 95%; só erro aleatório. Domínio: 0 a 100, uma casa. Linhagem: fórmula de Wilson sobre remotos e n_serie_comparavel. |
| 12 | `ic95_sup` | `double` | n/a (view) | Limite superior do intervalo de Wilson de 95%; só erro aleatório. Domínio: 0 a 100, uma casa. Linhagem: fórmula de Wilson sobre remotos e n_serie_comparavel. |

Fonte: o autor (2026), com base nos metadados e nas contagens do pipeline.

### `gold.vw_q5_arranjo_satisfacao`

*view* · Q5: Existe relação entre arranjo de trabalho e satisfação declarada com o emprego? 2024 e 2025; base trabalhando; média com erro padrão, média padronizada por experiência e distribuição; associação, não causa. Origem: gold.fato_resposta_pesquisa com dim_periodo, dim_arranjo_trabalho e dim_perfil_dev.

**Quadro 25 - Atributos de `gold.vw_q5_arranjo_satisfacao`**

| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |
|---|---|---|---|---|
| 1 | `safra` | `int` | n/a (view) | Ano da pesquisa (2024 ou 2025). Domínio: 2024, 2025. Linhagem: gold.dim_periodo.ano. |
| 2 | `arranjo` | `string` | n/a (view) | Arranjo harmonizado. Domínio: Remoto, Híbrido, Presencial, Flexível. Linhagem: gold.dim_arranjo_trabalho.arranjo. |
| 3 | `ordem` | `int` | n/a (view) | Ordem de exibição do arranjo. Domínio: 1 a 4. Linhagem: gold.dim_arranjo_trabalho.ordem. |
| 4 | `n_com_satisfacao` | `bigint` | n/a (view) | Respondentes trabalhando com arranjo e satisfação informados. Domínio: inteiro positivo. Linhagem: COUNT(*) das linhas de gold.fato_resposta_pesquisa com satisfacao_trabalho preenchida. |
| 5 | `satisfacao_media` | `double` | n/a (view) | Média de JobSat (0 a 10). Domínio: 0 a 10, duas casas. Linhagem: AVG(gold.fato_resposta_pesquisa.satisfacao_trabalho). |
| 6 | `erro_padrao_media` | `double` | n/a (view) | Desvio padrão amostral dividido pela raiz de n; só erro aleatório. Domínio: real positivo, três casas. Linhagem: STDDEV_SAMP(satisfacao_trabalho) / SQRT(n). |
| 7 | `desvio_padrao` | `double` | n/a (view) | Desvio padrão amostral de JobSat no arranjo; referência para ler o tamanho das diferenças entre médias. Domínio: real positivo, duas casas. Linhagem: STDDEV_SAMP(satisfacao_trabalho). |
| 8 | `satisfacao_media_padronizada` | `double` | n/a (view) | Média padronizada pela distribuição de faixa de experiência da safra. Domínio: 0 a 10, duas casas. Linhagem: média por faixa de experiência ponderada pelo peso da faixa na safra. |
| 9 | `satisfacao_p25` | `double` | n/a (view) | Primeiro quartil de JobSat. Domínio: 0 a 10. Linhagem: PERCENTILE_CONT(0.25) de satisfacao_trabalho. |
| 10 | `satisfacao_mediana` | `double` | n/a (view) | Mediana de JobSat. Domínio: 0 a 10. Linhagem: PERCENTILE_CONT(0.50) de satisfacao_trabalho. |
| 11 | `satisfacao_p75` | `double` | n/a (view) | Terceiro quartil de JobSat. Domínio: 0 a 10. Linhagem: PERCENTILE_CONT(0.75) de satisfacao_trabalho. |
| 12 | `pct_0_a_4` | `decimal(7,1)` | n/a (view) | Percentual com JobSat de 0 a 4. Domínio: 0 a 100, uma casa. Linhagem: parcela com satisfacao_trabalho até 4 × 100. |
| 13 | `pct_5_a_7` | `decimal(7,1)` | n/a (view) | Percentual com JobSat de 5 a 7. Domínio: 0 a 100, uma casa. Linhagem: parcela com satisfacao_trabalho acima de 4 e até 7 × 100. |
| 14 | `pct_8_a_10` | `decimal(7,1)` | n/a (view) | Percentual com JobSat de 8 a 10. Domínio: 0 a 100, uma casa. Linhagem: parcela com satisfacao_trabalho acima de 7 × 100. |

Fonte: o autor (2026), com base nos metadados e nas contagens do pipeline.

### `gold.vw_q6_teletrabalho_uf`

*view* · Q6: Qual o tamanho e a distribuição geográfica do teletrabalho no Brasil? PNAD Contínua anual 2022 (4º trimestre), estatísticas experimentais; Brasil pela linha nacional; sem as categorias que o IBGE declara disponíveis só para Brasil e Grande Região; cada medida com seu CV e a faixa adotada; modalidades não se somam. Origem: gold.fato_teletrabalho_uf com dim_geografia e dim_modalidade_ibge.

**Quadro 26 - Atributos de `gold.vw_q6_teletrabalho_uf`**

| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |
|---|---|---|---|---|
| 1 | `nivel` | `string` | n/a (view) | pais (Brasil) ou uf. Domínio: pais, uf. Linhagem: gold.dim_geografia.nivel. |
| 2 | `uf_sigla` | `string` | n/a (view) | Sigla da UF; nulo no Brasil. Domínio: 27 siglas de UF; nulo no Brasil. Linhagem: gold.dim_geografia.uf_sigla. |
| 3 | `territorio` | `string` | n/a (view) | Nome do território. Domínio: Brasil e as 27 UFs. Linhagem: gold.dim_geografia.nome. |
| 4 | `regiao` | `string` | n/a (view) | Grande região; nulo no Brasil. Domínio: Norte, Nordeste, Sudeste, Sul, Centro-Oeste; nulo no Brasil. Linhagem: gold.dim_geografia.regiao. |
| 5 | `modalidade_codigo` | `string` | n/a (view) | Código c1675 (59803 a 59808). Domínio: 59803 a 59808. Linhagem: gold.dim_modalidade_ibge.modalidade_codigo. |
| 6 | `modalidade` | `string` | n/a (view) | Nome da modalidade conforme o IBGE. Domínio: rótulos da classificação c1675. Linhagem: gold.dim_modalidade_ibge.modalidade. |
| 7 | `modalidade_pai_codigo` | `string` | n/a (view) | Modalidade que contém esta (hierarquia da verificação C23). Domínio: código c1675 ou nulo no Total. Linhagem: gold.dim_modalidade_ibge.modalidade_pai_codigo. |
| 8 | `e_teletrabalho` | `boolean` | n/a (view) | true para teletrabalho (59805) e seus recortes por local. Domínio: true, false. Linhagem: gold.dim_modalidade_ibge.e_teletrabalho. |
| 9 | `pessoas_mil` | `double` | n/a (view) | Pessoas ocupadas na modalidade, em mil. Domínio: real não negativo. Linhagem: gold.fato_teletrabalho_uf.pessoas_mil. |
| 10 | `cv_pessoas` | `double` | n/a (view) | CV de pessoas_mil, em %. Domínio: real não negativo. Linhagem: gold.fato_teletrabalho_uf.cv_pessoas. |
| 11 | `cv_pessoas_classificacao` | `string` | n/a (view) | Faixa de CV adotada no projeto sobre cv_pessoas, publicado pelo IBGE. Domínio: Exata, Ótima, Boa, Razoável, Pouco precisa, Imprecisa. Linhagem: gold.fato_teletrabalho_uf.cv_pessoas_classificacao. |
| 12 | `leitura_pessoas` | `string` | n/a (view) | Uso de pessoas_mil segundo a faixa adotada: Sustenta conclusão, Usar com ressalva, Só transparência. Domínio: Sustenta conclusão, Usar com ressalva, Só transparência. Linhagem: CASE sobre cv_pessoas_classificacao. |
| 13 | `percentual` | `double` | n/a (view) | Percentual do total de ocupados do território. Domínio: 0 a 100. Linhagem: gold.fato_teletrabalho_uf.percentual. |
| 14 | `cv_percentual` | `double` | n/a (view) | CV do percentual, em %. Domínio: real não negativo. Linhagem: gold.fato_teletrabalho_uf.cv_percentual. |
| 15 | `cv_classificacao` | `string` | n/a (view) | Faixa de CV adotada no projeto sobre cv_percentual, publicado pelo IBGE. Domínio: Exata, Ótima, Boa, Razoável, Pouco precisa, Imprecisa. Linhagem: gold.fato_teletrabalho_uf.cv_classificacao. |
| 16 | `leitura_percentual` | `string` | n/a (view) | Uso do percentual segundo a faixa adotada. Domínio: Sustenta conclusão, Usar com ressalva, Só transparência. Linhagem: CASE sobre cv_classificacao. |
| 17 | `ic95_percentual_inf` | `double` | n/a (view) | Limite inferior aproximado de 95% do percentual, truncado em 0. Domínio: 0 a 100. Linhagem: GREATEST(0, percentual × (1 − 1,96 × cv_percentual / 100)). |
| 18 | `ic95_percentual_sup` | `double` | n/a (view) | Limite superior aproximado de 95% do percentual. Domínio: real não negativo. Linhagem: percentual × (1 + 1,96 × cv_percentual / 100). |

Fonte: o autor (2026), com base nos metadados e nas contagens do pipeline.

### `gold.vw_q7_ocupacao_proxy_tecnologia_uf`

*view* · Q7: Como evoluiu a população ocupada no setor proxy de tecnologia por UF? Proxy = grupamento 56624, mais amplo que TI (premissa); variação anual sobre média móvel de quatro trimestres. Origem: gold.fato_ocupacao_uf_atividade com dim_periodo, dim_geografia e dim_atividade_economica.

**Quadro 27 - Atributos de `gold.vw_q7_ocupacao_proxy_tecnologia_uf`**

| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |
|---|---|---|---|---|
| 1 | `uf_sigla` | `string` | n/a (view) | Sigla da UF. Domínio: 27 siglas de UF. Linhagem: gold.dim_geografia.uf_sigla. |
| 2 | `uf_nome` | `string` | n/a (view) | Nome da UF. Domínio: 27 UFs. Linhagem: gold.dim_geografia.nome. |
| 3 | `regiao` | `string` | n/a (view) | Grande região. Domínio: Norte, Nordeste, Sudeste, Sul, Centro-Oeste. Linhagem: gold.dim_geografia.regiao. |
| 4 | `ano` | `int` | n/a (view) | Ano do trimestre. Domínio: 2012 em diante. Linhagem: gold.dim_periodo.ano. |
| 5 | `trimestre` | `int` | n/a (view) | Trimestre (1 a 4). Domínio: 1 a 4. Linhagem: gold.dim_periodo.trimestre. |
| 6 | `periodo` | `string` | n/a (view) | Rótulo AAAATn. Domínio: AAAATn, como 2022T4. Linhagem: gold.dim_periodo.rotulo. |
| 7 | `pessoas_mil` | `double` | n/a (view) | Ocupados no grupamento 56624, em mil. Domínio: real não negativo. Linhagem: gold.fato_ocupacao_uf_atividade.pessoas_mil com atividade 56624. |
| 8 | `media_movel_4t` | `double` | n/a (view) | Média de pessoas_mil nos últimos quatro trimestres; nulo sem janela completa. Domínio: real não negativo; nulo nos três primeiros trimestres. Linhagem: AVG(pessoas_mil) na janela dos quatro trimestres até o atual, por UF. |
| 9 | `media_movel_4t_ano_anterior` | `double` | n/a (view) | media_movel_4t quatro trimestres antes. Domínio: real não negativo ou nulo. Linhagem: LAG(media_movel_4t, 4) por UF. |
| 10 | `variacao_anual_media_movel_pct` | `double` | n/a (view) | Variação percentual de media_movel_4t contra o ano anterior. Domínio: real, uma casa; nulo sem ano anterior. Linhagem: (media_movel_4t / media_movel_4t_ano_anterior − 1) × 100. |

Fonte: o autor (2026), com base nos metadados e nas contagens do pipeline.

### `gold.vw_q8_mercado_brasil`

*view* · Q8: Qual a estimativa de mercado endereçável no Brasil? Ordem de grandeza em pessoas: proxy 56624 em 2022T4 × taxa de teletrabalho (A), de trabalho remoto (B) ou da pesquisa (C, teste de transferência); teto lógico = total em trabalho remoto. Origem: gold.fato_ocupacao_uf_atividade, gold.fato_teletrabalho_uf e gold.fato_resposta_pesquisa, com as dimensões.

**Quadro 28 - Atributos de `gold.vw_q8_mercado_brasil`**

| # | Coluna | Tipo | Nulos | Descrição, domínio e linhagem |
|---|---|---|---|---|
| 1 | `nivel` | `string` | n/a (view) | uf ou pais (Brasil). Domínio: pais, uf. Linhagem: gold.dim_geografia.nivel. |
| 2 | `uf_sigla` | `string` | n/a (view) | Sigla da UF; BR no Brasil. Domínio: 27 siglas de UF ou BR. Linhagem: gold.dim_geografia.uf_sigla; BR fixo no Brasil. |
| 3 | `territorio` | `string` | n/a (view) | Nome do território. Domínio: Brasil e as 27 UFs. Linhagem: gold.dim_geografia.nome. |
| 4 | `regiao` | `string` | n/a (view) | Grande região; nulo no Brasil. Domínio: cinco grandes regiões; nulo no Brasil. Linhagem: gold.dim_geografia.regiao. |
| 5 | `cenario` | `string` | n/a (view) | A (teletrabalho IBGE), B (trabalho remoto IBGE) ou C (Remoto + Híbrido na pesquisa, teste de transferência). Domínio: A, B, C. Linhagem: constante de cada bloco da view. |
| 6 | `metodo` | `string` | n/a (view) | Como a estimativa foi agregada. Domínio: taxa nacional × proxy do Brasil, soma das estimativas por UF, taxa da UF × proxy da UF, taxa da pesquisa × proxy do Brasil. Linhagem: constante de cada bloco da view. |
| 7 | `taxa_pct` | `double` | n/a (view) | Taxa aplicada ao proxy, em %. Domínio: 0 a 100. Linhagem: gold.fato_teletrabalho_uf.percentual (A: 59805, B: 59804); em C, Remoto + Híbrido de brasileiros em fato_resposta_pesquisa 2022. |
| 8 | `taxa_cv_classificacao` | `string` | n/a (view) | Faixa adotada para o CV da taxa publicado pelo IBGE; nulo no cenário C, que não tem CV. Domínio: seis faixas de CV ou nulo. Linhagem: gold.fato_teletrabalho_uf.cv_classificacao. |
| 9 | `taxa_cv_pct` | `double` | n/a (view) | CV da taxa publicado pelo IBGE, em %; nulo no cenário C e no método soma das UFs. Domínio: real não negativo ou nulo. Linhagem: gold.fato_teletrabalho_uf.cv_percentual. |
| 10 | `proxy_mil` | `double` | n/a (view) | Ocupados no grupamento 56624 em 2022T4, em mil. Domínio: real positivo. Linhagem: gold.fato_ocupacao_uf_atividade.pessoas_mil com atividade 56624 em 2022T4. |
| 11 | `estimativa_mil` | `double` | n/a (view) | proxy_mil × taxa_pct / 100, em mil pessoas. Domínio: real não negativo, uma casa. Linhagem: proxy_mil × taxa_pct / 100. |
| 12 | `estimativa_ic95_inf_mil` | `double` | n/a (view) | proxy_mil × taxa_pct × (1 − 1,96 × CV / 100) / 100; só a precisão amostral da taxa do IBGE; nulo no cenário C. Domínio: real não negativo ou nulo. Linhagem: proxy_mil × taxa_pct × (1 − 1,96 × taxa_cv_pct / 100) / 100. |
| 13 | `estimativa_ic95_sup_mil` | `double` | n/a (view) | proxy_mil × taxa_pct × (1 + 1,96 × CV / 100) / 100; só a precisão amostral da taxa do IBGE; nulo no cenário C. Domínio: real não negativo ou nulo. Linhagem: proxy_mil × taxa_pct × (1 + 1,96 × taxa_cv_pct / 100) / 100. |
| 14 | `teto_logico_mil` | `double` | n/a (view) | Pessoas em trabalho remoto (59804) no território, em mil: limite superior de qualquer estimativa. Domínio: real positivo. Linhagem: gold.fato_teletrabalho_uf.pessoas_mil da modalidade 59804 no território. |
| 15 | `excede_teto_logico` | `boolean` | n/a (view) | true quando estimativa_mil passa de teto_logico_mil, o que invalida o cenário. Só pode ocorrer no cenário C. Domínio: true, false. Linhagem: estimativa_mil maior que teto_logico_mil. |

Fonte: o autor (2026), com base nos metadados e nas contagens do pipeline.
