-- =============================================================================
--  AgroSentinela  |  Esquema do Banco de Dados Relacional (SQLite)
--  Challenge FIAP + Sompo Seguros  -  Sprint 2
-- =============================================================================
--  Objetivo: persistir leituras de telemetria, as predicoes do modelo e os
--  alertas gerados, garantindo HISTORICO e RASTREABILIDADE para a auditoria
--  do Analista da Seguradora (User Story "analisar historico operacional").
--
--  Modelo (5 tabelas):
--    regioes 1--N equipamentos
--    regioes 1--N leituras ; equipamentos 1--N leituras
--    leituras 1--1 predicoes
--    predicoes 1--N alertas
-- =============================================================================

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS alertas;
DROP TABLE IF EXISTS predicoes;
DROP TABLE IF EXISTS leituras;
DROP TABLE IF EXISTS equipamentos;
DROP TABLE IF EXISTS regioes;

-- ----------------------------------------------------------------------------
-- Regioes onde a frota opera
-- ----------------------------------------------------------------------------
CREATE TABLE regioes (
    regiao_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT    NOT NULL UNIQUE,
    estado      TEXT    NOT NULL,
    bioma       TEXT
);

-- ----------------------------------------------------------------------------
-- Cadastro das maquinas seguradas
-- ----------------------------------------------------------------------------
CREATE TABLE equipamentos (
    equipamento_id  TEXT PRIMARY KEY,          -- ex.: EQ-001
    modelo          TEXT,
    tipo            TEXT,                       -- Trator, Colheitadeira, Pulverizador
    ano_fabricacao  INTEGER,
    regiao_base_id  INTEGER,
    FOREIGN KEY (regiao_base_id) REFERENCES regioes(regiao_id)
);

-- ----------------------------------------------------------------------------
-- Leituras de sensores + condicoes ambientais (telemetria)
--   houve_sinistro = rotulo historico usado no treino (0/1)
-- ----------------------------------------------------------------------------
CREATE TABLE leituras (
    leitura_id              INTEGER PRIMARY KEY,
    data_hora               TEXT    NOT NULL,
    equipamento_id          TEXT    NOT NULL,
    regiao_id               INTEGER NOT NULL,
    umidade_solo_pct        REAL,
    precipitacao_24h_mm     REAL,
    temperatura_c           REAL,
    tipo_solo               TEXT,
    declividade_graus       REAL,
    distancia_corpo_dagua_m REAL,
    tipo_operacao           TEXT,
    idade_equipamento_anos  REAL,
    horas_desde_manutencao  REAL,
    horas_operacao_dia      REAL,
    carga_pct               REAL,
    periodo_dia             TEXT,
    houve_sinistro          INTEGER,
    FOREIGN KEY (equipamento_id) REFERENCES equipamentos(equipamento_id),
    FOREIGN KEY (regiao_id)      REFERENCES regioes(regiao_id)
);

-- ----------------------------------------------------------------------------
-- Predicoes do modelo (resultado da IA) - 1 por leitura
--   score_risco  : 0-100 (probabilidade do modelo * 100)
--   classe_risco : Baixo | Medio | Alto | Critico
--   fator_1..3   : explicabilidade (principais causas do risco)
--   modelo_versao: rastreabilidade (qual versao gerou a predicao)
-- ----------------------------------------------------------------------------
CREATE TABLE predicoes (
    predicao_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    leitura_id      INTEGER NOT NULL,
    score_risco     INTEGER NOT NULL,
    classe_risco    TEXT    NOT NULL,
    prob_sinistro   REAL    NOT NULL,
    fator_1         TEXT,
    fator_2         TEXT,
    fator_3         TEXT,
    modelo_versao   TEXT,
    criado_em       TEXT    DEFAULT (datetime('now')),
    FOREIGN KEY (leitura_id) REFERENCES leituras(leitura_id)
);

-- ----------------------------------------------------------------------------
-- Alertas preventivos gerados a partir das predicoes de risco Alto/Critico
-- ----------------------------------------------------------------------------
CREATE TABLE alertas (
    alerta_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    predicao_id  INTEGER NOT NULL,
    nivel        TEXT    NOT NULL,            -- Alto | Critico
    mensagem     TEXT,
    recomendacao TEXT,
    status       TEXT    DEFAULT 'aberto',    -- aberto | reconhecido | resolvido
    criado_em    TEXT    DEFAULT (datetime('now')),
    FOREIGN KEY (predicao_id) REFERENCES predicoes(predicao_id)
);

-- ----------------------------------------------------------------------------
-- Indices para acelerar as consultas analiticas mais comuns
-- ----------------------------------------------------------------------------
CREATE INDEX idx_leituras_equip   ON leituras(equipamento_id);
CREATE INDEX idx_leituras_regiao  ON leituras(regiao_id);
CREATE INDEX idx_leituras_data    ON leituras(data_hora);
CREATE INDEX idx_predicoes_leit   ON predicoes(leitura_id);
CREATE INDEX idx_predicoes_classe ON predicoes(classe_risco);
CREATE INDEX idx_alertas_status   ON alertas(status);
