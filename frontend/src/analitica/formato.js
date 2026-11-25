// src/analitica/formato.js — Dueña: Paula
// Cómo se muestran las cifras en las pantallas de analítica (formato español).

const ENTERO = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 0 });
const EUROS = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 });
const HORA = new Intl.DateTimeFormat('es-ES', { hour: '2-digit', minute: '2-digit' });
const DIA = new Intl.DateTimeFormat('es-ES', { weekday: 'long', day: 'numeric', month: 'long' });

const sinDato = (valor) => valor === null || valor === undefined || Number.isNaN(Number(valor));

/** 15688 → "15.688" */
export const numero = (valor) => (sinDato(valor) ? '—' : ENTERO.format(valor));

/** 2431500 → "2.431.500 €" */
export const euros = (valor) => (sinDato(valor) ? '—' : EUROS.format(valor));

/** 0.82 → "82 %" (fracción de 0 a 1) */
export const porcentaje = (fraccion) => (sinDato(fraccion) ? '—' : `${Math.round(fraccion * 100)} %`);

/** 0.15 → "+15 %", -0.08 → "−8 %" */
export const variacion = (fraccion) => {
  if (sinDato(fraccion)) return '—';
  const valor = Math.round(fraccion * 100);
  return valor > 0 ? `+${valor} %` : valor < 0 ? `−${Math.abs(valor)} %` : '0 %';
};

/** "2026-07-18T22:00:00+02:00" → "22:00" (hora local del navegador) */
export const hora = (iso) => (iso ? HORA.format(new Date(iso)) : '—');

/** "2026-07-18T22:00:00+02:00" → "sábado, 18 de julio" */
export const dia = (iso) => (iso ? DIA.format(new Date(iso)) : '—');

/** "FOOD_BEVERAGE" → "Food beverage" (para enums del backend sin traducción) */
export const legible = (codigo) => {
  if (!codigo) return '—';
  const texto = String(codigo).replaceAll('_', ' ').toLowerCase();
  return texto.charAt(0).toUpperCase() + texto.slice(1);
};
