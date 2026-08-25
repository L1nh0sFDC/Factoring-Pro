"""
core.py — Regras de negócio do Factoring Pro
================================================

Módulo PURO (zero dependência de UI/Flet) com as regras de cálculo de
liquidação de títulos em operações de Factoring: deságio, PIS,
COFINS, ISSQN e retenções.

Por que separado do app.py: no código original, todo esse cálculo
vivia dentro de closures do Flet (funções aninhadas dentro de
`main(page)`), o que tornava impossível testar a lógica sem
instanciar a interface gráfica inteira. Extrair para cá é o que
permite test_core.py existir.
"""

from decimal import Decimal, ROUND_HALF_UP, getcontext

getcontext().prec = 28

# --------- Constantes de negócio ----------
SERV_RATE = Decimal("0.01")        # Ad Valorem: 1% sobre o valor bruto
ISS_RATE = Decimal("0.02")         # ISSQN: 2% sobre a taxa de serviço
PIS_RATE = Decimal("0.019077")     # PIS: 1,9077% sobre o deságio
COFINS_RATE = Decimal("0.087862")  # COFINS: 8,7862% sobre o deságio

RETIDO_FIXO = Decimal("62.71")
RETIDO_LIMITE = Decimal("100000.00")

# Divisor do fator de deságio. NÃO é 30 (dias do mês civil) — é uma
# convenção operacional da empresa (24,95 dias como base de "1 mês"
# para efeito de deságio). Documentado aqui de propósito para que
# ninguém "corrija" para 30 no futuro achando que é bug.
FATOR_DIAS_BASE = Decimal("24.95")


def parse_decimal(txt: str) -> Decimal:
    """Converte string de valor monetário em Decimal.

    Aceita formato brasileiro com vírgula decimal ("1234,56") e
    formato com ponto decimal ("1234.56").

    LIMITAÇÃO CONHECIDA (documentada, não corrigida silenciosamente):
    não distingue "1.234" como separador de milhar brasileiro
    (= mil duzentos e trinta e quatro) de "1.234" como decimal
    (= um vírgula duzentos e trinta e quatro). Hoje "1.234" sempre
    vira Decimal("1.234"). Ver test_core.py::test_parse_decimal_*
    para os casos cobertos e o caso ambíguo documentado como
    limitação conhecida, não como bug silencioso.
    """
    if txt is None:
        return Decimal("0")
    s = txt.strip()
    if s == "":
        return Decimal("0")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    return Decimal(s)


def money(x: Decimal) -> Decimal:
    """Arredonda para 2 casas decimais com ROUND_HALF_UP (arredondamento
    comercial padrão). Usado em CADA valor intermediário antes de somar
    (deságio por título, impostos, etc.) — evita que erros de
    arredondamento se acumulem de forma imprevisível ao longo do
    cálculo."""
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def dias_corridos(venc, base) -> int:
    """Dias corridos entre a data base e o vencimento. Nunca negativo —
    um título vencido antes da data base conta como 0 dias, não como
    dias negativos (que inverteria o sinal do deságio)."""
    dias = (venc - base).days
    return max(dias, 0)


def calcular_desagio_titulo(bruto: Decimal, dias: int, dmu: Decimal, taxa_mensal: Decimal) -> Decimal:
    """Deságio de um único título.

    Fórmula: Deságio = Bruto × TaxaMensal × ((Dias + DMU) / FATOR_DIAS_BASE)
    """
    dias_efetivos = Decimal(dias) + dmu
    return money(bruto * taxa_mensal * (dias_efetivos / FATOR_DIAS_BASE))


def calcular_totais(titulos: list[dict], taxa_mensal_pct: Decimal, dmu: Decimal) -> dict:
    """Calcula o resumo financeiro completo de uma operação de factoring.

    `titulos`: lista de dicts com pelo menos as chaves 'bruto' (Decimal)
    e 'dias' (int). Função PURA — não modifica os dicts de entrada.

    Retorna um dict com bruto, deságio total, subtotal, serviço,
    PIS, COFINS, ISSQN, impostos totais, fator total, retido,
    líquido e líquido+retido — todos já arredondados (money()).
    """
    taxa_mensal = taxa_mensal_pct / Decimal("100")

    bruto = money(sum((t["bruto"] for t in titulos), Decimal("0")))

    desagio_total = Decimal("0.00")
    desagios_por_titulo = []
    for t in titulos:
        d = calcular_desagio_titulo(t["bruto"], t["dias"], dmu, taxa_mensal)
        desagios_por_titulo.append(d)
        desagio_total += d
    desagio_total = money(desagio_total)

    subtot = money(bruto - desagio_total)
    serv = money(bruto * SERV_RATE)

    pis = money(desagio_total * PIS_RATE)
    cofins = money(desagio_total * COFINS_RATE)
    iss = money(serv * ISS_RATE)
    impostos = money(pis + cofins + iss)

    fator_total = money(desagio_total + impostos)
    retido = RETIDO_FIXO if bruto > RETIDO_LIMITE else Decimal("0.00")

    liquido = money(bruto - fator_total - serv)
    liq_ret = money(liquido + retido)

    return {
        "bruto": bruto,
        "desagio": desagio_total,
        "desagios_por_titulo": desagios_por_titulo,
        "subtot": subtot,
        "serv": serv,
        "pis": pis,
        "cofins": cofins,
        "iss": iss,
        "impostos": impostos,
        "fator_total": fator_total,
        "retido": retido,
        "liquido": liquido,
        "liq_ret": liq_ret,
    }


def fmt_brl(x: Decimal) -> str:
    return f"{float(x):,.2f}"
