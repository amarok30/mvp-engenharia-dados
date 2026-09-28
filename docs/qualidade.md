# Qualidade de dados: detalhe

Este documento traz a abordagem, as faixas de CV e a tabela das verificações. A medição coluna a coluna está em
[`qualidade-por-atributo.md`](qualidade-por-atributo.md).

## 1 Abordagem

Cada regra tem um valor esperado escrito antes de rodar. O resultado fica gravado em `gold.verificacoes_qualidade`, e
cada achado recebe uma classificação:

- `problema_real`: característica da fonte que muda a leitura dos dados e pede tratamento;
- `guarda_defensiva`: proteção contra erro de implementação ou mudança futura da fonte.

A coluna `dimensao_qualidade` usa completude, consistência, unicidade, acurácia e outliers, mais validade, integridade,
estrutural e tempestividade. A coluna `dimensao_dama` traz uma das seis dimensões primárias da DAMA UK, na formulação de
Black e Van Nederpelt (2020). As duas nem sempre coincidem. A pesquisa não tem referência externa para a remuneração,
então a verificação mede validade (valor numa faixa plausível), não acurácia. E o CV do IBGE mede precisão amostral, não
viés, por isso o C13 fica como "não se aplica".

Dois cuidados mudam a leitura:

- **Ausência estrutural e ausência real.** `JobSat` nulo em 2022 é estrutural, porque a pergunta não existia. Em 2024
  é não resposta. Com `RemoteWork`, de 2022 a 2024 o nulo é quase todo de quem não trabalha (0,0% a 0,1% de nulo entre
  quem trabalha). Em 2025, 19,8% de quem trabalha deixou o arranjo em branco. Isso é não resposta real, e o C02
  registra como `medido`.
- **Precisão das estimativas do IBGE.** O IBGE publica o CV de cada estimativa, mas não define faixas. O projeto adota seis faixas:
  Exata (0), Ótima (até 5%), Boa (mais de 5% até 15%), Razoável (mais de 15% até 30%), Pouco precisa (mais de 30% até
  50%) e Imprecisa (mais de 50%). Só CV até 15% entra nas conclusões sem ressalva. O corte de 15% é o mesmo de
  `estimativa_confiavel`. A partir de 30%, a meia-largura do intervalo de 95% passa de metade do valor. As faixas ficam
  perto das do Statistics Canada, que sinaliza CV de 16,6% a 33,3% e recomenda não divulgar acima de 33,3%
  (`referencias.md` §7.4).

## 2 Tipo de regra

A coluna `tipo_regra` separa as verificações em três grupos:

- **regra**, que vale para qualquer carga: C02 a C07, C09, C10, C13, C15, C17 a C30;
- **referencia_externa**, que compara com um número publicado pela fonte: C14 (totais do IBGE) e C16 (respostas da
  metodologia da Stack Overflow);
- **retrato_da_extracao**, que compara com os valores medidos nos arquivos de 13/09/2026: C01, C08, C11 e C12. Se a fonte
  republicar o arquivo, "reprovado" quer dizer que o arquivo mudou, não que o dado piorou.

As tabelas da Silver, as tabelas fato da Gold e a `gold.verificacoes_qualidade` têm `NOT NULL` e `CHECK` gravados no
Delta. As regras da Silver são conferidas também no DataFrame antes de gravar: se alguma linha viola, o notebook para e
a tabela fica na versão anterior.

## 3 Perfil por atributo na captura e na Silver

O notebook 05b reúne o perfil dos atributos capturados na Bronze e das 60 colunas da Silver.
A captura mantém os valores como texto e registra completude, quantidade de valores distintos, tipo semântico,
domínio observado e verificações aplicáveis. O arquivo [`dominios-captura.json`](dominios-captura.json) permite
consultar categorias e limites encontrados. Um valor observado não define, por si só, o domínio admissível de futuras cargas.

Unicidade é exigida nas chaves, não em toda coluna. Em campos livres e respostas autodeclaradas sem referência externa,
a acurácia não pode ser comprovada; o relatório explicita essa limitação. Sinais convencionais do IBGE têm significado
próprio, e a ausência de um sinal não equivale automaticamente a dado perdido. Os outliers servem ao diagnóstico:
não são removidos apenas por ficarem fora do intervalo interquartil.

## 4 As verificações

O notebook 05 produz 29 resultados e o notebook 07 produz os três desdobramentos de C15: são 32 resultados para
30 famílias de verificação. Cada etapa registra seus próprios resultados em `gold.verificacoes_qualidade_historico`
antes de interromper uma execução reprovada. A chave `(job_run_id, verificacao_id)` faz a repetição de uma etapa
atualizar o mesmo resultado, sem duplicá-lo.

O histórico contém apenas verificações efetivamente produzidas pela execução. Uma falha anterior às verificações
pode não deixar registros nessa tabela; o estado das tarefas no Databricks Jobs é a referência para saber se o job
terminou. Um histórico parcial sem reprovações não significa sucesso. Execuções manuais recebem identificadores
próprios por etapa. A exportação dos resultados está em
[`evidencias/verificacoes-qualidade.csv`](../evidencias/verificacoes-qualidade.csv).

**Quadro 1 - As verificações**

| ID | Dimensão (DAMA) | Atributo | Esperado | Classificação | Resultado |
|---|---|---|---|---|---|
| C01 | Completude (Completude) | `RemoteWork` | Nulos 19,5% (2022), 17,2% (2023), 16,2% (2024), 31,3% (2025); 221.354 informados de 277.080 | problema_real | aprovado |
| C02 | Completude (Completude) | `RemoteWork` sobre quem trabalha | Até 1% de nulo entre quem trabalha em 2022 a 2024; 2025 registrado como `medido` | problema_real | medido: 19,8% em 2025 |
| C03 | Completude (Completude) | `JobSat` | Ausente e 100% nulo em 2022 e 2023; mesmo texto de pergunta em 2024 e 2025 | problema_real | aprovado |
| C04 | Completude (Completude) | `YearsCodePro` | Ausente em 2025 | problema_real | aprovado |
| C05 | Consistência (Consistência) | `RemoteWork` | Texto da pergunta idêntico; opções mudam em 2023 e 2025 | problema_real | aprovado |
| C06 | Consistência (Consistência) | `OrgSize` | 10 categorias em 2022 a 2024; 9 em 2025 | problema_real | aprovado |
| C07 | Consistência (Consistência) | `OrgSize` (encoding) | Todo `I don’t know` com U+2019 vira `Não sabe` | problema_real | aprovado |
| C08 | Consistência (Validade) | `Currency` | 72,4% com TAB em 2024, sobre Currency preenchido; regex tolerante | problema_real | aprovado |
| C09 | Unicidade (Unicidade) | `ResponseId` | Único por safra; colide entre safras | problema_real | aprovado |
| C10 | Unicidade (Unicidade) | Registros SIDRA | Sem duplicata por combinação de dimensões | guarda_defensiva | aprovado |
| C11 | Acurácia (Validade) | `ConvertedCompYearly` 2024 | Mínimo 1, máximo 16.256.603, mediana 65.000, média 86.155 | problema_real | aprovado |
| C12 | Acurácia (não se aplica: limite amostral) | Brasil | n = 2.109 · 2.042 · 1.375 · 825; 649 com arranjo em 2025 | problema_real | aprovado |
| C13 | Acurácia (não se aplica: precisão amostral) | CV SIDRA por UF | Distribuição nas seis faixas de CV | problema_real | medido |
| C14 | Acurácia (Consistência) | Totais do Brasil | 96.695 · 9.462 · 7.399 mil | guarda_defensiva | aprovado |
| C15 | Integridade e unicidade (Completude) | Chaves das três tabelas fato | Mesma contagem da Silver; nenhuma FK nula ou em `-1`; nenhuma chave primária repetida | guarda_defensiva | aprovado (C15.1 a C15.3) |
| C16 | Integridade (Consistência) | Reconciliação 2025 | 49.191 linhas no CSV contra 49.009 respostas publicadas (diferença de 182) | problema_real | medido: diferença de 182 |
| C17 | Validade (Validade) | Domínio do arranjo | 0 fora do domínio | guarda_defensiva | aprovado |
| C18 | Validade (Validade) | Percentuais e CVs do IBGE | Percentuais entre 0 e 100; CV e pessoas não negativos | guarda_defensiva | aprovado |
| C19 | Outliers (Validade) | Remuneração | Cauda extrema à direita; corte [1.000; 1.000.000] marcado | problema_real | medido |
| C20 | Outliers (Validade) | `anos_codando` | Pontas censuradas convertidas (0 e 50) | problema_real | aprovado |
| C21 | Estrutural (Validade) | JSON SIDRA | `d[0]` é cabeçalho: preservado na Bronze, descartado na Silver | problema_real | aprovado |
| C22 | Tempestividade (Tempestividade) | Período das fontes | Teletrabalho só em 2022; pesquisa até 2025 | problema_real | registrado |
| C23 | Consistência (Consistência) | Modalidades da 9471 | 59806 + 59807 − 59808 = 59805 no Brasil (±2 mil de arredondamento); 59805 ≤ 59804 ≤ 59803 nos 28 territórios | problema_real | aprovado |
| C24 | Consistência (Consistência) | Grupamentos da 5434 | Total = soma do primeiro nível (±5,5 mil); transformação ≤ indústria geral | problema_real | aprovado |
| C25 | Consistência (Consistência) | Universo 9471 e 5434 em 2022T4 | Diferença medida e declarada | problema_real | medido: 821 mil (0,85%) |
| C26 | Completude (Completude) | Estrutura do nulo de `RemoteWork` em 2025 | Nulo em bloco e por vínculo, medido | problema_real | medido |
| C27 | Completude (Completude) | Sinal `x` (sigilo) no IBGE | Toda célula com `x` tem valor nulo | guarda_defensiva | aprovado: 0 células |
| C28 | Validade (Validade) | 59807 e 59808 por UF | Linhas fora da disponibilidade declarada pelo IBGE marcadas | problema_real | medido: 54 linhas |
| C29 | Integridade (Consistência) | Hipóteses para a diferença do C16 | Quatro hipóteses contadas no microdado de 2025 | problema_real | medido: nenhuma iguala 182 |
| C30 | Completude (Completude) | `perfil_principal` (`DevType` multi-resposta) | Multi-resposta só em 2022 | problema_real | medido: 37.261 respondentes de 2022 com mais de um valor |

Fonte: elaborado pelo autor (2026), com base nas fontes e regras indicadas no texto.

**A trava.** Depois de gravar, o notebook 05 para o pipeline se o conjunto de verificações não é o esperado, se algum
resultado sai do domínio, se alguma verificação termina `reprovado` ou se uma `guarda_defensiva` termina `conferir`. Um
`problema_real` em `medido` ou `conferir` só registra, porque é característica da fonte e não erro de código.

**Reconciliação (C16 e C29).** O microdado de 2025 tem 49.191 linhas, e a metodologia publicada registra 49.009
respostas qualificadas, sem explicar a diferença de 182. No microdado não há linha sem resposta, nem com `MainBranch`
vazio, nem `ResponseId` repetido. Há 878 linhas com até três respostas, número que não coincide com 182. O pipeline usa as
linhas do CSV e registra a diferença sem atribuir causa.
