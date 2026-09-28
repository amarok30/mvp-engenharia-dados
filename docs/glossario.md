# Glossário

Os termos usados nas perguntas e nas tabelas, com as colunas onde cada um está.

**Quadro 1 - glossario**

| Termo | O que quer dizer aqui | Onde está |
|---|---|---|
| Safra | Edição anual da Stack Overflow Developer Survey (2022 a 2025) | `silver.so_respondente.safra`, `gold.fato_resposta_pesquisa.safra` |
| Arranjo de trabalho | Onde a pessoa diz que trabalha: Remoto, Híbrido, Presencial ou Flexível | `silver.so_respondente.arranjo_trabalho`, `gold.dim_arranjo_trabalho` |
| Remoto | Opção Remote (Fully remote em 2022) da pergunta RemoteWork. Não é o teletrabalho do IBGE | `gold.dim_arranjo_trabalho.arranjo` |
| Híbrido | Opções Hybrid da pergunta RemoteWork, juntas numa só | `docs/mapa-de-para-arranjo.csv` |
| Flexível | Opção Your choice, que só existe em 2025. Fica fora da série comparável | `gold.dim_arranjo_trabalho.entra_serie_historica` |
| Não presencial | Remoto mais Híbrido. É o recorte de arranjo investigado para o Mafia Office | `gold.vw_q4_perfil_remoto.pct_nao_presencial_comparavel` e contas sobre as views Q1 a Q3 |
| Série comparável | Remoto, Híbrido e Presencial, que existem nas quatro safras | `n_serie_comparavel` nas views Q1 a Q4 |
| Quem trabalha | Empregado ou autônomo. É a base das análises de arranjo | `silver.so_respondente.trabalhando` |
| Teletrabalho | Conceito do IBGE: trabalho remoto feito com tecnologia da informação, no 4º trimestre de 2022 | `gold.dim_modalidade_ibge`, código 59805 |
| Trabalho remoto (IBGE) | Conceito do IBGE mais amplo: trabalho fora do local habitual | `gold.dim_modalidade_ibge`, código 59804 |
| Setor proxy de tecnologia | Grupamento 56624 do IBGE: informação, comunicação e atividades financeiras, imobiliárias, profissionais e administrativas. É maior que TI | `silver.ibge_ocupados_uf_atividade.e_proxy_tecnologia` |
| CV | Coeficiente de variação que o IBGE publica para cada estimativa. Quanto menor, mais precisa | `cv_percentual`, `cv_pessoas` |
| Estimativa confiável | Estimativa do IBGE com CV até 15% | `silver.ibge_teletrabalho_uf.estimativa_confiavel` |
| Cenário de público | Resultado da transferência de taxas de teletrabalho ou trabalho remoto ao setor proxy na Q8. Depende das premissas; não mede compradores | `gold.vw_q8_mercado_brasil.estimativa_mil` |
| Membro -1 e -2 | Linhas especiais das dimensões: -1 é valor sem par na dimensão, -2 é campo em branco na fonte | `gold.dim_*` |
| Quase-identificador | Coluna que sozinha não identifica ninguém, mas junto com outras pode ajudar (idade, país, renda) | tag `sensibilidade` nas colunas |

Fonte: elaborado pelo autor (2026), com base nas fontes e regras indicadas no texto.
