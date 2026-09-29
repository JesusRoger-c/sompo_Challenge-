"""
Compatibilidade com a Sprint 3.

O dashboard passou a viver em src/somprev/dashboard/ (app.py com as 4 visões e
componentes.py com estilo e gráficos). Este arquivo apenas executa o dashboard
novo, para que `streamlit run src/dashboards/app.py` continue funcionando.

Forma recomendada:  python scripts/run.py dashboard
"""

import runpy
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC))

runpy.run_path(str(SRC / "somprev" / "dashboard" / "app.py"), run_name="__main__")
