# 🌎 Contextualização do Problema (com dados e fontes)

Esta seção complementa o README com **números de mercado, custos e sinistralidade**
e **fontes referenciadas**, atendendo ao ponto levantado no feedback da Sprint 1.

## O mercado de seguro rural no Brasil

O seguro rural movimenta cifras expressivas e é estratégico para o agronegócio.
Em 2024, o Programa de Subvenção ao Prêmio do Seguro Rural (PSR) cobriu cerca de
**6,3 milhões de hectares**, com **valor total segurado em torno de R$ 45 bilhões**;
soja, milho de 2ª safra, café, trigo e pecuária foram as atividades que mais
demandaram recursos (Ministério da Agricultura e Pecuária / Agência Gov, dez. 2024).

A demanda, porém, é instável: a área segurada caiu de cerca de **14 milhões de
hectares em 2021 para 6,3 milhões em 2023**, e o número de apólices subvencionadas
recuou de **217,9 mil para 107,4 mil** no mesmo período, segundo dados do Comitê
Gestor do Seguro Rural divulgados pelo SindsegSP. Atualmente, **17 seguradoras**
estão habilitadas a operar no programa.

A concentração do risco em poucas culturas amplia a exposição das seguradoras: a
soja sozinha responde por **29,4% do valor bruto da produção agropecuária**
brasileira (Revista de Economia e Sociologia Rural, dez. 2024), e enfrenta forte
exposição a intempéries climáticas — justamente o tipo de risco que uma análise
preditiva ajuda a antecipar.

## O custo humano e operacional dos acidentes

O Brasil registra o **maior número de fatalidades com tratores e implementos
agrícolas** do mundo: estima-se **cerca de 3 mil mortes por ano**, e a cada três
acidentes um causa incapacidade permanente ao trabalhador (Canal Rural).

Esses acidentes estão fortemente ligados a **terreno e condições operacionais**:
- Um estudo no Rio Grande do Sul (Tecno-Lógica, 2021) analisou 60 acidentes com
  tratores e concluiu que o **óbito do operador ocorreu em 45% dos casos**, em
  decorrência de **capotamento ou tombamento** da máquina.
- O mesmo estudo aponta que **96,8% dos acidentes poderiam ter sido evitados por
  prevenção** — o argumento central a favor de uma solução **preventiva** como o
  SomPrev Risk.
- Em outra caracterização (SciELO/Ciência Rural), o **capotamento respondeu por
  51,7% dos acidentes graves** com tratores.
- A literatura de segurança (NIOSH, citada pela Revista Cultivar) estima que
  estruturas de proteção contra capotamento somadas ao cinto reduziriam as lesões
  por tombamento em **cerca de 70%**.

## Por que isso importa para a solução

Os dados acima sustentam três decisões de projeto:

1. **Mudar de reativo para preventivo.** Se quase todos os acidentes são evitáveis,
   um score que antecipa o risco antes da operação ataca a raiz do problema.
2. **Priorizar variáveis de terreno e clima.** Tombamento/capotamento — principal
   mecanismo fatal — está ligado a declividade, umidade do solo e proximidade de
   água, que são exatamente as variáveis centrais do nosso modelo.
3. **Garantir rastreabilidade para a seguradora.** Em um mercado com R$ 45 bi
   segurados e poucas operadoras, histórico auditável e previsibilidade reduzem
   seleção adversa e perdas — daí a tabela `predicoes` versionada no banco.

## Fontes

- Ministério da Agricultura e Pecuária (Mapa) / Agência Gov — *Balanço: Mapa fecha
  2024 com maior Plano Safra da história* (dez. 2024).
  https://agenciagov.ebc.com.br/noticias/202412/mapa-fecha-2024-com-maior-plano-safra-da-historia-e-avancos-das-politicas-agricolas-para-o-agro-brasileiro
- SindsegSP — *Comitê aprova distribuição de R$ 947,5 milhões para seguro rural em 2024*.
  https://www.sindsegsp.org.br/site/noticia-texto.aspx?id=36134
- Revista de Economia e Sociologia Rural (vol. 63, dez. 2024) — *Seguro agrícola na
  lavoura de soja: fatores de impacto nos resultados das seguradoras*.
  https://doi.org/10.1590/1806-9479.2025.284948
- Canal Rural — *Brasil tem o maior número de fatalidades com tratores e implementos
  agrícolas no campo*.
  https://www.canalrural.com.br/agricultura/brasil-tem-maior-numero-fatalidades-com-tratores-implementos-agricolas-campo-33494/
- Tecno-Lógica (UNISC, v. 25, n. 2, 2021) — *Diagnóstico de acidentes de trabalho com
  tratores agrícolas no Estado do Rio Grande do Sul, Brasil*.
  https://online.unisc.br/seer/index.php/tecnologica/article/view/16397
- Ciência Rural (SciELO) — *Caracterização dos acidentes com tratores agrícolas*.
  https://www.scielo.br/j/cr/a/gpNTSnRTSkXhBdqYNZvKPTN/?lang=pt
- Revista Cultivar — *Acidentes com tratores agrícolas* (estimativa NIOSH).
  https://revistacultivar.com.br/artigos/acidentes-com-tratores-agricolas

> Observação acadêmica: os **dados operacionais** usados no modelo são **simulados**
> (uso permitido pelo enunciado), mas foram calibrados para refletir o comportamento
> descrito por essas fontes — terreno, clima e manutenção como principais vetores de risco.
