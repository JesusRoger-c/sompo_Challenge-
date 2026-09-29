"""
SomPrev Risk - Sistema preditivo de risco operacional para frotas agricolas.
Challenge FIAP + Sompo Seguros - Sprint 4 (MVP consolidado).

Organizacao do pacote (cada modulo tem uma unica responsabilidade):

    config        caminhos, variaveis de ambiente e parametros globais
    logs          logging estruturado (JSON) com rotacao de arquivo
    excecoes      excecoes de dominio (erros previsiveis do fluxo)
    esquema       contrato de dados: variaveis, faixas validas e categorias
    regras        regras de negocio configuraveis (faixas, alertas, recomendacoes)
    dados/        geracao da telemetria simulada e tratamento de qualidade
    banco/        conexao SQLite, schema e repositorio de consultas
    modelo/       treino, avaliacao, versionamento e inferencia do modelo
    seguranca/    autenticacao, controle de acesso e auditoria encadeada
    servicos/     processamento de ponta a ponta de uma leitura
    relatorios/   tendencias de risco por equipamento, regiao e operacao
    api/          backend FastAPI
    dashboard/    interface Streamlit por perfil de usuario
    pipeline      orquestracao do fluxo completo (reprodutivel)
"""

__version__ = "4.0.0"
