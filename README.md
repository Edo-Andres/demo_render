# Demo de soporte de pedidos

Aplicacion web con FastAPI, Google ADK y Gemini para consultar pedidos ficticios,
resumir importes y responder sobre envios, devoluciones y atencion con fuentes.
Cada consulta es independiente. No modifica pedidos ni realiza acciones comerciales.

## Estructura

- app/: API, acceso HTTP Basic, HTML, CSS y JavaScript.
- soporte/: agente, herramientas, contratos y recuperacion semantica.
- soporte/data/: CSV ficticio e indice documental ya generado.
- soporte/documentos/: politicas ficticias que corresponden al indice.
- tests/: pruebas HTTP, Runner, acceso y herramientas con proveedores simulados.
- pyproject.toml y uv.lock: dependencias fijadas.
- render.yaml: instalacion, arranque y variables para Render.

## Ejecutar localmente

Requiere Python 3.12 y uv.

```powershell
uv sync --locked
Copy-Item .\soporte\.env.example .\soporte\.env
```

Completar GOOGLE_API_KEY en soporte/.env. La copia del archivo se hace una sola
vez; no sobrescribir una configuracion existente. Para exigir acceso tambien en
local, completar juntos DEMO_USUARIO y DEMO_CLAVE. Nunca subir .env a Git.

```powershell
uv run uvicorn app.main:app --reload --port 8001
```

Abrir http://127.0.0.1:8001/. Ejemplos:

- Cuanto demora el envio estandar?
- Cual es el estado de PED-1001?
- Cuantos pedidos estan en camino?

Las consultas reales consumen Gemini y, al buscar documentos, embeddings.
El indice de documentos ya esta preparado; no se regenera al iniciar.
Los fragmentos consultados son candidatos y pueden incluir contexto adicional.
No editar documentos o vectores por separado.

## Pruebas locales

```powershell
uv run python -B -m unittest discover -s tests
```

No requieren API key ni llaman a Gemini. Una prueba simulada no valida la calidad
de las respuestas reales ni sustituye la comprobacion del despliegue.

## Desplegar en Render

1. Publicar este repositorio en GitHub; puede ser privado si se concede acceso a Render.
2. En Render, crear un Blueprint conectado a este repositorio y su render.yaml.
3. Completar GOOGLE_API_KEY, DEMO_USUARIO y DEMO_CLAVE en el formulario inicial.
   Los valores se almacenan en Render; no se escriben en render.yaml.
4. Revisar el plan Free y crear el servicio.
5. Esperar a que el build y el arranque finalicen; comprobar la URL publicada.

La configuracion fija Python 3.12.4 y uv 0.7.13. Instala mediante
`uv sync --locked --no-dev` y arranca con:

```sh
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Este comando es para Linux/Render. PORT y RENDER los proporciona la plataforma.
Los despliegues posteriores son manuales (autoDeployTrigger: off).
Para cambiar secretos: servicio -> Environment -> editar -> Save and deploy.

Comprobar despues del despliegue:

- /health devuelve status ok sin credenciales y sin llamadas a modelos.
- / pide las credenciales elegidas; /docs y POST /consultas tambien estan protegidos.
- Una pregunta sobre envios devuelve respuesta y fuentes; contrastar con la politica.
- Una consulta a PED-1001 coincide con el CSV; una entrada vacia se rechaza.

El acceso es compartido para probadores; no verifica propiedad de pedidos.
Las sesiones son temporales; no hay base de datos persistente ni historial entre
consultas. En Free, tras inactividad, el primer acceso puede esperar el arranque;
los cambios locales se pierden al reiniciar. Las cuotas o costos de Gemini son
independientes del plan del servidor.

Referencias: [Blueprints](https://render.com/docs/blueprint-spec),
[variables](https://render.com/docs/configure-environment-variables),
[plan Free](https://render.com/docs/free).
