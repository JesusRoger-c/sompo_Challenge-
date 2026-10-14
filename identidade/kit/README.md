# Kit de geração da marca

Os arquivos de `identidade/logo/` e `identidade/pecas/` não são desenhados à mão:
saem destes scripts. Assim o logo é sempre idêntico, as medidas das peças ficam
em um lugar só e os números do model card vêm direto de `src/models/model_card.json`.

```bash
cd identidade/kit
pip install fonttools cairosvg qrcode pillow brotli
python export.py     # logo em todas as versões  -> ../logo/
python pecas.py      # cartão-semente e model card -> ../pecas/
python camiseta.py   # artes e folha de medidas da camiseta -> ../pecas/
```

Os scripts geram SVG. Para gerar também PDF e PNG, use `cairosvg` em cima dos SVGs.

| Arquivo | O que faz |
| --- | --- |
| `brandkit.py` | cores, conversão de texto em curvas, a roda e o broto |
| `sheet.py` | os dois travamentos do logo (horizontal e empilhado) |
| `export.py` | gera todas as versões do logo |
| `pecas.py` | cartão-semente e model card, em milímetros reais com sangria |
| `camiseta.py` | artes da camiseta e a folha de medidas |
| `fontes/` | as fontes usadas (SIL OFL 1.1 — ver LICENCAS-FONTES.md) |

As fontes `.woff2` daqui são as mesmas que `src/somprev/dashboard/fontes.py` embute
no dashboard. Para regerar aquele arquivo, refaça o subconjunto e o base64.
