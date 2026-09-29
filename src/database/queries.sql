-- =============================================================================
--  SomPrev Risk | Consultas analiticas e de auditoria (SQL) - Sprint 4
-- =============================================================================
--  Rode no DB Browser for SQLite / DBeaver, ou no terminal:
--      sqlite3 src/database/somprev_risk.db < src/database/queries.sql
--  O schema completo esta em src/database/schema.sql.
-- =============================================================================

-- 1) GESTOR - tendencia semanal do risco por regiao (User Story "visualizar risco")
SELECT  strftime('%Y-%W', l.data_hora)          AS semana,
        r.nome                                   AS regiao,
        COUNT(*)                                 AS leituras,
        ROUND(AVG(p.score_risco), 1)             AS score_medio,
        ROUND(100.0 * AVG(p.classe_risco IN ('Alto', 'Critico')), 1) AS pct_alto_critico
FROM    leituras l
JOIN    regioes r   ON r.regiao_id = l.regiao_id
JOIN    predicoes p ON p.leitura_id = l.leitura_id
GROUP BY semana, r.regiao_id
ORDER BY semana, score_medio DESC;


-- 2) GESTOR - risco por tipo de operacao nos ultimos 30 dias da base
SELECT  l.tipo_operacao,
        COUNT(*)                                 AS leituras,
        ROUND(AVG(p.score_risco), 1)             AS score_medio,
        SUM(p.classe_risco = 'Critico')          AS leituras_criticas
FROM    leituras l
JOIN    predicoes p ON p.leitura_id = l.leitura_id
WHERE   l.data_hora >= (SELECT datetime(MAX(data_hora), '-30 days') FROM leituras)
GROUP BY l.tipo_operacao
ORDER BY score_medio DESC;


-- 3) GESTOR/TECNICO - ranking de equipamentos com alertas ativos
SELECT  e.equipamento_id, e.tipo, e.modelo,
        ROUND(AVG(p.score_risco), 1)             AS score_medio,
        MAX(p.score_risco)                       AS pior_score,
        (SELECT COUNT(*) FROM alertas a
          WHERE a.equipamento_id = e.equipamento_id AND a.status != 'resolvido') AS alertas_ativos
FROM    equipamentos e
JOIN    leituras l  ON l.equipamento_id = e.equipamento_id
JOIN    predicoes p ON p.leitura_id = l.leitura_id
GROUP BY e.equipamento_id
ORDER BY score_medio DESC
LIMIT 10;


-- 4) TECNICO - alertas de manutencao em aberto (fila da oficina)
SELECT  a.alerta_id, a.equipamento_id, a.codigo, a.nivel, a.criterio, a.ocorrencias,
        a.criado_em, a.ultima_ocorrencia, a.status
FROM    alertas a
WHERE   a.tipo = 'MANUTENCAO' AND a.status != 'resolvido'
ORDER BY a.nivel DESC, a.ultima_ocorrencia DESC;


-- 5) SEGURADORA - o score separa quem sofre sinistro? (taxa real por faixa)
SELECT  p.classe_risco,
        COUNT(*)                                 AS leituras,
        ROUND(100.0 * AVG(l.houve_sinistro), 1)  AS taxa_real_sinistro_pct
FROM    predicoes p
JOIN    leituras l ON l.leitura_id = p.leitura_id
WHERE   l.houve_sinistro IS NOT NULL
GROUP BY p.classe_risco
ORDER BY MIN(p.score_risco);


-- 6) SEGURADORA - rastreabilidade completa de UMA leitura (entrada -> saida -> decisao)
--    troque 1234 pelo leitura_id desejado
SELECT  l.leitura_id, l.data_hora, l.equipamento_id, l.origem, l.qualidade_status, l.qualidade_obs,
        l.hash_payload, p.score_risco, p.classe_risco, p.fator_1, p.fator_2, p.fator_3,
        p.modelo_versao, p.regras_versao
FROM    leituras l
JOIN    predicoes p ON p.leitura_id = l.leitura_id
WHERE   l.leitura_id = 1234;

SELECT  auditoria_id, data_hora, evento, ator, status, detalhes, hash_registro
FROM    auditoria
WHERE   leitura_id = 1234
ORDER BY auditoria_id;


-- 7) AUDITORIA - eventos de seguranca (logins falhos, bloqueios, acessos negados)
SELECT  data_hora, evento, ator, perfil, status, detalhes
FROM    auditoria
WHERE   evento IN ('LOGIN_FALHA', 'CONTA_BLOQUEADA', 'ACESSO_NEGADO', 'API_ACESSO_NEGADO',
                   'REGRAS_ALTERADAS')
ORDER BY auditoria_id DESC;


-- 8) QUALIDADE - motivos de quarentena (leituras rejeitadas)
SELECT  origem, motivo, COUNT(*) AS leituras
FROM    leituras_quarentena
GROUP BY origem, motivo
ORDER BY leituras DESC;


-- 9) CONSISTENCIA - leituras sem predicao (deve retornar zero linhas)
SELECT  l.leitura_id
FROM    leituras l
LEFT JOIN predicoes p ON p.leitura_id = l.leitura_id
WHERE   p.predicao_id IS NULL;
