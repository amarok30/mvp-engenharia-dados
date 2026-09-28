#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# baixar_fontes.sh
#
# Baixa, na máquina local, as quatro safras da Stack Overflow Developer
# Survey e as duas respostas JSON da API do SIDRA (IBGE). Valida integridade
# antes de qualquer upload para o Databricks.
#
# Por que roda localmente: o Databricks Free Edition bloqueia saída de internet
# por padrão, e a falha aparece como erro de DNS. A ingestão principal do MVP é
# upload manual destes arquivos para o Volume
# /Volumes/mafia_office/bronze/pouso/.
#
# Uso:
#   bash scripts/baixar_fontes.sh            # baixa tudo em ./dados
#   DESTINO=/outro/caminho bash scripts/baixar_fontes.sh
#
# Saída:
#   dados/stackoverflow/{2022..2025}/results.csv
#   dados/stackoverflow/{2022..2025}/schema.csv
#   dados/ibge/sidra_9471.json
#   dados/ibge/sidra_5434.json
#   dados/EXTRACAO.txt   (data de extração, URLs, bytes e sha256 de cada arquivo)
#
# Requisitos: bash, curl, python3 (só biblioteca padrão), shasum ou sha256sum.
# -----------------------------------------------------------------------------
set -euo pipefail

DESTINO="${DESTINO:-dados}"
BASE_SO="https://media.githubusercontent.com/media/StackExchange/Survey/main/packages/archive"

# 9471: Brasil (n1) e UF (n3) na mesma consulta, para que a linha nacional publicada
# sirva de validação exata; variáveis 4090 (pessoas), 4091 (CV de pessoas),
# 12965 (percentual) e 12966 (CV do percentual).
# 5434: período fixado em 201201-202602, para que a consulta e a contagem não mudem
# quando o IBGE publicar trimestres novos.
URL_9471="https://apisidra.ibge.gov.br/values/t/9471/n1/all/n3/all/v/4090,4091,12965,12966/p/2022/c1675/all/d/m"
URL_5434="https://apisidra.ibge.gov.br/values/t/5434/n3/all/v/4090/p/201201-202602/c888/all"

# Tamanho exato em bytes de results.csv por safra (medido no dado real).
# Função em vez de array associativo: o bash do macOS (3.2) não tem declare -A.
bytes_esperados() {
  case "$1" in
    2022) echo 108829270 ;;
    2023) echo 158626799 ;;
    2024) echo 159525875 ;;
    2025) echo 140893245 ;;
    *) echo 0 ;;
  esac
}

# Registros esperados, incluindo o cabeçalho d[0] (medidos em 13/09/2026).
REGISTROS_9471=673
REGISTROS_5434=20359

TAMANHO_PONTEIRO_LFS=134

falhar() {
  echo "ERRO: $*" >&2
  exit 1
}

tamanho_bytes() {
  # stat difere entre macOS e Linux; wc -c funciona nos dois.
  wc -c <"$1" | tr -d ' '
}

hash_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | cut -d' ' -f1
  else
    shasum -a 256 "$1" | cut -d' ' -f1
  fi
}

command -v curl >/dev/null 2>&1 || falhar "curl não encontrado."
command -v python3 >/dev/null 2>&1 || falhar "python3 não encontrado."

mkdir -p "$DESTINO/stackoverflow" "$DESTINO/ibge"
EXTRACAO="$DESTINO/EXTRACAO.txt"
DATA_EXTRACAO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

{
  echo "data_extracao_utc=$DATA_EXTRACAO"
  echo "arquivo|url|bytes|sha256"
} >"$EXTRACAO"

registrar() {
  local arquivo="$1" url="$2"
  echo "$arquivo|$url|$(tamanho_bytes "$arquivo")|$(hash_sha256 "$arquivo")" >>"$EXTRACAO"
}

# --- Stack Overflow ----------------------------------------------------------
for ano in 2022 2023 2024 2025; do
  pasta="$DESTINO/stackoverflow/$ano"
  mkdir -p "$pasta"

  for nome in results.csv schema.csv; do
    url="$BASE_SO/$ano/$nome"
    echo ">> Baixando $url"
    curl -fsSL --retry 3 --connect-timeout 30 -o "$pasta/$nome" "$url" \
      || falhar "download falhou: $url"

    bytes="$(tamanho_bytes "$pasta/$nome")"
    if [[ "$bytes" -eq "$TAMANHO_PONTEIRO_LFS" ]]; then
      falhar "$pasta/$nome tem $TAMANHO_PONTEIRO_LFS bytes: é o ponteiro do Git LFS, não o dado. \
Use media.githubusercontent.com, nunca raw.githubusercontent.com."
    fi
    registrar "$pasta/$nome" "$url"
  done

  bytes="$(tamanho_bytes "$pasta/results.csv")"
  esperado="$(bytes_esperados "$ano")"
  if [[ "$bytes" -ne "$esperado" ]]; then
    falhar "$pasta/results.csv tem $bytes bytes; esperado $esperado. Arquivo incompleto ou alterado na origem."
  fi
  echo "   ok: $ano results.csv com $bytes bytes"
done

# --- IBGE / SIDRA --------------------------------------------------------------
echo ">> Baixando SIDRA 9471"
curl -fsSL --retry 3 --max-time 120 -o "$DESTINO/ibge/sidra_9471.json" "$URL_9471" \
  || falhar "download da 9471 falhou: $URL_9471"
registrar "$DESTINO/ibge/sidra_9471.json" "$URL_9471"

echo ">> Baixando SIDRA 5434 (resposta grande, pode levar ~30 s)"
curl -fsSL --retry 3 --max-time 180 -o "$DESTINO/ibge/sidra_5434.json" "$URL_5434" \
  || falhar "download da 5434 falhou (timeout de 180 s): $URL_5434"
registrar "$DESTINO/ibge/sidra_5434.json" "$URL_5434"

# Validação estrutural dos JSON: array, d[0] é cabeçalho, contagem da 5434 e
# presença da linha Brasil (n1) na 9471.
python3 - "$DESTINO/ibge/sidra_9471.json" "$DESTINO/ibge/sidra_5434.json" "$REGISTROS_5434" "$REGISTROS_9471" <<'PY'
import json
import sys

caminho_9471, caminho_5434 = sys.argv[1], sys.argv[2]
esperado_5434, esperado_9471 = int(sys.argv[3]), int(sys.argv[4])


def carregar(caminho):
    with open(caminho, encoding="utf-8") as arquivo:
        dados = json.load(arquivo)
    if not isinstance(dados, list) or len(dados) < 2:
        sys.exit(f"ERRO: {caminho} não é um array JSON com cabeçalho e dados.")
    return dados


d_5434 = carregar(caminho_5434)
if len(d_5434) != esperado_5434:
    sys.exit(
        f"ERRO: 5434 tem {len(d_5434)} registros; esperado {esperado_5434} (com cabeçalho). "
        "Arquivo truncado ou consulta diferente da documentada (o período está fixado em 201201-202602)."
    )
print(f"   ok: 5434 com {len(d_5434)} registros (inclui cabeçalho d[0])")

d_9471 = carregar(caminho_9471)
if len(d_9471) != esperado_9471:
    sys.exit(f"ERRO: 9471 tem {len(d_9471)} registros; esperado {esperado_9471} (com cabeçalho).")
niveis = {registro.get("NC") for registro in d_9471[1:]}
if "1" not in niveis:
    sys.exit("ERRO: 9471 sem registros de nível Brasil (NC=1). Confira se a URL tem /n1/all/n3/all/.")
print(f"   ok: 9471 com {len(d_9471)} registros (inclui cabeçalho d[0]); níveis territoriais {sorted(niveis)}")
PY

echo
echo "Extração concluída em $DATA_EXTRACAO."
echo "Manifesto: $EXTRACAO"
echo
echo "Próximo passo: subir para o Volume, mantendo a estrutura de pastas:"
echo "  $DESTINO/stackoverflow/{ano}/results.csv e schema.csv -> /Volumes/mafia_office/bronze/pouso/stackoverflow/{ano}/"
echo "  $DESTINO/ibge/sidra_9471.json e sidra_5434.json      -> /Volumes/mafia_office/bronze/pouso/ibge/"
echo "  docs/mapa-de-para-arranjo.csv                        -> /Volumes/mafia_office/bronze/pouso/referencia/"
echo "Os quatro results.csv têm o mesmo nome: suba cada um na pasta do seu ano, nunca juntos."
echo "Compare bytes e sha256 de $EXTRACAO com evidencias/EXTRACAO.txt (a data muda a cada execução; os hashes não"
echo "devem mudar). Não substitua evidencias/EXTRACAO.txt: ele registra a extração usada no trabalho."
