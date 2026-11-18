"""Acceso compartido para probadores; no es autorizacion sobre pedidos reales."""

import os
import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials

basic = HTTPBasic(auto_error=False, realm="Demo de soporte")


def cargar_acceso() -> tuple[str, str] | None:
    usuario = os.getenv("DEMO_USUARIO", "").strip()
    clave = os.getenv("DEMO_CLAVE", "")
    if (usuario or clave) and (not usuario or not clave.strip()):
        raise RuntimeError("Configura DEMO_USUARIO y DEMO_CLAVE juntos.")
    if not usuario:
        if os.getenv("RENDER", "").strip().lower() == "true":
            raise RuntimeError("En Render se requieren DEMO_USUARIO y DEMO_CLAVE.")
        return None
    return usuario, clave


def verificar_acceso(
    request: Request,
    credenciales: Annotated[HTTPBasicCredentials | None, Depends(basic)],
):
    acceso = request.app.state.acceso
    if acceso is None:
        return
    if credenciales is not None:
        usuario_valido = secrets.compare_digest(credenciales.username.encode("utf-8"), acceso[0].encode("utf-8"))
        clave_valida = secrets.compare_digest(credenciales.password.encode("utf-8"), acceso[1].encode("utf-8"))
        if usuario_valido and clave_valida:
            return
    raise HTTPException(status_code=401, detail="Acceso no autorizado.",
                        headers={"WWW-Authenticate": 'Basic realm="Demo de soporte"'})
