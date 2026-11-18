"use strict";

const formulario = document.getElementById("consulta-form");
const pregunta = document.getElementById("pregunta");
const estado = document.getElementById("estado");
const error = document.getElementById("error");
const resultado = document.getElementById("resultado");
const fuentes = document.getElementById("fuentes");
let consultando = false;

function actualizarContador() {
  document.getElementById("contador").textContent = `${pregunta.value.length} / 2000`;
  pregunta.setCustomValidity("");
}

function mostrarRespuesta(datos) {
  document.getElementById("respuesta").textContent = datos.respuesta;
  document.getElementById("consulta-id").textContent = `Referencia de consulta: ${datos.consulta_id}`;
  fuentes.replaceChildren();
  for (const fuente of datos.fuentes_consultadas) {
    const detalle = document.createElement("details");
    const resumen = document.createElement("summary");
    resumen.append(document.createTextNode(fuente.seccion));
    const archivo = document.createElement("small");
    archivo.textContent = fuente.archivo;
    resumen.append(archivo);
    const texto = document.createElement("p");
    texto.textContent = fuente.texto;
    detalle.append(resumen, texto);
    fuentes.append(detalle);
  }
  document.getElementById("cantidad-fuentes").textContent = String(datos.fuentes_consultadas.length);
  document.getElementById("sin-fuentes").hidden = datos.fuentes_consultadas.length !== 0;
  resultado.hidden = false;
}

function mensajeError(status) {
  const mensajes = {
    401: "Tu acceso no es valido. Vuelve a abrir la pagina e inicia sesion.",
    422: "Escribe una pregunta de entre 1 y 2000 caracteres.",
    503: "No pudimos completar la consulta en este momento. Intentalo de nuevo.",
    504: "La consulta tardo demasiado. Intentalo de nuevo.",
  };
  return mensajes[status] || "No pudimos completar la consulta. Intentalo de nuevo.";
}

pregunta.addEventListener("input", actualizarContador);
for (const boton of document.querySelectorAll("[data-pregunta]")) {
  boton.addEventListener("click", () => {
    pregunta.value = boton.dataset.pregunta;
    actualizarContador();
    pregunta.focus();
  });
}

document.getElementById("limpiar").addEventListener("click", () => {
  formulario.reset();
  actualizarContador();
  resultado.hidden = true;
  error.hidden = true;
  estado.hidden = true;
  fuentes.replaceChildren();
  pregunta.focus();
});

formulario.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  if (consultando) return;
  const texto = pregunta.value.trim();
  if (!texto) {
    pregunta.setCustomValidity("Escribe una pregunta antes de consultar.");
    pregunta.reportValidity();
    return;
  }
  if (!formulario.reportValidity()) return;
  consultando = true;
  formulario.setAttribute("aria-busy", "true");
  formulario.querySelectorAll("button, textarea").forEach((elemento) => { elemento.disabled = true; });
  resultado.hidden = true;
  error.hidden = true;
  estado.textContent = "Consultando. Espera un momento...";
  estado.hidden = false;
  const controlador = new AbortController();
  const temporizador = setTimeout(() => controlador.abort(), 75000);
  try {
    const respuesta = await fetch("/consultas", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pregunta: texto }), signal: controlador.signal,
    });
    if (!respuesta.ok) {
      error.textContent = mensajeError(respuesta.status);
      error.hidden = false;
      return;
    }
    mostrarRespuesta(await respuesta.json());
  } catch (fallo) {
    error.textContent = fallo.name === "AbortError"
      ? "La consulta tardo demasiado. Intentalo de nuevo."
      : "No pudimos conectar con el servicio. Comprueba tu conexion e intentalo otra vez.";
    error.hidden = false;
  } finally {
    clearTimeout(temporizador);
    consultando = false;
    estado.hidden = true;
    formulario.setAttribute("aria-busy", "false");
    formulario.querySelectorAll("button, textarea").forEach((elemento) => { elemento.disabled = false; });
  }
});
