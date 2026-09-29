-- =============================================================================
--  SomPrev Risk | Esquema do banco de dados (SQLite) - versao final (Sprint 4)
--  Challenge FIAP + Sompo Seguros
-- =============================================================================
--  Evolucao em relacao a Sprint 3:
--    * CHECK constraints: o proprio banco recusa valores impossiveis
--      (score fora de 0-100, faixa inexistente, status de alerta invalido...).
--    * leituras: origem, status de qualidade e hash SHA-256 do payload recebido
--      (prova de integridade da entrada).
--    * leituras_quarentena: leituras rejeitadas pela qualidade de dados, com o
--      motivo - nada e descartado silenciosamente.
--    * predicoes: versao do modelo E versao das regras + explicacao (JSON).
--    * alertas: tipo, criterio que disparou, perfil de destino e ciclo de vida
--      (aberto -> reconhecido -> resolvido) com quem/quando alterou. Alertas
--      repetidos do mesmo equipamento/criterio sao agrupados (ocorrencias).
--    * usuarios: senha somente como hash PBKDF2 + controle de bloqueio.
--    * auditoria: trilha append-only (triggers impedem UPDATE/DELETE) e
--      encadeada por hash - qualquer adulteracao e detectavel.
--    * modelo_versoes e manutencoes.
--
--  Relacionamentos:
--    regioes 1--N equipamentos ; regioes 1--N leituras ; equipamentos 1--N leituras
--    leituras 1--1 predicoes ; predicoes 1--N alertas ; equipamentos 1--N manutencoes
-- =============================================================================

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS regioes (
    regiao_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT    NOT NULL UNIQUE,
    estado      TEXT    NOT NULL CHECK (length(estado) = 2),
    bioma       TEXT,
    regime      TEXT
);

CREATE TABLE IF NOT EXISTS equipamentos (
    equipamento_id          TEXT PRIMARY KEY CHECK (equipamento_id GLOB 'EQ-[0-9][0-9][0-9]'),
    modelo                  TEXT NOT NULL,
    tipo                    TEXT NOT NULL CHECK (tipo IN ('Trator', 'Colheitadeira', 'Pulverizador')),
    ano_fabricacao          INTEGER NOT NULL CHECK (ano_fabricacao BETWEEN 1980 AND 2100),
    data_fabricacao         TEXT NOT NULL,
    regiao_base_id          INTEGER NOT NULL REFERENCES regioes(regiao_id),
    intervalo_manutencao_h  INTEGER
);

CREATE TABLE IF NOT EXISTS leituras (
    leitura_id              INTEGER PRIMARY KEY,
    data_hora               TEXT    NOT NULL,
    equipamento_id          TEXT    NOT NULL REFERENCES equipamentos(equipamento_id),
    regiao_id               INTEGER NOT NULL REFERENCES regioes(regiao_id),
    umidade_solo_pct        REAL    NOT NULL CHECK (umidade_solo_pct BETWEEN 0 AND 100),
    precipitacao_24h_mm     REAL    NOT NULL CHECK (precipitacao_24h_mm >= 0),
    temperatura_c           REAL    NOT NULL,
    tipo_solo               TEXT    NOT NULL CHECK (tipo_solo IN ('Arenoso', 'Misto', 'Argiloso', 'Encharcado')),
    declividade_graus       REAL    NOT NULL CHECK (declividade_graus >= 0),
    distancia_corpo_dagua_m REAL    NOT NULL CHECK (distancia_corpo_dagua_m >= 0),
    tipo_operacao           TEXT    NOT NULL CHECK (tipo_operacao IN ('Plantio', 'Pulverizacao', 'Colheita', 'Transporte')),
    idade_equipamento_anos  REAL    NOT NULL CHECK (idade_equipamento_anos >= 0),
    horas_desde_manutencao  REAL    NOT NULL CHECK (horas_desde_manutencao >= 0),
    horas_operacao_dia      REAL    NOT NULL CHECK (horas_operacao_dia BETWEEN 0 AND 24),
    carga_pct               REAL    NOT NULL CHECK (carga_pct >= 0),
    periodo_dia             TEXT    NOT NULL CHECK (periodo_dia IN ('Manha', 'Tarde', 'Noite')),
    houve_sinistro          INTEGER CHECK (houve_sinistro IN (0, 1)),   -- NULL = ainda nao apurado
    origem                  TEXT    NOT NULL DEFAULT 'carga_historica'
                                    CHECK (origem IN ('carga_historica', 'api', 'simulador')),
    qualidade_status        TEXT    NOT NULL DEFAULT 'OK' CHECK (qualidade_status IN ('OK', 'CORRIGIDO')),
    qualidade_obs           TEXT,
    hash_payload            TEXT,
    recebido_em             TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (equipamento_id, data_hora)          -- impede reenvio da mesma medicao
);

CREATE TABLE IF NOT EXISTS leituras_quarentena (
    quarentena_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    recebido_em     TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    origem          TEXT NOT NULL,
    leitura_id      INTEGER,
    equipamento_id  TEXT,
    data_hora       TEXT,
    motivo          TEXT NOT NULL,
    payload_json    TEXT
);

CREATE TABLE IF NOT EXISTS modelo_versoes (
    versao          TEXT PRIMARY KEY,
    algoritmo       TEXT NOT NULL,
    treinado_em     TEXT NOT NULL,
    hash_artefato   TEXT NOT NULL,
    metricas_json   TEXT NOT NULL,
    ativo           INTEGER NOT NULL DEFAULT 0 CHECK (ativo IN (0, 1))
);

CREATE TABLE IF NOT EXISTS predicoes (
    predicao_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    leitura_id      INTEGER NOT NULL UNIQUE REFERENCES leituras(leitura_id),
    score_risco     INTEGER NOT NULL CHECK (score_risco BETWEEN 0 AND 100),
    classe_risco    TEXT    NOT NULL CHECK (classe_risco IN ('Baixo', 'Medio', 'Alto', 'Critico')),
    prob_sinistro   REAL    NOT NULL CHECK (prob_sinistro BETWEEN 0 AND 1),
    fator_1         TEXT,
    fator_2         TEXT,
    fator_3         TEXT,
    explicacao_json TEXT,
    modelo_versao   TEXT    NOT NULL,
    regras_versao   TEXT    NOT NULL,
    criado_em       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS alertas (
    alerta_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    predicao_id     INTEGER NOT NULL REFERENCES predicoes(predicao_id),
    leitura_id      INTEGER NOT NULL REFERENCES leituras(leitura_id),
    equipamento_id  TEXT    NOT NULL REFERENCES equipamentos(equipamento_id),
    tipo            TEXT    NOT NULL CHECK (tipo IN ('RISCO_MODELO', 'CONDICAO_AMBIENTAL',
                                                     'CONDICAO_OPERACIONAL', 'MANUTENCAO')),
    codigo          TEXT    NOT NULL,
    nivel           TEXT    NOT NULL CHECK (nivel IN ('Medio', 'Alto', 'Critico')),
    perfil_destino  TEXT    NOT NULL CHECK (perfil_destino IN ('Operador', 'Tecnico', 'Gestor', 'Seguradora')),
    criterio        TEXT    NOT NULL,
    mensagem        TEXT    NOT NULL,
    recomendacao    TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'aberto' CHECK (status IN ('aberto', 'reconhecido', 'resolvido')),
    ocorrencias     INTEGER NOT NULL DEFAULT 1,      -- repeticoes agrupadas (anti fadiga de alerta)
    criado_em       TEXT    NOT NULL,                -- instante da leitura que abriu o alerta
    ultima_ocorrencia TEXT  NOT NULL,
    atualizado_em   TEXT,
    atualizado_por  TEXT,
    comentario      TEXT
);

CREATE TABLE IF NOT EXISTS manutencoes (
    manutencao_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    equipamento_id  TEXT NOT NULL REFERENCES equipamentos(equipamento_id),
    alerta_id       INTEGER REFERENCES alertas(alerta_id),
    realizada_em    TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    tecnico         TEXT NOT NULL,
    descricao       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS usuarios (
    usuario_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    login               TEXT NOT NULL UNIQUE,
    nome                TEXT,
    perfil              TEXT NOT NULL CHECK (perfil IN ('Operador', 'Tecnico', 'Gestor', 'Seguradora')),
    hash_senha          TEXT NOT NULL,           -- pbkdf2_sha256$iteracoes$salt$hash
    ativo               INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
    tentativas_falhas   INTEGER NOT NULL DEFAULT 0,
    bloqueado_ate       TEXT,
    criado_em           TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    ultimo_login        TEXT
);

CREATE TABLE IF NOT EXISTS auditoria (
    auditoria_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    data_hora       TEXT NOT NULL,
    evento          TEXT NOT NULL,
    ator            TEXT NOT NULL,              -- usuario, "api:<chave>", "pipeline"
    perfil          TEXT,
    leitura_id      INTEGER,
    equipamento_id  TEXT,
    status          TEXT NOT NULL CHECK (status IN ('SUCESSO', 'FALHA', 'NEGADO', 'AVISO')),
    detalhes        TEXT,
    modelo_versao   TEXT,
    hash_anterior   TEXT NOT NULL,
    hash_registro   TEXT NOT NULL UNIQUE
);

-- Trilha append-only: nenhum evento de auditoria pode ser alterado ou apagado.
CREATE TRIGGER IF NOT EXISTS trg_auditoria_sem_update
BEFORE UPDATE ON auditoria
BEGIN
    SELECT RAISE(ABORT, 'auditoria e somente-insercao (append-only)');
END;

CREATE TRIGGER IF NOT EXISTS trg_auditoria_sem_delete
BEFORE DELETE ON auditoria
BEGIN
    SELECT RAISE(ABORT, 'auditoria e somente-insercao (append-only)');
END;

-- Visao analitica consumida por dashboard e relatorios.
CREATE VIEW IF NOT EXISTS vw_leituras_risco AS
SELECT  l.*,
        r.nome   AS regiao_nome, r.estado, r.regime,
        e.tipo   AS equip_tipo,  e.modelo AS equip_modelo,
        p.predicao_id, p.score_risco, p.classe_risco, p.prob_sinistro,
        p.fator_1, p.fator_2, p.fator_3, p.explicacao_json,
        p.modelo_versao, p.regras_versao
FROM    leituras l
JOIN    regioes r      ON r.regiao_id = l.regiao_id
JOIN    equipamentos e ON e.equipamento_id = l.equipamento_id
JOIN    predicoes p    ON p.leitura_id = l.leitura_id;

CREATE INDEX IF NOT EXISTS idx_leituras_equip_data ON leituras(equipamento_id, data_hora);
CREATE INDEX IF NOT EXISTS idx_leituras_regiao_data ON leituras(regiao_id, data_hora);
CREATE INDEX IF NOT EXISTS idx_leituras_data ON leituras(data_hora);
CREATE INDEX IF NOT EXISTS idx_predicoes_classe ON predicoes(classe_risco);
CREATE INDEX IF NOT EXISTS idx_alertas_status ON alertas(status, perfil_destino);
CREATE INDEX IF NOT EXISTS idx_alertas_equip ON alertas(equipamento_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_evento ON auditoria(evento);
CREATE INDEX IF NOT EXISTS idx_auditoria_leitura ON auditoria(leitura_id);
