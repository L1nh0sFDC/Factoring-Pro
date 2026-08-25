import flet as ft
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdf_canvas
import os

from core import calcular_totais, parse_decimal, money, fmt_brl, dias_corridos

# --------- PDF (camada de apresentação, fica aqui e não em core.py) ----------

def gerar_pdf(titulos, resumo, base_data_str, taxa_mensal_str, dmu_str):
    nome_arquivo = f"factoring_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    c = pdf_canvas.Canvas(nome_arquivo, pagesize=A4)
    w, h = A4

    y = h - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, "RELATÓRIO DE FACTORING")
    y -= 22

    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    y -= 14
    c.drawString(40, y, f"Data base: {base_data_str}")
    y -= 14
    c.drawString(40, y, f"Taxa mensal: {taxa_mensal_str}%")
    y -= 14
    c.drawString(40, y, f"DMU (dias): {dmu_str}")
    y -= 18

    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "Títulos")
    y -= 14

    c.setFont("Helvetica", 10)
    for i, t in enumerate(titulos, start=1):
        linha = (
            f"{i:02d} | Venc: {t['venc']} | Dias: {t['dias']} | "
            f"Valor: R$ {float(t['bruto']):,.2f} | "
            f"Deságio: R$ {float(t['desagio']):,.2f}"
        )
        c.drawString(40, y, linha)
        y -= 14
        if y < 120:
            c.showPage()
            y = h - 50
            c.setFont("Helvetica", 10)

    y -= 8
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Resumo")
    y -= 18

    c.setFont("Helvetica", 11)
    for label, val in resumo.items():
        c.drawString(40, y, f"{label}: {val}")
        y -= 16
        if y < 80:
            c.showPage()
            y = h - 50
            c.setFont("Helvetica", 11)

    c.showPage()
    c.save()
    return os.path.abspath(nome_arquivo)


# --------- App ----------

def main(page: ft.Page):
    page.title = "Factoring Pro"
    page.theme_mode = "dark"
    page.scroll = ft.ScrollMode.AUTO

    titulos = []

    valor_in = ft.TextField(label="Valor Nominal R$", expand=True)
    data_in = ft.TextField(label="Vencimento (DD/MM/AAAA)", expand=True)
    taxa_in = ft.TextField(label="Taxa Mensal %", value="2.0", width=160)
    dmu_in = ft.TextField(label="DMU (dias corridos)", value="4", width=200)

    base_data_in = ft.TextField(
        label="Data base (DD/MM/AAAA)",
        value=datetime.now().strftime("%d/%m/%Y"),
        width=200,
    )

    msg = ft.Text("", color="green")
    res_final = ft.Text("LÍQ+RET: R$ 0,00", size=28, color="green", weight="bold")

    body = ft.ListView(expand=True, spacing=10, padding=20)

    def get_base_data() -> datetime:
        return datetime.strptime(base_data_in.value.strip(), "%d/%m/%Y")

    def totais_atuais():
        taxa_mensal_pct = parse_decimal(taxa_in.value)
        dmu = parse_decimal(dmu_in.value)
        return calcular_totais(titulos, taxa_mensal_pct, dmu)

    def render():
        body.controls.clear()

        body.controls.append(ft.Text("Factoring Pro", size=24, weight="bold"))
        body.controls.append(ft.Row([valor_in, data_in, taxa_in, dmu_in, base_data_in]))

        body.controls.append(
            ft.Row([
                ft.ElevatedButton("Adicionar e Calcular", on_click=adicionar_titulo),
                ft.ElevatedButton("Gerar PDF", on_click=gerar_pdf_click),
                ft.OutlinedButton("Limpar", on_click=limpar),
            ])
        )

        if msg.value:
            body.controls.append(msg)

        body.controls.append(ft.Divider())

        if titulos:
            body.controls.append(ft.Text("Títulos:", weight="bold"))
            for t in titulos:
                body.controls.append(ft.Text(f"R$ {fmt_brl(t['bruto'])} | {t['venc']} ({t['dias']} dias)"))

            body.controls.append(ft.Divider())

            tot = totais_atuais()

            body.controls.append(ft.Text(f"DATA BASE: {base_data_in.value.strip()}"))
            body.controls.append(ft.Text(f"TAXA: {taxa_in.value.strip()}% ao mês"))
            body.controls.append(ft.Text(f"DMU: {dmu_in.value.strip()} (dias corridos)"))

            body.controls.append(ft.Divider())

            body.controls.append(ft.Text(f"BRUTO: R$ {fmt_brl(tot['bruto'])}"))
            body.controls.append(ft.Text(f"- FATOR (DESÁGIO): R$ {fmt_brl(tot['desagio'])}"))
            body.controls.append(ft.Text(f"SUBTOT: R$ {fmt_brl(tot['subtot'])}"))
            body.controls.append(ft.Text(f"- SERV. (1%): R$ {fmt_brl(tot['serv'])}"))
            body.controls.append(ft.Text(f"PIS: R$ {fmt_brl(tot['pis'])}"))
            body.controls.append(ft.Text(f"COFINS: R$ {fmt_brl(tot['cofins'])}"))
            body.controls.append(ft.Text(f"ISSQN: R$ {fmt_brl(tot['iss'])}"))
            body.controls.append(ft.Text(f"- IMPOSTOS: R$ {fmt_brl(tot['impostos'])}"))
            body.controls.append(ft.Text(f"- FATOR (DESÁGIO+IMP): R$ {fmt_brl(tot['fator_total'])}"))
            body.controls.append(ft.Text(f"LÍQUIDO: R$ {fmt_brl(tot['liquido'])}", color="blue", weight="bold"))
            body.controls.append(ft.Text(f"RETIDO: R$ {fmt_brl(tot['retido'])}"))
            body.controls.append(ft.Divider())
            body.controls.append(res_final)

        page.update()

    def adicionar_titulo(e):
        try:
            msg.value = ""

            bruto = money(parse_decimal(valor_in.value))
            venc = datetime.strptime(data_in.value.strip(), "%d/%m/%Y")
            base = get_base_data()
            dias = dias_corridos(venc, base)

            titulos.append({
                "bruto": bruto,
                "venc": venc.strftime("%d/%m/%Y"),
                "dias": dias,
            })

            tot = totais_atuais()
            res_final.value = f"LÍQ+RET: R$ {fmt_brl(tot['liq_ret'])}"

            valor_in.value = ""
            data_in.value = ""
            render()

        except Exception as ex:
            msg.value = f"Erro: {ex}"
            render()

    def gerar_pdf_click(e):
        if not titulos:
            msg.value = "Adicione pelo menos 1 título antes de gerar o PDF."
            render()
            return

        tot = totais_atuais()

        # anexa o deságio individual calculado a cada título, só para
        # exibição no PDF (não altera o dict usado nos cálculos)
        titulos_com_desagio = [
            {**t, "desagio": d}
            for t, d in zip(titulos, tot["desagios_por_titulo"])
        ]

        resumo = {
            "Data base": base_data_in.value.strip(),
            "Taxa mensal": f"{taxa_in.value.strip()}%",
            "DMU": f"{dmu_in.value.strip()} (dias corridos)",
            "Bruto": f"R$ {fmt_brl(tot['bruto'])}",
            "Deságio": f"R$ {fmt_brl(tot['desagio'])}",
            "Serviço (1%)": f"R$ {fmt_brl(tot['serv'])}",
            "PIS": f"R$ {fmt_brl(tot['pis'])}",
            "COFINS": f"R$ {fmt_brl(tot['cofins'])}",
            "ISSQN": f"R$ {fmt_brl(tot['iss'])}",
            "Impostos": f"R$ {fmt_brl(tot['impostos'])}",
            "Fator (Deságio+Imp)": f"R$ {fmt_brl(tot['fator_total'])}",
            "Líquido": f"R$ {fmt_brl(tot['liquido'])}",
            "Retido": f"R$ {fmt_brl(tot['retido'])}",
            "LÍQ+RET": f"R$ {fmt_brl(tot['liq_ret'])}",
        }

        caminho = gerar_pdf(
            titulos=titulos_com_desagio,
            resumo=resumo,
            base_data_str=base_data_in.value.strip(),
            taxa_mensal_str=taxa_in.value.strip(),
            dmu_str=dmu_in.value.strip(),
        )

        msg.value = f"PDF gerado em: {caminho}"
        render()

    def limpar(e):
        titulos.clear()
        valor_in.value = ""
        data_in.value = ""
        msg.value = ""
        res_final.value = "LÍQ+RET: R$ 0,00"
        render()

    page.add(body)
    render()


ft.app(target=main)
