import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="ED-LEACH: Comportamento Interativo das Equações", layout="wide")

st.title("ED-LEACH: Comportamento Interativo das Equações")
st.markdown("Comportamento da Seleção de Cluster Head e definição dos limiares de evento em função dos parâmetros energéticos.")
st.divider()

# -------------------------------------------------------------------
# SIDEBAR: PARÂMETROS CONFIGURÁVEIS
# -------------------------------------------------------------------
with st.sidebar:
    st.header("Parâmetros do Protocolo")

    st.subheader("Eleição de CH")
    p_base = st.slider(
        "Percentual ideal de CHs — p (%)",
        min_value=1.0, max_value=20.0, value=5.0, step=0.5,
        help="Percentual ideal de Cluster Heads na rede por rodada."
    )
    e_ref = st.slider(
        "Consumo de referência — E_ref (%)",
        min_value=0.5, max_value=10.0, value=2.0, step=0.5,
        help="Consumo médio esperado por rodada, definido pelo administrador."
    )
    theta_critico = st.slider(
        "Limiar de desqualificação — θ_crítico (%)",
        min_value=5.0, max_value=40.0, value=20.0, step=1.0,
        help="Nós com E_res abaixo deste limiar são desqualificados para CH."
    )

    st.divider()
    st.subheader("Limiares das Fases Energéticas")
    limiar_critico = st.slider(
        "Fronteira Crítica / Alerta (%)",
        min_value=5.0, max_value=40.0, value=30.0, step=1.0,
        help="E_res abaixo deste valor classifica o nó na Fase Crítica."
    )
    limiar_alerta = st.slider(
        "Fronteira Alerta / Normal (%)",
        min_value=limiar_critico + 1.0, max_value=70.0, value=50.0, step=1.0,
        help="E_res abaixo deste valor classifica o nó na Fase de Alerta."
    )
    limiar_normal = st.slider(
        "Fronteira Normal / Abundância (%)",
        min_value=limiar_alerta + 1.0, max_value=95.0, value=85.0, step=1.0,
        help="E_res abaixo deste valor classifica o nó na Fase Normal."
    )

    st.divider()
    st.subheader("Limiares de Evento por Fase")
    st.caption("Valores âncora da variável monitorada para cada fase energética.")

    col_inf, col_sup = st.columns(2)
    with col_inf:
        st.markdown("**Limite Inferior**")
        th_critica_inf  = st.number_input("Crítica inf",  value=60.0, step=0.5)
        th_alerta_inf   = st.number_input("Alerta inf",   value=62.0, step=0.5)
        th_normal_inf   = st.number_input("Normal inf",   value=65.0, step=0.5)
    with col_sup:
        st.markdown("**Limite Superior**")
        th_critica_sup  = st.number_input("Crítica sup",  value=80.0, step=0.5)
        th_alerta_sup   = st.number_input("Alerta sup",   value=78.0, step=0.5)
        th_normal_sup   = st.number_input("Normal sup",   value=75.0, step=0.5)

    st.divider()
    st.subheader("Janela Crítica da Aplicação")
    st.caption("Limites absolutos da variável monitorada para a aplicação.")
    app_min = st.number_input("Valor mínimo crítico", value=60.0, step=0.5,
        help="Ex: 60% de umidade — abaixo disso a cultura sofre seca.")
    app_max = st.number_input("Valor máximo crítico", value=80.0, step=0.5,
        help="Ex: 80% de umidade — acima disso a cultura sofre encharcamento.")
    app_var_label = st.text_input("Nome da variável monitorada", value="Umidade do Solo (%)")

# -------------------------------------------------------------------
# CONDIÇÕES ATUAIS DO NÓ (área principal)
# -------------------------------------------------------------------
st.header("Condições Atuais do Nó")
col_cond1, col_cond2 = st.columns(2)
with col_cond1:
    e_res = st.slider(
        "Energia Residual — E_res (%)",
        min_value=0.0, max_value=100.0, value=40.0, step=0.1,
        help="Energia residual atual do nó, expressa como percentagem de E_max."
    )
with col_cond2:
    e_harv_medio = st.slider(
        "Média de Colheita das últimas K rodadas — Ē_harv (%)",
        min_value=0.0, max_value=30.0, value=5.0, step=0.1,
        help="Média móvel da energia colhida nas últimas K rodadas (Equação 1)."
    )

st.divider()

# -------------------------------------------------------------------
# LÓGICA E CÁLCULOS
# -------------------------------------------------------------------

# Limiares das fases organizados
FASE_CRITICA_MIN    = 0.0
FASE_CRITICA_MAX    = limiar_critico
FASE_ALERTA_MIN     = limiar_critico
FASE_ALERTA_MAX     = limiar_alerta
FASE_NORMAL_MIN     = limiar_alerta
FASE_NORMAL_MAX     = limiar_normal
FASE_ABUNDANCIA_MIN = limiar_normal
FASE_ABUNDANCIA_MAX = 100.0

TH_CRITICA = (th_critica_inf, th_critica_sup)
TH_ALERTA  = (th_alerta_inf,  th_alerta_sup)
TH_NORMAL  = (th_normal_inf,  th_normal_sup)

# --- DIMENSÃO 1: Seleção de CH ---

# Equação 2: Energia residual projetada
e_proj = max(0.0, min(100.0, e_res + e_harv_medio - e_ref))

# Equação 3: Probabilidade de eleição de CH
if e_res < theta_critico:
    e_proj_norm = 0.0
    p_ch = 0.0
    apto_ch = False
    status_ch = "🔴 FASE CRÍTICA: Desqualificado para eleição de CH"
else:
    e_proj_norm = e_proj / 100.0
    p_ch = (p_base / 100.0) * e_proj_norm * 100.0  # em percentagem
    apto_ch = True
    status_ch = "🟢 APTO: Elegível para eleição de CH"

# --- DIMENSÃO 2: Limiares de Evento ---

# Determinação da fase energética
if e_res < FASE_CRITICA_MAX:
    fase = "Fase Crítica"
    f_min, f_max = FASE_CRITICA_MIN, FASE_CRITICA_MAX
    th_base = TH_CRITICA
    th_next = TH_ALERTA
    transmissao_irrestrita = False

elif e_res < FASE_ALERTA_MAX:
    fase = "Fase de Alerta"
    f_min, f_max = FASE_ALERTA_MIN, FASE_ALERTA_MAX
    th_base = TH_ALERTA
    th_next = TH_NORMAL
    transmissao_irrestrita = False

elif e_res < FASE_NORMAL_MAX:
    fase = "Fase Normal"
    f_min, f_max = FASE_NORMAL_MIN, FASE_NORMAL_MAX
    th_base = TH_NORMAL
    th_next = None
    transmissao_irrestrita = False

else:
    fase = "Fase de Abundância"
    f_min, f_max = FASE_ABUNDANCIA_MIN, FASE_ABUNDANCIA_MAX
    th_base = None
    th_next = None
    transmissao_irrestrita = True

# Equação 4: Fator de posição dentro da fase (λ)
lam = (e_res - f_min) / (f_max - f_min) if (f_max - f_min) > 0 else 1.0
lam = max(0.0, min(1.0, lam))

# Equações 5a e 5b: Limiares efetivos interpolados
if transmissao_irrestrita:
    th_inf_efetivo = None
    th_sup_efetivo = None

elif th_next is None:
    # Transição Normal -> Abundância: interpola em direção ao centro
    centro = (th_base[0] + th_base[1]) / 2.0
    th_inf_efetivo = th_base[0] + lam * (centro - th_base[0])
    th_sup_efetivo = th_base[1] - lam * (th_base[1] - centro)

else:
    # Interpolação padrão entre fase atual e fase superior adjacente
    th_inf_efetivo = th_base[0] + lam * (th_next[0] - th_base[0])
    th_sup_efetivo = th_base[1] - lam * (th_base[1] - th_next[1])

# -------------------------------------------------------------------
# RESULTADOS
# -------------------------------------------------------------------

# ----------------------------------------------------------------
# BLOCO 1: Seleção de CH
# ----------------------------------------------------------------
st.subheader("1. Seleção de Cluster Head")

r1, r2, r3, r4 = st.columns(4)
r1.metric(
    "Energia Residual Atual",
    f"{e_res:.1f}%",
    help="E_res(t): energia disponível no presente."
)
r2.metric(
    "Energia Projetada — Ê_res(t+1)",
    f"{e_proj:.1f}%",
    delta=f"{e_harv_medio - e_ref:+.1f}% tendência",
    help="Equação 2: min(E_res + Ē_harv - E_ref, E_max)."
)
r3.metric(
    "Ê_res Normalizada",
    f"{e_proj_norm:.3f}",
    help="Ê_res(t+1) / E_max — fator que pondera P(n,t)."
)
r4.metric(
    "Chance de ser CH nesta rodada",
    f"{p_ch:.2f}%",
    help=f"P(n,t) = p × Ê_res(t+1) / E_max = {p_base:.1f}% × {e_proj_norm:.3f} = {p_ch:.2f}%"
)

if apto_ch:
    st.success(status_ch)
else:
    st.error(status_ch)

# Gráfico de probabilidade de CH
e_vals = [i / 10.0 for i in range(0, 1001)]
p_vals = []
for e in e_vals:
    e_p = max(0.0, min(100.0, e + e_harv_medio - e_ref))
    if e < theta_critico:
        p_vals.append(0.0)
    else:
        p_vals.append((p_base / 100.0) * (e_p / 100.0) * 100.0)

fig_ch = go.Figure()

# Área de desqualificação
fig_ch.add_vrect(
    x0=0, x1=theta_critico,
    fillcolor="rgba(231, 76, 60, 0.15)",
    layer="below", line_width=0,
    annotation_text="Desqualificado (E_res < θ_crítico)",
    annotation_position="top left"
)

# Regiões das fases
fases_regioes = [
    (FASE_CRITICA_MIN,    FASE_CRITICA_MAX,    "rgba(231, 76, 60, 0.05)",   "Crítica"),
    (FASE_ALERTA_MIN,     FASE_ALERTA_MAX,     "rgba(230, 126, 34, 0.05)",  "Alerta"),
    (FASE_NORMAL_MIN,     FASE_NORMAL_MAX,     "rgba(52, 152, 219, 0.05)",  "Normal"),
    (FASE_ABUNDANCIA_MIN, FASE_ABUNDANCIA_MAX, "rgba(46, 204, 113, 0.05)",  "Abundância"),
]
for f_min_r, f_max_r, cor, label in fases_regioes:
    fig_ch.add_vrect(
        x0=f_min_r, x1=f_max_r,
        fillcolor=cor, layer="below", line_width=0,
        annotation_text=label, annotation_position="top left"
    )

# Curva de probabilidade
fig_ch.add_trace(go.Scatter(
    x=e_vals, y=p_vals,
    mode="lines",
    line=dict(color="rgba(46, 134, 193, 1)", width=2),
    name="P(n,t) = p × Ê_res / E_max"
))

# Marcador do nó atual
fig_ch.add_vline(
    x=e_res, line_dash="dash", line_color="orange",
    annotation_text=f"Nó atual (E_res={e_res:.1f}%)",
    annotation_position="top right"
)
fig_ch.add_trace(go.Scatter(
    x=[e_res], y=[p_ch],
    mode="markers",
    marker=dict(color="orange", size=12, symbol="circle"),
    name=f"P(n,t) = {p_ch:.2f}%"
))

fig_ch.update_layout(
    height=320,
    margin=dict(l=20, r=20, t=40, b=20),
    title_text="Chance de Eleição de CH em função de E_res",
    xaxis_title="Energia Residual E_res (%)",
    yaxis_title="Chance de ser CH (%)",
    yaxis=dict(range=[0, p_base * 1.1]),
    plot_bgcolor="rgba(240, 240, 240, 0.5)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02)
)

st.plotly_chart(fig_ch, use_container_width=True)

st.divider()

# ----------------------------------------------------------------
# BLOCO 2: Limiares de Evento
# ----------------------------------------------------------------
st.subheader("2. Limiares de Evento")

s1, s2, s3 = st.columns(3)
s1.metric("Fase Energética", fase)
s2.metric("Fator de Posição (λ)", f"{lam:.3f}")

if transmissao_irrestrita:
    s3.metric("Janela de Silêncio", "Irrestrita")
    st.success(
        "🟢 FASE DE ABUNDÂNCIA: flagTX sempre verdadeiro — "
        "o nó transmite qualquer leitura independentemente do valor sensoriado."
    )
else:
    s3.metric(
        "Janela de Silêncio",
        f"[{th_inf_efetivo:.2f} , {th_sup_efetivo:.2f}]"
    )

# Gráfico da janela de silêncio
fig_ev = go.Figure()

if not transmissao_irrestrita:
    # Janela de silêncio efetiva interpolada
    fig_ev.add_vrect(
        x0=th_inf_efetivo, x1=th_sup_efetivo,
        fillcolor="rgba(46, 204, 113, 0.3)",
        layer="below", line_width=2,
        line_color="rgba(46, 204, 113, 1)",
        annotation_text="Janela de Silêncio (nó não transmite)",
        annotation_position="top left"
    )
else:
    fig_ev.add_annotation(
        x=(app_min + app_max) / 2.0, y=0.5,
        text="Transmissão Irrestrita — flagTX sempre verdadeiro",
        showarrow=False,
        font=dict(size=14, color="green")
    )

# Limites absolutos da aplicação
fig_ev.add_vline(
    x=app_min, line_dash="dash", line_color="red",
    annotation_text=f"Mínimo crítico ({app_min})",
    annotation_position="top left"
)
fig_ev.add_vline(
    x=app_max, line_dash="dash", line_color="red",
    annotation_text=f"Máximo crítico ({app_max})",
    annotation_position="top right"
)

# Âncoras das fases para referência visual
for th, label, cor in [
    (TH_CRITICA, "Âncora Crítica",  "rgba(231, 76, 60, 0.2)"),
    (TH_ALERTA,  "Âncora Alerta",   "rgba(230, 126, 34, 0.2)"),
    (TH_NORMAL,  "Âncora Normal",   "rgba(52, 152, 219, 0.2)"),
]:
    fig_ev.add_vrect(
        x0=th[0], x1=th[1],
        fillcolor=cor, layer="below", line_width=1,
        line_color=cor,
        annotation_text=label,
        annotation_position="bottom left"
    )

margem = (app_max - app_min) * 0.3
fig_ev.update_xaxes(
    range=[app_min - margem, app_max + margem],
    title_text=app_var_label
)
fig_ev.update_yaxes(showticklabels=False, range=[0, 1])

fig_ev.update_layout(
    height=320,
    margin=dict(l=20, r=20, t=40, b=20),
    title_text="Gatilho de Transmissão — Janela de Silêncio Interpolada",
    plot_bgcolor="rgba(240, 240, 240, 0.5)"
)

st.plotly_chart(fig_ev, use_container_width=True)

st.divider()

# ----------------------------------------------------------------
# BLOCO 3: Resumo das equações aplicadas
# ----------------------------------------------------------------
st.subheader("3. Resumo das Equações Aplicadas")

st.markdown(f"""
| Equação | Expressão | Valor calculado |
|---|---|---|
| Eq. 1 — Média móvel colheita | Ē_harv(t) | **{e_harv_medio:.2f}%** |
| Eq. 2 — Energia projetada | Ê_res(t+1) = min(E_res + Ē_harv - E_ref, E_max) | **{e_proj:.2f}%** |
| Eq. 3 — Chance de ser CH | P(n,t) = p × Ê_res(t+1) / E_max | **{p_ch:.2f}%** |
| Eq. 4 — Fator de posição | λ(t) = (E_res - f_min) / (f_max - f_min) | **{lam:.3f}** |
| Eq. 5a — Limiar inferior efetivo | θ_inf = θ_inf_f + λ × (θ_inf_f+1 - θ_inf_f) | **{f"{th_inf_efetivo:.2f}" if th_inf_efetivo is not None else "Irrestrito"}** |
| Eq. 5b — Limiar superior efetivo | θ_sup = θ_sup_f - λ × (θ_sup_f - θ_sup_f+1) | **{f"{th_sup_efetivo:.2f}" if th_sup_efetivo is not None else "Irrestrito"}** |
""")

st.divider()
st.caption(
    "Nota: A desqualificação para CH é avaliada sobre E_res atual e não sobre a energia projetada, "
    "eliminando o risco de um nó sem energia suficiente no presente assumir o papel de CH "
    "com base em perspectiva futura otimista."
)
