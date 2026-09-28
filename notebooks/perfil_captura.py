"""Perfil da captura: valores observados, ausência, formato e extremos numéricos."""
import csv
import math
from pathlib import Path
import re
from array import array

NULOS = {"", "NA"}
LIMITE_CATEGORIAS = 256
LIMITE_TAMANHO_OPCAO = 512
# Famílias Matrix confirmadas nos schema.csv de 2022 a 2025. Matrizes de
# concordância (Knowledge, Frequency etc.) não são listas de tecnologias.
FAMILIAS_TECNOLOGIA = {
    "Language", "Database", "Platform", "Webframe", "MiscTech", "ToolsTech",
    "NEWCollabTools", "OfficeStackAsync", "OfficeStackSync", "AISearch", "AIDev",
    "Embedded", "AISearchDev", "DevEnvs", "SOTags", "CommPlatform", "AIModels",
}
SUFIXOS_TECNOLOGIA = ("HaveWorkedWith", "WantToWorkWith", "Admired")
# Nestas exportações, cada coluna reúne os itens associados à categoria.
# AITool 2025 permite uma resposta por cenário; isso não impede vários
# cenários na mesma célula exportada. Knowledge/Frequency usam outro formato.
SUFIXOS_MATRIZES_AGRUPADAS = {
    "OpSys": ("Personal use", "Professional use"),
    "AITool": (
        "Interested in Using", "Currently Using", "Not interested in Using",
        "Currently partially AI", "Don't plan to use AI for this task",
        "Plan to partially use AI", "Plan to mostly use AI", "Currently mostly AI",
    ),
    "AINext": (
        "Very different", "Neither different nor similar", "Somewhat similar",
        "Very similar", "Somewhat different", "Much more integrated", "No change",
        "More integrated", "Less integrated", "Much less integrated",
    ),
    "AIAgentImpact": (
        "Somewhat agree", "Neutral", "Somewhat disagree", "Strongly agree", "Strongly disagree",
    ),
    "AIAgentChallenges": (
        "Somewhat agree", "Neutral", "Somewhat disagree", "Strongly agree", "Strongly disagree",
    ),
}
# O schema de 2025 omite selector. As perguntas e os resultados publicados em
# survey.stackoverflow.co/2025/ai identificam listas de ferramentas; a captura
# mostra a serialização multivalorada. Não se presume um seletor não publicado.
CAMPOS_MC_MULTIVALORADOS = {
    "AIAgentKnowledge", "AIAgentOrchestration", "AIAgentObserveSecure", "AIAgentExternal",
}
FUNDAMENTO_OBSERVADO = "campo de escolha MC; formato multivalorado observado na captura"
MEDIDAS = { "ConvertedCompYearly", "YearsCode", "YearsCodePro", "WorkExp", "JobSat"}
DOMINIOS = {
    "ResponseId": "inteiro positivo, identificador único dentro da safra",
    "YearsCode": "anos em texto; aceita Less than 1 year e More than 50 years; a safra 2025 admite valores acima de 50",
    "YearsCodePro": "anos de experiência profissional em texto, incluindo as categorias de extremidade da safra",
    "JobSat": "escala de satisfação de 0 a 10",
    "CompTotal": "remuneração declarada na moeda e periodicidade da resposta; número não negativo",
    "ConvertedCompYearly": "remuneração anual em dólares, convertida pela fonte; número não negativo",
}

def _colunas_multisselecao(caminho_schema: Path, colunas: list[str]) -> dict[str, str]:
    """Relaciona campos de opções e o fundamento da interpretação da captura."""
    encontradas = {}
    with caminho_schema.open(encoding="utf-8-sig", newline="") as arquivo:
        for pergunta in csv.DictReader(arquivo):
            nome = pergunta.get("qname")
            tipo = pergunta.get("type")
            seletor = pergunta.get("selector")
            texto = re.sub(r"<[^>]+>", " ", pergunta.get("question", "")).lower()
            if tipo == "MC":
                explicito = re.search(r"\b(?:select|check) all that apply\b", texto)
                if seletor == "MAVR" or (not seletor and explicito):
                    encontradas[nome] = "múltipla seleção declarada no schema da safra"
                elif (not seletor and nome in CAMPOS_MC_MULTIVALORADOS
                      and "any of the following" in texto):
                    encontradas[nome] = FUNDAMENTO_OBSERVADO
            elif tipo == "Matrix":
                if nome in FAMILIAS_TECNOLOGIA:
                    for sufixo in SUFIXOS_TECNOLOGIA:
                        encontradas[nome + sufixo] = "lista de tecnologias da matriz declarada no schema"
                for sufixo in SUFIXOS_MATRIZES_AGRUPADAS.get(nome, ()):
                    encontradas[nome + sufixo] = (
                        "itens da matriz agrupados pela categoria de resposta na coluna"
                    )
    return {c: fundamento for c, fundamento in encontradas.items() if c in colunas}


def perfil_csv(caminho, colunas):
    """Lê campos longos; usa schema.csv na mesma pasta, quando presente.

    O schema e o formato da captura fundamentam a interpretação dos campos de escolha.
    O delimitador sozinho não comprova múltipla seleção.
    O limite global do leitor é restaurado ao terminar, inclusive em caso de erro.
    """
    caminho = Path(caminho)
    limite_anterior = csv.field_size_limit()
    try:
        csv.field_size_limit(max(limite_anterior, caminho.stat().st_size))
        esquema = caminho.with_name("schema.csv")
        multisselecao = _colunas_multisselecao(esquema, colunas) if esquema.exists() else set()
        with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
            return perfil_registros(csv.DictReader(arquivo), colunas, multisselecao)
    finally:
        csv.field_size_limit(limite_anterior)


def perfil_registros(registros, colunas, multisselecao: set[str] | dict[str, str] | None = None):
    """Enumera até 256 combinações e opções nos campos de escolha reconhecidos."""
    multisselecao = multisselecao or set()
    fundamentos = (multisselecao if isinstance(multisselecao, dict) else
                   {c: "múltipla seleção informada pelo chamador" for c in multisselecao})
    estados = {c: {"nulos": 0, "valores": set(), "saturado": False, "numeros": array("d"),
                   "opcoes": set(), "opcoes_saturadas": False, "separador_observado": False,
                   "nao_numericos": 0, "invalidos": 0} for c in colunas}
    ids, duplicados, total = set(), 0, 0
    for registro in registros:
        total += 1
        for c, e in estados.items():
            valor = registro[c] if c in registro else None
            texto = "" if valor is None else str(valor).strip()
            if texto in NULOS:
                e["nulos"] += 1
                continue
            if not e["saturado"]:
                e["valores"].add(texto)
                if len(e["valores"]) > LIMITE_CATEGORIAS:
                    e["saturado"] = True
                    e["valores"].clear()
            if c in multisselecao:
                e["separador_observado"] |= ";" in texto
            if c in multisselecao and not e["opcoes_saturadas"]:
                for opcao in texto.split(";"):
                    opcao = opcao.strip()
                    if not opcao:
                        continue
                    e["opcoes"].add(opcao)
                    if len(e["opcoes"]) > LIMITE_CATEGORIAS or len(opcao) > LIMITE_TAMANHO_OPCAO:
                        e["opcoes_saturadas"] = True
                        e["opcoes"].clear()
                        break
            try:
                numero = float(texto)
                if not math.isfinite(numero):
                    raise ValueError("não finito")
                e["numeros"].append(numero)
            except (ValueError, OverflowError):
                numero = None
                e["nao_numericos"] += 1
            if c == "ResponseId":
                if texto in ids:
                    duplicados += 1
                ids.add(texto)
                e["invalidos"] += int(numero is None or numero <= 0 or re.fullmatch(r"[+]?\d+", texto) is None)
            elif c in {"CompTotal", "ConvertedCompYearly", "WorkExp"}:
                e["invalidos"] += int(numero is None or numero < 0)
            elif c == "JobSat":
                e["invalidos"] += int(numero is None or not 0 <= numero <= 10)
            elif c in {"YearsCode", "YearsCodePro"}:
                e["invalidos"] += int(texto not in {"Less than 1 year", "More than 50 years"}
                                      and (numero is None or numero < 0 or re.fullmatch(r"[+]?\d+", texto) is None))
    resultado = {}
    for c, e in estados.items():
        preenchidos = total - e["nulos"]
        numerico = bool(preenchidos and not e["nao_numericos"])
        valores = sorted(e["valores"])
        if c in DOMINIOS:
            dominio = DOMINIOS[c]
        elif not preenchidos:
            dominio = "nenhum valor preenchido observado; consultar o dicionário da fonte para o domínio admissível"
        elif c in multisselecao:
            dominio = fundamentos[c]
            if dominio == FUNDAMENTO_OBSERVADO and not e["separador_observado"]:
                dominio = "campo de escolha MC; não foi observada combinação de opções nesta captura"
            dominio += "; opções separadas por ponto e vírgula quando há mais de uma"
            opcoes = sorted(e["opcoes"])
            if e["opcoes_saturadas"]:
                dominio += "; enumeração de opções omitida por exceder o limite de 256 itens ou 512 caracteres por item"
            elif len(opcoes) <= 40 and all(len(v) <= 160 for v in opcoes):
                dominio += "; opções observadas: " + "; ".join(opcoes)
            else:
                dominio += f"; {len(opcoes)} opções observadas, enumeradas em docs/dominios-captura.json"
        elif numerico:
            dominio = "formato numérico observado; sem faixa admissível publicada no dicionário da fonte"
        elif not e["saturado"] and len(valores) <= 40 and all(len(v) <= 160 for v in valores):
            dominio = "valores observados: " + "; ".join(valores)
        elif not e["saturado"]:
            dominio = f"texto; {len(valores)} valores distintos observados; enumeração em docs/dominios-captura.json"
        else:
            dominio = "texto com mais de 256 valores distintos observados; pode incluir respostas livres ou combinações de opções"
        if numerico:
            dominio += f"; mínimo observado {min(e['numeros']):g}; máximo observado {max(e['numeros']):g}"
        dominio += "; NA ou vazio indica ausência. Valores observados não definem, por si só, todas as respostas admissíveis."
        regra = DOMINIOS.get(c)
        if c == "WorkExp":
            regra = "anos de experiência não negativos"
        outliers = inferior = superior = None
        if c in MEDIDAS and e["numeros"]:
            numeros = sorted(e["numeros"])
            def quantil(p):
                pos = (len(numeros) - 1) * p
                i = int(pos)
                return numeros[i] + (numeros[min(i + 1, len(numeros) - 1)] - numeros[i]) * (pos - i)
            q1, q3 = quantil(.25), quantil(.75)
            inferior, superior = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
            outliers = sum(n < inferior or n > superior for n in numeros)
        resultado[c] = {
            "linhas": total, "nulos": e["nulos"], "dominio": dominio,
            "valores_observados": valores if not e["saturado"] else [],
            "lista_truncada": e["saturado"],
            "multisselecao": c in multisselecao and (
                fundamentos[c] != FUNDAMENTO_OBSERVADO or e["separador_observado"]
            ),
            "fundamento_multisselecao": (
                "schema MC; combinação de opções não observada"
                if fundamentos.get(c) == FUNDAMENTO_OBSERVADO and not e["separador_observado"]
                else fundamentos.get(c)
            ),
            "opcoes_observadas": sorted(e["opcoes"]),
            "opcoes_truncadas": e["opcoes_saturadas"],
            "unicidade": (f"identificador da safra: {duplicados} repetições" if c == "ResponseId"
                          else "não se aplica: atributo sem requisito de unicidade"),
            "regra_consistencia": regra or "sem domínio fechado publicado; perfil descritivo da captura",
            "fora_da_regra": e["invalidos"] if regra else None,
            "consistencia_pct": round(100 * (preenchidos - e["invalidos"]) / preenchidos, 2) if regra and preenchidos else None,
            "acuracia": "não verificável por resposta: sem referência externa individual; formato e plausibilidade são avaliados separadamente",
            "outliers_iqr": outliers, "limite_inf_iqr": inferior, "limite_sup_iqr": superior,
        }
    return resultado
