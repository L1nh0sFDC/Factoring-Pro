"""
test_core.py — Testes das regras de negócio do Factoring Pro

Cobre: parsing de valores monetários, arredondamento comercial,
cálculo de dias corridos, deságio por título e o cálculo consolidado
(bruto, impostos, retenção, líquido).
"""

from decimal import Decimal
from datetime import datetime

import pytest

from core import (
    parse_decimal,
    money,
    dias_corridos,
    calcular_desagio_titulo,
    calcular_totais,
    RETIDO_LIMITE,
    RETIDO_FIXO,
)


# ---------------------------------------------------------------------------
# parse_decimal
# ---------------------------------------------------------------------------

class TestParseDecimal:
    def test_formato_ponto_decimal(self):
        assert parse_decimal("1234.56") == Decimal("1234.56")

    def test_formato_virgula_decimal_brasileiro(self):
        assert parse_decimal("1234,56") == Decimal("1234.56")

    def test_formato_brasileiro_com_milhar(self):
        assert parse_decimal("1.234,56") == Decimal("1234.56")

    def test_string_vazia_retorna_zero(self):
        assert parse_decimal("") == Decimal("0")

    def test_none_retorna_zero(self):
        assert parse_decimal(None) == Decimal("0")

    def test_espacos_sao_removidos(self):
        assert parse_decimal("  100,50  ") == Decimal("100.50")

    def test_limitacao_conhecida_ponto_como_milhar_sem_decimal(self):
        """Limitação documentada em core.py: "1.234" sem vírgula é
        interpretado como Decimal("1.234") (1 vírgula 234), NÃO como
        1234 (mil duzentos e trinta e quatro). Este teste existe para
        que, se o comportamento mudar no futuro, a mudança seja
        intencional e visível aqui -- não uma regressão silenciosa."""
        assert parse_decimal("1.234") == Decimal("1.234")


# ---------------------------------------------------------------------------
# money / dias_corridos
# ---------------------------------------------------------------------------

class TestMoney:
    def test_arredonda_para_cima_no_meio(self):
        # ROUND_HALF_UP: 0.005 -> 0.01, não 0.00 (diferente do padrão
        # bancário ROUND_HALF_EVEN)
        assert money(Decimal("10.005")) == Decimal("10.01")

    def test_arredonda_para_baixo(self):
        assert money(Decimal("10.001")) == Decimal("10.00")


class TestDiasCorridos:
    def test_dias_positivos(self):
        base = datetime(2026, 2, 10)
        venc = datetime(2026, 2, 20)
        assert dias_corridos(venc, base) == 10

    def test_vencimento_antes_da_base_nao_fica_negativo(self):
        base = datetime(2026, 2, 10)
        venc = datetime(2026, 1, 1)
        assert dias_corridos(venc, base) == 0


# ---------------------------------------------------------------------------
# calcular_desagio_titulo
# ---------------------------------------------------------------------------

class TestCalcularDesagioTitulo:
    def test_desagio_de_um_titulo(self):
        d = calcular_desagio_titulo(
            bruto=Decimal("1000.00"), dias=10, dmu=Decimal("4"),
            taxa_mensal=Decimal("0.02"),
        )
        assert d == Decimal("11.22")

    def test_desagio_zero_quando_bruto_zero(self):
        d = calcular_desagio_titulo(
            bruto=Decimal("0.00"), dias=10, dmu=Decimal("4"),
            taxa_mensal=Decimal("0.02"),
        )
        assert d == Decimal("0.00")


# ---------------------------------------------------------------------------
# calcular_totais — casos de regressão (valores conferidos manualmente)
# ---------------------------------------------------------------------------

class TestCalcularTotais:
    def test_titulo_unico_abaixo_do_limite_de_retencao(self):
        titulos = [{"bruto": Decimal("1000.00"), "dias": 10}]
        tot = calcular_totais(titulos, taxa_mensal_pct=Decimal("2.0"), dmu=Decimal("4"))

        assert tot["bruto"] == Decimal("1000.00")
        assert tot["desagio"] == Decimal("11.22")
        assert tot["serv"] == Decimal("10.00")
        assert tot["pis"] == Decimal("0.21")
        assert tot["cofins"] == Decimal("0.99")
        assert tot["iss"] == Decimal("0.20")
        assert tot["impostos"] == Decimal("1.40")
        assert tot["fator_total"] == Decimal("12.62")
        assert tot["retido"] == Decimal("0.00")   # abaixo do limite -> sem retenção
        assert tot["liquido"] == Decimal("977.38")
        assert tot["liq_ret"] == Decimal("977.38")

    def test_titulo_acima_do_limite_aplica_retencao_fixa(self):
        titulos = [{"bruto": Decimal("120000.00"), "dias": 20}]
        tot = calcular_totais(titulos, taxa_mensal_pct=Decimal("1.5"), dmu=Decimal("4"))

        assert tot["bruto"] > RETIDO_LIMITE
        assert tot["retido"] == RETIDO_FIXO
        assert tot["liq_ret"] == tot["liquido"] + RETIDO_FIXO

    def test_retencao_nao_se_aplica_exatamente_no_limite(self):
        """Regra é > (estritamente maior), não >=. Um bruto exatamente
        igual ao limite NÃO deve sofrer retenção."""
        titulos = [{"bruto": Decimal("100000.00"), "dias": 10}]
        tot = calcular_totais(titulos, taxa_mensal_pct=Decimal("2.0"), dmu=Decimal("4"))
        assert tot["retido"] == Decimal("0.00")

    def test_multiplos_titulos_somam_bruto_e_desagio_individualmente(self):
        """Cada título tem seu próprio deságio (dias diferentes), e o
        deságio total deve ser a SOMA dos deságios já arredondados
        individualmente -- não o deságio calculado sobre o bruto total.
        Isso evita erro de arredondamento acumulado incorreto."""
        titulos = [
            {"bruto": Decimal("1000.00"), "dias": 10},
            {"bruto": Decimal("2000.00"), "dias": 25},
        ]
        tot = calcular_totais(titulos, taxa_mensal_pct=Decimal("2.0"), dmu=Decimal("4"))

        assert tot["bruto"] == Decimal("3000.00")
        soma_individual = sum(tot["desagios_por_titulo"])
        assert tot["desagio"] == soma_individual

    def test_lista_vazia_de_titulos_nao_quebra(self):
        tot = calcular_totais([], taxa_mensal_pct=Decimal("2.0"), dmu=Decimal("4"))
        assert tot["bruto"] == Decimal("0.00")
        assert tot["liquido"] == Decimal("0.00")
