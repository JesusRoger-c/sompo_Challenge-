# Roteiro do estande — SomPrev Risk · NEXT 2026

A bancada está resolvida. O que decide a nota agora é a conversa. Este é o
roteiro: o que falar em 30 segundos, o que falar em 2 minutos, e as respostas
honestas para as perguntas difíceis.

**Regra única:** nunca prometer o que a gente não mediu. A força deste projeto é
que os limites estão escritos nas próprias peças. Quem avalia percebe a diferença
entre um grupo que sabe o que fez e um grupo que decorou um discurso.

---

## 1. Os 30 segundos — visitante comum

> "Pode inclinar o trator."

Deixa a pessoa inclinar. **Não fale enquanto ela mexe** — deixa o número subir
sozinho na tela, é isso que prende.

> "Esse número é o risco daquela operação agora. Subiu porque o terreno
> inclinou — mas não é só o declive: o modelo olha chuva, solo, carga e
> manutenção junto."

> "Qual seu nome?"

Imprime a apólice. Entrega na mão. **A conversa acaba com papel com o nome da
pessoa** — é o que ela leva e o que ela mostra para outra pessoa.

---

## 2. Os 2 minutos — avaliador

Mesma demonstração, mas com o **cenário 2 (Depois da chuva)** na tela, e aí você
faz a virada:

**Abre pelo problema, não pela tecnologia.**
> "Seguro de frota agrícola age depois. A máquina tomba e só então o sinistro
> existe. Só que tudo que teria evitado aquilo — o declive, o solo encharcado, a
> manutenção vencida — já estava disponível antes."

**A demonstração.** Incline. O número vai de 26 para 59, a faixa vira Alto.

**Agora a virada — esse é o momento que separa vocês dos outros estandes.**
Aperte **1** (Dia seco) e repita exatamente a mesma inclinação.
> "Mesmo declive. Quase não mexe. A diferença é que ontem não choveu."

> "É esse o ponto do projeto: risco é a combinação, não uma variável. Um sensor
> de inclinação de vinte reais faz o primeiro gráfico. Ele não sabe que choveu
> 28 milímetros ontem nem que essa máquina está com 260 horas sem revisão."

**O número que prova.**
> "No conjunto de teste, 177 operações terminaram em sinistro. O modelo avisou
> 159 delas antes. Dados de agosto, que o modelo nunca viu no treino."

**O limite, dito por você antes de perguntarem.**
> "Os dados são simulados, como o enunciado permite. Antes de uso real isso
> precisa ser recalibrado com sinistros de verdade."

**O pedido.** Entrega o resumo A4 e o kit:
> "Posso te mandar o repositório? Qual seu contato?"

---

## 3. As perguntas difíceis

### "A precisão é 32%. Dois em cada três alertas são falso positivo."

A pergunta mais provável, e a melhor de responder.

> "É verdade, e foi escolha. O limiar não foi escolhido para maximizar acerto, e
> sim pelo menor custo esperado. Um alerta errado custa uma parada preventiva. Um
> sinistro não avisado custa a máquina, a safra e às vezes a pessoa. Com o limiar
> em 0,1 a gente alerta em 51% das operações e pega 90% dos sinistros — e ainda
> perde 18 dos 177. Se a seguradora quiser menos alarme, isso é um parâmetro, não
> um retrabalho: a curva de custo por limiar está no repositório."

### "Os dados são simulados. Isso vale alguma coisa?"

> "O enunciado permite simulação, e a gente diz isso na peça impressa, não no
> rodapé. O que é real é o resto: tratamento de qualidade, treino separado no
> tempo, calibração medida, trilha de auditoria com hash, API com chave por
> escopo. Trocar o gerador por telemetria real é trocar a fonte, não a
> arquitetura."

### "Isso não é só um alarme de inclinação?"

**Não responda com palavras — responda com a tela.** Cenário 2, inclina. Cenário
1, mesma inclinação. Depois:

> "O declive sozinho move o score uns 10 pontos. O que muda a faixa é a
> combinação. E isso não foi ajustado para a demonstração: está no
> `conferir_cenarios.py`, roda contra o modelo em 20 segundos."

### "Qual o ganho financeiro para a seguradora?"

Resista a inventar número.

> "A gente não tem ROI medido, porque isso exige sinistros reais. O que dá para
> afirmar: sinistro evitado é sinistro não pago, e o score é probabilidade
> calibrada — Brier 0,081 — medida leitura a leitura, não média de carteira. O
> próximo passo honesto é um piloto de uma safra comparando operações com e sem
> alerta. Só depois disso dá para falar de precificação."

### "Como vocês sabem que não decorou os dados?"

> "Treino até 30 de junho, validação em julho, teste em agosto. Períodos
> separados no tempo, sem embaralhar — o teste só viu dado posterior a tudo. No
> teste: PR-AUC 0,76, ROC-AUC 0,88, Brier 0,081."

### "O modelo decide sozinho? Nega cobertura?"

> "Não, e isso está escrito no model card como fora de escopo. Ele apoia decisão
> preventiva: liberar, restringir ou suspender. Não nega cobertura nem precifica
> apólice sem revisão humana."

### "E se o sensor falhar no campo?"

> "A etapa de qualidade trata, imputa ou rejeita a leitura, e o que é rejeitado
> vai para quarentena em vez de virar score silencioso. Dá para mostrar no
> dashboard."

---

## 4. O que NÃO dizer

| Não diga | Por quê |
| --- | --- |
| "O modelo acerta 90%" | 90% é **recall**, não acurácia. Um avaliador técnico pega isso na hora e você perde a confiança dele no resto. |
| "Vai economizar X reais" | Não foi medido. Um número inventado derruba tudo que é verdadeiro. |
| "Está pronto para produção" | Não está, e a peça impressa diz isso. Contradizer o próprio material é pior que a limitação. |
| Citar a Sompo como cliente ou parceira | A tutoria barrou a marca nas peças. Fale "uma seguradora". |
| "É só machine learning" | Tira o valor do que vocês fizeram — o diferencial é o pipeline inteiro com auditoria. |

---

## 5. Se der errado no dia

| O que acontece | O que você diz enquanto resolve |
| --- | --- |
| Sensor cai | Aperta **M**. "Vou simular a inclinação aqui." Ninguém percebe. |
| Placar trava | Recarrega a página. O score volta na primeira inclinação. |
| Impressora não imprime | "Te mando por e-mail." Pega o contato — vale mais que o papel. |
| Travou tudo | `./estande/fechar_estande.sh` e `./estande/abrir_estande.sh`. ~40 segundos. |

---

## 6. O fechamento que faz diferença

Todo mundo entrega folheto. Quase ninguém pede o contato.

> "Posso te mandar o repositório com o modelo e a documentação? Me passa seu
> e-mail ou seu LinkedIn."

Anota na hora, no caderninho. No domingo, manda — com o nome da pessoa e uma
frase do que vocês conversaram. É isso que transforma um estande visitado em
alguém que lembra de vocês.
