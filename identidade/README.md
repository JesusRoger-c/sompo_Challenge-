# Identidade visual — SomPrev Risk

Kit de marca do projeto: o logo, as cores, as fontes e as artes do estande do NEXT.
Tudo em vetor, com o texto já convertido em curvas — a gráfica não precisa de
nenhuma fonte instalada para abrir os arquivos.

## O símbolo

O **O** de S**o**mPrev é uma roda de trator vista de frente, com um broto de duas
folhas saindo por trás dela. É a ideia do produto em um desenho: a máquina que
continua rodando porque o risco foi previsto antes. A roda é grafite, o aro é
amarelo e o broto é verde.

## Cores

| Uso | Nome | Hex |
| --- | --- | --- |
| Marca, menu lateral, botão primário | Amarelo institucional | `#FFC400` |
| Hover, bordas do amarelo | Amarelo escuro | `#E0A500` |
| Acento escuro sobre fundo claro (texto, linha de gráfico) | Âmbar profundo | `#A06A00` |
| Tinta principal, pneu do símbolo | Grafite | `#17160F` |
| Broto do símbolo | Verde marca | `#1A7048` |
| Fundo da aplicação | Papel | `#FBFAF5` |

As quatro cores da escala de risco (`#2E9E5B` · `#E8B800` · `#E8761B` · `#C20A14`)
ficam em `src/somprev/tema.py` e **não** fazem parte da marca.

**A regra que não se quebra:** a cor da marca nunca representa risco. O amarelo
institucional só aparece na moldura do produto — barra, menu, botão, foco,
assinatura. Dentro de gráfico, KPI ou alerta, nunca. Sem isso ninguém distingue
"isto é da SomPrev" de "isto está em atenção".

## Fontes

Manrope ExtraBold nos títulos, IBM Plex Sans no texto e IBM Plex Mono nos números.
Ambas sob SIL Open Font License 1.1. O dashboard carrega versões reduzidas
embutidas no próprio código (`src/somprev/dashboard/fontes.py`), então abre
idêntico mesmo sem internet — o que importa no notebook emprestado do evento.

## Como escolher a versão do logo

| Situação | Arquivo |
| --- | --- |
| Fundo claro, uso geral | `logo/somprev-horizontal` |
| Fundo grafite ou camiseta preta | `logo/somprev-horizontal-negativo` |
| Sobre um bloco amarelo | `logo/somprev-horizontal-sobre-amarelo` |
| Assinatura principal (site, crachá, capa) | `logo/somprev-empilhado` |
| Uma cor só (bordado, carimbo, gravação) | `logo/somprev-horizontal-mono-grafite` ou `-mono-branco` |
| Avatar, favicon, perfil | `logo/somprev-icone` |
| Selo isolado, sem o nome | `logo/somprev-simbolo` |

**Respiro:** deixe em volta do logo, livre de qualquer outro elemento, uma
margem igual à altura da roda. **Tamanho mínimo:** 26 mm de largura no impresso e
120 px na tela — abaixo disso o broto some.

**O que não fazer:** não mude as cores, não incline, não aplique sombra ou
contorno, não troque a fonte do nome, não use o símbolo colorido sobre fundo
colorido e não coloque o logo em cima de foto sem um bloco sólido atrás.

## Peças do estande

Todas em PDF (pronto para a gráfica), SVG (editável) e PNG (para visualizar).

| Peça | Formato final | Observações |
| --- | --- | --- |
| `pecas/cartao-semente-frente` e `-verso` | 90 × 50 mm | sangria de 3 mm e marcas de corte já incluídas; papel-semente |
| `pecas/model-card-frente` e `-verso` | 85,6 × 54 mm (CR80) | sangria de 2 mm; PVC 0,76 mm, impressão 4×4 |
| `pecas/camiseta-frente-peito` | 220 mm de largura | fundo transparente, 100 mm abaixo da gola |
| `pecas/camiseta-costas` | 280 mm de largura | marca + FIAP em branco, 320 mm abaixo da gola |
| `pecas/camiseta-mockup` | — | folha de medidas para mandar junto com a arte |

A camiseta é preta, com impressão DTF ou transfer digital: para quatro peças sai
mais barato que silk e não limita o número de cores.

Os números do model card vêm de `src/models/model_card.json` e mudam se o
pipeline for rodado de novo. Confira antes de mandar imprimir:
`python scripts/run.py pipeline` e depois regere a peça.

## Sobre a menção à Sompo

Não há nenhuma menção à Sompo nas peças do estande nem na tela de entrada do
dashboard: nem logo, nem o nome em texto. O rodapé das peças assina
"Challenge FIAP · NEXT 2026". O nome continua aparecendo na documentação do
projeto (README, model card, relatórios), que é entrega acadêmica e não material
de estande.

## Por que o model card não começa com "hgb-v2.0"

Porque ninguém que passa pelo estande sabe o que é isso. A frente do cartão abre
com o que o modelo entrega — *90% dos sinistros são avisados antes de acontecer* —
e a identificação técnica (`hgb-v2.0 · HistGradientBoosting · 12 variáveis`) fica
na linha de rodapé, para quem for procurar.

A precisão (32% dos alertas viram sinistro) **não** está na frente de propósito:
sem contexto ela lê como "erra duas de cada três". O motivo está no verso — o
limiar foi escolhido pelo menor custo esperado e prioriza não deixar sinistro
passar — e o resto é conversa ao vivo.
