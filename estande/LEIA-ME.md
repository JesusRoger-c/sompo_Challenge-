# A demonstração do estande — SomPrev Risk · NEXT 2026

O visitante inclina o trator, o score muda na tela, a apólice sai na impressora.
Esta pasta tem as três peças que fazem isso acontecer.

| Arquivo | O que é |
| --- | --- |
| `firmware/somprev_sensor/somprev_sensor.ino` | Código do ESP32: lê o sensor e publica o ângulo numa rede Wi-Fi própria |
| `placar.py` | Servidor que serve a tela e pergunta o score ao modelo de verdade |
| `placar.html` | A tela que fica virada para o visitante |
| `conferir_cenarios.py` | Confere em 20 s se a demonstração ainda atravessa as faixas |
| `apolice.py` *(na pasta do kit)* | Imprime a apólice do visitante na térmica |

---

## Como tudo se liga

```
  MPU6050 no trator
        │ I2C (4 jumpers)
     ESP32  ──── cria a rede Wi-Fi "SomPrev-Risk" ────┐
        │ (alimentado pela power bank)                │
        └── http://192.168.4.1/dados → o ângulo       │
                                                      ▼
                                          notebook conectado nessa rede
                                                      │
                                      placar.html ──► placar.py ──► API do projeto
                                      (a tela)         (guarda a chave)   (modelo real)
```

**Por que rede própria do ESP32 e não o hotspot do celular:** numa feira o Wi-Fi
é a primeira coisa a falhar. Assim a demonstração não depende de internet, de
roteador, nem do celular de ninguém. A API roda em `localhost`, que funciona sem
rede nenhuma.

---

## Ligação do sensor (4 jumpers fêmea-fêmea)

| MPU6050 | ESP32 |
| --- | --- |
| VCC | **3V3** (nunca 5 V) |
| GND | GND |
| SCL | GPIO **22** |
| SDA | GPIO **21** |

Monte o diorama **nivelado** e só então ligue o ESP32 — a primeira leitura vira o
"zero". Dá para corrigir depois abrindo `http://192.168.4.1/zerar`.

---

## Gravar o firmware (uma vez, na segunda ou terça)

1. Arduino IDE → Preferências → URL adicional de placas:
   `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
2. Ferramentas → Placa → **ESP32 Dev Module**
3. Plugue o ESP32 no Mac com cabo **USB-C para USB-C** e escolha a porta.
   Se a porta não aparecer, instale o driver **CP210x da Silicon Labs**.
4. Abra `somprev_sensor.ino` e clique em gravar.

Não precisa instalar biblioteca nenhuma — o MPU6050 é lido direto, com o que já
vem no core do ESP32. Menos biblioteca, menos coisa para quebrar na véspera.

---

## Subir a demonstração (todo dia que for testar)

```bash
# 1. a API do projeto
python scripts/run.py api

# 2. a chave de ingestão (a mesma que a API usa)
export SOMPREV_API_KEY="...a sua chave..."

# 3. o placar
python estande/placar.py
```

Abra **http://localhost:8800** e deixe em tela cheia (F11 / Ctrl+Cmd+F).

No notebook, conecte-se à rede **SomPrev-Risk** (senha `somprev2026`).

---

## Os três cenários — e por que eles existem

Testando contra o modelo real ficou claro que **a inclinação sozinha move o score
de 10 a 20 pontos**, não de Baixo a Crítico. Isso não é defeito: o modelo pesa 12
variáveis e não é um espelho do sensor. Em vez de maquiar, a demonstração usa
três contextos declarados — e o argumento fica mais forte:

| Cenário | 0° | 25° | O que ele mostra |
| --- | --- | --- | --- |
| 1. Dia seco, máquina nova | 5 Baixo | 15 Médio | o declive sozinho muda pouco |
| 2. Depois da chuva | 26 Médio | 59 Alto | **o mesmo declive, com solo molhado, muda de faixa** |
| 3. Chuva forte + manutenção vencida | 77 Crítico | 92 Crítico | já está crítico parado; o declive só piora |

Troque de cenário com as teclas **1, 2, 3** ou clicando nos botões.

O cenário 2 é o da conversa: incline o trator, o número pula de 26 para 59 e a
faixa vira Alto. Depois aperte 1 e repita a mesma inclinação — quase nada
acontece. **É o projeto inteiro explicado em 30 segundos: risco é a combinação,
não uma variável.**

Os números acima vieram do modelo. Para conferir que continuam valendo:

```bash
python estande/conferir_cenarios.py
```

Rode isso **depois de qualquer `run.py pipeline`**. Se o modelo for retreinado e
um cenário parar de atravessar a faixa, o script avisa — e é melhor descobrir na
terça do que na frente do avaliador.

---

## O seguro: modo manual

Se o sensor cair no meio da feira, a tela entra sozinha em **modo manual** depois
de ~2 segundos e você controla a inclinação com as **setas ↑ ↓** ou arrastando a
barra. A conversa continua e ninguém percebe a diferença.

Para forçar o modo manual a qualquer momento, aperte **M**.

---

## Se der errado

| Sintoma | Causa provável |
| --- | --- |
| "procurando o sensor…" não sai | O notebook não está na rede `SomPrev-Risk` |
| "ESP32 ok, MPU6050 mudo" | Um dos 4 jumpers soltou — confira o 3V3 e o GND |
| "Placar sem resposta do servidor" | O `placar.py` não está rodando |
| "Falta a chave" | Faltou o `export SOMPREV_API_KEY` **antes** de subir o placar |
| "API não respondeu" | Faltou subir `python scripts/run.py api` |
| Ângulo nunca volta a zero | Abra `http://192.168.4.1/zerar` com o diorama nivelado |

---

## Detalhe que vale citar se perguntarem

A chave da API fica no `placar.py`, **nunca** dentro do HTML. O projeto defende
chaves com escopo, limite de taxa e auditoria — deixar a chave numa página aberta
no notebook da bancada contradiria exatamente isso. Cada inclinação vira uma
leitura real, com trilha de auditoria, e aparece no dashboard como qualquer outra.
