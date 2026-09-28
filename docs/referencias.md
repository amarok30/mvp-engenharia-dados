# Referências

Fontes citadas no README e nos documentos de `docs/`. Os notebooks citam as entradas pelo número da seção
(por exemplo, `referencias.md` §6.2), por isso a numeração não é sequencial. As entradas estão
agrupadas por assunto; [s. d.] indica que a data de publicação não foi identificada, sem usar a data de acesso como substituta.

## 1 Arquitetura medalhão

### 1.1 Documentação da Databricks

DATABRICKS. **What is the medallion lakehouse architecture?** [S. l.]: Databricks, 2026. Atualizado em: 11 set. 2026. Disponível em:
<https://docs.databricks.com/aws/en/lakehouse/medallion>. Acesso em: 27 set. 2026.

## 2 Modelagem dimensional

### 2.2 Kimball Group

KIMBALL GROUP. **Conformed dimensions.** Kimball Dimensional Modeling Techniques. [S. l.]: Kimball Group, [s. d.]. Disponível em:
<https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/conformed-dimension/>.
Acesso em: 13 set. 2026.

KIMBALL GROUP. **Nulls in fact tables.** Kimball Dimensional Modeling Techniques. [S. l.]: Kimball Group, [s. d.]. Disponível em:
<https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/fact-table-null/>.
Acesso em: 13 set. 2026.

KIMBALL GROUP. **Kimball Dimensional Modeling Techniques.** [S. l.]: Kimball Group, 2013. Disponível em:
<https://www.kimballgroup.com/wp-content/uploads/2013/08/2013.09-Kimball-Dimensional-Modeling-Techniques11.pdf>.
Acesso em: 22 set. 2026.

Da compilação, o projeto aplica a matriz de barramento (*Enterprise Data Warehouse Bus Matrix*), as dimensões degeneradas e a tabela
ponte para dimensões multivaloradas (*Multivalued Dimensions and Bridge Tables*), que é a alternativa registrada para `DevType` em 2022.

## 3 Qualidade de dados

### 3.2 As seis dimensões primárias

DAMA UK. **The six primary dimensions for data quality assessment.** [S. l.]: DAMA UK, 2013. Disponível em:
<https://www.dama-uk.org/resources/the-six-primary-dimensions-for-data-quality-assessment>.
Referência original citada por Black e Van Nederpelt (2020); formulação consultada em §3.3.

O projeto adota as seis dimensões na formulação aberta de §3.3.

### 3.3 Formulação aberta

BLACK, Andrew; VAN NEDERPELT, Peter. **How to select the right dimensions of data quality.** v. 1.1. [S. l.]: DAMA NL
Foundation, 14 nov. 2020. Disponível em:
<https://dama-nl.org/wp-content/uploads/2020/11/How-to-Select-the-Right-Dimensions-of-Data-Quality-v1.1-d.d.-14-Nov-2020.pdf>.
Acesso em: 13 set. 2026.

Padroniza 60 dimensões de qualidade e traz as seis dimensões da DAMA UK (Tabela 4).

## 6 Plataformas e pesquisas

### 6.1 Limites do Databricks Free Edition

DATABRICKS. **Databricks Free Edition limitations.** [S. l.]: Databricks, 2026. Atualizado em: 25 set. 2026. Disponível em:
<https://docs.databricks.com/aws/en/getting-started/free-edition-limitations>. Acesso em: 27 set. 2026.

Trechos que fundamentam a configuração: "outbound internet access is restricted to a limited set of trusted domains"; "If you exceed your
quota, your workspace's compute resources will be shut down and unavailable for the rest of the day (and in extreme
cases, the rest of the month)"; "Free Edition accounts may not be used for commercial purposes".

### 6.2 Metodologia da Stack Overflow Developer Survey 2025

STACK OVERFLOW. **2025 Developer Survey: Methodology.** [S. l.]: Stack Overflow, 2025. Disponível em:
<https://survey.stackoverflow.co/2025/methodology/>. Acesso em: 13 set. 2026.

49.009 respostas qualificadas, de 177 países, com campo de 29 de maio a 23 de junho de 2025; cerca de 15.000 respostas
descartadas pelas perguntas de qualificação. Sobre o viés: "Since
respondents were recruited in this way, highly-engaged users on Stack Overflow were more likely to notice the prompts
to take the survey over the duration of the collection promotion."

### 6.3 Coeficiente de variação na PNAD Contínua

IBGE. **PNAD Contínua: notas técnicas.** Rio de Janeiro: IBGE, [s. d.]. Disponível em:
<https://biblioteca.ibge.gov.br/visualizacao/livros/liv102269_notas_tecnicas.pdf>. Acesso em: 13 set. 2026.

As notas não definem faixas nem limiares de CV. As seis faixas usadas no MVP são uma convenção do projeto.

### 6.4 Módulo de teletrabalho da PNAD Contínua

IBGE. **PNAD Contínua: teletrabalho e trabalho por meio de plataformas digitais 2022.** Rio de Janeiro: IBGE, 2023.
Disponível em:
<https://loja.ibge.gov.br/pnad-continua-teletrabalho-e-trabalho-por-meio-de-plataformas-digitais-2022.html>.
Acesso em: 13 set. 2026.

A página respondeu HTTP 403 em 13 set. 2026. O trimestre e a classificação como experimental estão confirmados em §6.8.

### 6.5 API do SIDRA

IBGE. **API SIDRA: ajuda.** Rio de Janeiro: IBGE, [s. d.]. Disponível em: <https://apisidra.ibge.gov.br/home/ajuda>. Acesso em: 13 set. 2026.

Limite de 100.000 valores por consulta, pelo produto dos elementos selecionados em cada dimensão. Padrões: `/v/allxp`,
`/p/last`, `/f/a`, `/h/y` e `/d/s`.

### 6.6 Sinais convencionais do IBGE

IBGE. **Normas de apresentação tabular.** 3. ed. Rio de Janeiro: IBGE, 1993. Disponível em:
<https://biblioteca.ibge.gov.br/visualizacao/livros/liv23907.pdf>. Acesso em: 13 set. 2026.

### 6.7 Erro de DNS na Free Edition

DATABRICKS COMMUNITY. **[Free Edition] Outbound internet suddenly blocked.** Tópico 121832. [S. l.]: Databricks Community, [s. d.]. Disponível em:
<https://community.databricks.com/t5/data-engineering/free-edition-outbound-internet-suddenly-blocked-error/td-p/121832>.
Acesso em: 13 set. 2026.

O tópico registra um relato do erro `[Errno -3] Temporary failure in name resolution`.

### 6.8 Tabelas 9471 e 5434 no SIDRA

IBGE. **Pesquisa Nacional por Amostra de Domicílios Contínua:** tabelas SIDRA 9471 e 5434. Rio de Janeiro: IBGE, [s. d.].
Disponível em: <https://apisidra.ibge.gov.br/>. Acesso em: 13 set. 2026.

IBGE. **SIDRA: descrição da tabela 9471.** Rio de Janeiro: IBGE, [s. d.]. Disponível em: <https://apisidra.ibge.gov.br/desctabapi.aspx?c=9471>.
Acesso em: 13 set. 2026.

IBGE. **SIDRA: descrição da tabela 5434.** Rio de Janeiro: IBGE, [s. d.]. Disponível em: <https://apisidra.ibge.gov.br/desctabapi.aspx?c=5434>.
Acesso em: 13 set. 2026.

As notas citadas em [`licencas-e-fontes.md`](licencas-e-fontes.md) (estatística experimental, exclusão dos afastados,
disponibilidade só para Brasil e Grande Região, nova ponderação da 5434) vêm dessas páginas.

### 6.9 Licença e distribuição da Stack Overflow Developer Survey

STACK OVERFLOW. **Stack Overflow Developer Survey.** [S. l.]: Stack Overflow, [s. d.]. Disponível em: <https://survey.stackoverflow.co/>. Acesso em:
14 set. 2026.

STACK EXCHANGE. **StackExchange/Survey: LICENSE.md.** [S. l.]: GitHub, [s. d.]. Disponível em:
<https://github.com/StackExchange/Survey/blob/main/LICENSE.md>. Acesso em: 14 set. 2026.

STACK EXCHANGE. **StackExchange/Survey: README.md.** [S. l.]: GitHub, [s. d.]. Disponível em:
<https://github.com/StackExchange/Survey/blob/main/README.md>. Acesso em: 22 set. 2026.

O `README.md` separa as licenças: "Data is published under the Open Database License (ODbL) 1.0; individual cell
contents are published under the Database Contents License (DbCL) 1.0." e "Unless otherwise stated, the contents of
this repository are licensed under the Apache License, Version 2.0."

### 6.11 Expectativas de pipelines declarativos

DATABRICKS. **Manage data quality with pipeline expectations.** [S. l.]: Databricks, 2026. Atualizado em: 11 set. 2026. Disponível em:
<https://docs.databricks.com/aws/en/ldp/expectations>. Acesso em: 27 set. 2026.

### 6.12 Restrições e diagrama de relacionamento no Unity Catalog

DATABRICKS. **Constraints on Databricks.** [S. l.]: Databricks, 2026. Atualizado em: 11 set. 2026. Disponível em:
<https://docs.databricks.com/aws/en/tables/constraints>. Acesso em: 27 set. 2026.

DATABRICKS. **View the Entity Relationship Diagram.** [S. l.]: Databricks, 2026. Atualizado em: 11 set. 2026. Disponível em:
<https://docs.databricks.com/aws/en/catalog-explorer/entity-relationship-diagram>. Acesso em: 27 set. 2026.

## 7 Método estatístico

### 7.1 Intervalo de Wilson

WILSON, Edwin B. **Probable inference, the law of succession, and statistical inference.** Journal of the American
Statistical Association, v. 22, n. 158, p. 209-212, 1927. DOI: <https://doi.org/10.1080/01621459.1927.10502953>.

### 7.2 Limites de pior caso para a não resposta

DUTZ, Deniz; HUITFELDT, Ingrid; LACOUTURE, Santiago; MOGSTAD, Magne; TORGOVITSKY, Alexander; VAN DIJK, Winnie.
**Selection in surveys.** Becker Friedman Institute Working Paper n. 2021-141, dez. 2021. Disponível em:
<https://bfi.uchicago.edu/wp-content/uploads/2021/12/BFI_WP_2021-141.pdf>. Acesso em: 22 set. 2026.

Descreve os limites de pior caso para a não resposta; em desfecho binário, os limites são zero e um.

### 7.3 Padronização direta

AHMAD, Omar B.; BOSCHI-PINTO, Cynthia; LOPEZ, Alan D.; MURRAY, Christopher J. L.; LOZANO, Rafael; INOUE, Mie.
**Age standardization of rates: a new WHO standard.** GPE Discussion Paper Series n. 31. Geneva: World Health
Organization, 2001. Disponível em:
<https://cdn.who.int/media/docs/default-source/gho-documents/global-health-estimates/gpe_discussion_paper_series_paper31_2001_age_standardization_rates.pdf>.
Acesso em: 22 set. 2026.

### 7.4 Faixas de coeficiente de variação em estatística oficial

STATISTICS CANADA. **Quality level guidelines based on the CV of a particular estimate.** Documento 5065_D3_T9_V1.
[S. l.]: Statistics Canada, [s. d.].
Disponível em: <https://www.statcan.gc.ca/en/statistical-programs/document/5065_D3_T9_V1-eng.pdf>. Acesso em: 22 set.
2026.

Três níveis: *Acceptable*, CV "in the range of 0.0% to 16.5%"; *Marginal*, CV "in the range of 16.6% to 33.3%";
*Unacceptable*, CV "in excess of 33.3%".

## 8 Contexto sobre trabalho remoto

### 8.1 Potencial de teletrabalho no Brasil

GÓES, Geraldo Sandoval; MARTINS, Felipe dos Santos; NASCIMENTO, José Antônio Sena. **O trabalho remoto potencial e
efetivo no Brasil: possíveis razões de um hiato elevado.** Texto para Discussão n. 2738. Brasília: Ipea, fev. 2022.
Disponível em: <https://repositorio.ipea.gov.br/bitstream/11058/11094/1/td_2738.pdf>. Acesso em: 22 set. 2026.

Potencial de teletrabalho de "cerca de 22,7%, o que corresponde a 20,8 milhões de pessoas", pela PNAD Contínua
anterior à pandemia.

### 8.2 Arranjo híbrido e satisfação

BLOOM, Nicholas; HAN, Ruobing; LIANG, James. **Hybrid working from home improves retention without damaging
performance.** Nature, v. 630, p. 920-925, 2024. DOI: <https://doi.org/10.1038/s41586-024-07500-2>. Acesso em: 23
set. 2026.

Do resumo: "we ran a six-month randomized control trial investigating the effects of hybrid working from home on 1,612
employees in a Chinese technology company in 2021–2022. We found that hybrid working improved job satisfaction and
reduced quit rates by one-third."

### 8.3 Teletrabalho por grupamento de atividade

AGÊNCIA BRASIL. **Pnad Contínua mostra que 9,5 milhões faziam trabalho remoto em 2022.** Brasília: Agência Brasil, 25 out. 2023. Disponível em:
<https://agenciabrasil.ebc.com.br/economia/noticia/2023-10/pnad-continua-mostra-que-95-milhoes-faziam-trabalho-remoto-em-2022>.
Acesso em: 25 set. 2026.

Pela matéria, o grupamento de informação, comunicação e atividades financeiras, imobiliárias, profissionais e
administrativas apresentou taxa de teletrabalho de 25,8% entre seus próprios ocupados. O denominador é o total
de ocupados no grupamento; esse percentual não é sua participação no teletrabalho nacional.

IBGE. **PNAD Contínua: teletrabalho e trabalho por meio de plataformas digitais 2022**. Apresentação dos resultados.
Rio de Janeiro: IBGE, 2023. Disponível em:
<https://agenciadenoticias.ibge.gov.br/media/com_mediaibge/arquivos/448a4b1b10d3cba64647966eb2772316.pdf>.
Acesso em: 27 set. 2026.

A apresentação identifica a taxa de teletrabalho por grupamento de atividade e remete à tabela SIDRA 9539.
Essa referência fundamenta a interpretação do percentual setorial; a tabela 9539 não compõe a carga deste MVP.
