import asyncio
import json
import logging
import re
import subprocess
from pathlib import Path

log = logging.getLogger("kaggle")


def _kaggle(*args: str) -> str:
    """Ejecuta el CLI de kaggle (el venv con kaggle debe estar activo)."""
    r = subprocess.run(["kaggle", *args], capture_output=True, text=True)
    if r.returncode != 0:
        detalle = r.stderr.strip() or r.stdout.strip()
        raise RuntimeError(f"kaggle {' '.join(args)} falló: {detalle}")
    return r.stdout


async def ejecutar_kernel(
    carpeta: str | Path,
    kernel_id: str,
    salida: str | Path = "resultado",
    sondeo: int = 10,
    timeout: int = 3600,
) -> str:
    """Sube el kernel, espera a que termine y devuelve lo que imprimió (stdout)."""
    loop = asyncio.get_running_loop()

    await asyncio.to_thread(_kaggle, "kernels", "push", "-p", str(carpeta))
    log.info("%s subido", kernel_id)

    inicio = loop.time()
    while True:
        await asyncio.sleep(sondeo)
        estado = await asyncio.to_thread(_kaggle, "kernels", "status", kernel_id)
        log.info(estado.strip())
        if "COMPLETE" in estado:
            break
        if re.search("ERROR|CANCEL", estado):
            raise RuntimeError(f"El kernel terminó mal: {estado.strip()}")
        if loop.time() - inicio > timeout:
            raise TimeoutError(f"{kernel_id} superó {timeout}s")

    await asyncio.to_thread(_kaggle, "kernels", "output", kernel_id, "-p", str(salida))
    archivo = Path(salida) / f"{kernel_id.split('/')[1]}.log"
    registros = json.loads(archivo.read_text(encoding="utf-8"))
    return "".join(r["data"] for r in registros if r["stream_name"] == "stdout")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    texto = asyncio.run(
        ejecutar_kernel("kaggle/prueba", "andresalmanza/prueba-orquestador")
    )
    print(texto)
