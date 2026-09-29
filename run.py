#!/usr/bin/env python3
"""
SomPrev Risk — ponto de entrada unico (CLI).

Uso (a partir da raiz do repositorio):

    python run.py configurar          # cria o .env com chaves e senhas fortes (1a vez)
    python run.py pipeline            # roda TUDO do zero: dados -> qualidade -> modelo -> banco -> relatorios
    python run.py api                 # sobe o backend FastAPI em http://127.0.0.1:8000/docs
    python run.py dashboard           # sobe o dashboard Streamlit em http://localhost:8501
    python run.py simular             # envia telemetria simulada (com falhas) para a API em execucao
    python run.py verificar           # confere integridade do banco e da trilha de auditoria
    python run.py relatorio           # regenera o relatorio de tendencias
    python run.py usuario LOGIN PERFIL  # cadastra/redefine um usuario (senha pedida no terminal)
    python run.py testes              # executa a suite de testes automatizados
"""

from __future__ import annotations

import argparse
import getpass
import os
import secrets
import string
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "src"))


def _senha_forte(n: int = 16) -> str:
    alfabeto = string.ascii_letters + string.digits
    while True:
        senha = "".join(secrets.choice(alfabeto) for _ in range(n))
        if any(c.isdigit() for c in senha) and any(c.isalpha() for c in senha):
            return senha


def cmd_configurar(args) -> int:
    destino = RAIZ / ".env"
    if destino.exists() and not args.forcar:
        print(".env já existe — nada foi alterado (use --forcar para recriar).")
        return 0
    linhas = ["# Gerado por: python run.py configurar  (NÃO versionar este arquivo)",
              f"SOMPREV_API_KEY={secrets.token_urlsafe(32)}",
              f"SOMPREV_API_KEY_CONSULTA={secrets.token_urlsafe(32)}", ""]
    credenciais = []
    for perfil, login in [("OPERADOR", "operador"), ("TECNICO", "tecnico"), ("GESTOR", "gestor"),
                          ("SEGURADORA", "seguradora")]:
        senha = _senha_forte()
        linhas += [f"SOMPREV_{perfil}_USER={login}", f"SOMPREV_{perfil}_PASSWORD={senha}", ""]
        credenciais.append((perfil.title(), login, senha))
    destino.write_text("\n".join(linhas), encoding="utf-8")
    try:
        os.chmod(destino, 0o600)
    except OSError:
        pass
    print("✔ .env criado com chaves de API e senhas aleatórias fortes.\n")
    print("Credenciais de demonstração (ficam só no .env; no banco vai apenas o hash):")
    for perfil, login, senha in credenciais:
        print(f"  {perfil:<11} usuário: {login:<11} senha: {senha}")
    print("\nPróximo passo: python run.py pipeline")
    return 0


def cmd_pipeline(args) -> int:
    from somprev import pipeline
    return 0 if pipeline.executar(rapido=args.rapido, pular_treino=args.pular_treino) else 1


def cmd_api(args) -> int:
    import uvicorn
    uvicorn.run("somprev.api.app:app", host=args.host, port=args.porta, reload=False, app_dir=str(RAIZ / "src"))
    return 0


def cmd_dashboard(args) -> int:
    app = RAIZ / "src" / "somprev" / "dashboard" / "app.py"
    env = {**os.environ, "PYTHONPATH": str(RAIZ / "src") + os.pathsep + os.environ.get("PYTHONPATH", "")}
    return subprocess.call([sys.executable, "-m", "streamlit", "run", str(app), "--server.port", str(args.porta)],
                           env=env)


def cmd_simular(args) -> int:
    from somprev.servicos import simulador
    return simulador.main(quantidade=args.quantidade, url=args.url, taxa_falhas=args.taxa_falhas,
                          relatorio=not args.sem_relatorio)


def cmd_verificar(args) -> int:
    from somprev.banco.conexao import sessao
    from somprev.servicos.verificacao import verificar_sistema
    with sessao() as conn:
        itens = verificar_sistema(conn)
    for i in itens:
        print(f"{'✔' if i['ok'] else '✖'} {i['verificacao']} — {i['detalhe']}")
    return 0 if all(i["ok"] for i in itens) else 1


def cmd_relatorio(args) -> int:
    from somprev import pipeline
    pipeline.etapa_relatorios()
    return 0


def cmd_usuario(args) -> int:
    from somprev.banco.conexao import sessao, transacao
    from somprev.excecoes import SomPrevErro
    from somprev.seguranca.autenticacao import criar_usuario
    senha = getpass.getpass(f"Senha para {args.login} (12+ caracteres, letras e números): ")
    try:
        with sessao() as conn, transacao(conn):
            criar_usuario(conn, args.login, senha, args.perfil, ator="cli")
    except SomPrevErro as erro:
        print(f"✖ {erro.mensagem}")
        return 1
    print(f"✔ Usuário '{args.login}' ({args.perfil}) cadastrado.")
    return 0


def cmd_testes(args) -> int:
    return subprocess.call([sys.executable, "-m", "pytest", str(RAIZ / "tests"), "-q", *args.extra])


def main() -> int:
    parser = argparse.ArgumentParser(description="SomPrev Risk — CLI", formatter_class=argparse.RawTextHelpFormatter)
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("configurar", help="cria o .env com segredos fortes")
    p.add_argument("--forcar", action="store_true", help="recria o .env mesmo se já existir")
    p.set_defaults(func=cmd_configurar)

    p = sub.add_parser("pipeline", help="roda o fluxo completo de ponta a ponta")
    p.add_argument("--rapido", action="store_true", help="busca de hiperparâmetros reduzida")
    p.add_argument("--pular-treino", action="store_true", help="reaproveita o modelo já treinado")
    p.set_defaults(func=cmd_pipeline)

    p = sub.add_parser("api", help="sobe o backend FastAPI")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--porta", type=int, default=8000)
    p.set_defaults(func=cmd_api)

    p = sub.add_parser("dashboard", help="sobe o dashboard Streamlit")
    p.add_argument("--porta", type=int, default=8501)
    p.set_defaults(func=cmd_dashboard)

    p = sub.add_parser("simular", help="envia telemetria simulada para a API")
    p.add_argument("--quantidade", type=int, default=200)
    p.add_argument("--url", default="http://127.0.0.1:8000")
    p.add_argument("--taxa-falhas", type=float, default=0.15, help="fração de leituras com defeito")
    p.add_argument("--sem-relatorio", action="store_true")
    p.set_defaults(func=cmd_simular)

    sub.add_parser("verificar", help="verifica integridade e consistência").set_defaults(func=cmd_verificar)
    sub.add_parser("relatorio", help="regenera o relatório de tendências").set_defaults(func=cmd_relatorio)

    p = sub.add_parser("usuario", help="cadastra/redefine um usuário")
    p.add_argument("login")
    p.add_argument("perfil", choices=["Operador", "Tecnico", "Gestor", "Seguradora"])
    p.set_defaults(func=cmd_usuario)

    p = sub.add_parser("testes", help="executa os testes automatizados")
    p.add_argument("extra", nargs="*")
    p.set_defaults(func=cmd_testes)

    args = parser.parse_args()
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nInterrompido pelo usuário.")
        return 130
    except Exception as erro:  # erro inesperado: mensagem clara + detalhe no log
        from somprev.excecoes import SomPrevErro
        if isinstance(erro, SomPrevErro):
            print(f"✖ {erro.mensagem}")
            return 1
        from somprev.logs import obter_logger
        obter_logger("cli").exception("Falha inesperada no comando %s", args.comando)
        print(f"✖ Falha inesperada em '{args.comando}': {erro}\n  Detalhes em logs/somprev.log")
        return 1


if __name__ == "__main__":
    sys.exit(main())
