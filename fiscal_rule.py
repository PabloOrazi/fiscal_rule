import streamlit as st
import pandas as pd
import numpy as np
from math import log
import matplotlib.pyplot as plt

st.set_page_config(layout="wide", page_title="Calculadora de Regla Fiscal")

st.markdown("<h2 style='font-size:1.5em;'>Regla Fiscal — Descomposición del Balance Primario</h2>", unsafe_allow_html=True)
st.markdown("<h3 style='font-size:1.2em;'>Autor: Pablo Orazi</h3>", unsafe_allow_html=True)

# Entradas de la barra lateral
st.sidebar.header("Entradas de Stock de Deuda")
# 67% 43.3% local
d_dom = st.sidebar.number_input("Deuda doméstica (% del PIB)", value=29.0, step=0.5)
d_fx = st.sidebar.number_input("Deuda extranjera (% del PIB)", value=38.0, step=0.5)
d_star = st.sidebar.number_input("Ancla de deuda d* (% del PIB)", value=50.0, step=0.5)

st.sidebar.header("Parámetros de la Regla Fiscal")
tau = st.sidebar.number_input("Tau (fracción del exceso a remover)", value=0.05, step=0.01)
kappa = st.sidebar.number_input("Kappa (ajuste prudencial FX)", value=0.3, step=0.01)

st.sidebar.header("Tasas de Interés y Crecimiento")
r_dom = st.sidebar.number_input("Tasa de interés real doméstica (r_dom)", value=4.0, step=0.1)
r_fx = st.sidebar.number_input("Tasa de interés real FX (r_fx)", value=4.0, step=0.1)
n = st.sidebar.number_input("Crecimiento real del PIB (n)", value=3.0, step=0.1)

st.sidebar.header("Entradas de Tipo de Cambio")
E = st.sidebar.number_input("Tipo de cambio real actual (dom por FX)", value=1.00, step=0.01)
E10 = st.sidebar.number_input("Promedio 10 años tipo de cambio real", value=1.10, step=0.01)

st.sidebar.header("Ajuste Cíclico")
OG = st.sidebar.number_input("Brecha de producto (OG)", value=0.0, step=0.1)
epsilon_pb = st.sidebar.number_input("Epsilon (elasticidad impuestos/PIB)", value=0.5, step=0.1)


# Función principal
def compute_pb_req(params, include_convergence=True, include_fx_debt_risk=True,
                  r_dom_override=None, r_fx_override=None):
    d_dom = params["d_dom"]
    d_fx = params["d_fx"]
    d_total = d_dom + d_fx
    d_star = params["d_star"]
    tau = params["tau"] if include_convergence else 0.0
    r_dom = params["r_dom"] if r_dom_override is None else r_dom_override
    r_fx = params["r_fx"] if r_fx_override is None else r_fx_override
    n = params["n"]
    E = params["E"]
    E10 = params["E10"]
    kappa = params["kappa"]

    undervaluation = np.log(E) - np.log(E10)
    fx_debt_risk = kappa * (-undervaluation) if include_fx_debt_risk else 0.0
    d_target =  d_total - tau * max(d_total - d_star, 0)

    domestic_term = ((1 + r_dom/100) / (1 + n/100) ) * d_dom
    fx_term = (1 + r_fx/100) * (1 + fx_debt_risk) / (1 + n/100) * d_fx
    pb_req = domestic_term + fx_term - d_target

    return pb_req, domestic_term, fx_term, fx_debt_risk, undervaluation, d_target

params = {
    "d_dom": d_dom, "d_fx": d_fx, "d_star": d_star, "tau": tau,
    "r_dom": r_dom, "r_fx": r_fx, "n": n, "E": E, "E10": E10, "kappa": kappa,
    "OG": OG, "epsilon_pb": epsilon_pb
}

# Descomposición secuencial
base = compute_pb_req(params, include_convergence=True, include_fx_debt_risk=True,
                      r_dom_override=r_dom, r_fx_override=r_fx)
step_dom = compute_pb_req(params, include_convergence=False, include_fx_debt_risk=False,
                          r_dom_override=r_dom, r_fx_override=n)
step_fx = compute_pb_req(params, include_convergence=False, include_fx_debt_risk=False,
                         r_dom_override=n, r_fx_override=r_fx)
step_fxval = compute_pb_req(params, include_convergence=False, include_fx_debt_risk=True,
                            r_dom_override=n, r_fx_override=r_fx)
step_conv = compute_pb_req(params, include_convergence=True, include_fx_debt_risk=False,
                           r_dom_override=n, r_fx_override=n)

pb_structural = base[0]
OG_over_3 = max(OG, 3) - 3
OG_under_3 = min(OG, 3)
epsilon_over_3 = 1.0
output_gap_effect = epsilon_pb * OG_under_3 + OG_over_3 * epsilon_over_3
pb_target = pb_structural + output_gap_effect

# Contribuciones
contribs = pd.DataFrame({
    "component": [
        "Balance \nPrimario \nObjetivo",
        "Efecto \nEstabilizador \nFiscal (brecha \nde producto)",
        "Balance \nPrimario \nEstructural \nObjetivo",
        "Efecto \nde interés \ndoméstico",
        "Efecto \nde interés \nextranjero",
        "Efecto \nde valoración \nFX (prudencial)",
        "Convergencia \nal objetivo \nde deuda (efecto \ntau)",
    ],
    "contribution_pctGDP": [
        pb_target,
        output_gap_effect,
        pb_structural,
        step_dom[0],
        step_fx[0],
        step_fxval[0] - step_fx[0],
        step_conv[0],
    ]
})

st.markdown("**Requisito estructural de balance primario (Brecha de producto=0):**")
st.latex(r"""
PB^{struct} = 
\underbrace{\frac{(1+r_{dom})}{(1+g)} \cdot d_{dom}}_{\text{Efecto interés doméstico}}
\;+\;
\underbrace{\frac{(1+r_{fx})}{(1+g)} \cdot d_{fx}}_{\text{Efecto interés extranjero}}
\;+\;
\underbrace{\frac{(1+r_{fx})(FX_{Risk})}{(1+g)} \cdot d_{fx}}_{\text{Efecto riesgo FX}}
\;-\;
\underbrace{\big[d - \tau(d - d^*)\big]}_{\text{Convergencia al objetivo de deuda}}
""")

st.markdown("**Balance primario objetivo (con ajuste cíclico):**")
st.latex(r"""
PB^{target} = PB^{struct} + \epsilon_{pb} \cdot OG
""")

# Gráfico
fig, ax = plt.subplots(figsize=(7, 3.5))

# lista de colores por nombre
colors = ["blue", "purple", "orange", "green", "red", "black",  "brown"]


# Niveles inferiores personalizados para cada barra
bottoms = [0, 
           contribs["contribution_pctGDP"][2], 
           0, 
           0,
           contribs["contribution_pctGDP"][3], 
           contribs["contribution_pctGDP"][3]+contribs["contribution_pctGDP"][4], 
           contribs["contribution_pctGDP"][3]+contribs["contribution_pctGDP"][4]+contribs["contribution_pctGDP"][5]]
ax.bar(contribs["component"], contribs["contribution_pctGDP"], color=colors, bottom=bottoms)
ax.axhline(0, linewidth=0.6, color="black")

# Anotaciones sobre cada barra con el valor. Ajustar por los bottoms
for i, v in enumerate(contribs["contribution_pctGDP"]):
    ax.text(i, bottoms[i] + v + 0.1, f"{v:.2f}", ha="center", fontsize=8)

plt.xticks(rotation=0, ha="center", fontsize=8)
# Ajustar los límites del eje y
ax.set_ylim(None, contribs["contribution_pctGDP"].max() + 0.3)
plt.ylabel("Contribución (% del PIB)")
plt.title("Descomposición del Balance Primario Objetivo")
plt.tight_layout()
st.pyplot(fig)

st.write("Balance primario estructural requerido (OG=0):", round(pb_structural, 2), "% del PIB")
st.write("Balance primario objetivo ajustado por brecha de producto:", round(pb_target, 2), "% del PIB")

# Mostrar resultados

st.subheader("Descomposición")
st.dataframe(contribs.round(2).set_index("component"))

# Añadir una descripción del propósito de la regla
st.subheader("Explicación")

st.write("Esta regla tiene como objetivo reducir la deuda pública a un porcentaje del PIB, eliminando cada año una fracción (Tau) del exceso de deuda respecto al objetivo.")
st.write("Por ejemplo, si la deuda pública es 70% del PIB y el objetivo es 50%, el exceso es 20%. Si Tau es 5%, se debería reducir 1% del PIB el próximo año (5% * 20%)."
         " Esto implica que el superávit primario, después de considerar intereses y crecimiento, debe ser suficiente para lograr esa reducción.")
st.write("La regla del superávit primario objetivo se basa en cinco componentes:")
st.write("- Efecto de interés doméstico: Impacto de los intereses reales en moneda local sobre la deuda.")
st.write("- Efecto de interés extranjero: Impacto de los intereses reales en moneda extranjera sobre la deuda.")
st.write("- Efecto de valoración FX (prudencial): Ajuste por riesgo de corrección del tipo de cambio.")
st.write("- Convergencia al objetivo de deuda (efecto tau): Reducción anual del exceso de deuda respecto al objetivo.")
st.write("- Efecto estabilizador fiscal (brecha de producto): Ajuste del balance primario por el ciclo económico.")

st.write("La suma de los primeros cuatro efectos determina el balance primario estructural requerido para alcanzar el objetivo de deuda. Al sumar el efecto estabilizador fiscal, se obtiene el balance primario objetivo.")

st.write("El efecto de valoración FX (prudencial) refleja cómo las variaciones en el tipo de cambio afectan la deuda en moneda extranjera. El coeficiente Kappa indica el porcentaje del desvío del tipo de cambio real respecto al promedio de 10 años que se considera para el ajuste.")
st.write("El efecto estabilizador fiscal (brecha de producto) muestra cómo el ciclo económico influye en el balance primario. El coeficiente Epsilon mide la sensibilidad del balance primario a la brecha de producto. En recesión, se tolera un menor superávit primario objetivo; en expansión, se exige uno mayor.")
st.write("El efecto de la tasa de interés, tanto doméstica como extranjera, se calcula por la relación entre la tasa de interés real y el crecimiento real del PIB, multiplicado por la razón deuda/PIB.")
st.write("La tasa de interés relevante para cada tipo de deuda es el promedio ponderado entre la tasa actual y la tasa histórica de la deuda emitida, según el porcentaje de vencimiento en el próximo año.")

st.subheader("Cláusulas de Escape y Contingencias")

st.write("- Recesiones económicas fuertes: Si el Output gap es menor a -3 puntos, el exceso se computa con un Epsilon de 100%. El producto potencial no puede superar el máximo producto histórico de los últimos 5 años.")
st.write("- Eventos de fuerza mayor: Pandemias, guerras o desastres naturales que afecten significativamente las finanzas públicas.")
st.write("- Crisis bancarias: Si es necesario capitalizar bancos, se permite aumentar la deuda por encima del objetivo.")

st.subheader("Créditos")
st.write("Desarrollado por Pablo Orazi")
