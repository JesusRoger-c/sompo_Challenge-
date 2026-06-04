-- =============================================================================
--  AgroSentinela  |  Consultas Analiticas (SQL)
--  Challenge FIAP + Sompo Seguros  -  Sprint 2
-- =============================================================================
--  Estas queries alimentam os dashboards e atendem a auditoria do Analista da
--  Seguradora. Para rodar uma delas no terminal:
--      sqlite3 database/agrosentinela.db < database/queries.sql
--  ou abra o arquivo .db no DBeaver / DB Browser for SQLite.
-- =============================================================================


-- 1) PAINEL DA SEGURADORA: risco medio e nivel de sinistralidade por regiao
--    (areas de alta criticidade - User Story "visualizar risco")
SELECT  r.nome                              AS regiao,
        r.estado,
        COUNT(*)                            AS leituras,
        ROUND(AVG(p.score_risco), 1)        AS score_medio,
        SUM(CASE WHEN p.classe_risco IN ('Alto','Critico') THEN 1 ELSE 0 END) AS leituras_risco_alto,
        ROUND(100.0 * AVG(l.houve_sinistro), 1) AS taxa_sinistro_pct
FROM        leituras   l
JOIN        regioes    r ON r.regiao_id  = l.regiao_id
JOIN        predicoes  p ON p.leitura_id = l.leitura_id
GROUP BY    r.regiao_id
ORDER BY    score_medio DESC;


-- 2) PAINEL DO GESTOR: ranking dos equipamentos com maior risco medio
--    (User Story "equipamentos com maior incidencia")
SELECT  e.equipamento_id,
        e.modelo,
        e.tipo,
        COUNT(*)                       AS leituras,
        ROUND(AVG(p.score_risco), 1)   AS score_medio,
        MAX(p.score_risco)             AS pior_score,
        SUM(CASE WHEN p.classe_risco = 'Critico' THEN 1 ELSE 0 END) AS leituras_criticas
FROM        leituras   l
JOIN        equipamentos e ON e.equipamento_id = l.equipamento_id
JOIN        predicoes  p ON p.leitura_id = l.leitura_id
GROUP BY    e.equipamento_id
ORDER BY    score_medio DESC
LIMIT 10;


-- 3) ALERTAS ABERTOS de maior gravidade (fila de acao do Gestor/Operador)
SELECT  a.alerta_id,
        a.nivel,
        e.equipamento_id,
        r.nome                  AS regiao,
        p.score_risco,
        p.fator_1, p.fator_2, p.fator_3,
        a.recomendacao,
        l.data_hora
FROM        alertas    a
JOIN        predicoes  p ON p.predicao_id = a.predicao_id
JOIN        leituras   l ON l.leitura_id  = p.leitura_id
JOIN        equipamentos e ON e.equipamento_id = l.equipamento_id
JOIN        regioes    r ON r.regiao_id = l.regiao_id
WHERE       a.status = 'aberto'
ORDER BY    p.score_risco DESC
LIMIT 20;


-- 4) EVOLUCAO TEMPORAL do risco medio por dia (tendencia para o dashboard)
SELECT  DATE(l.data_hora)             AS dia,
        COUNT(*)                      AS leituras,
        ROUND(AVG(p.score_risco), 1)  AS score_medio,
        SUM(CASE WHEN p.classe_risco IN ('Alto','Critico') THEN 1 ELSE 0 END) AS alertas
FROM        leituras   l
JOIN        predicoes  p ON p.leitura_id = l.leitura_id
GROUP BY    DATE(l.data_hora)
ORDER BY    dia;


-- 5) AUDITORIA: fatores de risco mais frequentes como causa principal (fator_1)
--    (User Story "entender fatores de risco")
SELECT  p.fator_1                AS fator_principal,
        COUNT(*)                 AS ocorrencias,
        ROUND(AVG(p.score_risco), 1) AS score_medio
FROM        predicoes p
WHERE       p.classe_risco IN ('Alto','Critico')
GROUP BY    p.fator_1
ORDER BY    ocorrencias DESC;


-- 6) VALIDACAO DO MODELO: o score realmente separa quem teve sinistro?
--    (taxa real de sinistro observada em cada faixa de score)
SELECT  p.classe_risco,
        COUNT(*)                            AS leituras,
        SUM(l.houve_sinistro)               AS sinistros_reais,
        ROUND(100.0 * AVG(l.houve_sinistro), 1) AS taxa_sinistro_real_pct
FROM        predicoes p
JOIN        leituras  l ON l.leitura_id = p.leitura_id
GROUP BY    p.classe_risco
ORDER BY    CASE p.classe_risco WHEN 'Baixo' THEN 1 WHEN 'Medio' THEN 2
                                WHEN 'Alto' THEN 3 ELSE 4 END;


-- 7) RELACAO proximidade de agua x risco (User Story / faixas do enunciado)
SELECT  CASE
            WHEN l.distancia_corpo_dagua_m < 50   THEN '1) < 50 m (critico)'
            WHEN l.distancia_corpo_dagua_m < 200  THEN '2) 50-200 m (alto)'
            WHEN l.distancia_corpo_dagua_m < 500  THEN '3) 200-500 m (medio)'
            ELSE                                       '4) > 500 m (baixo)'
        END                                AS faixa_distancia_agua,
        COUNT(*)                           AS leituras,
        ROUND(AVG(p.score_risco), 1)       AS score_medio,
        ROUND(100.0 * AVG(l.houve_sinistro), 1) AS taxa_sinistro_pct
FROM        leituras  l
JOIN        predicoes p ON p.leitura_id = l.leitura_id
GROUP BY    faixa_distancia_agua
ORDER BY    faixa_distancia_agua;
