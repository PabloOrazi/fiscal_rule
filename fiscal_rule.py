import streamlit as st
import pandas as pd
import numpy as np
from math import log
import matplotlib.pyplot as plt

st.set_page_config(layout="wide", page_title="Fiscal Rule Calculator")

st.markdown("<h2 style='font-size:1.5em;'>Fiscal Rule — Primary Balance Decomposition</h2>", unsafe_allow_html=True)

# Sidebar inputs
st.sidebar.header("Debt Stock Inputs")
# 67% 43.3% local
d_dom = st.sidebar.number_input("Domestic debt (% of GDP)", value=29.0, step=0.5)
d_fx = st.sidebar.number_input("Foreign debt (% of GDP)", value=38.0, step=0.5)
d_star = st.sidebar.number_input("Debt anchor d* (% of GDP)", value=50.0, step=0.5)

st.sidebar.header("Fiscal Rule Parameters")
tau = st.sidebar.number_input("Tau (fraction of excess to remove)", value=0.05, step=0.01)
kappa = st.sidebar.number_input("Kappa (prudential FX Adjustment)", value=0.3, step=0.01)

st.sidebar.header("Interest Rates & Growth")
r_dom = st.sidebar.number_input("Domestic real interest rate (r_dom)", value=4.0, step=0.1)
r_fx = st.sidebar.number_input("FX real interest rate (r_fx)", value=4.0, step=0.1)
n = st.sidebar.number_input("Real GDP growth (n)", value=3.0, step=0.1)

st.sidebar.header("Exchange Rate Inputs")
E = st.sidebar.number_input("Current Real exchange rate (dom per FX)", value=1.00, step=0.01)
E10 = st.sidebar.number_input("10-yr avg Real exchange rate", value=1.10, step=0.01)

st.sidebar.header("Cyclical Adjustment")
OG = st.sidebar.number_input("Output gap (OG)", value=0.0, step=0.1)
epsilon_pb = st.sidebar.number_input("Epsilon (Tax/GDP elasticity)", value=0.5, step=0.1)


# Core function
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
    d_target =  d_total - tau * (d_total - d_star)

    domestic_term = ((1 + r_dom/100) / (1 + n/100) ) * d_dom
    fx_term = (1 + r_fx/100) * (1 + fx_debt_risk) / (1 + n/100) * d_fx
    pb_req = domestic_term + fx_term - d_target

    return pb_req, domestic_term, fx_term, fx_debt_risk, undervaluation, d_target

params = {
    "d_dom": d_dom, "d_fx": d_fx, "d_star": d_star, "tau": tau,
    "r_dom": r_dom, "r_fx": r_fx, "n": n, "E": E, "E10": E10, "kappa": kappa,
    "OG": OG, "epsilon_pb": epsilon_pb
}

# Sequential decomposition
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
output_gap_effect = epsilon_pb * OG
pb_target = pb_structural + output_gap_effect

# Contributions
contribs = pd.DataFrame({
    "component": [
        "Target \nPrimary \nBalance",
        "Fiscal \nStabilizer \nEffect (output \ngap)",
        "Structural \nPrimary \nBalance \nTarget",
        "Domestic \ninterest \neffect",
        "Foreign \ninterest \neffect",
        "FX \nvaluation \neffect \n(prudential)",
        "Convergence \nto target \ndebt (tau \neffect)",
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

st.markdown("**Structural PB requirement (Output Gap=0):**")
st.latex(r"""
PB^{struct} = 
\underbrace{\frac{(1+r_{dom})}{(1+g)} \cdot d_{dom}}_{\text{Domestic interest effect}}
\;+\;
\underbrace{\frac{(1+r_{fx})}{(1+g)} \cdot d_{fx}}_{\text{Foreign interest effect}}
\;+\;
\underbrace{\frac{(1+r_{fx})(FX_{Risk})}{(1+g)} \cdot d_{fx}}_{\text{FX Risk effect}}
\;-\;
\underbrace{\big[d - \tau(d - d^*)\big]}_{\text{Convergence to target debt}}
""")

st.markdown("**Target PB (with cyclical adjustment):**")
st.latex(r"""
PB^{target} = PB^{struct} + \epsilon_{pb} \cdot OG
""")

# Plot
fig, ax = plt.subplots(figsize=(7, 3.5))

# make a list of colours by name
colors = ["blue", "purple", "orange", "green", "red", "black",  "brown"]


# Set custom bottom levels for each bar
bottoms = [0, 
           contribs["contribution_pctGDP"][2], 
           0, 
           0,
           contribs["contribution_pctGDP"][3], 
           contribs["contribution_pctGDP"][3]+contribs["contribution_pctGDP"][4], 
           contribs["contribution_pctGDP"][3]+contribs["contribution_pctGDP"][4]+contribs["contribution_pctGDP"][5]]
ax.bar(contribs["component"], contribs["contribution_pctGDP"], color=colors, bottom=bottoms)
ax.axhline(0, linewidth=0.6, color="black")

# Make annotations above each bar of the value. Adjust by the bottoms
for i, v in enumerate(contribs["contribution_pctGDP"]):
    ax.text(i, bottoms[i] + v + 0.1, f"{v:.2f}", ha="center", fontsize=8)

plt.xticks(rotation=0, ha="center", fontsize=8)
# Adjust the y-axis limits
ax.set_ylim(bottoms[0], contribs["contribution_pctGDP"].max() + 0.3)
plt.ylabel("Contribution (% of GDP)")
plt.title("Decomposition of Primary Balance Target")
plt.tight_layout()
st.pyplot(fig)

st.write("Structural primary balance required (OG=0):", round(pb_structural, 2), "% of GDP")
st.write("Output-gap adjusted primary balance target:", round(pb_target, 2), "% of GDP")

# Display results

st.subheader("Decomposition")
st.dataframe(contribs.round(2).set_index("component"))
