import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
import requests
from datetime import datetime
import base64
from pathlib import Path

st.set_page_config(
    page_title="VOUCLÉR · Dashboard Ejecutivo",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
.stApp { background-color: #F5F3EF; }
.block-container { padding: 2rem 2.5rem 3rem !important; max-width: 1400px !important; }
[data-testid="metric-container"] {
    background: #FFFFFF; border: 1px solid rgba(0,0,0,0.07);
    border-radius: 12px; padding: 1rem 1.25rem !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
[data-testid="metric-container"] label {
    font-size: 11px !important; font-weight: 500 !important;
    letter-spacing: 0.06em !important; text-transform: uppercase !important; color: #A09D99 !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-family: 'DM Serif Display', serif !important; font-size: 1.75rem !important; color: #1A1814 !important;
}
.section-title {
    font-size: 11px; font-weight: 500; letter-spacing: 0.08em; text-transform: uppercase;
    color: #A09D99; margin: 1.5rem 0 0.75rem;
    border-bottom: 1px solid rgba(0,0,0,0.06); padding-bottom: 0.5rem;
}
.insight-card {
    background: #FFFFFF; border: 1px solid rgba(0,0,0,0.07); border-radius: 12px;
    padding: 1rem 1.25rem; margin-bottom: 0.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.insight-tag { font-size: 10px; font-weight: 500; letter-spacing: 0.06em; text-transform: uppercase; margin-bottom: 6px; }
.insight-text { font-size: 13px; color: #6B6760; line-height: 1.6; }
.topbar {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid rgba(0,0,0,0.07);
}
.refresh-info { font-size: 11px; color: #A09D99; text-align: right; line-height: 1.6; }
</style>
""", unsafe_allow_html=True)

COLORS = {
    "primary": "#1A1814", "accent": "#C4956A", "accent2": "#8B6B47",
    "green": "#3D7A5C", "red": "#B84040", "amber": "#B87820",
    "blue": "#2D5F8A", "gray": "#A09D99", "light": "#D5CFC7",
}
CHART_LAYOUT = dict(
    paper_bgcolor="white", plot_bgcolor="white",
    font=dict(family="DM Sans, sans-serif", color="#6B6760", size=11),
    margin=dict(l=16, r=16, t=16, b=16), showlegend=False,
)

def fmt_eur(v):
    return f"{v:,.0f} €".replace(",", ".")

def get_category(name):
    n = (name or "").lower()
    if re.search(r"toalla|towel", n): return "Toallas"
    if re.search(r"albornoz|bathrobe", n): return "Albornoces"
    if re.search(r"sabana|saban|encimera|bajera", n): return "Sábanas"
    if re.search(r"funda|nordica|duvet", n): return "Fundas/Nórdico"
    if re.search(r"home spray|spray", n): return "Fragancia"
    if re.search(r"candle|vela", n): return "Velas"
    if re.search(r"diffuser|difusor", n): return "Difusores"
    if re.search(r"almohada", n): return "Almohadas"
    return "Otros"

def short_product(name):
    parts = name.split(" - ")
    if len(parts) >= 2:
        return parts[0].strip() + " — " + " ".join(parts[1].split()[:3])
    return name[:55] + ("…" if len(name) > 55 else "")

# LOGO
logo_path = Path("logo.png")
if logo_path.exists():
    with open(logo_path, "rb") as f:
        logo_b64 = base64.b64encode(f.read()).decode()
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height:36px;object-fit:contain;">'
else:
    logo_html = '<span style="font-family:DM Serif Display,serif;font-size:1.8rem;letter-spacing:0.1em;">VOUCLÉR</span>'

st.markdown(
    f'<div class="topbar">{logo_html}'
    f'<div class="refresh-info">Datos en tiempo real · Shopify API<br>'
    f'Actualizado: <b>{datetime.now().strftime("%d/%m/%Y %H:%M")}</b></div></div>',
    unsafe_allow_html=True
)

@st.cache_data(ttl=3600)
def load_shopify_orders():
    token = st.secrets["SHOPIFY_TOKEN"]
    store = st.secrets["SHOPIFY_STORE"]
    base_url = f"https://{store}.myshopify.com/admin/api/2024-01/orders.json"
    headers = {"X-Shopify-Access-Token": token}
    params = {
        "status": "any", "limit": 250,
        "fields": "id,name,created_at,email,total_price,subtotal_price,total_discounts,"
                  "total_tax,financial_status,fulfillment_status,cancel_reason,cancelled_at,"
                  "line_items,tags,source_name"
    }
    all_orders = []
    url = base_url
    while url:
        r = requests.get(url, headers=headers, params=params if url == base_url else None)
        if r.status_code != 200:
            st.error(f"Error Shopify API: {r.status_code} — {r.text}")
            return pd.DataFrame(), pd.DataFrame()
        all_orders.extend(r.json().get("orders", []))
        link = r.headers.get("Link", "")
        url = next((p.split(";")[0].strip().strip("<>") for p in link.split(",") if 'rel="next"' in p), None)
        params = None

    if not all_orders:
        return pd.DataFrame(), pd.DataFrame()

    rows, item_rows = [], []
    for o in all_orders:
        ch = o.get("source_name", "")
        ch_clean = "Amazon ES" if ch == "amazon-es" else "Web" if ch == "web" else "POS" if ch == "pos" else "Otros"
        rows.append({
            "order_id": o["id"], "name": o.get("name",""),
            "created_at": o.get("created_at",""), "email": o.get("email",""),
            "total": float(o.get("total_price",0) or 0),
            "total_discounts": float(o.get("total_discounts",0) or 0),
            "financial_status": o.get("financial_status",""),
            "fulfillment_status": o.get("fulfillment_status",""),
            "channel": ch_clean,
        })
        for item in o.get("line_items", []):
            name = item.get("title","")
            item_rows.append({
                "order_id": o["id"], "product": name,
                "category": get_category(name),
                "qty": int(item.get("quantity",1)),
                "price": float(item.get("price",0) or 0),
            })

    df = pd.DataFrame(rows)
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
    df["month"] = df["created_at"].dt.to_period("M").astype(str)
    df["weekday"] = df["created_at"].dt.dayofweek
    items_df = pd.DataFrame(item_rows) if item_rows else pd.DataFrame(columns=["order_id","product","category","qty","price"])
    return df, items_df

with st.spinner("Conectando con Shopify..."):
    df, items_df = load_shopify_orders()

if df.empty:
    st.warning("No se han encontrado pedidos en Shopify.")
    st.stop()

total_orders    = len(df)
total_revenue   = df["total"].sum()
avg_order       = df["total"].mean()
discount_orders = (df["total_discounts"] > 0).sum()
avg_discount    = df[df["total_discounts"] > 0]["total_discounts"].mean() if discount_orders else 0
unique_emails   = df["email"].nunique()
repeat_clients  = (df.groupby("email").size() >= 2).sum()
retention_rate  = repeat_clients / unique_emails * 100 if unique_emails else 0
refunds         = df["financial_status"].isin(["refunded","partially_refunded"]).sum()
refund_rate     = refunds / total_orders * 100

monthly_rev    = df.groupby("month")["total"].sum().sort_index()
best_month_key = monthly_rev.idxmax() if not monthly_rev.empty else "—"
best_month_val = monthly_rev.max() if not monthly_rev.empty else 0
mom_str = ""
if len(monthly_rev) >= 2:
    mom = (monthly_rev.iloc[-1] / monthly_rev.iloc[-2] - 1) * 100
    mom_str = f"{mom:+.0f}% vs mes anterior"

months_es = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
date_min = df["created_at"].min()
date_max = df["created_at"].max()
fmt_date = lambda d: f"{d.day} {months_es[d.month-1].lower()} {d.year}" if pd.notna(d) else "—"

st.markdown(
    f'<div style="font-size:12px;color:#A09D99;margin-bottom:1.25rem;">'
    f'Periodo: {fmt_date(date_min)} → {fmt_date(date_max)} · {total_orders} pedidos totales</div>',
    unsafe_allow_html=True
)

st.markdown('<div class="section-title">Resumen ejecutivo</div>', unsafe_allow_html=True)
c1,c2,c3,c4,c5,c6 = st.columns(6)
c1.metric("Facturación total",  fmt_eur(total_revenue),  f"{total_orders} pedidos")
c2.metric("Ticket medio",       fmt_eur(avg_order),       mom_str or "Por pedido")
c3.metric("Clientes únicos",    f"{unique_emails:,}",     f"{repeat_clients} repiten ({retention_rate:.1f}%)")
c4.metric("Tasa de descuento",  f"{discount_orders/total_orders*100:.1f}%", f"Media {fmt_eur(avg_discount)}")
c5.metric("Tasa de devolución", f"{refund_rate:.1f}%",   f"{refunds} pedidos")
c6.metric("Mejor mes",          best_month_key,           fmt_eur(best_month_val))

st.markdown('<div class="section-title">Tendencias</div>', unsafe_allow_html=True)
col_main, col_ch = st.columns([1.8, 1])

with col_main:
    tab_rev, tab_ord = st.tabs(["💰 Facturación","📦 Pedidos"])
    monthly = df.groupby("month").agg(revenue=("total","sum"), orders=("total","count")).reset_index()
    monthly["label"] = monthly["month"].apply(lambda k: months_es[int(k.split("-")[1])-1] + " '" + k.split("-")[0][2:])
    max_rev = monthly["revenue"].max()
    max_ord = monthly["orders"].max()
    with tab_rev:
        fig = go.Figure(go.Bar(
            x=monthly["label"], y=monthly["revenue"],
            marker_color=[COLORS["primary"] if v==max_rev else COLORS["light"] for v in monthly["revenue"]],
            marker_line_width=0, hovertemplate="%{x}<br><b>%{y:,.0f} €</b><extra></extra>",
        ))
        fig.update_layout(**CHART_LAYOUT, height=260,
            yaxis=dict(tickformat=",.0f", ticksuffix=" €", gridcolor="rgba(0,0,0,0.05)"),
            xaxis=dict(showgrid=False))
        fig.update_traces(marker_cornerradius=4)
        st.plotly_chart(fig, use_container_width=True)
    with tab_ord:
        fig2 = go.Figure(go.Bar(
            x=monthly["label"], y=monthly["orders"],
            marker_color=[COLORS["primary"] if v==max_ord else COLORS["light"] for v in monthly["orders"]],
            marker_line_width=0, hovertemplate="%{x}<br><b>%{y} pedidos</b><extra></extra>",
        ))
        fig2.update_layout(**CHART_LAYOUT, height=260,
            yaxis=dict(gridcolor="rgba(0,0,0,0.05)"), xaxis=dict(showgrid=False))
        fig2.update_traces(marker_cornerradius=4)
        st.plotly_chart(fig2, use_container_width=True)

with col_ch:
    st.markdown("**Canal de ventas**")
    ch_data = df["channel"].value_counts().reset_index()
    ch_data.columns = ["canal","pedidos"]
    ch_colors = [COLORS["accent"], COLORS["green"], COLORS["blue"], COLORS["gray"]]
    fig_ch = go.Figure(go.Pie(
        labels=ch_data["canal"], values=ch_data["pedidos"], hole=0.68,
        marker=dict(colors=ch_colors[:len(ch_data)], line=dict(width=0)),
        hovertemplate="%{label}<br><b>%{value} pedidos</b> (%{percent})<extra></extra>", textinfo="none",
    ))
    fig_ch.update_layout(**CHART_LAYOUT, height=220)
    st.plotly_chart(fig_ch, use_container_width=True)
    for i, row in ch_data.iterrows():
        pct = row["pedidos"] / ch_data["pedidos"].sum() * 100
        color = ch_colors[i % len(ch_colors)]
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;font-size:12px;color:#6B6760;margin-bottom:4px;">'
            f'<span style="width:10px;height:10px;border-radius:2px;background:{color};flex-shrink:0;"></span>'
            f'{row["canal"]} <span style="margin-left:auto;font-weight:500;color:#1A1814;">{pct:.0f}%</span></div>',
            unsafe_allow_html=True)

st.markdown('<div class="section-title">Producto & comportamiento</div>', unsafe_allow_html=True)
c_cat, c_day, c_aov = st.columns(3)

with c_cat:
    st.markdown("**Categorías de producto**")
    cat_data = items_df.groupby("category")["qty"].sum().sort_values(ascending=True).reset_index()
    fig_cat = go.Figure(go.Bar(
        x=cat_data["qty"], y=cat_data["category"], orientation="h",
        marker_color=COLORS["accent"], marker_line_width=0,
        hovertemplate="%{y}<br><b>%{x} unidades</b><extra></extra>",
    ))
    fig_cat.update_layout(**CHART_LAYOUT, height=280,
        xaxis=dict(gridcolor="rgba(0,0,0,0.05)"), yaxis=dict(showgrid=False))
    fig_cat.update_traces(marker_cornerradius=4)
    st.plotly_chart(fig_cat, use_container_width=True)

with c_day:
    st.markdown("**Pedidos por día de la semana**")
    day_labels = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"]
    day_vals = [df[df["weekday"]==i].shape[0] for i in range(7)]
    max_day = max(day_vals)
    fig_day = go.Figure(go.Bar(
        x=day_labels, y=day_vals,
        marker_color=[COLORS["primary"] if v==max_day else COLORS["light"] for v in day_vals],
        marker_line_width=0, hovertemplate="%{x}<br><b>%{y} pedidos</b><extra></extra>",
    ))
    fig_day.update_layout(**CHART_LAYOUT, height=280,
        yaxis=dict(gridcolor="rgba(0,0,0,0.05)"), xaxis=dict(showgrid=False))
    fig_day.update_traces(marker_cornerradius=4)
    st.plotly_chart(fig_day, use_container_width=True)

with c_aov:
    st.markdown("**Distribución valor de pedido**")
    bins = [0, 0.01, 25, 50, 100, 200, 1e9]
    labels = ["0€","1–25€","26–50€","51–100€","101–200€","200€+"]
    df["aov_bucket"] = pd.cut(df["total"], bins=bins, labels=labels, right=True)
    aov_data = df["aov_bucket"].value_counts().reindex(labels).reset_index()
    aov_data.columns = ["rango","count"]
    aov_colors = [COLORS["light"],COLORS["light"],COLORS["accent"],COLORS["accent"],COLORS["accent2"],COLORS["primary"]]
    fig_aov = go.Figure(go.Bar(
        x=aov_data["rango"], y=aov_data["count"],
        marker_color=aov_colors, marker_line_width=0,
        hovertemplate="%{x}<br><b>%{y} pedidos</b><extra></extra>",
    ))
    fig_aov.update_layout(**CHART_LAYOUT, height=280,
        yaxis=dict(gridcolor="rgba(0,0,0,0.05)"), xaxis=dict(showgrid=False))
    fig_aov.update_traces(marker_cornerradius=4)
    st.plotly_chart(fig_aov, use_container_width=True)

st.markdown('<div class="section-title">Productos & estado de pedidos</div>', unsafe_allow_html=True)
c_prod, c_status = st.columns([1.6, 1])

with c_prod:
    st.markdown("**Top 10 productos por unidades vendidas**")
    top_products = items_df.groupby("product")["qty"].sum().sort_values(ascending=False).head(10).reset_index()
    top_products["short"] = top_products["product"].apply(short_product)
    top_products = top_products.sort_values("qty", ascending=True)
    fig_prod = go.Figure(go.Bar(
        x=top_products["qty"], y=top_products["short"], orientation="h",
        marker_color=COLORS["accent"], marker_line_width=0,
        hovertemplate="%{y}<br><b>%{x} unidades</b><extra></extra>",
        text=top_products["qty"], textposition="outside", textfont=dict(size=11, color="#6B6760"),
    ))
    fig_prod.update_layout(**CHART_LAYOUT, height=340,
        xaxis=dict(gridcolor="rgba(0,0,0,0.05)"), yaxis=dict(showgrid=False, tickfont=dict(size=11)))
    fig_prod.update_traces(marker_cornerradius=4)
    st.plotly_chart(fig_prod, use_container_width=True)

with c_status:
    st.markdown("**Estado financiero de pedidos**")
    status_map = {"paid":"Pagado","refunded":"Reembolsado","partially_refunded":"Parcial"}
    status_colors_map = {"Pagado":COLORS["green"],"Reembolsado":COLORS["red"],"Parcial":COLORS["amber"]}
    s_data = df["financial_status"].map(status_map).fillna("Otro").value_counts().reset_index()
    s_data.columns = ["estado","count"]
    s_colors = [status_colors_map.get(e, COLORS["gray"]) for e in s_data["estado"]]
    fig_st = go.Figure(go.Pie(
        labels=s_data["estado"], values=s_data["count"], hole=0.65,
        marker=dict(colors=s_colors, line=dict(width=0)),
        hovertemplate="%{label}<br><b>%{value} pedidos</b> (%{percent})<extra></extra>", textinfo="none",
    ))
    fig_st.update_layout(**CHART_LAYOUT, height=240)
    st.plotly_chart(fig_st, use_container_width=True)
    for i, row in s_data.iterrows():
        pct = row["count"] / s_data["count"].sum() * 100
        color = status_colors_map.get(row["estado"], COLORS["gray"])
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;font-size:12px;color:#6B6760;margin-bottom:4px;">'
            f'<span style="width:10px;height:10px;border-radius:2px;background:{color};flex-shrink:0;"></span>'
            f'{row["estado"]} <span style="margin-left:auto;font-weight:500;color:#1A1814;">{pct:.0f}% · {row["count"]}</span></div>',
            unsafe_allow_html=True)

st.markdown('<div class="section-title">✦ Insights ejecutivos</div>', unsafe_allow_html=True)
top_ch     = df["channel"].value_counts().index[0] if not df.empty else "—"
top_ch_pct = df["channel"].value_counts().iloc[0] / total_orders * 100 if not df.empty else 0
top_cat    = items_df.groupby("category")["qty"].sum().idxmax() if not items_df.empty else "—"
best_day   = day_labels[day_vals.index(max(day_vals))]
worst_day  = day_labels[day_vals.index(min(day_vals))]

insights = [
    ("↑ Crecimiento", COLORS["green"],
     f"El último mes registra <b>{monthly['orders'].iloc[-1]} pedidos</b> y <b>{fmt_eur(monthly['revenue'].iloc[-1])}</b>. {mom_str}."),
    ("⚠ Retención", COLORS["amber"],
     f"Solo el <b>{retention_rate:.1f}%</b> de los clientes repiten. Con <b>{unique_emails} clientes</b>, hay potencial de email marketing post-compra."),
    ("⚠ Descuentos", COLORS["amber"],
     f"El <b>{discount_orders/total_orders*100:.1f}%</b> de pedidos llevan descuento (media <b>{fmt_eur(avg_discount)}</b>). Revisar política para proteger margen."),
    ("◎ Canal", COLORS["blue"],
     f"<b>{top_ch}</b> representa el <b>{top_ch_pct:.0f}%</b> de los pedidos. Diversificar hacia canal web propio reduce comisiones."),
    ("● Producto", COLORS["accent"],
     f"<b>{top_cat}</b> lidera en unidades. Potencial de cross-sell hacia albornoces, sábanas y fragancias para subir el ticket."),
    ("◷ Timing", COLORS["blue"],
     f"<b>{best_day}</b> concentra el mayor volumen. <b>{worst_day}</b> el mínimo. Optimizar inversión publicitaria por día mejora el ROI."),
]

cols_ins = st.columns(3)
for i, (tag, color, text) in enumerate(insights):
    with cols_ins[i % 3]:
        st.markdown(
            f'<div class="insight-card"><div class="insight-tag" style="color:{color}">{tag}</div>'
            f'<div class="insight-text">{text}</div></div>',
            unsafe_allow_html=True)

st.markdown(
    '<div style="text-align:center;padding:2rem 0 1rem;font-size:11px;color:#A09D99;letter-spacing:0.04em;">'
    'VOUCLÉR · Dashboard Ejecutivo · Datos en tiempo real via Shopify API</div>',
    unsafe_allow_html=True)
