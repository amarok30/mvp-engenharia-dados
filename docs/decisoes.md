# Decisões de projeto

Decisões do pipeline, justificativas e alternativas consideradas.

**Quadro 1 - Decisões de arquitetura, transformação e qualidade**

| Ponto | Decisão | Por quê | Alternativa considerada |
|---|---|---|---|
| Nível territorial da tabela 9471 | Consulta com Brasil (`n1`) e UF (`n3`) na mesma chamada | A linha nacional publicada, com o próprio CV, serve de validação externa e de base da Q6 | Somar UFs arredondadas, que perde o CV nacional |
| Precisão das estimativas da 9471 | Consulta também o CV de pessoas (4091), além do CV do percentual (12966) | Cada medida tem o próprio CV | Usar o CV do percentual também para pessoas |
| Nomes de coluna com espaço na Bronze | `delta.columnMapping.mode = 'name'` | Renomear seria corrigir na Bronze | Substituir espaço por `_` |
| Cabeçalho do SIDRA | Coluna `_ordem_registro` na Bronze do IBGE | Delta não guarda ordem de linha | Reconhecer o cabeçalho pelo conteúdo |
| `_safra` da 5434 | Nulo | A tabela cobre de 2012 a 2026 | Ano da extração |
| Ausência `NA` no CSV | Texto na Bronze, nulo na Silver | A Bronze não corrige | Tratar `NA` como categoria |
| Sinais convencionais do IBGE | `-` vira 0; `..`, `...` e `x` viram nulo com o sinal guardado em `<medida>_sinal` | Cada sinal tem significado próprio nas normas do IBGE | Tratar todos os símbolos como nulo |
| Categorias 59807 e 59808 por UF | Mantidas com `disponivel_no_nivel = false` e fora da análise por UF | O IBGE as declara só para Brasil e Grande Região, mas a API devolve valor por UF | Apagar as linhas |
| `empregado` | `Employment` com item `Employed` (2025) ou `Employed, ...` (2022 a 2024) | O rótulo mudou em 2025 | Regex só com vírgula, que zerava 2025 |
| Base das análises de arranjo | `trabalhando` = empregado ou autônomo | De 2022 a 2024 o nulo de `RemoteWork` é quase todo de quem não trabalha (C02) | Todos os respondentes |
| `DevType` | Primeiro valor | Multi-resposta só em 2022; o custo está medido no C30 | Explodir linhas, que contaria o mesmo respondente várias vezes; tabela ponte, que só 2022 usaria |
| `YearsCode` acima de 50 em 2025 | 50 | 2022 a 2024 já censuram em 50 | Anular 248 respostas |
| Porte em 2025 | Faixa `Menos de 20`, com piso nulo | 2025 funde 2 a 9 e 10 a 19 | Manter dez faixas, que deixaria 2025 sem as duas menores |
| Geografia | Nome de país em inglês e `pais_nome = 'Brazil'` nas UFs | Liga o Brasil das duas fontes sem inventar tradução | Traduzir os nomes de país |
| Sigla e região da UF | Tabela de referência pelo código IBGE | A API não devolve esses atributos | Deixar nulo |
| `safra` e `resposta_id` na tabela fato | Dimensões degeneradas | Rastreabilidade sem dimensão de mesmo grão | `dim_respondente` |
| Filtros `e_profissional`, `empregado`, `autonomo`, `trabalhando`, `remuneracao_outlier` | Atributos degenerados | Evitam `JOIN` sem ganho | Dimensão lixo |
| Chave substituta das dimensões sem ordem canônica | `xxhash64` da chave natural, levado a inteiro não negativo | A mesma chave natural gera a mesma chave em qualquer recarga, e filtros salvos no dashboard continuam valendo | `ROW_NUMBER()` (versão inicial), que muda as chaves quando entra um país novo |
| Chaves primária e estrangeira | Declaradas no Unity Catalog (informativas) | Documentam o grão e geram o diagrama de relacionamento | Deixar a relação só no texto |
| Regras de domínio da Silver | Conferidas no DataFrame antes de gravar e gravadas na tabela como `CHECK` e `NOT NULL` | Dado inválido nunca chega à tabela, nem por escrita fora do pipeline | Conferir só no notebook de qualidade |
| Regras nas tabelas fato | Os mesmos `CHECK` da Silver, também na Gold | A Gold não depende só de a Silver estar certa | Regra só na Silver |
| Recarga da Gold | O notebook 07 recria as tabelas fato com `CREATE OR REPLACE` | Guarda o histórico do Delta, o que permite provar a idempotência e voltar uma versão com `RESTORE` | `DROP` das tabelas fato (versão inicial), que zerava o histórico |
| Histórico da qualidade | Os notebooks 05 e 07 gravam os resultados produzidos pela própria etapa antes da verificação final de reprovação; `MERGE` pela chave `(job_run_id, verificacao_id)` atualiza o resultado nas repetições | Preserva resultados já produzidos sem copiar verificações de outra execução; o estado completo é consultado no Databricks Jobs | Copiar o último estado compartilhado apenas no fim do pipeline |
| Qualidade por atributo | Notebook 05b reúne 580 atributos: 520 da Bronze e 60 da Silver, com medidas e justificativas para dimensões não aplicáveis ou não verificáveis | Cobre a captura inicial e os dados tratados; complementa as verificações por problema do notebook 05 | Limitar o perfil à Silver ou manter somente as verificações C01 a C30 |

Fonte: elaborado pelo autor (2026), com base nas fontes e regras indicadas no texto.
