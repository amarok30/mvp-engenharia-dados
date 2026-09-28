"""Gera os gráficos de docs/img/ a partir das views Gold exportadas do Databricks.

Entrada: evidencias/views/<view>.csv, um arquivo por view do notebook 08, exportado do catálogo depois da execução.
Saída: docs/img/*.png, um por gráfico, com a mesma especificação (tipo, eixos, série, filtro) registrada nos
comentários "-- Gráfico ..." do notebook 08.

    python3 scripts/gerar_graficos.py

Dependência: matplotlib. Nenhum número é digitado neste script: tudo vem dos CSVs.
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
VIEWS = REPO / "evidencias" / "views"
IMG = REPO / "docs" / "img"

CORES = {"Remoto": "#2f6f9f", "Híbrido": "#e0a83a", "Presencial": "#b5493a", "Flexível": "#7a8b99"}
SAFRAS = [2022, 2023, 2024, 2025]
FAIXAS = ["0–2", "3–5", "6–10", "11–20", "21+"]


def ler(view: str) -> list[dict]:
    # O export do Databricks grava booleanos como true e false; o Spark local, como True e False.
    with open(VIEWS / f"{view}.csv", encoding="utf-8", newline="") as f:
        return [{k: v.lower() if v in ("True", "False") else v for k, v in r.items()} for r in csv.DictReader(f)]


def num(v: str) -> float | None:
    return None if v in ("", None) else float(v)


def salvar(fig, nome: str) -> None:
    fig.tight_layout()
    fig.savefig(IMG / nome, dpi=150)
    plt.close(fig)
    print("ok", nome)


def rodape(ax, texto: str) -> None:
    ax.annotate(texto, (0, 0), xycoords="axes fraction", xytext=(0, -44), textcoords="offset points", fontsize=8,
                color="#555555", va="top")


def q1a() -> None:
    linhas = [r for r in ler("vw_q1_evolucao_arranjo") if r["base"] == "trabalhando" and r["entra_serie_historica"] == "true"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    base = [0.0] * len(SAFRAS)
    for arranjo in ("Remoto", "Híbrido", "Presencial"):
        vals = [next(num(r["pct_serie_comparavel"]) for r in linhas if int(r["safra"]) == s and r["arranjo"] == arranjo) for s in SAFRAS]
        ax.bar([str(s) for s in SAFRAS], vals, bottom=base, color=CORES[arranjo], label=arranjo, width=0.6)
        for i, v in enumerate(vals):
            ax.text(i, base[i] + v / 2, f"{v:.1f}%".replace(".", ","), ha="center", va="center", color="white", fontsize=9)
        base = [b + v for b, v in zip(base, vals)]
    ax.set_ylim(0, 100)
    ax.set_ylabel("% da série comparável")
    ax.set_title("Q1a · Arranjo de trabalho, 2022 a 2025 (base: quem trabalha, série comparável)")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.08), ncol=3, frameon=False)
    rodape(ax, "Fonte: gold.vw_q1_evolucao_arranjo. Flexível (só em 2025) fica fora da série comparável; ver tabela Q1b.")
    salvar(fig, "q1-evolucao-arranjo.png")


def q2() -> None:
    linhas = [r for r in ler("vw_q2_arranjo_por_porte") if r["safra"] == "2025" and r["e_autonomo"] == "false" and r["porte"] != "Não sabe"]
    portes = sorted({(int(r["porte_ordem"]), r["porte"]) for r in linhas})
    nomes = [p for _, p in portes]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    base = [0.0] * len(nomes)
    for arranjo in ("Remoto", "Híbrido", "Presencial", "Flexível"):
        vals = [next((num(r["pct_no_porte"]) for r in linhas if r["porte"] == p and r["arranjo"] == arranjo), 0.0) for p in nomes]
        ax.bar(nomes, vals, bottom=base, color=CORES[arranjo], label=arranjo, width=0.65)
        for i, v in enumerate(vals):
            if v >= 6:
                ax.text(i, base[i] + v / 2, f"{v:.1f}".replace(".", ","), ha="center", va="center", color="white", fontsize=8)
        base = [b + v for b, v in zip(base, vals)]
    for i, p in enumerate(nomes):
        rh = sum(next((num(r["pct_no_porte"]) for r in linhas if r["porte"] == p and r["arranjo"] == a), 0.0) for a in ("Remoto", "Híbrido"))
        ax.text(i, 102, f"{rh:.1f}".replace(".", ","), ha="center", va="bottom", fontsize=9, fontweight="bold", color="#333333")
    ns = {p: next(r["n_porte"] for r in linhas if r["porte"] == p) for p in nomes}
    ax.set_xticks(range(len(nomes)), [f"{p}\n(n = {int(ns[p]):,})".replace(",", ".") for p in nomes], fontsize=8)
    ax.set_ylim(0, 109)
    ax.set_yticks(range(0, 101, 20))
    ax.set_ylabel("% das respostas informadas do porte")
    ax.set_title("Q2 · Arranjo por porte da empresa, 2025\n(número em negrito: remoto mais híbrido; sem Autônomo e Não sabe)", pad=26)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=4, frameon=False, fontsize=8)
    rodape(ax, "Fonte: gold.vw_q2_arranjo_por_porte. Percentual dentro do porte, com Flexível no denominador.")
    salvar(fig, "q2-arranjo-por-porte.png")


def q3() -> None:
    linhas = [r for r in ler("vw_q3_brasil_x_resto_mundo") if r["entra_serie_historica"] == "true"]
    fig, eixos = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    for ax, (titulo, arranjos) in zip(eixos, (("Remoto", ("Remoto",)), ("Remoto mais híbrido", ("Remoto", "Híbrido")))):
        for grupo, cor in (("Brasil", "#2f6f9f"), ("Resto do mundo", "#7a8b99")):
            ys = [sum(num(r["pct_serie_comparavel"]) for r in linhas if int(r["safra"]) == s and r["grupo"] == grupo and r["arranjo"] in arranjos) for s in SAFRAS]
            ax.plot(SAFRAS, ys, marker="o", color=cor, label=grupo)
            for x, y in zip(SAFRAS, ys):
                ax.annotate(f"{y:.1f}".replace(".", ","), (x, y), textcoords="offset points", xytext=(0, 7 if grupo == "Brasil" else -13), ha="center", fontsize=8, color=cor)
        ax.set_xticks(SAFRAS)
        ax.set_ylim(0, 100)
        ax.set_title(titulo)
    eixos[0].set_ylabel("% da série comparável")
    eixos[0].legend(frameon=False, loc="lower left")
    fig.suptitle("Q3 · Brasil e resto do mundo, 2022 a 2025 (base: quem trabalha)")
    fig.text(0.01, 0.01, "Fonte: gold.vw_q3_brasil_x_resto_mundo. Resto do mundo exclui o Brasil. Brasil com 586 respostas em 2025.",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(IMG / "q3-brasil-x-resto-mundo.png", dpi=150)
    plt.close(fig)
    print("ok", "q3-brasil-x-resto-mundo.png")


def wilson(remotos: int, n: int) -> tuple[float, float, float]:
    p = remotos / n
    z2n = 3.8416 / n
    raiz = (p * (1 - p) / n + z2n ** 2 / (4 * 3.8416)) ** 0.5
    return round(100 * p, 1), round(100 * (p + z2n / 2 - 1.96 * raiz) / (1 + z2n), 1), round(100 * (p + z2n / 2 + 1.96 * raiz) / (1 + z2n), 1)


def q4a() -> None:
    linhas = [r for r in ler("vw_q4_perfil_remoto") if r["safra"] == "2025"]
    agg: dict[str, list[int]] = {}
    for r in linhas:
        a = agg.setdefault(r["perfil"], [0, 0, 0])
        a[0] += int(r["n_serie_comparavel"]); a[1] += int(r["remotos"]); a[2] += int(r["hibridos"])
    perfis = sorted(((100 * rem / n, 100 * hib / n, n, d) for d, (n, rem, hib) in agg.items() if n >= 100), key=lambda t: t[0] + t[1])
    fig, ax = plt.subplots(figsize=(9, 0.32 * len(perfis) + 1.8))
    ys = list(range(len(perfis)))
    ax.barh(ys, [p[0] for p in perfis], color=CORES["Remoto"], height=0.65, label="Remoto")
    ax.barh(ys, [p[1] for p in perfis], left=[p[0] for p in perfis], color=CORES["Híbrido"], height=0.65, label="Híbrido")
    ax.set_yticks(ys, [f"{p[3]} (n = {format(p[2], ',').replace(',', '.')})" for p in perfis], fontsize=8)
    for p, y in zip(perfis, ys):
        ax.text(p[0] + p[1] + 0.8, y, f"{p[0] + p[1]:.1f}".replace(".", ","), va="center", fontsize=7)
    ax.set_xlim(0, 105)
    ax.set_xlabel("% da série comparável")
    ax.set_title("Q4a · Remoto e híbrido por perfil, 2025 (perfis com n ≥ 100)")
    ax.legend(frameon=False, loc="lower right", fontsize=8)
    rodape(ax, "Fonte: gold.vw_q4_perfil_remoto. Perfil = primeiro valor de DevType, como a pesquisa publica.")
    salvar(fig, "q4-perfil.png")


def q4b() -> None:
    linhas = ler("vw_q4_perfil_remoto")
    agg: dict[tuple[int, str], list[int]] = {}
    for r in linhas:
        if r["faixa_experiencia"] not in FAIXAS:
            continue
        a = agg.setdefault((int(r["safra"]), r["faixa_experiencia"]), [0, 0])
        a[0] += int(r["n_serie_comparavel"]); a[1] += int(r["remotos"])
    fig, ax = plt.subplots(figsize=(9, 4.5))
    largura = 0.2
    for i, s in enumerate(SAFRAS):
        vals = [wilson(*reversed(agg[(s, f)]))[0] if (s, f) in agg and agg[(s, f)][0] >= 100 else 0 for f in FAIXAS]
        xs = [j + (i - 1.5) * largura for j in range(len(FAIXAS))]
        ax.bar(xs, vals, width=largura, label=str(s), color=["#c9d6e3", "#8fb0cc", "#4f86b0", "#2f6f9f"][i])
        for x, v in zip(xs, vals):
            ax.text(x, v + 0.8, f"{v:.1f}".replace(".", ","), ha="center", fontsize=7)
    ax.set_xticks(range(len(FAIXAS)), [f"{f} anos" for f in FAIXAS])
    ax.set_ylabel("% Remoto na série comparável")
    ax.set_title("Q4b · Remoto por faixa de anos codando e safra (combinações com n de pelo menos 100)")
    ax.set_ylim(0, 60)
    ax.legend(title="Safra", frameon=False, ncol=4, loc="upper left")
    rodape(ax, "Fonte: gold.vw_q4_perfil_remoto, agregada por faixa. YearsCode inclui anos de estudo; censurada em 0 e 50.")
    salvar(fig, "q4-experiencia.png")


def q5() -> None:
    linhas = ler("vw_q5_arranjo_satisfacao")
    arranjos = ["Remoto", "Híbrido", "Presencial", "Flexível"]
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    for i, (s, cor) in enumerate(((2024, "#8fb0cc"), (2025, "#2f6f9f"))):
        pts = [next((r for r in linhas if int(r["safra"]) == s and r["arranjo"] == a), None) for a in arranjos]
        xs = [j + (i - 0.5) * 0.3 for j in range(len(arranjos)) if pts[j]]
        med = [num(p["satisfacao_media"]) for p in pts if p]
        err = [1.96 * num(p["erro_padrao_media"]) for p in pts if p]
        ax.errorbar(xs, med, yerr=err, fmt="o", color=cor, capsize=4, markersize=7, label=f"{s} · média")
        pad = [num(p["satisfacao_media_padronizada"]) for p in pts if p]
        ax.plot(xs, pad, "D", color="#b5493a", markersize=4, label="padronizada por experiência" if i else None)
        for x, m in zip(xs, med):
            ax.text(x + 0.05, m, f"{m:.2f}".replace(".", ","), va="center", fontsize=8)
    ax.set_xticks(range(len(arranjos)), arranjos)
    ax.set_ylim(6, 8)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.2f}".replace(".", ",")))
    ax.set_ylabel("Satisfação com o emprego (0 a 10)")
    ax.set_title("Q5 · Satisfação média por arranjo, 2024 e 2025, com intervalo de 95%\n(o eixo mostra só de 6 a 8)")
    ax.legend(frameon=False, fontsize=8, ncol=3)
    rodape(ax, "Fonte: gold.vw_q5_arranjo_satisfacao. Flexível só existe em 2025. Associação, não causa.")
    salvar(fig, "q5-satisfacao.png")


def q6() -> None:
    linhas = [r for r in ler("vw_q6_teletrabalho_uf") if r["modalidade_codigo"] == "59805"]
    ufs = sorted((r for r in linhas if r["nivel"] == "uf"), key=lambda r: num(r["percentual"]))
    brasil = next(r for r in linhas if r["nivel"] == "pais")
    cores = {"Sustenta conclusão": "#2f6f9f", "Usar com ressalva": "#e0a83a"}
    fig, ax = plt.subplots(figsize=(9, 8))
    ys = range(len(ufs))
    ax.barh(list(ys), [num(r["percentual"]) for r in ufs],
            xerr=[[num(r["percentual"]) - num(r["ic95_percentual_inf"]) for r in ufs], [num(r["ic95_percentual_sup"]) - num(r["percentual"]) for r in ufs]],
            color=[cores.get(r["leitura_percentual"], "#b5493a") for r in ufs], capsize=2, height=0.7)
    ax.set_yticks(list(ys), [f"{r['uf_sigla']} · {r['territorio']} (CV {r['cv_percentual'].replace('.', ',')}%)" for r in ufs], fontsize=8)
    ax.axvline(num(brasil["percentual"]), color="#333333", linestyle="--", linewidth=1)
    ax.text(num(brasil["percentual"]) + 0.15, 0.2, f"Brasil: {brasil['percentual'].replace('.', ',')}%", fontsize=8)
    for r, y in zip(ufs, ys):
        ax.text(num(r["ic95_percentual_sup"]) + 0.2, y, r["percentual"].replace(".", ","), va="center", fontsize=7)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}".replace(".", ",")))
    ax.set_xlabel("% dos ocupados em teletrabalho, 4º trimestre de 2022, com intervalo de 95%")
    ax.set_title("Q6 · Teletrabalho por UF (PNAD Contínua, tabela 9471)")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=c, label=f"CV do percentual: {k}") for k, c in cores.items()], frameon=False, fontsize=8, loc="lower right")
    rodape(ax, "Fonte: gold.vw_q6_teletrabalho_uf. Faixas de CV são convenção do projeto sobre o CV publicado pelo IBGE.")
    salvar(fig, "q6-teletrabalho-uf.png")


def q7a() -> None:
    linhas = ler("vw_q7_ocupacao_proxy_tecnologia_uf")
    por_periodo: dict[tuple[int, int], list[float]] = {}
    for r in linhas:
        a = por_periodo.setdefault((int(r["ano"]), int(r["trimestre"])), [0.0, 0.0, 0])
        a[0] += num(r["pessoas_mil"]) or 0
        if num(r["media_movel_4t"]) is not None:
            a[1] += num(r["media_movel_4t"]); a[2] += 1
    chaves = sorted(por_periodo)
    xs = [a + (t - 1) / 4 for a, t in chaves]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(xs, [por_periodo[k][0] for k in chaves], color="#8fb0cc", linewidth=1, label="trimestral (soma das UFs)")
    mm = [(x, por_periodo[k][1]) for x, k in zip(xs, chaves) if por_periodo[k][2] == 27]
    ax.plot([m[0] for m in mm], [m[1] for m in mm], color="#2f6f9f", linewidth=2, label="média móvel de 4 trimestres")
    ax.set_ylabel("Pessoas ocupadas (mil)")
    ax.set_title("Q7a · Ocupados no grupamento proxy de tecnologia, Brasil (soma das 27 UFs), 2012 a 2026")
    ax.legend(frameon=False)
    rodape(ax, "Fonte: gold.vw_q7_ocupacao_proxy_tecnologia_uf (PNAD Contínua, tabela 5434, grupamento 56624). Sem CV nesta consulta.")
    salvar(fig, "q7-serie-brasil.png")


def q7b() -> None:
    linhas = ler("vw_q7_ocupacao_proxy_tecnologia_uf")
    ultimo = max((int(r["ano"]) * 10 + int(r["trimestre"])) for r in linhas)
    ufs = sorted((r for r in linhas if int(r["ano"]) * 10 + int(r["trimestre"]) == ultimo), key=lambda r: num(r["pessoas_mil"]))
    fig, ax = plt.subplots(figsize=(9, 7.5))
    ys = range(len(ufs))
    ax.barh(list(ys), [num(r["pessoas_mil"]) for r in ufs], color=["#b5493a" if num(r["variacao_anual_media_movel_pct"]) < 0 else "#2f6f9f" for r in ufs], height=0.7)
    ax.set_yticks(list(ys), [f"{r['uf_sigla']} · {r['uf_nome']}" for r in ufs], fontsize=8)
    for r, y in zip(ufs, ys):
        v = num(r["variacao_anual_media_movel_pct"])
        ax.text(num(r["pessoas_mil"]) + 20, y, f"{v:+.1f}%".replace(".", ",") + " ao ano", va="center", fontsize=7)
    ax.set_xlabel(f"Pessoas ocupadas (mil) no período {ufs[0]['periodo']}; rótulo: variação anual da média móvel")
    ax.set_title("Q7b · Ocupados no grupamento proxy por UF, último trimestre\n(vermelho: variação anual negativa da média móvel)")
    rodape(ax, "Fonte: gold.vw_q7_ocupacao_proxy_tecnologia_uf. UFs pequenas têm variação mais instável.")
    salvar(fig, "q7-ufs.png")


def q1b() -> None:
    linhas = [r for r in ler("vw_q1_evolucao_arranjo") if r["base"] == "trabalhando" and r["safra"] == "2025"]
    n = {r["arranjo"]: int(r["respondentes"]) for r in linhas}
    informados = int(linhas[0]["n_informados"])
    fig, ax = plt.subplots(figsize=(9, 3.8))
    grupos = (("Remoto", ("Remoto",)), ("Híbrido", ("Híbrido",)), ("Remoto mais híbrido", ("Remoto", "Híbrido")))
    for y, (rotulo, arranjos) in enumerate(grupos):
        base = sum(n[a] for a in arranjos)
        inf, sup = 100 * base / informados, 100 * (base + n["Flexível"]) / informados
        comparavel = 100 * base / (informados - n["Flexível"])
        ax.plot([inf, sup], [y, y], color="#7a8b99", linewidth=8, solid_capstyle="butt")
        ax.plot(comparavel, y, "o", color=CORES.get(arranjos[-1], "#2f6f9f"), markersize=9)
        for x, txt in ((inf, f"{inf:.1f}"), (sup, f"{sup:.1f}")):
            ax.text(x, y + 0.22, txt.replace(".", ","), ha="center", fontsize=8)
        ax.text(comparavel, y - 0.36, f"{comparavel:.1f}".replace(".", ","), ha="center", fontsize=8, fontweight="bold")
    ax.set_yticks(range(len(grupos)), [g[0] for g in grupos])
    ax.set_ylim(-0.6, len(grupos) - 0.3)
    ax.set_xlim(0, 100)
    ax.set_xlabel("% de quem trabalha e informou o arranjo, 2025")
    ax.set_title("Q1b · Sensibilidade à classificação de Your choice em 2025\n"
                 "faixa: Flexível contado fora e dentro do arranjo; ponto: série comparável, sem Flexível")
    rodape(ax, "Fonte: gold.vw_q1_evolucao_arranjo, base trabalhando, 2025.")
    salvar(fig, "q1-limites.png")


def q1c() -> None:
    linhas = [r for r in ler("vw_q1_remoto_por_vinculo") if r["classificacao_duplos"] == "duplos como Empregado" and r["safra"] in ("2024", "2025")]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    rotulos, valores, cores = [], [], []
    for s in ("2024", "2025"):
        for v in ("Empregado", "Autônomo", "Todos"):
            r = next(x for x in linhas if x["safra"] == s and x["vinculo"] == v)
            rotulos.append(f"{s}\n{v}"); valores.append(num(r["pct_remoto"])); cores.append("#8fb0cc" if s == "2024" else "#2f6f9f")
    ax.bar(range(len(valores)), valores, color=cores, width=0.6)
    for i, v in enumerate(valores):
        ax.text(i, v + 1, f"{v:.1f}".replace(".", ","), ha="center", fontsize=8)
    todos25 = next(x for x in linhas if x["safra"] == "2025" and x["vinculo"] == "Todos")
    inf, sup, pad = num(todos25["remoto_limite_inf_nulos"]), num(todos25["remoto_limite_sup_nulos"]), num(todos25["pct_remoto_padronizado_2024"])
    ax.plot([5.5, 5.5], [inf, sup], color="#b5493a", linewidth=2)
    ax.plot(5.5, pad, "D", color="#b5493a")
    ax.text(5.65, sup, f"com os nulos como remotos: {sup:.1f}".replace(".", ","), fontsize=7, va="center")
    ax.text(5.65, inf, f"com os nulos como não remotos: {inf:.1f}".replace(".", ","), fontsize=7, va="center")
    ax.text(5.65, pad, f"na composição de 2024: {pad:.1f}".replace(".", ","), fontsize=7, va="center", color="#b5493a")
    ax.set_xticks(range(len(rotulos)), rotulos, fontsize=8)
    ax.set_xlim(-0.5, 8)
    ax.set_ylim(0, 80)
    ax.set_ylabel("% Remoto na série comparável")
    ax.set_title("Q1c · Remoto por vínculo em 2024 e 2025, e o que a não resposta de 2025 permite dizer")
    rodape(ax, "Fonte: gold.vw_q1_remoto_por_vinculo, quem marcou empregado e autônomo contado como empregado.")
    salvar(fig, "q1-vinculo.png")


def q8() -> None:
    linhas = [r for r in ler("vw_q8_mercado_brasil") if r["nivel"] == "pais" and r["cenario"] in ("A", "B")]
    linhas.sort(key=lambda r: num(r["estimativa_mil"]))
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ys = range(len(linhas))
    rot = {"A": "teletrabalho", "B": "trabalho remoto"}
    for y, r in zip(ys, linhas):
        est, inf, sup = num(r["estimativa_mil"]), num(r["estimativa_ic95_inf_mil"]), num(r["estimativa_ic95_sup_mil"])
        ax.barh(y, est, color="#2f6f9f" if r["cenario"] == "A" else "#8fb0cc", height=0.6)
        if inf is not None and sup is not None:
            ax.plot([inf, sup], [y, y], color="#333333", linewidth=1)
        ax.text((sup if sup is not None else est) + 15, y, f"{est:,.1f}".replace(",", "X").replace(".", ",").replace("X", "."), fontsize=8, va="center")
    ax.set_xlim(0, 1550)
    ax.set_yticks(list(ys), [f"{rot[r['cenario']]} · {'taxa nacional' if 'nacional' in r['metodo'] else 'soma das UFs'}" for r in linhas], fontsize=8)
    ax.set_xlabel("Mil pessoas no setor proxy, 4º trimestre de 2022 (traço: precisão da taxa do IBGE)")
    ax.set_title("Q8 · Cenários de público no Brasil, por taxa usada")
    rodape(ax, "Fonte: gold.vw_q8_mercado_brasil. Transferência da taxa geral ao setor proxy; hipótese não validada.")
    salvar(fig, "q8-mercado-brasil.png")


if __name__ == "__main__":
    IMG.mkdir(parents=True, exist_ok=True)
    for f in (q1a, q1b, q1c, q2, q3, q4a, q4b, q5, q6, q7a, q7b, q8):
        f()
