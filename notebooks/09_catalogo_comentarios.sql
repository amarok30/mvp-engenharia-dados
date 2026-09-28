-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 09 · Catálogo: comentários de tabelas e colunas
-- MAGIC
-- MAGIC **Lê:** nada de dado; só metadado.
-- MAGIC
-- MAGIC **Escreve:** `COMMENT ON TABLE` e `COMMENT ON COLUMN` em todas as tabelas das camadas Silver e Gold, e as tags de
-- MAGIC tabelas, views e colunas.
-- MAGIC
-- MAGIC **Por quê:** o catálogo de dados fica no próprio Unity Catalog, junto do dado. Cada comentário de coluna diz o que
-- MAGIC o campo é, o domínio de valores e a linhagem (de onde veio e que transformação sofreu). O notebook 10 lê esses
-- MAGIC comentários do `information_schema` e gera `docs/catalogo-de-dados.md`.
-- MAGIC
-- MAGIC Fica separado dos notebooks de carga para poder rodar sem tocar em dado. As views recebem os comentários na própria
-- MAGIC definição (notebook 08).
-- MAGIC
-- MAGIC `CREATE OR REPLACE` (06 e 07) e `overwriteSchema` (01 a 04) recriam as tabelas e apagam os comentários. Por isso,
-- MAGIC depois de rodar qualquer notebook de 01 a 07, rodo também o 09 e o 10. O 10 para se achar coluna sem comentário.
-- MAGIC
-- MAGIC "Remoto" na pesquisa e "teletrabalho" no IBGE não são o mesmo conceito, e os comentários deixam isso claro campo a
-- MAGIC campo.
-- MAGIC
-- MAGIC Comentar de novo só sobrescreve o mesmo texto.

-- COMMAND ----------

USE CATALOG mafia_office;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Silver · `so_respondente`

-- COMMAND ----------

COMMENT ON TABLE silver.so_respondente IS 'Grão: um respondente da Stack Overflow Developer Survey em uma safra. Chave (safra, resposta_id). 277.080 linhas (2022 a 2025). Representação validada e não agregada; sem modelo estrela. Origem: bronze.so_pesquisa_2022 a 2025.';

COMMENT ON COLUMN silver.so_respondente.safra IS 'Ano da edição da pesquisa. Domínio: 2022, 2023, 2024, 2025. Linhagem: coluna de auditoria _safra da tabela bronze.so_pesquisa_{ano}.';
COMMENT ON COLUMN silver.so_respondente.resposta_id IS 'Identificador da resposta dentro da safra. Domínio: inteiro positivo, único por safra e repetido entre safras (a chave exige a safra). Linhagem: ResponseId, convertido de STRING para BIGINT.';
COMMENT ON COLUMN silver.so_respondente.e_profissional IS 'Indica desenvolvedor de profissão. Domínio: true, false, nulo quando MainBranch ausente. Linhagem: MainBranch igual a I am a developer by profession, após normalização Unicode.';
COMMENT ON COLUMN silver.so_respondente.empregado IS 'Indica vínculo empregatício. Domínio: true, false. Linhagem: Employment; algum item é Employed (2025, resposta única) ou começa com Employed, (2022 a 2024: full-time ou part-time, multi-resposta). Freelancer e autônomo ficam false.';
COMMENT ON COLUMN silver.so_respondente.autonomo IS 'Indica trabalho autônomo. Domínio: true, false. Linhagem: algum item de Employment é Independent contractor, freelancer, or self-employed (rótulo igual nas quatro safras).';
COMMENT ON COLUMN silver.so_respondente.trabalhando IS 'Indica quem trabalha, população à qual a pergunta de arranjo se aplica e base das views Q1 a Q5. Domínio: true, false. Linhagem: empregado OR autonomo.';
COMMENT ON COLUMN silver.so_respondente.arranjo_trabalho_origem IS 'Resposta original sobre situação de trabalho, cópia fiel, nunca sobrescrita. Domínio: rótulos da safra (ver silver.so_de_para_arranjo) ou NA. Linhagem: RemoteWork sem transformação. Não equivale a teletrabalho do IBGE.';
COMMENT ON COLUMN silver.so_respondente.arranjo_trabalho IS 'Arranjo de trabalho harmonizado entre safras. Domínio: Remoto, Híbrido, Presencial, Flexível, Não informado. Linhagem: RemoteWork (NA e vazio viram nulo) mapeado por JOIN com silver.so_de_para_arranjo por (safra, valor); valor sem mapeamento derruba o notebook 03. Conceito autodeclarado da pesquisa, não comparável ao teletrabalho do IBGE.';
COMMENT ON COLUMN silver.so_respondente.comparavel_serie IS 'Indica se o arranjo entra na série 2022 a 2025. Domínio: true, false. Linhagem: arranjo_trabalho fora de Flexível e Não informado.';
COMMENT ON COLUMN silver.so_respondente.pais IS 'País declarado pelo respondente, nome em inglês. Domínio: nomes da lista da pesquisa; nulo quando ausente. Linhagem: Country com NA e vazio para nulo, normalização Unicode e trim.';
COMMENT ON COLUMN silver.so_respondente.e_brasil IS 'Indica respondente do Brasil. Domínio: true, false. Linhagem: pais igual a Brazil. Subamostra pequena (825 em 2025): usar só no agregado nacional.';
COMMENT ON COLUMN silver.so_respondente.porte_empresa_origem IS 'Porte da empresa como declarado. Domínio: rótulos da safra (10 em 2022 a 2024, 9 em 2025). Linhagem: OrgSize com NA e vazio para nulo e normalização Unicode (apóstrofo U+2019 para ASCII).';
COMMENT ON COLUMN silver.so_respondente.porte_empresa IS 'Faixa canônica de porte. Domínio: Autônomo, Menos de 20, 20 a 99, 100 a 499, 500 a 999, 1.000 a 4.999, 5.000 a 9.999, 10.000 ou mais, Não sabe; nulo se rótulo não mapeado. Linhagem: porte_empresa_origem por mapa fixo; 2 to 9 e 10 to 19 (2022 a 2024) e Less than 20 (2025) viram Menos de 20.';
COMMENT ON COLUMN silver.so_respondente.porte_ordem IS 'Ordem da faixa de porte para ordenação. Domínio: 1 a 9. Linhagem: mesmo mapa de porte_empresa.';
COMMENT ON COLUMN silver.so_respondente.perfil_principal IS 'Perfil profissional principal. Domínio: rótulos de DevType da safra; nulo quando ausente. Linhagem: primeiro item de DevType antes do ; (multi-resposta só em 2022; resposta única de 2023 a 2025, e em 2025 a pergunta inclui o emprego de mais tempo no último ano), com trim. Perfis de 2022 não se comparam aos seguintes.';
COMMENT ON COLUMN silver.so_respondente.anos_codando IS 'Anos programando, incluindo anos de estudo (não é experiência profissional). Domínio: 0 a 50, censurado nas pontas. Linhagem: YearsCode; Less than 1 year vira 0; More than 50 years (2022 a 2024) e valores numéricos acima de 50 (2025, sem teto na fonte) viram 50; negativo ou não numérico vira nulo.';
COMMENT ON COLUMN silver.so_respondente.faixa_experiencia IS 'Faixa de anos codando. Domínio: 0–2, 3–5, 6–10, 11–20, 21+; nulo quando anos_codando nulo. Linhagem: derivada de anos_codando.';
COMMENT ON COLUMN silver.so_respondente.remuneracao_usd IS 'Remuneração anual convertida para dólar pela própria Stack Overflow. Domínio: real não negativo. Linhagem: ConvertedCompYearly para DOUBLE. Usa o câmbio da safra: comparar anos mistura efeito câmbio e efeito salário. Resumir por mediana.';
COMMENT ON COLUMN silver.so_respondente.remuneracao_outlier IS 'Marca remuneração implausível, sem remover a linha. Domínio: true quando remuneracao_usd fora de [1.000; 1.000.000], false caso contrário ou nulo. Linhagem: derivada de remuneracao_usd.';
COMMENT ON COLUMN silver.so_respondente.satisfacao_trabalho IS 'Satisfação declarada com o emprego. Domínio: 0 a 10; nulo em 2022 e 2023 (pergunta inexistente, ausência estrutural). Linhagem: JobSat para DOUBLE; fora de 0 a 10 vira nulo.';
COMMENT ON COLUMN silver.so_respondente._ingerido_em IS 'Momento da ingestão na Bronze. Domínio: data e hora UTC da carga. Linhagem: coluna de auditoria _ingerido_em da Bronze, propagada.';

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Silver · `so_de_para_arranjo`

-- COMMAND ----------

COMMENT ON TABLE silver.so_de_para_arranjo IS 'De-para versionado do arranjo de trabalho, uma linha por valor de origem em cada safra, incluindo o nulo. 15 linhas. Origem: docs/mapa-de-para-arranjo.csv no Git, enviado ao Volume bronze.pouso/referencia.';

COMMENT ON COLUMN silver.so_de_para_arranjo.safra IS 'Safra em que o rótulo existe. Domínio: 2022 a 2025; nulo significa todas as safras (linha do valor nulo). Linhagem: coluna safra do CSV, com todas convertido para nulo.';
COMMENT ON COLUMN silver.so_de_para_arranjo.valor_origem IS 'Rótulo literal de RemoteWork na safra. Domínio: opções da pesquisa; nulo representa resposta ausente. Linhagem: coluna valor_origem do CSV, campo vazio lido como nulo.';
COMMENT ON COLUMN silver.so_de_para_arranjo.valor_canonico IS 'Categoria harmonizada. Domínio: Remoto, Híbrido, Presencial, Flexível, Não informado. Linhagem: coluna valor_canonico do CSV versionado no Git.';
COMMENT ON COLUMN silver.so_de_para_arranjo.entra_serie_historica IS 'Indica se o rótulo entra na série comparável 2022 a 2025. Domínio: true, false. Linhagem: coluna do CSV convertida para BOOLEAN.';
COMMENT ON COLUMN silver.so_de_para_arranjo.observacao IS 'Justificativa do mapeamento, incluindo perda de granularidade em 2025 e ausência de equivalente para Your choice. Domínio: texto livre. Linhagem: coluna observacao do CSV.';

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Silver · `so_metadados_pergunta`

-- COMMAND ----------

COMMENT ON TABLE silver.so_metadados_pergunta IS 'Uma linha por pergunta (qname) em cada safra, inclusive quando a pergunta não existia. Mostra que o texto de RemoteWork é o mesmo nas quatro safras, embora as opções tenham mudado. Origem: bronze.so_esquema.';

COMMENT ON COLUMN silver.so_metadados_pergunta.safra IS 'Safra. Domínio: 2022 a 2025. Linhagem: _safra de bronze.so_esquema, completada por produto cartesiano com as quatro safras.';
COMMENT ON COLUMN silver.so_metadados_pergunta.qname IS 'Nome curto da pergunta, igual ao nome de coluna do results.csv quando a pergunta é de resposta única. Domínio: identificador sem espaço, 383 distintos nas quatro safras. Linhagem: qname de bronze.so_esquema.';
COMMENT ON COLUMN silver.so_metadados_pergunta.texto_pergunta IS 'Texto da pergunta. Domínio: texto; nulo quando a pergunta não existia na safra. Linhagem: question de bronze.so_esquema; se o qname se repete na safra (subperguntas de 2025), o menor texto em ordem alfabética.';
COMMENT ON COLUMN silver.so_metadados_pergunta.tipo IS 'Tipo da pergunta segundo a pesquisa. Domínio: códigos do schema.csv. Linhagem: type de bronze.so_esquema, menor valor por (safra, qname).';
COMMENT ON COLUMN silver.so_metadados_pergunta.presente_na_safra IS 'Indica se a pergunta existia na safra. Domínio: true, false. Linhagem: texto_pergunta não nulo. Distingue ausência estrutural de não resposta.';

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Silver · `ibge_teletrabalho_uf`

-- COMMAND ----------

COMMENT ON TABLE silver.ibge_teletrabalho_uf IS 'Grão: território (Brasil ou UF) × modalidade de trabalho remoto ou teletrabalho, 2022 (4º trimestre). Módulo de teletrabalho divulgado para 2022; não foi localizada edição posterior com esse recorte, então não há série. Origem: bronze.ibge_sidra_9471 sem o cabeçalho d[0], variáveis pivotadas.';

COMMENT ON COLUMN silver.ibge_teletrabalho_uf.nivel_territorial IS 'Nível do território. Domínio: pais (Brasil), uf. Linhagem: campo NC do SIDRA (1 para Brasil, 3 para UF).';
COMMENT ON COLUMN silver.ibge_teletrabalho_uf.uf_codigo IS 'Código IBGE do território. Domínio: 1 para Brasil; dois dígitos para UF. Linhagem: campo DnC da dimensão territorial, identificada pelo rótulo do cabeçalho.';
COMMENT ON COLUMN silver.ibge_teletrabalho_uf.uf_nome IS 'Nome do território. Domínio: Brasil e as 27 UFs. Linhagem: campo DnN da dimensão territorial.';
COMMENT ON COLUMN silver.ibge_teletrabalho_uf.ano IS 'Ano de referência. Domínio: 2022 (PNAD Contínua anual, 4º trimestre, segundo a nota da tabela 9471). Linhagem: quatro primeiros caracteres do código de período do SIDRA.';
COMMENT ON COLUMN silver.ibge_teletrabalho_uf.modalidade_codigo IS 'Código da classificação c1675. Domínio: 59803 Total, 59804 Realizou trabalho remoto, 59805 Realizou teletrabalho, 59806 Teletrabalho no domicílio, 59807 Fora do domicílio, 59808 No domicílio e fora. Linhagem: DnC da classificação.';
COMMENT ON COLUMN silver.ibge_teletrabalho_uf.modalidade IS 'Nome da modalidade conforme o IBGE. Domínio: rótulos da classificação c1675. Linhagem: DnN da classificação. Teletrabalho do IBGE não é o Remoto autodeclarado da pesquisa.';
COMMENT ON COLUMN silver.ibge_teletrabalho_uf.pessoas_mil IS 'Estimativa de pessoas de 14 anos ou mais ocupadas na modalidade, em mil. Domínio: real não negativo; nulo quando pessoas_mil_sinal é .., ... ou x. Linhagem: campo V da variável 4090, pivotado. Modalidades não se somam (verificação C23).';
COMMENT ON COLUMN silver.ibge_teletrabalho_uf.pessoas_mil_sinal IS 'Sinal convencional do IBGE na célula (Normas de apresentação tabular). Domínio: nulo quando a célula traz número; - (zero não resultante de arredondamento, valor 0); .. (não se aplica); ... (não disponível); x (omitido por sigilo); nos três últimos o valor é nulo. Linhagem: campo V da variável 4090.';
COMMENT ON COLUMN silver.ibge_teletrabalho_uf.cv_pessoas IS 'Coeficiente de variação de pessoas_mil, em %. Domínio: real não negativo. Linhagem: campo V da variável 4091, pivotado.';
COMMENT ON COLUMN silver.ibge_teletrabalho_uf.cv_pessoas_sinal IS 'Sinal convencional do IBGE na célula (Normas de apresentação tabular). Domínio: nulo quando a célula traz número; - (zero não resultante de arredondamento, valor 0); .. (não se aplica); ... (não disponível); x (omitido por sigilo); nos três últimos o valor é nulo. Linhagem: campo V da variável 4091.';
COMMENT ON COLUMN silver.ibge_teletrabalho_uf.cv_pessoas_classificacao IS 'Faixa de CV adotada no projeto sobre o cv_pessoas publicado pelo IBGE (convenção, não classificação do IBGE). Domínio: Exata, Ótima, Boa, Razoável, Pouco precisa, Imprecisa; nulo sem CV. Linhagem: derivada de cv_pessoas.';
COMMENT ON COLUMN silver.ibge_teletrabalho_uf.percentual IS 'Percentual publicado pelo IBGE para a modalidade. Domínio: 0 a 100. Linhagem: campo V da variável 12965, com precisão máxima (/d/m), pivotado.';
COMMENT ON COLUMN silver.ibge_teletrabalho_uf.percentual_sinal IS 'Sinal convencional do IBGE na célula (Normas de apresentação tabular). Domínio: nulo quando a célula traz número; - (zero não resultante de arredondamento, valor 0); .. (não se aplica); ... (não disponível); x (omitido por sigilo); nos três últimos o valor é nulo. Linhagem: campo V da variável 12965.';
COMMENT ON COLUMN silver.ibge_teletrabalho_uf.cv_percentual IS 'Coeficiente de variação do percentual, em %. Domínio: real não negativo; 0 no Total, publicado com o sinal - (zero não resultante de arredondamento). Linhagem: campo V da variável 12966, com precisão máxima (/d/m), pivotado.';
COMMENT ON COLUMN silver.ibge_teletrabalho_uf.cv_percentual_sinal IS 'Sinal convencional do IBGE na célula (Normas de apresentação tabular). Domínio: nulo quando a célula traz número; - (zero não resultante de arredondamento, valor 0); .. (não se aplica); ... (não disponível); x (omitido por sigilo); nos três últimos o valor é nulo. Linhagem: campo V da variável 12966.';
COMMENT ON COLUMN silver.ibge_teletrabalho_uf.cv_classificacao IS 'Faixa de CV adotada no projeto sobre o cv_percentual publicado pelo IBGE (convenção, não classificação do IBGE). Domínio: Exata (0), Ótima (até 5), Boa (mais de 5 até 15), Razoável (mais de 15 até 30), Pouco precisa (mais de 30 até 50), Imprecisa (mais de 50); nulo sem CV. Linhagem: derivada de cv_percentual.';
COMMENT ON COLUMN silver.ibge_teletrabalho_uf.estimativa_confiavel IS 'CV publicado pelo IBGE; o limiar de 15% é critério do projeto. Domínio: true quando cv_percentual até 15 (Exata, Ótima ou Boa), false acima, nulo sem CV. Linhagem: derivada de cv_percentual.';
COMMENT ON COLUMN silver.ibge_teletrabalho_uf.e_experimental IS 'Marca estatística experimental do IBGE. Domínio: sempre true. Linhagem: constante; o nome da tabela 9471 no SIDRA termina em Estatísticas experimentais.';
COMMENT ON COLUMN silver.ibge_teletrabalho_uf.disponivel_no_nivel IS 'Indica se o IBGE declara a categoria disponível no nível territorial da linha. Domínio: false para 59807 e 59808 por UF (a nota da tabela 9471 as declara só para Brasil e Grande Região), true nas demais. Linhagem: nivel_territorial e modalidade_codigo; medido na verificação C28.';

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Silver · `ibge_ocupados_uf_atividade`

-- COMMAND ----------

COMMENT ON TABLE silver.ibge_ocupados_uf_atividade IS 'Grão: UF × trimestre × grupamento de atividade no trabalho principal. Pessoas de 14 anos ou mais ocupadas, PNAD Contínua. Origem: bronze.ibge_sidra_5434 sem o cabeçalho d[0].';

COMMENT ON COLUMN silver.ibge_ocupados_uf_atividade.uf_codigo IS 'Código IBGE da UF. Domínio: dois dígitos, 27 UFs. Linhagem: DnC da dimensão territorial.';
COMMENT ON COLUMN silver.ibge_ocupados_uf_atividade.uf_nome IS 'Nome da UF. Domínio: 27 UFs. Linhagem: DnN da dimensão territorial.';
COMMENT ON COLUMN silver.ibge_ocupados_uf_atividade.ano IS 'Ano do trimestre. Domínio: 2012 em diante. Linhagem: quatro primeiros caracteres de periodo_codigo.';
COMMENT ON COLUMN silver.ibge_ocupados_uf_atividade.trimestre IS 'Trimestre do ano. Domínio: 1 a 4. Linhagem: dois últimos caracteres de periodo_codigo.';
COMMENT ON COLUMN silver.ibge_ocupados_uf_atividade.periodo_codigo IS 'Código de período do SIDRA. Domínio: AAAATT (ex.: 202204). Linhagem: DnC da dimensão de período, sem transformação.';
COMMENT ON COLUMN silver.ibge_ocupados_uf_atividade.atividade_codigo IS 'Código do grupamento de atividade (classificação c888). Domínio: 13 códigos, incluindo 47946 Total, que soma os demais. Linhagem: DnC da classificação.';
COMMENT ON COLUMN silver.ibge_ocupados_uf_atividade.atividade_nome IS 'Nome do grupamento de atividade conforme o IBGE. Domínio: rótulos da classificação c888. Linhagem: DnN da classificação.';
COMMENT ON COLUMN silver.ibge_ocupados_uf_atividade.e_proxy_tecnologia IS 'Marca o grupamento usado como proxy de tecnologia. Domínio: true só para 56624 (Informação, comunicação e atividades financeiras, imobiliárias, profissionais e administrativas). Linhagem: atividade_codigo igual a 56624. Premissa: mais amplo que TI.';
COMMENT ON COLUMN silver.ibge_ocupados_uf_atividade.pessoas_mil IS 'Estimativa de pessoas ocupadas, em mil. Domínio: real não negativo; 0 quando o sinal é -; nulo quando o sinal é .., ... ou x. Linhagem: campo V da variável 4090. Não somar grupamentos livremente: 47946 é o Total e 60031 está contido em 47948 (verificação C24).';
COMMENT ON COLUMN silver.ibge_ocupados_uf_atividade.pessoas_mil_sinal IS 'Sinal convencional do IBGE na célula (Normas de apresentação tabular). Domínio: nulo quando a célula traz número; - (zero não resultante de arredondamento, valor 0); .. (não se aplica); ... (não disponível); x (omitido por sigilo); nos três últimos o valor é nulo. Linhagem: campo V da variável 4090.';

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Gold · dimensões

-- COMMAND ----------

COMMENT ON TABLE gold.dim_periodo IS 'Dimensão conformada de período, usada pelas três tabelas fato. Uma linha por ano (pesquisa e teletrabalho) e por trimestre (ocupação), mais o membro -1. Origem: silver.so_respondente, silver.ibge_teletrabalho_uf, silver.ibge_ocupados_uf_atividade.';
COMMENT ON COLUMN gold.dim_periodo.periodo_chave IS 'Chave substituta determinística. Domínio: ano × 10 para ano (20220), ano × 10 + trimestre para trimestre (20224), -1 desconhecido. Linhagem: calculada de ano e trimestre.';
COMMENT ON COLUMN gold.dim_periodo.tipo_periodo IS 'Granularidade do período. Domínio: ano, trimestre, Desconhecido. Linhagem: fonte que originou a linha.';
COMMENT ON COLUMN gold.dim_periodo.ano IS 'Ano. Domínio: inteiro de quatro dígitos; nulo no membro -1. Linhagem: safra da pesquisa, ano da 9471 e ano da 5434.';
COMMENT ON COLUMN gold.dim_periodo.trimestre IS 'Trimestre. Domínio: 1 a 4; nulo em períodos anuais e no membro -1. Linhagem: trimestre da 5434.';
COMMENT ON COLUMN gold.dim_periodo.rotulo IS 'Rótulo legível. Domínio: AAAA ou AAAATn (ex.: 2022T4). Linhagem: derivado de ano e trimestre.';

COMMENT ON TABLE gold.dim_geografia IS 'Dimensão conformada de geografia, usada pelas três tabelas fato. Países da pesquisa (nome em inglês) e UFs do IBGE, com o Brasil conformado como Brazil nas duas fontes. Membros especiais: -1 Desconhecido (falha de busca na dimensão) e -2 Não informado (país em branco na pesquisa).';
COMMENT ON COLUMN gold.dim_geografia.geo_chave IS 'Chave substituta estável. Domínio: inteiro não negativo, xxhash64 de (nivel, codigo); -1 Desconhecido; -2 Não informado (país em branco na pesquisa). Linhagem: gerada no notebook 06; a mesma chave natural gera sempre a mesma chave em qualquer recarga.';
COMMENT ON COLUMN gold.dim_geografia.nivel IS 'Nível territorial. Domínio: pais, uf, Desconhecido. Linhagem: pais vem de silver.so_respondente.pais; uf vem das tabelas Silver do IBGE.';
COMMENT ON COLUMN gold.dim_geografia.codigo IS 'Chave natural. Domínio: nome do país em inglês para nivel pais; código IBGE de dois dígitos para nivel uf. Linhagem: silver.so_respondente.pais e uf_codigo das tabelas IBGE; a linha Brasil (NC 1) do IBGE é associada a Brazil.';
COMMENT ON COLUMN gold.dim_geografia.nome IS 'Nome do território. Domínio: nome do país em inglês ou nome da UF em português. Linhagem: pais da pesquisa ou uf_nome do IBGE (menor valor por código).';
COMMENT ON COLUMN gold.dim_geografia.pais_nome IS 'País a que o território pertence. Domínio: nome do país em inglês; Brazil para todas as UFs. Linhagem: pais da pesquisa; constante Brazil para UFs, para conformar as fontes.';
COMMENT ON COLUMN gold.dim_geografia.uf_sigla IS 'Sigla da UF. Domínio: 27 siglas; nulo para países. Linhagem: tabela de referência código IBGE para sigla, embutida no notebook 06.';
COMMENT ON COLUMN gold.dim_geografia.regiao IS 'Grande região do Brasil. Domínio: Norte, Nordeste, Sudeste, Sul, Centro-Oeste; nulo para países. Linhagem: primeiro dígito do código IBGE da UF.';

COMMENT ON TABLE gold.dim_arranjo_trabalho IS 'Dimensão do arranjo de trabalho autodeclarado na pesquisa. Não conformada com dim_modalidade_ibge, porque os conceitos são diferentes. Origem: silver.so_de_para_arranjo.';
COMMENT ON COLUMN gold.dim_arranjo_trabalho.arranjo_chave IS 'Chave substituta igual à ordem canônica. Domínio: 1 a 5; -1 desconhecido. Linhagem: ordem fixa no notebook 06.';
COMMENT ON COLUMN gold.dim_arranjo_trabalho.arranjo IS 'Categoria harmonizada. Domínio: Remoto, Híbrido, Presencial, Flexível, Não informado, Desconhecido. Linhagem: valor_canonico do de-para.';
COMMENT ON COLUMN gold.dim_arranjo_trabalho.entra_serie_historica IS 'Indica categoria comparável entre 2022 e 2025. Domínio: true para Remoto, Híbrido e Presencial. Linhagem: entra_serie_historica do de-para (conjunção por categoria).';
COMMENT ON COLUMN gold.dim_arranjo_trabalho.ordem IS 'Ordem de exibição. Domínio: 1 a 5; 99 no membro -1. Linhagem: fixa no notebook 06.';

COMMENT ON TABLE gold.dim_porte_empresa IS 'Dimensão de porte da empresa em nove faixas canônicas, harmonizando a fusão de faixas de 2025. Membros especiais: -1 Desconhecido (rótulo sem mapeamento) e -2 Não informado (porte em branco). Origem: mapa fixo equivalente ao do notebook 03.';
COMMENT ON COLUMN gold.dim_porte_empresa.porte_chave IS 'Chave substituta igual à ordem da faixa. Domínio: 1 a 9; -1 Desconhecido (rótulo sem mapeamento); -2 Não informado. Linhagem: fixa no notebook 06.';
COMMENT ON COLUMN gold.dim_porte_empresa.porte IS 'Faixa canônica. Domínio: Autônomo, Menos de 20, 20 a 99, 100 a 499, 500 a 999, 1.000 a 4.999, 5.000 a 9.999, 10.000 ou mais, Não sabe, Não informado, Desconhecido. Linhagem: silver.so_respondente.porte_empresa.';
COMMENT ON COLUMN gold.dim_porte_empresa.ordem IS 'Ordem crescente de porte. Domínio: 1 a 9; 98 no membro -2; 99 no membro -1. Linhagem: silver.so_respondente.porte_ordem.';
COMMENT ON COLUMN gold.dim_porte_empresa.faixa_min IS 'Menor número de empregados da faixa. Domínio: inteiro; nulo em Menos de 20 (2025 não informa o piso), Não sabe, Não informado e Desconhecido. Linhagem: rótulos da pesquisa.';
COMMENT ON COLUMN gold.dim_porte_empresa.faixa_max IS 'Maior número de empregados da faixa. Domínio: inteiro; nulo em 10.000 ou mais, Não sabe, Não informado e Desconhecido. Linhagem: rótulos da pesquisa.';

COMMENT ON TABLE gold.dim_perfil_dev IS 'Dimensão de perfil profissional: combinação de perfil principal e faixa de experiência. Origem: silver.so_respondente.';
COMMENT ON COLUMN gold.dim_perfil_dev.perfil_chave IS 'Chave substituta estável. Domínio: inteiro não negativo, xxhash64 de (perfil, faixa_experiencia); -1 desconhecido. Linhagem: gerada no notebook 06; a mesma chave natural gera sempre a mesma chave em qualquer recarga.';
COMMENT ON COLUMN gold.dim_perfil_dev.perfil IS 'Perfil profissional principal. Domínio: rótulos de DevType; Não informado quando ausente. Linhagem: silver.so_respondente.perfil_principal (primeiro item de DevType).';
COMMENT ON COLUMN gold.dim_perfil_dev.faixa_experiencia IS 'Faixa de anos codando. Domínio: 0–2, 3–5, 6–10, 11–20, 21+, Não informado. Linhagem: silver.so_respondente.faixa_experiencia.';

COMMENT ON TABLE gold.dim_modalidade_ibge IS 'Dimensão de modalidade de trabalho remoto e teletrabalho do IBGE (classificação c1675). Não conformada com dim_arranjo_trabalho, porque os conceitos são diferentes. Origem: silver.ibge_teletrabalho_uf.';
COMMENT ON COLUMN gold.dim_modalidade_ibge.modalidade_chave IS 'Chave substituta estável. Domínio: inteiro não negativo, xxhash64 de modalidade_codigo; -1 desconhecido. Linhagem: gerada no notebook 06; a mesma chave natural gera sempre a mesma chave em qualquer recarga.';
COMMENT ON COLUMN gold.dim_modalidade_ibge.modalidade IS 'Nome da modalidade conforme o IBGE. Domínio: rótulos da c1675. Linhagem: silver.ibge_teletrabalho_uf.modalidade.';
COMMENT ON COLUMN gold.dim_modalidade_ibge.e_teletrabalho IS 'Indica teletrabalho ou recorte de teletrabalho por local. Domínio: true para 59805 a 59808; false para 59803 (Total) e 59804 (trabalho remoto, conceito mais amplo). Linhagem: regra sobre modalidade_codigo. Não somar as linhas com true: 59806 e 59807 se sobrepõem em 59808.';
COMMENT ON COLUMN gold.dim_modalidade_ibge.modalidade_codigo IS 'Código da classificação c1675. Domínio: 59803 a 59808. Linhagem: silver.ibge_teletrabalho_uf.modalidade_codigo.';
COMMENT ON COLUMN gold.dim_modalidade_ibge.modalidade_pai_codigo IS 'Modalidade que contém esta. Domínio: 59803 para 59804; 59804 para 59805; 59805 para 59806, 59807 e 59808; nulo para 59803. Linhagem: hierarquia fixa no notebook 06, verificada no dado pela verificação C23 (59806 + 59807 - 59808 = 59805).';

COMMENT ON TABLE gold.dim_atividade_economica IS 'Dimensão de grupamento de atividade no trabalho principal (classificação c888). Origem: silver.ibge_ocupados_uf_atividade.';
COMMENT ON COLUMN gold.dim_atividade_economica.atividade_chave IS 'Chave substituta estável. Domínio: inteiro não negativo, xxhash64 de codigo; -1 desconhecido. Linhagem: gerada no notebook 06; a mesma chave natural gera sempre a mesma chave em qualquer recarga.';
COMMENT ON COLUMN gold.dim_atividade_economica.codigo IS 'Código do grupamento. Domínio: códigos da c888. Linhagem: silver.ibge_ocupados_uf_atividade.atividade_codigo.';
COMMENT ON COLUMN gold.dim_atividade_economica.nome IS 'Nome do grupamento conforme o IBGE. Domínio: rótulos da c888. Linhagem: atividade_nome (menor valor por código).';
COMMENT ON COLUMN gold.dim_atividade_economica.e_proxy_tecnologia IS 'Marca o proxy de tecnologia. Domínio: true só para 56624. Linhagem: silver.ibge_ocupados_uf_atividade.e_proxy_tecnologia. Premissa: mais amplo que TI.';
COMMENT ON COLUMN gold.dim_atividade_economica.e_total IS 'Marca o grupamento Total, que soma os demais. Domínio: true só para 47946. Linhagem: regra sobre codigo, verificada pela verificação C24.';
COMMENT ON COLUMN gold.dim_atividade_economica.e_subgrupamento IS 'Marca grupamento contido em outro. Domínio: true só para 60031 (Indústria de transformação, contida em 47948, Indústria geral). Linhagem: regra sobre codigo, verificada pela verificação C24.';

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Gold · fatos e qualidade

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## gold.analise_q1d_modelo_logistico (notebook 08b)

-- COMMAND ----------

COMMENT ON TABLE gold.analise_q1d_modelo_logistico IS 'Q1d: regressão logística de Remoto (série comparável, base trabalhando) sobre safra, vínculo, Brasil e faixa de experiência; uma linha por termo e por contraste entre safras. Controla composição observada; não corrige seleção. Escrita pelo notebook 08b.';
COMMENT ON COLUMN gold.analise_q1d_modelo_logistico.fator IS 'Fator do modelo. Domínio: safra, vinculo, brasil, faixa_experiencia. Linhagem: nome do bloco de colunas na matriz do modelo do notebook 08b.';
COMMENT ON COLUMN gold.analise_q1d_modelo_logistico.categoria IS 'Categoria do fator a que o coeficiente se refere. Domínio: safras 2023 a 2025; Autônomo e Ambos; Brasil; faixas de experiência exceto 0–2. Linhagem: rótulo da coluna na matriz do modelo do notebook 08b.';
COMMENT ON COLUMN gold.analise_q1d_modelo_logistico.referencia IS 'Categoria de referência do coeficiente (a que fica com chance 1). Domínio: 2022, Empregado, fora do Brasil, 0–2; nos contrastes, a safra anterior. Linhagem: categoria omitida de cada fator na matriz do modelo do notebook 08b.';
COMMENT ON COLUMN gold.analise_q1d_modelo_logistico.tipo IS 'termo (coeficiente contra a referência global) ou contraste (diferença entre duas safras). Domínio: termo, contraste. Linhagem: termo vem direto do GLM; contraste é a diferença entre dois coeficientes de safra no notebook 08b.';
COMMENT ON COLUMN gold.analise_q1d_modelo_logistico.coeficiente IS 'Coeficiente na escala logit. Domínio: real, em geral entre −3 e 3. Linhagem: GLM binomial do statsmodels sobre as células agregadas por safra, vínculo, Brasil e faixa.';
COMMENT ON COLUMN gold.analise_q1d_modelo_logistico.erro_padrao IS 'Erro padrão do coeficiente; só erro aleatório. Domínio: real positivo. Linhagem: raiz da diagonal da matriz de covariância do GLM, multiplicada pela raiz da dispersão de Pearson.';
COMMENT ON COLUMN gold.analise_q1d_modelo_logistico.razao_de_chances IS 'exp(coeficiente): razão de chances (odds) de Remoto contra a referência, a composição constante; 0,80 quer dizer odds 20% menores, não proporção 20% menor. Domínio: real positivo. Linhagem: derivada de coeficiente.';
COMMENT ON COLUMN gold.analise_q1d_modelo_logistico.ic95_inf IS 'Limite inferior do intervalo de 95% da razão de chances. Domínio: real positivo. Linhagem: exp(coeficiente − 1,96 × erro_padrao).';
COMMENT ON COLUMN gold.analise_q1d_modelo_logistico.ic95_sup IS 'Limite superior do intervalo de 95% da razão de chances. Domínio: real positivo. Linhagem: exp(coeficiente + 1,96 × erro_padrao).';
COMMENT ON COLUMN gold.analise_q1d_modelo_logistico.p_valor IS 'p-valor bilateral do teste de Wald. Domínio: 0 a 1. Linhagem: teste de Wald do GLM, ou do contraste, no notebook 08b.';
COMMENT ON COLUMN gold.analise_q1d_modelo_logistico.n_celulas IS 'Combinações de safra × vínculo × Brasil × faixa usadas no ajuste. Domínio: inteiro de 1 a 160 (4 safras × 4 vínculos × 2 × 5 faixas). Linhagem: número de linhas da tabela agregada do notebook 08b.';
COMMENT ON COLUMN gold.analise_q1d_modelo_logistico.n_respondentes IS 'Respondentes na base do modelo (trabalhando, série comparável, país e faixa informados). Domínio: inteiro positivo. Linhagem: soma de gold.fato_resposta_pesquisa.qtd_respondentes na base do modelo.';
COMMENT ON COLUMN gold.analise_q1d_modelo_logistico.remotos IS 'Respondentes em Remoto na base do modelo. Domínio: inteiro de 0 a n_respondentes. Linhagem: soma de gold.fato_resposta_pesquisa.qtd_respondentes com arranjo Remoto.';
COMMENT ON COLUMN gold.analise_q1d_modelo_logistico.dispersao_pearson IS 'Dispersão de Pearson do modelo binomial (qui-quadrado de Pearson sobre graus de liberdade); acima de 1, os erros-padrão foram corrigidos por ela. Domínio: real positivo, igual em todas as linhas. Linhagem: pearson_chi2 / df_resid do GLM binomial do notebook 08b.';

-- COMMAND ----------

COMMENT ON TABLE gold.fato_resposta_pesquisa IS 'Grão: um respondente da Stack Overflow Developer Survey em uma safra. Amostra autosselecionada, sem peso amostral: contagens descrevem quem respondeu, não a população. Origem: silver.so_respondente.';
COMMENT ON COLUMN gold.fato_resposta_pesquisa.periodo_chave IS 'FK para dim_periodo (tipo ano). Domínio: chaves de dim_periodo; -1 se a busca na dimensão falhar. Linhagem: safra.';
COMMENT ON COLUMN gold.fato_resposta_pesquisa.geo_chave IS 'FK para dim_geografia (nivel pais). Domínio: chaves de dim_geografia; -2 quando o país está em branco; -1 se a busca na dimensão falhar (a verificação C15 exige zero). Linhagem: silver.so_respondente.pais.';
COMMENT ON COLUMN gold.fato_resposta_pesquisa.arranjo_chave IS 'FK para dim_arranjo_trabalho. Domínio: 1 a 5; -1 se a busca na dimensão falhar. Linhagem: silver.so_respondente.arranjo_trabalho.';
COMMENT ON COLUMN gold.fato_resposta_pesquisa.porte_chave IS 'FK para dim_porte_empresa. Domínio: 1 a 9; -2 quando o porte está em branco; -1 se o rótulo não tiver mapeamento (a verificação C15 exige zero). Linhagem: silver.so_respondente.porte_empresa e porte_empresa_origem.';
COMMENT ON COLUMN gold.fato_resposta_pesquisa.perfil_chave IS 'FK para dim_perfil_dev. Domínio: chaves de dim_perfil_dev; -1 se a busca na dimensão falhar. Linhagem: perfil_principal e faixa_experiencia, com nulo como Não informado.';
COMMENT ON COLUMN gold.fato_resposta_pesquisa.safra IS 'Dimensão degenerada: safra da pesquisa. Domínio: 2022 a 2025. Linhagem: silver.so_respondente.safra.';
COMMENT ON COLUMN gold.fato_resposta_pesquisa.resposta_id IS 'Dimensão degenerada: identificador da resposta na safra; com safra, rastreia a linha até a Silver e a Bronze. Domínio: inteiro positivo. Linhagem: silver.so_respondente.resposta_id.';
COMMENT ON COLUMN gold.fato_resposta_pesquisa.e_profissional IS 'Atributo degenerado: desenvolvedor de profissão. Domínio: true, false, nulo. Linhagem: silver.so_respondente.e_profissional.';
COMMENT ON COLUMN gold.fato_resposta_pesquisa.empregado IS 'Atributo degenerado: vínculo empregatício. Domínio: true, false. Linhagem: silver.so_respondente.empregado.';
COMMENT ON COLUMN gold.fato_resposta_pesquisa.autonomo IS 'Atributo degenerado: trabalho autônomo. Domínio: true, false. Linhagem: silver.so_respondente.autonomo.';
COMMENT ON COLUMN gold.fato_resposta_pesquisa.trabalhando IS 'Atributo degenerado: empregado ou autônomo; base das views Q1 a Q5. Domínio: true, false. Linhagem: silver.so_respondente.trabalhando.';
COMMENT ON COLUMN gold.fato_resposta_pesquisa.remuneracao_outlier IS 'Atributo degenerado: remuneração fora de [1.000; 1.000.000] USD. Domínio: true, false. Linhagem: silver.so_respondente.remuneracao_outlier.';
COMMENT ON COLUMN gold.fato_resposta_pesquisa.qtd_respondentes IS 'Medida aditiva de contagem. Domínio: sempre 1. Linhagem: constante no notebook 07.';
COMMENT ON COLUMN gold.fato_resposta_pesquisa.remuneracao_usd IS 'Medida não aditiva: remuneração anual em USD no câmbio da safra. Domínio: real não negativo ou nulo. Linhagem: silver.so_respondente.remuneracao_usd. Resumir por mediana.';
COMMENT ON COLUMN gold.fato_resposta_pesquisa.satisfacao_trabalho IS 'Medida não aditiva: satisfação com o emprego. Domínio: 0 a 10; nulo em 2022 e 2023. Linhagem: silver.so_respondente.satisfacao_trabalho.';
COMMENT ON COLUMN gold.fato_resposta_pesquisa.anos_codando IS 'Medida não aditiva: anos programando, incluindo anos de estudo. Domínio: 0 a 50, censurado nas pontas. Linhagem: silver.so_respondente.anos_codando.';

COMMENT ON TABLE gold.fato_teletrabalho_uf IS 'Grão: território (Brasil ou UF) × modalidade de trabalho remoto ou teletrabalho, 2022 (4º trimestre). Estimativa populacional ponderada da PNAD Contínua anual, estatísticas experimentais segundo o SIDRA. Origem: silver.ibge_teletrabalho_uf.';
COMMENT ON COLUMN gold.fato_teletrabalho_uf.periodo_chave IS 'FK para dim_periodo (tipo ano, 2022). Domínio: chaves de dim_periodo; -1 se a busca na dimensão falhar. Linhagem: silver.ibge_teletrabalho_uf.ano.';
COMMENT ON COLUMN gold.fato_teletrabalho_uf.geo_chave IS 'FK para dim_geografia: nivel pais Brazil para a linha nacional, nivel uf para UFs. Domínio: chaves de dim_geografia; -1 se a busca na dimensão falhar. Linhagem: nivel_territorial e uf_codigo.';
COMMENT ON COLUMN gold.fato_teletrabalho_uf.modalidade_chave IS 'FK para dim_modalidade_ibge. Domínio: chaves de dim_modalidade_ibge; -1 se a busca na dimensão falhar. Linhagem: modalidade_codigo.';
COMMENT ON COLUMN gold.fato_teletrabalho_uf.pessoas_mil IS 'Medida semiaditiva: pessoas ocupadas em mil. Soma entre UFs dentro de uma modalidade; não somar modalidades (Total contém as demais; teletrabalho está contido em trabalho remoto; 59806 e 59807 se sobrepõem). Domínio: real não negativo. Linhagem: variável 4090.';
COMMENT ON COLUMN gold.fato_teletrabalho_uf.cv_pessoas IS 'Coeficiente de variação de pessoas_mil, em %. Domínio: real não negativo. Linhagem: variável 4091.';
COMMENT ON COLUMN gold.fato_teletrabalho_uf.cv_pessoas_classificacao IS 'Faixa de CV adotada no projeto sobre o cv_pessoas publicado pelo IBGE. Domínio: Exata, Ótima, Boa, Razoável, Pouco precisa, Imprecisa. Linhagem: silver.ibge_teletrabalho_uf.cv_pessoas_classificacao.';
COMMENT ON COLUMN gold.fato_teletrabalho_uf.percentual IS 'Medida não aditiva: percentual publicado. Domínio: 0 a 100. Linhagem: variável 12965.';
COMMENT ON COLUMN gold.fato_teletrabalho_uf.cv_percentual IS 'Coeficiente de variação do percentual, em %. Domínio: real não negativo. Linhagem: variável 12966.';
COMMENT ON COLUMN gold.fato_teletrabalho_uf.cv_classificacao IS 'Faixa de CV adotada no projeto sobre o cv_percentual publicado pelo IBGE. Domínio: Exata, Ótima, Boa, Razoável, Pouco precisa, Imprecisa. Linhagem: silver.ibge_teletrabalho_uf.cv_classificacao.';
COMMENT ON COLUMN gold.fato_teletrabalho_uf.estimativa_confiavel IS 'CV publicado pelo IBGE; o limiar de 15% é critério do projeto. Domínio: true, false, nulo. Linhagem: silver.ibge_teletrabalho_uf.estimativa_confiavel.';
COMMENT ON COLUMN gold.fato_teletrabalho_uf.pessoas_mil_sinal IS 'Sinal convencional do IBGE na célula (Normas de apresentação tabular). Domínio: nulo quando a célula traz número; - (zero não resultante de arredondamento, valor 0); .. (não se aplica); ... (não disponível); x (omitido por sigilo); nos três últimos o valor é nulo. Linhagem: silver.ibge_teletrabalho_uf.pessoas_mil_sinal.';
COMMENT ON COLUMN gold.fato_teletrabalho_uf.cv_pessoas_sinal IS 'Sinal convencional do IBGE na célula (Normas de apresentação tabular). Domínio: nulo quando a célula traz número; - (zero não resultante de arredondamento, valor 0); .. (não se aplica); ... (não disponível); x (omitido por sigilo); nos três últimos o valor é nulo. Linhagem: silver.ibge_teletrabalho_uf.cv_pessoas_sinal.';
COMMENT ON COLUMN gold.fato_teletrabalho_uf.percentual_sinal IS 'Sinal convencional do IBGE na célula (Normas de apresentação tabular). Domínio: nulo quando a célula traz número; - (zero não resultante de arredondamento, valor 0); .. (não se aplica); ... (não disponível); x (omitido por sigilo); nos três últimos o valor é nulo. Linhagem: silver.ibge_teletrabalho_uf.percentual_sinal.';
COMMENT ON COLUMN gold.fato_teletrabalho_uf.cv_percentual_sinal IS 'Sinal convencional do IBGE na célula (Normas de apresentação tabular). Domínio: nulo quando a célula traz número; - (zero não resultante de arredondamento, valor 0); .. (não se aplica); ... (não disponível); x (omitido por sigilo); nos três últimos o valor é nulo. Linhagem: silver.ibge_teletrabalho_uf.cv_percentual_sinal.';
COMMENT ON COLUMN gold.fato_teletrabalho_uf.disponivel_no_nivel IS 'Indica se o IBGE declara a categoria disponível no nível territorial da linha. Domínio: false para 59807 e 59808 por UF, true nas demais. Linhagem: silver.ibge_teletrabalho_uf.disponivel_no_nivel (verificação C28).';

COMMENT ON TABLE gold.fato_ocupacao_uf_atividade IS 'Grão: UF × trimestre × grupamento de atividade econômica. Estimativa de pessoas ocupadas da PNAD Contínua. Origem: silver.ibge_ocupados_uf_atividade.';
COMMENT ON COLUMN gold.fato_ocupacao_uf_atividade.periodo_chave IS 'FK para dim_periodo (tipo trimestre). Domínio: chaves de dim_periodo; -1 se a busca na dimensão falhar. Linhagem: ano e trimestre.';
COMMENT ON COLUMN gold.fato_ocupacao_uf_atividade.geo_chave IS 'FK para dim_geografia (nivel uf). Domínio: chaves de dim_geografia; -1 se a busca na dimensão falhar. Linhagem: uf_codigo.';
COMMENT ON COLUMN gold.fato_ocupacao_uf_atividade.atividade_chave IS 'FK para dim_atividade_economica. Domínio: chaves da dimensão; -1 se a busca na dimensão falhar. Linhagem: atividade_codigo.';
COMMENT ON COLUMN gold.fato_ocupacao_uf_atividade.pessoas_mil IS 'Medida semiaditiva: pessoas ocupadas em mil. Soma entre UFs no mesmo trimestre e grupamento; não somar grupamentos (o grupamento 47946 Total contém os demais) nem trimestres. Domínio: real não negativo; nulo quando pessoas_mil_sinal é .., ... ou x. Linhagem: variável 4090 da tabela 5434.';
COMMENT ON COLUMN gold.fato_ocupacao_uf_atividade.pessoas_mil_sinal IS 'Sinal convencional do IBGE na célula (Normas de apresentação tabular). Domínio: nulo quando a célula traz número; - (zero não resultante de arredondamento, valor 0); .. (não se aplica); ... (não disponível); x (omitido por sigilo); nos três últimos o valor é nulo. Linhagem: silver.ibge_ocupados_uf_atividade.pessoas_mil_sinal.';

COMMENT ON TABLE gold.verificacoes_qualidade IS 'Resultado persistido das verificações de qualidade, uma linha por verificação. Escrita pelos notebooks 05 (camadas bronze e silver) e 07 (camada gold, C15) com MERGE por verificacao_id.';
COMMENT ON COLUMN gold.verificacoes_qualidade.verificacao_id IS 'Identificador da verificação. Domínio: C01 a C30 (C15 gravado como C15.1 a C15.3, um por tabela fato). Linhagem: primeiro argumento de registrar() no notebook 05; C15.1 a C15.3 no notebook 07.';
COMMENT ON COLUMN gold.verificacoes_qualidade.camada IS 'Camada em que a medição foi feita. Domínio: bronze, silver, gold. Linhagem: segundo argumento de registrar() no notebook 05; gold no MERGE do notebook 07.';
COMMENT ON COLUMN gold.verificacoes_qualidade.tabela IS 'Tabela ou tabelas medidas. Domínio: nomes schema.tabela. Linhagem: argumento tabela de registrar() no notebook 05 e coluna tabela de _contagens_fatos no 07.';
COMMENT ON COLUMN gold.verificacoes_qualidade.atributo IS 'Campo ou aspecto medido, com o nome da fonte quando existe. Domínio: texto livre. Linhagem: argumento atributo de registrar() no notebook 05; texto fixo no 07.';
COMMENT ON COLUMN gold.verificacoes_qualidade.dimensao_qualidade IS 'Dimensão de qualidade da verificação. Domínio: Completude, Consistência, Unicidade, Acurácia, Integridade, Validade, Outliers, Estrutural, Tempestividade. Linhagem: argumento dimensao_qualidade de registrar() no notebook 05; Integridade no 07.';
COMMENT ON COLUMN gold.verificacoes_qualidade.dimensao_dama IS 'Dimensão entre as seis primárias da DAMA UK que de fato se aplica (formulação de Black e Van Nederpelt, 2020). Domínio: Completude, Unicidade, Tempestividade, Validade, Acurácia, Consistência, ou Não se aplica com o motivo (limite amostral, precisão amostral). Linhagem: argumento dimensao_dama de registrar() no notebook 05; Completude no 07.';
COMMENT ON COLUMN gold.verificacoes_qualidade.resultado IS 'Resultado da verificação. Domínio: aprovado, reprovado, conferir, explicado, medido, registrado. Linhagem: comparação entre medido e esperado no notebook 05; regra de _contagens_fatos no 07.';
COMMENT ON COLUMN gold.verificacoes_qualidade.valor_medido IS 'Valor medido e valor esperado declarado. Domínio: texto no formato medido: ... | esperado: .... Linhagem: argumentos medido e esperado de registrar() no notebook 05; CONCAT das contagens no 07.';
COMMENT ON COLUMN gold.verificacoes_qualidade.linhas_afetadas IS 'Quantidade de linhas envolvidas no achado. Domínio: inteiro não negativo ou nulo quando não se aplica. Linhagem: argumento linhas_afetadas de registrar() no notebook 05; diferença de contagens no 07.';
COMMENT ON COLUMN gold.verificacoes_qualidade.classificacao IS 'Natureza do achado. Domínio: problema_real (característica da fonte que muda a análise), guarda_defensiva (proteção contra erro de código ou mudança da fonte). Linhagem: argumento classificacao de registrar() no notebook 05; guarda_defensiva no 07.';
COMMENT ON COLUMN gold.verificacoes_qualidade.tipo_regra IS 'Tipo da verificação. Domínio: regra (vale para qualquer carga), referencia_externa (compara com número publicado pela fonte), retrato_da_extracao (compara com o que foi medido nos arquivos de 13/09/2026 e funciona como teste de regressão). Linhagem: dicionário TIPO_REGRA do notebook 05; C15 é regra.';
COMMENT ON COLUMN gold.verificacoes_qualidade.severidade IS 'Impacto potencial na análise. Domínio: alta, média, baixa. Linhagem: argumento severidade de registrar() no notebook 05; alta no 07.';
COMMENT ON COLUMN gold.verificacoes_qualidade.tratamento IS 'O que o pipeline faz com o achado. Domínio: texto livre. Linhagem: argumento tratamento de registrar() no notebook 05; texto fixo no 07.';
COMMENT ON COLUMN gold.verificacoes_qualidade.executado_em IS 'Momento da execução da verificação. Domínio: data e hora UTC. Linhagem: relógio do notebook no momento da execução.';

COMMENT ON TABLE gold.verificacoes_qualidade_historico IS 'Resultados produzidos por etapa e execução. Os notebooks 05 e 07 gravam por MERGE antes de interromper por reprovação, com chave (job_run_id, verificacao_id). Uma repetição atualiza a tentativa mais recente; etapas não executadas não são copiadas. O histórico pode ser parcial; o estado completo consta no Databricks Jobs.';
COMMENT ON COLUMN gold.verificacoes_qualidade_historico.job_run_id IS 'Identificador da execução que produziu o resultado. Domínio: número do run do Databricks ou manual-UUID em execução interativa. Linhagem: parâmetro job_run_id do job, preenchido com {{job.run_id}}, ou UUID gerado por persistir_historico.';
COMMENT ON COLUMN gold.verificacoes_qualidade_historico.verificacao_id IS 'Identificador da verificação. Domínio: C01 a C30 (C15 como C15.1 a C15.3). Linhagem: campo verificacao_id dos resultados produzidos no notebook 05 ou 07, recebido por persistir_historico.';
COMMENT ON COLUMN gold.verificacoes_qualidade_historico.camada IS 'Camada medida. Domínio: bronze, silver, gold. Linhagem: campo camada dos resultados produzidos no notebook 05 ou 07, recebido por persistir_historico.';
COMMENT ON COLUMN gold.verificacoes_qualidade_historico.tabela IS 'Tabela ou tabelas medidas. Domínio: nomes schema.tabela. Linhagem: campo tabela dos resultados produzidos no notebook 05 ou 07, recebido por persistir_historico.';
COMMENT ON COLUMN gold.verificacoes_qualidade_historico.atributo IS 'Campo ou aspecto medido. Domínio: texto livre. Linhagem: campo atributo dos resultados produzidos no notebook 05 ou 07, recebido por persistir_historico.';
COMMENT ON COLUMN gold.verificacoes_qualidade_historico.dimensao_qualidade IS 'Dimensão de qualidade da verificação. Domínio: Completude, Consistência, Unicidade, Acurácia, Integridade, Validade, Outliers, Estrutural, Tempestividade. Linhagem: campo dimensao_qualidade dos resultados produzidos no notebook 05 ou 07, recebido por persistir_historico.';
COMMENT ON COLUMN gold.verificacoes_qualidade_historico.dimensao_dama IS 'Dimensão da DAMA que de fato se aplica. Domínio: seis dimensões da DAMA ou Não se aplica com o motivo. Linhagem: campo dimensao_dama dos resultados produzidos no notebook 05 ou 07, recebido por persistir_historico.';
COMMENT ON COLUMN gold.verificacoes_qualidade_historico.resultado IS 'Resultado na execução. Domínio: aprovado, reprovado, conferir, explicado, medido, registrado. Linhagem: campo resultado dos resultados produzidos no notebook 05 ou 07, recebido por persistir_historico.';
COMMENT ON COLUMN gold.verificacoes_qualidade_historico.valor_medido IS 'Valor medido e esperado na execução. Domínio: texto no formato medido | esperado. Linhagem: campo valor_medido dos resultados produzidos no notebook 05 ou 07, recebido por persistir_historico.';
COMMENT ON COLUMN gold.verificacoes_qualidade_historico.linhas_afetadas IS 'Linhas envolvidas no achado. Domínio: inteiro não negativo ou nulo. Linhagem: campo linhas_afetadas dos resultados produzidos no notebook 05 ou 07, recebido por persistir_historico.';
COMMENT ON COLUMN gold.verificacoes_qualidade_historico.classificacao IS 'Natureza do achado. Domínio: problema_real, guarda_defensiva. Linhagem: campo classificacao dos resultados produzidos no notebook 05 ou 07, recebido por persistir_historico.';
COMMENT ON COLUMN gold.verificacoes_qualidade_historico.tipo_regra IS 'Tipo da verificação. Domínio: regra, referencia_externa, retrato_da_extracao. Linhagem: campo tipo_regra dos resultados produzidos no notebook 05 ou 07, recebido por persistir_historico.';
COMMENT ON COLUMN gold.verificacoes_qualidade_historico.severidade IS 'Impacto potencial. Domínio: alta, média, baixa. Linhagem: campo severidade dos resultados produzidos no notebook 05 ou 07, recebido por persistir_historico.';
COMMENT ON COLUMN gold.verificacoes_qualidade_historico.tratamento IS 'O que o pipeline faz com o achado. Domínio: texto livre. Linhagem: campo tratamento dos resultados produzidos no notebook 05 ou 07, recebido por persistir_historico.';
COMMENT ON COLUMN gold.verificacoes_qualidade_historico.executado_em IS 'Momento em que a verificação rodou. Domínio: data e hora UTC. Linhagem: campo executado_em dos resultados produzidos no notebook 05 ou 07, recebido por persistir_historico.';

COMMENT ON TABLE gold.qualidade_por_atributo IS 'Qualidade de cada coluna da Bronze e da Silver nas cinco dimensões de qualidade: completude, unicidade, consistência, acurácia e outliers. Uma linha por coluna. Escrita pelo notebook 05b.';
COMMENT ON COLUMN gold.qualidade_por_atributo.tabela IS 'Tabela medida. Domínio: tabelas bronze.* e silver.*. Linhagem: perfil da captura e lista REGRAS do notebook 05b.';
COMMENT ON COLUMN gold.qualidade_por_atributo.coluna IS 'Coluna medida. Domínio: nomes de coluna da tabela. Linhagem: schema da tabela medida.';
COMMENT ON COLUMN gold.qualidade_por_atributo.posicao IS 'Posição da coluna na tabela, a partir de 1. Domínio: inteiro positivo. Linhagem: ordem do schema da tabela medida.';
COMMENT ON COLUMN gold.qualidade_por_atributo.tipo IS 'Tipo da coluna. Domínio: tipos do Spark (string, int, bigint, double, boolean, timestamp). Linhagem: dtypes da tabela medida.';
COMMENT ON COLUMN gold.qualidade_por_atributo.linhas IS 'Linhas da tabela. Domínio: inteiro não negativo. Linhagem: contagem da tabela medida.';
COMMENT ON COLUMN gold.qualidade_por_atributo.nulos IS 'Valores ausentes; na Bronze inclui NA e vazio. Domínio: 0 até linhas. Linhagem: perfil da captura ou soma de coluna IS NULL na Silver.';
COMMENT ON COLUMN gold.qualidade_por_atributo.completude_pct IS 'Completude: parcela de valores preenchidos, em %. Domínio: 0 a 100. Linhagem: (linhas − nulos) / linhas × 100.';
COMMENT ON COLUMN gold.qualidade_por_atributo.unicidade IS 'Unicidade: combinações repetidas da chave, nas colunas da chave; nas demais, registra a ausência de requisito e, na Silver, a contagem de valores distintos. Domínio: texto. Linhagem: ResponseId repetido por safra em perfil_captura.py para a Bronze; GROUP BY da chave e COUNT(DISTINCT coluna) na Silver.';
COMMENT ON COLUMN gold.qualidade_por_atributo.regra_consistencia IS 'Regra de domínio da coluna, em português. Domínio: texto; texto livre quando a coluna não tem regra fechada. Linhagem: DOMINIOS e validações de perfil_captura.py na Bronze; lista REGRAS do notebook 05b na Silver.';
COMMENT ON COLUMN gold.qualidade_por_atributo.fora_da_regra IS 'Valores preenchidos que violam a regra. Domínio: inteiro não negativo; nulo quando não há regra. Linhagem: contadores de formato e plausibilidade de perfil_captura.py na Bronze; soma de NOT regra nas linhas preenchidas da Silver.';
COMMENT ON COLUMN gold.qualidade_por_atributo.consistencia_pct IS 'Consistência: parcela dos valores preenchidos dentro da regra, em %. Domínio: 0 a 100; nulo sem regra. Linhagem: (preenchidos − fora_da_regra) / preenchidos × 100.';
COMMENT ON COLUMN gold.qualidade_por_atributo.acuracia IS 'Acurácia: verificação que compara a coluna com referência externa e o resultado dela, ou o motivo de não ser mensurável. Domínio: texto. Linhagem: justificativas do perfil de captura produzido no 01 e complementado no 05b; listas ACURACIA e SEM_REFERENCIA do 05b e resultado das verificações na Silver.';
COMMENT ON COLUMN gold.qualidade_por_atributo.outliers_iqr IS 'Outliers: valores fora de Q1 − 1,5 × IQR e Q3 + 1,5 × IQR. Domínio: inteiro não negativo; nulo sem regra de extremos definida. Linhagem: quantis interpolados na captura; percentile_approx na Silver.';
COMMENT ON COLUMN gold.qualidade_por_atributo.limite_inf_iqr IS 'Limite inferior da regra do IQR. Domínio: real; nulo sem regra de extremos definida. Linhagem: Q1 − 1,5 × (Q3 − Q1).';
COMMENT ON COLUMN gold.qualidade_por_atributo.limite_sup_iqr IS 'Limite superior da regra do IQR. Domínio: real; nulo sem regra de extremos definida. Linhagem: Q3 + 1,5 × (Q3 − Q1).';
COMMENT ON COLUMN gold.qualidade_por_atributo.executado_em IS 'Momento do cálculo. Domínio: data e hora UTC. Linhagem: relógio do notebook 05b.';

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Tags de governança
-- MAGIC
-- MAGIC Cada tabela e cada view recebe seis tags, visíveis e pesquisáveis no Catalog Explorer:
-- MAGIC
-- MAGIC - `camada`: bronze, silver ou gold;
-- MAGIC - `fonte`: de onde vem o dado;
-- MAGIC - `dado_pessoal`: `anonimizado` no microdado da pesquisa (uma linha por pessoa, sem nome nem e-mail) e `nao` no
-- MAGIC   resto. O IBGE só publica estimativas agregadas;
-- MAGIC - `licenca`: `ODbL-1.0` no que vem da Stack Overflow, inclusive o que deriva dela, `dado_publico_ibge` no IBGE e
-- MAGIC   `MIT` no que o pipeline produz sozinho;
-- MAGIC - `atualizacao`: anual (pesquisa), trimestral (5434), edição única de 2022 (9471), manual (de-para) ou a cada
-- MAGIC   execução (Gold);
-- MAGIC - `projeto`.
-- MAGIC
-- MAGIC Algumas colunas recebem a tag `sensibilidade = quase_identificador`. Sozinhas, idade, país e renda não identificam
-- MAGIC ninguém, mas juntas, numa amostra pequena como a do Brasil, podem ajudar a reconhecer alguém. Por isso, são marcados
-- MAGIC essas colunas, mesmo com a pesquisa sendo anônima.

-- COMMAND ----------

ALTER SCHEMA bronze SET TAGS ('camada' = 'bronze', 'projeto' = 'mvp-pipeline-dados');
ALTER SCHEMA silver SET TAGS ('camada' = 'silver', 'projeto' = 'mvp-pipeline-dados');
ALTER SCHEMA gold SET TAGS ('camada' = 'gold', 'projeto' = 'mvp-pipeline-dados');

ALTER TABLE bronze.so_pesquisa_2022 SET TAGS ('camada' = 'bronze', 'fonte' = 'stack_overflow', 'dado_pessoal' = 'anonimizado', 'licenca' = 'ODbL-1.0', 'atualizacao' = 'anual', 'projeto' = 'mvp-pipeline-dados');
ALTER TABLE bronze.so_pesquisa_2023 SET TAGS ('camada' = 'bronze', 'fonte' = 'stack_overflow', 'dado_pessoal' = 'anonimizado', 'licenca' = 'ODbL-1.0', 'atualizacao' = 'anual', 'projeto' = 'mvp-pipeline-dados');
ALTER TABLE bronze.so_pesquisa_2024 SET TAGS ('camada' = 'bronze', 'fonte' = 'stack_overflow', 'dado_pessoal' = 'anonimizado', 'licenca' = 'ODbL-1.0', 'atualizacao' = 'anual', 'projeto' = 'mvp-pipeline-dados');
ALTER TABLE bronze.so_pesquisa_2025 SET TAGS ('camada' = 'bronze', 'fonte' = 'stack_overflow', 'dado_pessoal' = 'anonimizado', 'licenca' = 'ODbL-1.0', 'atualizacao' = 'anual', 'projeto' = 'mvp-pipeline-dados');
ALTER TABLE bronze.so_esquema SET TAGS ('camada' = 'bronze', 'fonte' = 'stack_overflow', 'dado_pessoal' = 'nao', 'licenca' = 'ODbL-1.0', 'atualizacao' = 'anual', 'projeto' = 'mvp-pipeline-dados');
ALTER TABLE bronze.ibge_sidra_9471 SET TAGS ('camada' = 'bronze', 'fonte' = 'ibge_sidra', 'dado_pessoal' = 'nao', 'licenca' = 'dado_publico_ibge', 'atualizacao' = 'edicao_unica_2022', 'projeto' = 'mvp-pipeline-dados');
ALTER TABLE bronze.ibge_sidra_5434 SET TAGS ('camada' = 'bronze', 'fonte' = 'ibge_sidra', 'dado_pessoal' = 'nao', 'licenca' = 'dado_publico_ibge', 'atualizacao' = 'trimestral', 'projeto' = 'mvp-pipeline-dados');
ALTER TABLE silver.so_respondente SET TAGS ('camada' = 'silver', 'fonte' = 'stack_overflow', 'dado_pessoal' = 'anonimizado', 'licenca' = 'ODbL-1.0', 'atualizacao' = 'anual', 'projeto' = 'mvp-pipeline-dados');
ALTER TABLE silver.so_de_para_arranjo SET TAGS ('camada' = 'silver', 'fonte' = 'referencia_do_projeto', 'dado_pessoal' = 'nao', 'licenca' = 'MIT', 'atualizacao' = 'manual', 'projeto' = 'mvp-pipeline-dados');
ALTER TABLE silver.so_metadados_pergunta SET TAGS ('camada' = 'silver', 'fonte' = 'stack_overflow', 'dado_pessoal' = 'nao', 'licenca' = 'ODbL-1.0', 'atualizacao' = 'anual', 'projeto' = 'mvp-pipeline-dados');
ALTER TABLE silver.ibge_teletrabalho_uf SET TAGS ('camada' = 'silver', 'fonte' = 'ibge_sidra', 'dado_pessoal' = 'nao', 'licenca' = 'dado_publico_ibge', 'atualizacao' = 'edicao_unica_2022', 'projeto' = 'mvp-pipeline-dados');
ALTER TABLE silver.ibge_ocupados_uf_atividade SET TAGS ('camada' = 'silver', 'fonte' = 'ibge_sidra', 'dado_pessoal' = 'nao', 'licenca' = 'dado_publico_ibge', 'atualizacao' = 'trimestral', 'projeto' = 'mvp-pipeline-dados');
ALTER TABLE gold.dim_periodo SET TAGS ('camada' = 'gold', 'fonte' = 'stack_overflow_e_ibge', 'dado_pessoal' = 'nao', 'licenca' = 'ODbL-1.0', 'atualizacao' = 'a_cada_execucao', 'projeto' = 'mvp-pipeline-dados');
ALTER TABLE gold.dim_geografia SET TAGS ('camada' = 'gold', 'fonte' = 'stack_overflow_e_ibge', 'dado_pessoal' = 'nao', 'licenca' = 'ODbL-1.0', 'atualizacao' = 'a_cada_execucao', 'projeto' = 'mvp-pipeline-dados');
ALTER TABLE gold.dim_arranjo_trabalho SET TAGS ('camada' = 'gold', 'fonte' = 'stack_overflow', 'dado_pessoal' = 'nao', 'licenca' = 'ODbL-1.0', 'atualizacao' = 'a_cada_execucao', 'projeto' = 'mvp-pipeline-dados');
ALTER TABLE gold.dim_porte_empresa SET TAGS ('camada' = 'gold', 'fonte' = 'stack_overflow', 'dado_pessoal' = 'nao', 'licenca' = 'ODbL-1.0', 'atualizacao' = 'a_cada_execucao', 'projeto' = 'mvp-pipeline-dados');
ALTER TABLE gold.dim_perfil_dev SET TAGS ('camada' = 'gold', 'fonte' = 'stack_overflow', 'dado_pessoal' = 'nao', 'licenca' = 'ODbL-1.0', 'atualizacao' = 'a_cada_execucao', 'projeto' = 'mvp-pipeline-dados');
ALTER TABLE gold.dim_modalidade_ibge SET TAGS ('camada' = 'gold', 'fonte' = 'ibge_sidra', 'dado_pessoal' = 'nao', 'licenca' = 'dado_publico_ibge', 'atualizacao' = 'a_cada_execucao', 'projeto' = 'mvp-pipeline-dados');
ALTER TABLE gold.dim_atividade_economica SET TAGS ('camada' = 'gold', 'fonte' = 'ibge_sidra', 'dado_pessoal' = 'nao', 'licenca' = 'dado_publico_ibge', 'atualizacao' = 'a_cada_execucao', 'projeto' = 'mvp-pipeline-dados');
ALTER TABLE gold.fato_resposta_pesquisa SET TAGS ('camada' = 'gold', 'fonte' = 'stack_overflow', 'dado_pessoal' = 'anonimizado', 'licenca' = 'ODbL-1.0', 'atualizacao' = 'a_cada_execucao', 'projeto' = 'mvp-pipeline-dados');
ALTER TABLE gold.fato_teletrabalho_uf SET TAGS ('camada' = 'gold', 'fonte' = 'ibge_sidra', 'dado_pessoal' = 'nao', 'licenca' = 'dado_publico_ibge', 'atualizacao' = 'a_cada_execucao', 'projeto' = 'mvp-pipeline-dados');
ALTER TABLE gold.fato_ocupacao_uf_atividade SET TAGS ('camada' = 'gold', 'fonte' = 'ibge_sidra', 'dado_pessoal' = 'nao', 'licenca' = 'dado_publico_ibge', 'atualizacao' = 'a_cada_execucao', 'projeto' = 'mvp-pipeline-dados');
ALTER TABLE gold.verificacoes_qualidade SET TAGS ('camada' = 'gold', 'fonte' = 'pipeline', 'dado_pessoal' = 'nao', 'licenca' = 'MIT', 'atualizacao' = 'a_cada_execucao', 'projeto' = 'mvp-pipeline-dados');
ALTER TABLE gold.verificacoes_qualidade_historico SET TAGS ('camada' = 'gold', 'fonte' = 'pipeline', 'dado_pessoal' = 'nao', 'licenca' = 'MIT', 'atualizacao' = 'a_cada_execucao', 'projeto' = 'mvp-pipeline-dados');
ALTER TABLE gold.qualidade_por_atributo SET TAGS ('camada' = 'gold', 'fonte' = 'pipeline', 'dado_pessoal' = 'nao', 'licenca' = 'MIT', 'atualizacao' = 'a_cada_execucao', 'projeto' = 'mvp-pipeline-dados');
ALTER TABLE gold.analise_q1d_modelo_logistico SET TAGS ('camada' = 'gold', 'fonte' = 'stack_overflow', 'dado_pessoal' = 'nao', 'licenca' = 'ODbL-1.0', 'atualizacao' = 'a_cada_execucao', 'projeto' = 'mvp-pipeline-dados');

ALTER VIEW gold.vw_q1_evolucao_arranjo SET TAGS ('camada' = 'gold', 'fonte' = 'stack_overflow', 'dado_pessoal' = 'nao', 'licenca' = 'ODbL-1.0', 'atualizacao' = 'a_cada_execucao', 'projeto' = 'mvp-pipeline-dados');
ALTER VIEW gold.vw_q1_remoto_por_vinculo SET TAGS ('camada' = 'gold', 'fonte' = 'stack_overflow', 'dado_pessoal' = 'nao', 'licenca' = 'ODbL-1.0', 'atualizacao' = 'a_cada_execucao', 'projeto' = 'mvp-pipeline-dados');
ALTER VIEW gold.vw_q2_arranjo_por_porte SET TAGS ('camada' = 'gold', 'fonte' = 'stack_overflow', 'dado_pessoal' = 'nao', 'licenca' = 'ODbL-1.0', 'atualizacao' = 'a_cada_execucao', 'projeto' = 'mvp-pipeline-dados');
ALTER VIEW gold.vw_q3_brasil_x_resto_mundo SET TAGS ('camada' = 'gold', 'fonte' = 'stack_overflow', 'dado_pessoal' = 'nao', 'licenca' = 'ODbL-1.0', 'atualizacao' = 'a_cada_execucao', 'projeto' = 'mvp-pipeline-dados');
ALTER VIEW gold.vw_q4_perfil_remoto SET TAGS ('camada' = 'gold', 'fonte' = 'stack_overflow', 'dado_pessoal' = 'nao', 'licenca' = 'ODbL-1.0', 'atualizacao' = 'a_cada_execucao', 'projeto' = 'mvp-pipeline-dados');
ALTER VIEW gold.vw_q5_arranjo_satisfacao SET TAGS ('camada' = 'gold', 'fonte' = 'stack_overflow', 'dado_pessoal' = 'nao', 'licenca' = 'ODbL-1.0', 'atualizacao' = 'a_cada_execucao', 'projeto' = 'mvp-pipeline-dados');
ALTER VIEW gold.vw_q6_teletrabalho_uf SET TAGS ('camada' = 'gold', 'fonte' = 'ibge_sidra', 'dado_pessoal' = 'nao', 'licenca' = 'dado_publico_ibge', 'atualizacao' = 'a_cada_execucao', 'projeto' = 'mvp-pipeline-dados');
ALTER VIEW gold.vw_q7_ocupacao_proxy_tecnologia_uf SET TAGS ('camada' = 'gold', 'fonte' = 'ibge_sidra', 'dado_pessoal' = 'nao', 'licenca' = 'dado_publico_ibge', 'atualizacao' = 'a_cada_execucao', 'projeto' = 'mvp-pipeline-dados');
ALTER VIEW gold.vw_q8_mercado_brasil SET TAGS ('camada' = 'gold', 'fonte' = 'stack_overflow_e_ibge', 'dado_pessoal' = 'nao', 'licenca' = 'ODbL-1.0', 'atualizacao' = 'a_cada_execucao', 'projeto' = 'mvp-pipeline-dados');

-- COMMAND ----------

ALTER TABLE bronze.so_pesquisa_2022 ALTER COLUMN Age SET TAGS ('sensibilidade' = 'quase_identificador');
ALTER TABLE bronze.so_pesquisa_2022 ALTER COLUMN Country SET TAGS ('sensibilidade' = 'quase_identificador');
ALTER TABLE bronze.so_pesquisa_2022 ALTER COLUMN CompTotal SET TAGS ('sensibilidade' = 'quase_identificador');
ALTER TABLE bronze.so_pesquisa_2022 ALTER COLUMN ConvertedCompYearly SET TAGS ('sensibilidade' = 'quase_identificador');
ALTER TABLE bronze.so_pesquisa_2023 ALTER COLUMN Age SET TAGS ('sensibilidade' = 'quase_identificador');
ALTER TABLE bronze.so_pesquisa_2023 ALTER COLUMN Country SET TAGS ('sensibilidade' = 'quase_identificador');
ALTER TABLE bronze.so_pesquisa_2023 ALTER COLUMN CompTotal SET TAGS ('sensibilidade' = 'quase_identificador');
ALTER TABLE bronze.so_pesquisa_2023 ALTER COLUMN ConvertedCompYearly SET TAGS ('sensibilidade' = 'quase_identificador');
ALTER TABLE bronze.so_pesquisa_2024 ALTER COLUMN Age SET TAGS ('sensibilidade' = 'quase_identificador');
ALTER TABLE bronze.so_pesquisa_2024 ALTER COLUMN Country SET TAGS ('sensibilidade' = 'quase_identificador');
ALTER TABLE bronze.so_pesquisa_2024 ALTER COLUMN CompTotal SET TAGS ('sensibilidade' = 'quase_identificador');
ALTER TABLE bronze.so_pesquisa_2024 ALTER COLUMN ConvertedCompYearly SET TAGS ('sensibilidade' = 'quase_identificador');
ALTER TABLE bronze.so_pesquisa_2025 ALTER COLUMN Age SET TAGS ('sensibilidade' = 'quase_identificador');
ALTER TABLE bronze.so_pesquisa_2025 ALTER COLUMN Country SET TAGS ('sensibilidade' = 'quase_identificador');
ALTER TABLE bronze.so_pesquisa_2025 ALTER COLUMN CompTotal SET TAGS ('sensibilidade' = 'quase_identificador');
ALTER TABLE bronze.so_pesquisa_2025 ALTER COLUMN ConvertedCompYearly SET TAGS ('sensibilidade' = 'quase_identificador');
ALTER TABLE silver.so_respondente ALTER COLUMN pais SET TAGS ('sensibilidade' = 'quase_identificador');
ALTER TABLE silver.so_respondente ALTER COLUMN remuneracao_usd SET TAGS ('sensibilidade' = 'quase_identificador');
ALTER TABLE silver.so_respondente ALTER COLUMN anos_codando SET TAGS ('sensibilidade' = 'quase_identificador');
ALTER TABLE gold.fato_resposta_pesquisa ALTER COLUMN remuneracao_usd SET TAGS ('sensibilidade' = 'quase_identificador');
ALTER TABLE gold.fato_resposta_pesquisa ALTER COLUMN anos_codando SET TAGS ('sensibilidade' = 'quase_identificador');

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Verificação: nenhuma coluna sem comentário, da Bronze à Gold
-- MAGIC
-- MAGIC Os comentários das colunas da Bronze são gravados na própria carga (notebooks 01 e 02); os da Silver e da Gold,
-- MAGIC neste notebook e nas definições das views.
-- MAGIC

-- COMMAND ----------

WITH sem_comentario AS (
  SELECT c.table_schema, c.table_name, c.column_name
  FROM mafia_office.information_schema.columns c
  JOIN mafia_office.information_schema.tables t
    ON t.table_schema = c.table_schema AND t.table_name = c.table_name
  WHERE c.table_schema IN ('bronze', 'silver', 'gold')
    AND (c.comment IS NULL OR TRIM(c.comment) = '')
)
SELECT *, raise_error(CONCAT('Coluna sem comentário: ', table_schema, '.', table_name, '.', column_name)) AS falha
FROM sem_comentario;
