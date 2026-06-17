import streamlit as st
import plotly.graph_objects as go

# Configuração da página para ocupar a tela toda
st.set_page_config(page_title="ED-LEACH: Arquitetura Bimodal (Hard Fail-Safe)", layout="wide")

st.title("ED-LEACH: Arquitetura Bimodal")
st.markdown("Simulador da separação arquitetural entre a **Camada de Roteamento** e a **Camada de Sensoriamento**, agora com **Hard Fail-Safe** físico na eleição de CH.")
st.divider()

# --- CONSTANTES DO SISTEMA ---
THETA_CRITICO = 20.0
E_REF = 2.0

# Limiares Agronómicos (Inf, Sup)
TH_CRITICA = (60.0, 80.0)
TH_ALERTA = (62.0, 78.0)
TH_ABUNDANCIA = (65.0, 75.0)

# --- LAYOUT: COLUNA ESQUERDA (INPUTS) ---
col_inputs, col_resultados = st.columns([1, 2])

with col_inputs:
    st.header("Condições Atuais")
    st.markdown("Altere os valores físicos do nó e do ambiente para observar a reação assimétrica do protocolo.")
    
    # Valores iniciais escolhidos propositadamente para mostrar a trava a funcionar
    e_res = st.slider("Bateria Física Atual (E_res %)", min_value=0.0, max_value=100.0, value=18.0, step=0.1)
    e_harv = st.slider("Média de Colheita Solar (E_harv %)", min_value=0.0, max_value=30.0, value=15.0, step=0.1)
    
    st.info(f"**Custo Base (E_ref):** {E_REF}%\n\n**Corte Físico de Sobrevivência (θ_crítico):** {THETA_CRITICO}%")

# --- LÓGICA E CÁLCULOS ---

# 1. Camada de Roteamento
e_proj = max(0.0, min(100.0, e_res + e_harv - E_REF))

# ALTERAÇÃO: A trava agora olha puramente para a energia física (E_res), cortando o "otimismo fatal"
if e_res < THETA_CRITICO:
    omega = 0.0
    status_roteamento = "🔴 MODO DE SOBREVIVÊNCIA: Eleição Desativada (Bateria Física Insuficiente)"
else:
    omega = e_proj / 100.0
    status_roteamento = "🟢 ATIVO: Participando do Sorteio"

# 2. Camada de Sensoriamento
if e_res < 30.0:
    fase = "Fase Crítica"
    l_min, l_max = 0.0, 30.0
    th_base_inf, th_base_sup = TH_CRITICA
    th_next_inf, th_next_sup = TH_ALERTA
elif e_res < 70.0:
    fase = "Fase de Alerta"
    l_min, l_max = 30.0, 70.0
    th_base_inf, th_base_sup = TH_ALERTA
    th_next_inf, th_next_sup = TH_ABUNDANCIA
else:
    fase = "Fase de Abundância"
    l_min, l_max = 70.0, 100.0
    th_base_inf, th_base_sup = TH_ABUNDANCIA
    th_next_inf, th_next_sup = TH_ABUNDANCIA # Na abundância, o limiar é estático ideal

# Interpolação (Fator Lambda)
if fase == "Fase de Abundância":
    lam = 1.0 # Janela colapsada na precisão máxima
    th_min = th_base_inf
    th_max = th_base_sup
else:
    lam = (e_res - l_min) / (l_max - l_min)
    th_min = th_base_inf + lam * (th_next_inf - th_base_inf)
    th_max = th_base_sup - lam * (th_base_sup - th_next_sup)

# --- LAYOUT: COLUNA DIREITA (RESULTADOS) ---
with col_resultados:
    # Bloco 1: Roteamento
    st.subheader("1. Camada de Roteamento (Hard Fail-Safe Físico)")
    r1, r2, r3 = st.columns(3)
    r1.metric("Energia Projetada", f"{e_proj:.1f}%", f"{e_harv - E_REF:+.1f}% nas próximas rondas")
    r2.metric("Fator de Ponderação (ω)", f"{omega:.2f}")
    
    if omega == 0:
        st.error(status_roteamento)
    else:
        st.success(status_roteamento)

    st.divider()

    # Bloco 2: Sensoriamento
    st.subheader("2. Camada de Aplicação (Conservadora & Inerte)")
    s1, s2, s3 = st.columns(3)
    s1.metric("Fase Energética Física", fase)
    s2.metric("Fator Lambda (λ)", f"{lam:.3f}")
    s3.metric("Janela de Silêncio", f"[{th_min:.2f}% a {th_max:.2f}%]")

    # --- GRÁFICO PLOTLY DA JANELA DE SILÊNCIO ---
    fig = go.Figure()

    # Adicionar o retângulo da Janela de Silêncio
    fig.add_vrect(
        x0=th_min, x1=th_max,
        fillcolor="rgba(46, 204, 113, 0.3)", # Verde translúcido
        layer="below", line_width=2, line_color="rgba(46, 204, 113, 1)",
        annotation_text="Janela de Silêncio (Hibernação)", annotation_position="top left"
    )

    # Linhas Críticas absolutas para referência
    fig.add_vline(x=60, line_dash="dash", line_color="red", annotation_text="Morte por Seca (60%)")
    fig.add_vline(x=80, line_dash="dash", line_color="red", annotation_text="Morte por Encharcamento (80%)")

    # Configuração do Eixo X para manter o gráfico estático e ver a barra encolher/esticar
    fig.update_xaxes(range=[50, 90], title_text="Umidade do Solo (%)")
    fig.update_yaxes(showticklabels=False, range=[0, 1]) # Oculta o eixo Y
    
    fig.update_layout(
        height=250,
        margin=dict(l=20, r=20, t=30, b=20),
        title_text="Comportamento Elástico do Gatilho de Transmissão",
        plot_bgcolor="rgba(240, 240, 240, 0.5)"
    )

    st.plotly_chart(fig, use_container_width=True)
    
    st.caption("Nota: O rigor do sensoriamento e a barreira de sobrevivência refletem estritamente a energia física lida pelo sensor, eliminando inconsistências na aferição do código durante a execução das rotinas do dispositivo.")
