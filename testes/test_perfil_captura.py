"""Regras do perfil da captura sobre valores que precisam permanecer na Bronze."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "notebooks"))
from perfil_captura import perfil_registros


def test_nulos_sentinelas_e_identificador_duplicado():
    linhas = [{"ResponseId": v, "JobSat": s} for v, s in [("1", "10"), ("1", "11"), ("2", "NA"), ("-3", "")]]
    p = perfil_registros(linhas, ["ResponseId", "JobSat"])
    assert p["ResponseId"]["fora_da_regra"] == 1
    assert "1 repetições" in p["ResponseId"]["unicidade"]
    assert p["JobSat"]["nulos"] == 2
    assert p["JobSat"]["fora_da_regra"] == 1
    assert p["JobSat"]["consistencia_pct"] == 50


def test_extremos_de_anos_nao_sao_erros_de_parse():
    p = perfil_registros([{"YearsCode": v} for v in ["Less than 1 year", "More than 50 years", "65", "-1"]], ["YearsCode"])
    assert p["YearsCode"]["fora_da_regra"] == 1
    assert "2025" in p["YearsCode"]["dominio"]


def test_perfil_nao_inventa_dominio_fechado_para_texto_livre():
    p = perfil_registros([{"Texto": "resposta" + str(i)} for i in range(300)], ["Texto"])["Texto"]
    assert p["lista_truncada"]
    assert p["valores_observados"] == []
    assert p["consistencia_pct"] is None
    assert "mais de 256" in p["dominio"]


def test_iqr_marca_extremo_sem_remover_valor():
    p = perfil_registros([{"ConvertedCompYearly": str(x)} for x in [10, 10, 10, 10, 1000]], ["ConvertedCompYearly"])["ConvertedCompYearly"]
    assert p["linhas"] == 5
    assert p["outliers_iqr"] == 1
    assert "1000" in p["dominio"]


def test_nao_finito_nao_e_numero_valido():
    p = perfil_registros([{"CompTotal": x} for x in ["inf", "NaN", "100"]], ["CompTotal"])["CompTotal"]
    assert p["fora_da_regra"] == 2
    assert p["consistencia_pct"] == 33.33


def test_anos_fracionarios_sao_inconsistentes_com_a_silver():
    p = perfil_registros([{"YearsCode": "1.2"}, {"YearsCode": "10"}], ["YearsCode"])["YearsCode"]
    assert p["fora_da_regra"] == 1


def test_remuneracao_em_moedas_diferentes_nao_recebe_iqr_global():
    p = perfil_registros([{"CompTotal": str(x)} for x in [10, 10, 10, 10, 1000]], ["CompTotal"])["CompTotal"]
    assert p["outliers_iqr"] is None

def test_csv_preserva_campo_longo_e_restaura_limite(tmp_path):
    import csv
    from perfil_captura import perfil_csv

    limite = csv.field_size_limit()
    resposta = "á" * (limite + 1)
    caminho = tmp_path / "captura.csv"
    with caminho.open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["Texto"])
        escritor.writerow([resposta])
    perfil = perfil_csv(caminho, ["Texto"])["Texto"]
    assert perfil["linhas"] == 1
    assert perfil["valores_observados"] == [resposta]
    assert csv.field_size_limit() == limite


def test_multisselecao_preserva_opcoes_apos_saturar_combinacoes():
    from itertools import combinations

    opcoes = [f"tecnologia_{i}" for i in range(14)]
    linhas = [{"LanguageHaveWorkedWith": ";".join(v)} for v in combinations(opcoes, 4)]
    p = perfil_registros(linhas, ["LanguageHaveWorkedWith"], {"LanguageHaveWorkedWith"})["LanguageHaveWorkedWith"]
    assert p["lista_truncada"]
    assert p["valores_observados"] == []
    assert p["opcoes_observadas"] == sorted(opcoes)
    assert not p["opcoes_truncadas"]
    assert "múltipla seleção" in p["dominio"]
    assert "não definem" in p["dominio"]


def test_ponto_e_virgula_nao_transforma_texto_livre_em_multisselecao():
    p = perfil_registros([{"Texto": "comentário; outro trecho"}], ["Texto"])["Texto"]
    assert not p["multisselecao"]
    assert p["opcoes_observadas"] == []
    assert p["valores_observados"] == ["comentário; outro trecho"]


def test_opcoes_tem_limite_de_quantidade_e_tamanho():
    from perfil_captura import LIMITE_CATEGORIAS, LIMITE_TAMANHO_OPCAO

    for valores in ([str(i) for i in range(LIMITE_CATEGORIAS + 1)], ["x" * (LIMITE_TAMANHO_OPCAO + 1)]):
        p = perfil_registros([{"Campo": ";".join(valores)}], ["Campo"], {"Campo"})["Campo"]
        assert p["opcoes_truncadas"]
        assert p["opcoes_observadas"] == []
        assert "omitida" in p["dominio"]


def test_schema_distingue_familias_matrizes_e_selecao_unica(tmp_path):
    import csv
    from perfil_captura import perfil_csv

    with (tmp_path / "schema.csv").open("w", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["qname", "type", "selector"])
        escritor.writerows([
            ["Language", "Matrix", "Likert"], ["Database", "Matrix", "Likert"],
            ["Knowledge", "Matrix", "Likert"], ["Employment", "MC", "MAVR"],
            ["DevType", "MC", "SAVR"], ["EmploymentAddl", "MC", ""],
            ["LanguagesHaveEntry", "TE", ""],
        ])
    colunas = ["LanguageHaveWorkedWith", "DatabaseWantToWorkWith", "LanguageAdmired",
               "KnowledgeHaveWorkedWith", "Employment", "DevType", "EmploymentAddl", "LanguagesHaveEntry"]
    caminho = tmp_path / "results.csv"
    with caminho.open("w", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(colunas)
        escritor.writerow(["A;B"] * len(colunas))
    p = perfil_csv(caminho, colunas)
    for c in colunas[:3] + ["Employment"]:
        assert p[c]["multisselecao"]
        assert p[c]["opcoes_observadas"] == ["A", "B"]
    for c in ["KnowledgeHaveWorkedWith", "DevType", "EmploymentAddl", "LanguagesHaveEntry"]:
        assert not p[c]["multisselecao"]
        assert p[c]["valores_observados"] == ["A;B"]


def test_schema_mc_sem_seletor_exige_instrucao_ou_lista_conhecida(tmp_path):
    import csv
    from perfil_captura import _colunas_multisselecao, perfil_registros

    esquema = tmp_path / "schema.csv"
    linhas = [
        ["LearnCode", "MC", "", "How did you learn? Select all that apply."],
        ["AILearnHow", "MC", "", "Please <b>check all that apply</b>."],
        ["AIHuman", "MC", "", "Select all that apply."],
        ["AIAgent_Uses", "MC", "", "Select all that apply from both lists."],
        ["AIAgentOrchestration", "MC", "", "Have you used any of the following tools?"],
        ["AIAgentExternal", "MC", "", "Have you used any of the following tools?"],
        ["Texto", "TE", "", "Select all that apply."],
        ["Employment", "MC", "", "What is your employment status?"],
        ["Outra", "MC", "", "Have you used any of the following tools?"],
        ["Unica", "MC", "SAVR", "Select all that apply."],
    ]
    with esquema.open("w", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["qname", "type", "selector", "question"])
        escritor.writerows(linhas)
    nomes = [r[0] for r in linhas]
    regras = _colunas_multisselecao(esquema, nomes)
    assert set(regras) == set(nomes[:6])
    perfil = perfil_registros([{c: "A;B" for c in nomes}], nomes, regras)
    assert "declarada no schema" in perfil["LearnCode"]["dominio"]
    assert "observado na captura" in perfil["AIAgentOrchestration"]["dominio"]
    assert "declarada no schema" not in perfil["AIAgentOrchestration"]["dominio"]
    simples = perfil_registros([{"AIAgentExternal": "A"}], ["AIAgentExternal"], regras)
    assert not simples["AIAgentExternal"]["multisselecao"]
    assert "não foi observada combinação" in simples["AIAgentExternal"]["dominio"]


def test_matrizes_agrupadas_preservam_itens_e_excluem_escalas_por_item(tmp_path):
    import csv
    from perfil_captura import _colunas_multisselecao, perfil_registros

    esquema = tmp_path / "schema.csv"
    with esquema.open("w", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["qname", "type", "question"])
        escritor.writerows([
            ["OpSys", "Matrix", "What is the primary operating system?"],
            ["AITool", "Matrix", "Please select one for each scenario."],
            ["AINext", "Matrix", "How integrated will tools be?"],
            ["AIAgentImpact", "Matrix", "To what extent do you agree?"],
            ["AIAgentChallenges", "Matrix", "To what extent do you agree?"],
            ["Knowledge", "Matrix", "To what extent do you agree?"],
            ["OpSysEntry", "TE", "Describe your system."],
        ])
    colunas = [
        "OpSysPersonal use", "OpSysProfessional use", "AIToolCurrently mostly AI",
        "AINextMuch more integrated", "AIAgentImpactStrongly agree",
        "AIAgentChallengesNeutral", "Knowledge_1", "OpSysEntry", "AIToolOutro",
    ]
    regras = _colunas_multisselecao(esquema, colunas)
    assert set(regras) == set(colunas[:6])
    perfil = perfil_registros([{c: "item A;item B" for c in colunas}], colunas, regras)
    for c in colunas[:6]:
        assert perfil[c]["opcoes_observadas"] == ["item A", "item B"]
        assert "itens da matriz agrupados" in perfil[c]["dominio"]
        assert "múltipla seleção declarada" not in perfil[c]["dominio"]
    for c in colunas[6:]:
        assert not perfil[c]["multisselecao"]
