import streamlit as st
import plotly.graph_objects as go

# Configuração da página
st.set_page_config(page_title="ED-LEACH: Comportamento Interativo das Equações", layout="wide")

st.title("ED-LEACH: Comportamento Interativo das Equações")
st.markdown("Comportamento da Seleção de Cluster Head e definição dos limiares de evento em função dos parâmetros energéticos.")
st.divider()

# -------------------------------------------------------------------
# CONSTANTES DO SISTEMA
# -------------------------------------------------------------------

# Limiar de desqualificação para eleição de CH
THETA_CRITICO = 20.0

# Consumo médio de referência por rodada (E_ref)
E_REF = 2.0

# Limiares das fases energéticas (energia residual em % de E_max)
FASE_CRITICA_MIN    = 0.0
FASE_CRITICA_MAX    = 30.0

FASE_ALERTA_MIN     = 30.0
FASE_ALERTA_MAX     = 50.0

FASE_NORMAL_MIN     = 50.0
FASE_NORMAL_MAX     = 85.0

FASE_ABUNDANCIA_MIN = 85.0
FASE_ABUNDANCIA_MAX = 100.0

# Limiares de evento por fase (valores absolutos da variável monitorada)
# Cenário: monitoramento de umidade do solo
# Fase Crítica    -> janela mais ampla (menor restrição de transmissão)
# Fase Alerta     -> janela intermediária superior
# Fase Normal     -> janela intermediária inferior
# Fase Abundância -> transmissão irrestrita (janela colapsada)
TH_CRITICA   = (60.0, 80.0)
TH_ALERTA    = (62.0, 78.0)
TH_NORMAL    = (65.0, 75.0)
TH_ABUNDANCIA = None  # Transmissão irrestrita — flagTX sempre verdadeiro

# -------------------------------------------------------------------
# LAYOUT: COLUNA DE INPUTS
# -------------------------------------------------------------------
col_inputs, col_resultados = st.columns([1, 2])

with col_inputs:
    st.header("Condições Atuais do Nó")
    st.markdown(
        "Ajuste os valores energéticos do nó para observar "
        "a reação do protocolo nas duas dimensões operacionais."
    )

    e_res = st.slider(
        "Energia Residual — E_res (%)",
        min_value=0.0, max_value=100.0, value=40.0, step=0.1,
        help="Energia residual atual do nó, expressa como percentagem de E_max."
    )

    e_harv_medio = st.slider(
        "Média de Colheita das últimas K rodadas — Ē_harv (%)",
        min_value=0.0, max_value=30.0, value=5.0, step=0.1,
        help=(
            "Média móvel da energia colhida nas últimas K rodadas, "
            "conforme a Equação 1 do protocolo. "
            "Representa a perspectiva de colheita futura do nó."
        )
    )

    st.info(
        f"**Consumo de referência (E_ref):** {E_REF}%  \n"
        f"**Limiar de desqualificação (θ_crítico):** {THETA_CRITICO}%"
    )

    st.caption(
        "Nota: A desqualificação para CH é avaliada sobre E_res atual, "
        "não sobre a energia projetada, eliminando o risco de um nó "
        "sem energia suficiente no presente assumir o papel de CH "
        "com base em perspectiva futura otimista."
    )

# -------------------------------------------------------------------
# LÓGICA E CÁLCULOS
# -------------------------------------------------------------------

# --- DIMENSÃO 1: Seleção de CH ---

# Equação 1: Média móvel já fornecida pelo slider (Ē_harv)

# Equação 2: Energia residual projetada para a próxima rodada
e_proj = max(0.0, min(100.0, e_res + e_harv_medio - E_REF))

# Equação 3: Probabilidade de eleição de CH
# A desqualificação é avaliada sobre E_res atual (não sobre e_proj)
# para evitar o "otimismo fatal": um nó abaixo do limiar crítico agora
# não deve ser CH independentemente de sua perspectiva futura.
if e_res < THETA_CRITICO:
    e_proj_norm = 0.0
    apto_ch = False
    status_ch = "🔴 FASE CRÍTICA: Desqualificado para eleição de CH"
else:
    e_proj_norm = e_proj / 100.0
    apto_ch = True
    status_ch = "🟢 APTO: Elegível para eleição de CH"

# --- DIMENSÃO 2: Limiares de Evento ---

# Determinação da fase energética pela energia residual atual
if e_res < FASE_CRITICA_MAX:
    fase = "Fase Crítica"
    f_min, f_max       = FASE_CRITICA_MIN, FASE_CRITICA_MAX
    th_base            = TH_CRITICA
    th_next            = TH_ALERTA
    transmissao_irrestrita = False

elif e_res < FASE_ALERTA_MAX:
    fase = "Fase de Alerta"
    f_min, f_max       = FASE_ALERTA_MIN, FASE_ALERTA_MAX
    th_base            = TH_ALERTA
    th_next            = TH_NORMAL
    transmissao_irrestrita = False

elif e_res < FASE_NORMAL_MAX:
    fase = "Fase Normal"
    f_min, f_max       = FASE_NORMAL_MIN, FASE_NORMAL_MAX
    th_base            = TH_NORMAL
    th_next            = TH_ABUNDANCIA  # None — fase superior é irrestrita
    transmissao_irrestrita = False

else:
    fase = "Fase de Abundância"
    f_min, f_max       = FASE_ABUNDANCIA_MIN, FASE_ABUNDANCIA_MAX
    th_base            = None
    th_next            = None
    transmissao_irrestrita = True

# Equação 4: Fator de posição dentro da fase (λ)
lam = (e_res - f_min) / (f_max - f_min) if (f_max - f_min) > 0 else 1.0
lam = max(0.0, min(1.0, lam))  # Garantia de permanência em [0, 1]

# Equações 5a e 5b: Limiares efetivos interpolados
if transmissao_irrestrita:
    # Fase de Abundância: janela colapsada — flagTX sempre verdadeiro
    th_inf_efetivo = None
    th_sup_efetivo = None

elif th_next is None:
    # Transição para Abundância: interpola em direção à transmissão irrestrita
    # A fase superior não tem limiares, portanto o limite inferior sobe
    # e o superior desce em direção ao centro do intervalo da aplicação
    centro = (th_base[0] + th_base[1]) / 2.0
    th_inf_efetivo = th_base[0] + lam * (centro - th_base[0])
    th_sup_efetivo = th_base[1] - lam * (th_base[1] - centro)

else:
    # Interpolação padrão entre fase atual e fase superior adjacente
    th_inf_efetivo = th_base[0] + lam * (th_next[0] - th_base[0])
    th_sup_efetivo = th_base[1] - lam * (th_base[1] - th_next[1])

# -------------------------------------------------------------------
# LAYOUT: COLUNA DE RESULTADOS
# -------------------------------------------------------------------
with col_resultados:

    # ----------------------------------------------------------------
    # BLOCO 1: Seleção de CH
    # ----------------------------------------------------------------
    st.subheader("1. Seleção de Cluster Head")

    r1, r2, r3 = st.columns(3)
    r1.metric(
        "Energia Residual Atual",
        f"{e_res:.1f}%",
        help="E_res(t): energia disponível no presente."
    )
    r2.metric(
        "Energia Projetada — Ê_res(t+1)",
        f"{e_proj:.1f}%",
        delta=f"{e_harv_medio - E_REF:+.1f}% tendência",
        help="Equação 2: E_res(t) + Ē_harv(t) - E_ref, limitado a [0, E_max]."
    )
    r3.metric(
        "Ê_res Normalizada — Ê_res / E_max",
        f"{e_proj_norm:.3f}",
        help=(
            "Fator que pondera diretamente a probabilidade de eleição de CH. "
            "P(n,t) = p × (Ê_res(t+1) / E_max), se E_res ≥ θ_crítico."
        )
    )

    if apto_ch:
        st.success(status_ch)
    else:
        st.error(status_ch)

    # Gráfico de probabilidade de CH em função de E_res
    e_vals = [i / 10.0 for i in range(0, 1001)]
    p_vals = []
    for e in e_vals:
        e_p = max(0.0, min(100.0, e + e_harv_medio - E_REF))
        if e < THETA_CRITICO:
            p_vals.append(0.0)
        else:
            p_vals.append(e_p / 100.0)

    fig_ch = go.Figure()

    # Área de desqualificação
    fig_ch.add_vrect(
        x0=0, x1=THETA_CRITICO,
        fillcolor="rgba(231, 76, 60, 0.15)",
        layer="below", line_width=0,
        annotation_text="Desqualificado", annotation_position="top left"
    )

    # Curva de probabilidade
    fig_ch.add_trace(go.Scatter(
        x=e_vals, y=p_vals,
        mode="lines",
        line=dict(color="rgba(46, 134, 193, 1)", width=2),
        name="Ê_res(t+1) / E_max"
    ))

    # Marcador do nó atual
    fig_ch.add_vline(
        x=e_res,
        line_dash="dash", line_color="orange",
        annotation_text=f"Nó atual\nE_res={e_res:.1f}%",
        annotation_position="top right"
    )
    fig_ch.add_trace(go.Scatter(
        x=[e_res], y=[e_proj_norm],
        mode="markers",
        marker=dict(color="orange", size=12, symbol="circle"),
        name=f"P(n,t) proporcional = {e_proj_norm:.3f}"
    ))

    fig_ch.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=40, b=20),
        title_text="Probabilidade Proporcional de Eleição de CH em função de E_res",
        xaxis_title="Energia Residual E_res (%)",
        yaxis_title="Ê_res(t+1) / E_max",
        yaxis=dict(range=[0, 1.05]),
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
            f"[{th_inf_efetivo:.2f}% , {th_sup_efetivo:.2f}%]"
        )

    # Gráfico da janela de silêncio
    fig_ev = go.Figure()

    if not transmissao_irrestrita:
        # Janela de silêncio efetiva (interpolada)
        fig_ev.add_vrect(
            x0=th_inf_efetivo, x1=th_sup_efetivo,
            fillcolor="rgba(46, 204, 113, 0.3)",
            layer="below", line_width=2,
            line_color="rgba(46, 204, 113, 1)",
            annotation_text="Janela de Silêncio (nó não transmite)",
            annotation_position="top left"
        )
    else:
        # Fase de Abundância: sem janela de silêncio
        fig_ev.add_annotation(
            x=70, y=0.5,
            text="Transmissão Irrestrita — flagTX sempre verdadeiro",
            showarrow=False,
            font=dict(size=14, color="green")
        )

    # Limites absolutos da aplicação
    fig_ev.add_vline(
        x=TH_CRITICA[0], line_dash="dash", line_color="red",
        annotation_text="Seca Crítica (60%)", annotation_position="top left"
    )
    fig_ev.add_vline(
        x=TH_CRITICA[1], line_dash="dash", line_color="red",
        annotation_text="Encharcamento Crítico (80%)", annotation_position="top right"
    )

    # Limiares por fase para referência visual
    for th, label, cor in [
        (TH_ALERTA,  "Alerta",  "rgba(230, 126, 34, 0.4)"),
        (TH_NORMAL,  "Normal",  "rgba(52, 152, 219, 0.4)"),
    ]:
        fig_ev.add_vrect(
            x0=th[0], x1=th[1],
            fillcolor=cor,
            layer="below", line_width=1,
            line_color=cor,
            annotation_text=f"Âncora {label}",
            annotation_position="bottom left"
        )

    fig_ev.update_xaxes(range=[55, 85], title_text="Umidade do Solo (%)")
    fig_ev.update_yaxes(showticklabels=False, range=[0, 1])

    fig_ev.update_layout(
        height=300,
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
    | Eq. 2 — Energia projetada | Ê_res(t+1) = E_res + Ē_harv - E_ref | **{e_proj:.2f}%** |
    | Eq. 3 — Prob. eleição CH | P(n,t) ∝ Ê_res(t+1) / E_max | **{e_proj_norm:.3f} × p** |
    | Eq. 4 — Fator de posição | λ(t) = (E_res - f_min) / (f_max - f_min) | **{lam:.3f}** |
    | Eq. 5a — Limiar inferior | θ_inf = θ_inf_f + λ × (θ_inf_f+1 - θ_inf_f) | **{f"{th_inf_efetivo:.2f}%" if th_inf_efetivo is not None else "Irrestrito"}** |
    | Eq. 5b — Limiar superior | θ_sup = θ_sup_f - λ × (θ_sup_f - θ_sup_f+1) | **{f"{th_sup_efetivo:.2f}%" if th_sup_efetivo is not None else "Irrestrito"}** |
    """)
