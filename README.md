# Factoring Pro — Calculadora de Operações FinTech

Aplicação desktop/web em Python (Flet) para calcular liquidação de
títulos em operações de **Factoring**: deságio, impostos (PIS,
COFINS, ISSQN, Ad Valorem) e retenções, com geração de relatório em
PDF.

## Contexto e caso de uso

O cálculo de liquidação de títulos em Factoring exige precisão
financeira exata e conformidade tributária. A ferramenta processa
múltiplos títulos aplicando:

- **Precisão decimal extrema:** `Decimal` com 28 casas, para evitar
  os erros de arredondamento que `float` introduziria em cálculo
  financeiro.
- **Deságio proporcional:** considera data base, prazo de vencimento
  e DMU (Dias de Margem Operacional/Uso).
- **Cálculo tributário automatizado:** PIS, COFINS, ISSQN e Ad Valorem.
- **Relatório em PDF** gerado automaticamente por operação.

## Arquitetura

```
factoring-pro/
├── core.py         # regras de negócio — PURO, sem UI, testável isoladamente
├── app.py          # interface Flet — chama core.py, cuida só de I/O e apresentação
├── test_core.py    # 18 testes cobrindo parsing, arredondamento e cálculo de totais
└── requirements.txt
```

A separação `core.py` / `app.py` existe porque, originalmente, todo
o cálculo vivia dentro de closures do Flet — impossível de testar sem
subir a interface gráfica inteira. Extrair para um módulo puro é o
que permite `test_core.py` existir e rodar em milissegundos, sem
depender de renderização de UI.

## Regras de negócio implementadas

1. **Deságio diário:**
   `Deságio = Bruto × TaxaMensal × ((Dias + DMU) / 24.95)`

   > O divisor `24.95` não é os 30 dias do mês civil — é uma
   > convenção operacional definida pela empresa como base de "1 mês"
   > para efeito de deságio. Documentado em `core.py` de propósito,
   > para não ser "corrigido" para 30 por engano no futuro.

2. **Serviço (Ad Valorem):** 1,00% do valor bruto do título.
3. **Encargos tributários:**
   - PIS: 1,9077% sobre o deságio
   - COFINS: 8,7862% sobre o deságio
   - ISSQN: 2,00% sobre a taxa de serviço
4. **Retenção de garantia:** valor fixo de R$ 62,71 para somatórios
   brutos **acima** de R$ 100.000,00 (limite estritamente maior, não
   maior-ou-igual).

## Limitação conhecida do parser de valores

`parse_decimal()` aceita formato brasileiro (`"1234,56"`) e formato
com ponto (`"1234.56"`), mas **não distingue** `"1.234"` como
separador de milhar (mil duzentos e trinta e quatro) de `"1.234"`
como decimal — hoje sempre interpreta como decimal. Documentado e
coberto por teste em `test_core.py` para que qualquer mudança futura
de comportamento seja intencional, não uma regressão silenciosa.
Recomendação de uso: digitar sempre sem separador de milhar.

## Como executar

### Pré-requisitos
Python 3.10+

### Passos

```bash
git clone https://github.com/L1nh0sFDC/Factoring-Pro.git
cd Factoring-Pro
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

### Rodando os testes

```bash
python -m pytest test_core.py -v   # 18 testes
```

## Funcionalidades da interface

- Cadastro dinâmico de título (valor + vencimento).
- Data base configurável (padrão: hoje) — antes fixa no código.
- Ajuste em tempo real de taxa mensal e DMU.
- Exportação do relatório completo em PDF.
- Limpeza rápida para novo cálculo.

## Tecnologias

- **[Python](https://www.python.org/)**
- **[Flet](https://flet.dev/)** — UI desktop/web
- **[ReportLab](https://www.reportlab.com/)** — geração de PDF
- **pytest** — testes da camada de negócio

## Licença

MIT.
