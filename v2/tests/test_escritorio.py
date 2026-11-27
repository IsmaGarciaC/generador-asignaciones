import asyncio
from contextlib import closing
from functools import partial
from pathlib import Path

import pytest
from nicegui.testing import user_simulation

from generador_asignaciones_v2.escritorio import mostrar_inicio
from generador_asignaciones_v2.persistencia.base_datos import BaseDatos


def test_boton_crea_y_confirma_un_respaldo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    with closing(BaseDatos(tmp_path / "programa.sqlite3")) as base:
        base.preparar()

        async def probar_boton() -> None:
            async with user_simulation(root=partial(mostrar_inicio, base.respaldar)) as usuario:
                await usuario.open("/")
                usuario.find("Crear respaldo").click()
                await usuario.should_see("Respaldo guardado en", retries=20)

        asyncio.run(probar_boton())
    assert len(list((tmp_path / "respaldos").glob("manual-*.sqlite3"))) == 1
