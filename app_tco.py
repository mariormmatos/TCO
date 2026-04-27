import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
from dataclasses import asdict
from typing import List, Dict, Optional
from datetime import datetime
import io
from fpdf import FPDF
from models import Vehicle, TcoParams, CalculationResult
from engine import TCOEngine
from theme_mint_ledger import (
    apply_theme,
    style_plotly,
    VEHICLE_PALETTE,
    SEG_COLORS,
    render_hero,
    render_leaderboard,
    heatmap_styler,
)
import db

# =========================================================
# i18n (PT/EN)
# =========================================================
I18N = {
    "pt": {
        "app_title": "Cálculo de Total Cost of Ownership",
        "app_caption": "Comparador de viaturas por custo total e custo por km (inclui importados).",
        "tab_config": "⚙️ Configuração",
        "tab_manage": "📋 Gestão de Viaturas",
        "tab_compare": "📊 Comparação",
        "tab_data": "💾 Dados & Export",
        "advanced_assumptions": "⚙️ Assunções",
        "hold_years": "Anos de Posse",
        "annual_km": "Kms Anuais",
        "fuel_energy_prices": "Combustível & Energia (€)",
        "depr_profile": "Depreciação (perfil não-linear)",
        "edit_depr": "Editar manualmente o perfil anual de depreciação",
        "depr_bias": "Ajuste global de depreciação (pontos percentuais por ano)",
        "depr_note": "Nota: percentagens aplicadas ao valor inicial (não ao valor corrente).",
        "fixed_costs": "Custos Fixos (anuais) (€)",
        "insurance": "Seguro (anual) (€)",
        "iuc": "IUC (anual) (€)",
        "inspection": "Inspeção (anual) (€)",
        "tolls_parking": "Portagens + Parqueamento (média anual) (€)",
        "vehicle_details": "Detalhes da Viatura",
        "name": "Nome da Viatura",
        "price": "Preço de compra (€)",
        "fuel": "Combustível",
        "cons_l": "Consumo (L/100km)",
        "cons_kwh": "Consumo (kWh/100km)",
        "year": "Ano",
        "km_current": "Kms Atuais",
        "imported": "Viatura Importada?",
        "co2": "CO2 (g/km)",
        "cc": "Cilindrada (cc)",
        "add_update": "➕ Adicionar / Atualizar",
        "clear_form": "Limpar formulário",
        "vehicles": "Viaturas adicionadas",
        "edit": "Editar",
        "remove": "Remover",
        "base_vehicle": "Viatura base (para deltas)",
        "chart_title": "Composição do TCO (EUR)",
        "comparison_table": "Tabela detalhada (categorias nas linhas)",
        "export_json": "Exportar cenário (JSON)",
        "import_json": "Importar cenário (JSON)",
        "export_csv": "Exportar resultados (CSV)",
        "export_pdf": "Exportar relatório (PDF)",
        "config_user": "Conta",
        "config_lang": "Idioma",
        "save_sim": "Guardar simulação atual",
        "saved_sims": "Simulações guardadas",
        "load": "Carregar",
        "delete": "Apagar",
        "no_saved": "Ainda não existem simulações guardadas nesta sessão.",
        "disclaimer": "Disclaimer: os valores são estimativas (não substituem simulações oficiais/aconselhamento fiscal).",
        "real_cons": "Ajuste do consumo real (%)",
    },
    "en": {
        "app_title": "Total Cost of Ownership Calculator",
        "app_caption": "Vehicle comparison by total cost and cost per km (imports supported).",
        "tab_config": "⚙️ Settings",
        "tab_manage": "📋 Vehicles",
        "tab_compare": "📊 Comparison",
        "tab_data": "💾 Data & Export",
        "advanced_assumptions": "⚙️ Assumptions",
        "hold_years": "Ownership years",
        "annual_km": "Annual km",
        "fuel_energy_prices": "Fuel & Energy (€)",
        "depr_profile": "Depreciation (non-linear profile)",
        "edit_depr": "Manually edit annual depreciation profile",
        "depr_bias": "Global depreciation adjustment (percentage points per year)",
        "depr_note": "Note: percentages are applied to initial value (not current value).",
        "fixed_costs": "Fixed Costs (annual) (€)",
        "insurance": "Insurance (annual) (€)",
        "iuc": "Road tax (annual) (€)",
        "inspection": "Inspection (annual) (€)",
        "tolls_parking": "Tolls + Parking (avg annual) (€)",
        "vehicle_details": "Vehicle details",
        "name": "Vehicle name",
        "price": "Purchase price (€)",
        "fuel": "Fuel type",
        "cons_l": "Consumption (L/100km)",
        "cons_kwh": "Consumption (kWh/100km)",
        "year": "Year",
        "km_current": "Current km",
        "imported": "Imported vehicle?",
        "co2": "CO2 (g/km)",
        "cc": "Engine size (cc)",
        "add_update": "➕ Add / Update",
        "clear_form": "Clear form",
        "vehicles": "Added vehicles",
        "edit": "Edit",
        "remove": "Remove",
        "base_vehicle": "Baseline vehicle (for deltas)",
        "chart_title": "TCO breakdown (EUR)",
        "comparison_table": "Detailed table (categories as rows)",
        "export_json": "Export scenario (JSON)",
        "import_json": "Import scenario (JSON)",
        "export_csv": "Export results (CSV)",
        "export_pdf": "Export report (PDF)",
        "config_user": "Account",
        "config_lang": "Language",
        "save_sim": "Save current simulation",
        "saved_sims": "Saved simulations",
        "load": "Load",
        "delete": "Delete",
        "no_saved": "No saved simulations in this session yet.",
        "disclaimer": "Disclaimer: values are estimates (not a substitute for official simulators/tax advice).",
        "real_cons": "Real-world consumption adjustment (%)",
    }
}

def t(key: str) -> str:
    lang = st.session_state.get("lang", "pt")
    return I18N.get(lang, I18N["pt"]).get(key, key)

# =========================================================
# Helpers
# =========================================================
def get_display_user() -> str:
    db_user = st.session_state.get("db_user")
    if db_user and getattr(db_user, "email", None):
        return db_user.email
    return st.session_state.get("user_name") or "Anon"

# =========================================================
# PDF REPORT ENGINE
# =========================================================
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'TCO Calculator Report', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, txt):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 8, txt, 0, 1, 'L', 1)
        self.ln(4)

    def chapter_body(self, txt):
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 5, txt)
        self.ln()

def build_pdf_report(results: List[CalculationResult], user_name: str) -> bytes:
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Meta Info
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, 1)
    pdf.cell(0, 6, f"Utilizador: {user_name}", 0, 1)
    pdf.ln(10)

    # Summary Table
    pdf.chapter_title("Comparativo Geral")
    
    # Header
    pdf.set_font("Arial", "B", 9)
    cols = ["Viatura", "TCO Total", "EUR/Km", "Revenda"]
    col_widths = [60, 40, 40, 40]
    
    for i, h in enumerate(cols):
        pdf.cell(col_widths[i], 7, h, 1, 0, 'C')
    pdf.ln()
    
    # Rows
    pdf.set_font("Arial", "", 9)
    for r in results:
        pdf.cell(col_widths[0], 7, r.vehicle_name, 1)
        pdf.cell(col_widths[1], 7, f"{r.total_cost:,.2f}", 1, 0, 'R')
        pdf.cell(col_widths[2], 7, f"{r.cost_per_km:.3f}", 1, 0, 'R')
        pdf.cell(col_widths[3], 7, f"{r.resale_value:,.2f}", 1, 0, 'R')
        pdf.ln()
    
    pdf.ln(10)

    # Detailed Analysis
    for r in results:
        pdf.chapter_title(f"Detalhe: {r.vehicle_name}")
        
        pdf.set_font("Arial", "", 9)
        pdf.cell(50, 6, "Aquisicao:", 0)
        pdf.cell(50, 6, f"{r.acquisition_cost:,.2f}", 0, 1)
        
        pdf.cell(50, 6, "Energia:", 0)
        pdf.cell(50, 6, f"{r.energy_cost:,.2f}", 0, 1)
        
        pdf.cell(50, 6, "Manutencao:", 0)
        pdf.cell(50, 6, f"{r.maint_cost:,.2f}", 0, 1)
        
        pdf.cell(50, 6, "Seguro/Fiscal:", 0)
        pdf.cell(50, 6, f"{r.insurance_fiscality_cost:,.2f}", 0, 1)
        
        pdf.cell(50, 6, "Tolls/Parking:", 0)
        pdf.cell(50, 6, f"{r.tolls_parking_cost:,.2f}", 0, 1)
        
        pdf.cell(50, 6, "Valor Revenda:", 0)
        pdf.cell(50, 6, f"{r.resale_value:,.2f}", 0, 1)
        pdf.ln(5)

    return pdf.output(dest='S').encode('latin-1', 'replace')


# =========================================================
# UI helpers
# =========================================================
def euro(x: float) -> str:
    try:
        return f"{x:,.0f} €".replace(",", " ").replace(".", ",")
    except Exception:
        return f"{x} €"

def init_state():
    if "lang" not in st.session_state:
        st.session_state["lang"] = "pt"
    if "user_name" not in st.session_state:
        st.session_state["user_name"] = ""
    if "vehicles" not in st.session_state:
        st.session_state["vehicles"] = []
    if "editing_id" not in st.session_state:
        st.session_state["editing_id"] = None
    if "saved_sims" not in st.session_state:
        st.session_state["saved_sims"] = []
    if "params" not in st.session_state:
        st.session_state["params"] = TcoParams(
            hold_years=10,
            annual_km=20000,
            fuel_prices={"Gasolina": 1.85, "Diesel": 1.70, "GPL": 0.95, "Elétrico": 0.18},
            real_cons_adj=0.20,
        )
    if "db_user" not in st.session_state:
        st.session_state["db_user"] = None
    if "db_session" not in st.session_state:
        st.session_state["db_session"] = None
    if "pending_load_sim" not in st.session_state:
        st.session_state["pending_load_sim"] = None

def render_sidebar_auth(conn):
    st.sidebar.markdown(f"### {t('config_user')}")
    
    if st.session_state.get("db_user") and not st.session_state.get("db_session"):
        st.session_state["db_user"] = None

    if st.session_state["db_user"]:
        st.sidebar.success(f"Logado: {st.session_state['db_user'].email}")
        if st.sidebar.button("Logout"):
            conn.sign_out()
            st.session_state["db_user"] = None
            st.session_state["db_session"] = None
            st.rerun()
    else:
        def _store_session(res):
            session = None
            if getattr(res, "session", None):
                session = res.session
            elif isinstance(res, dict) and res.get("session"):
                session = res.get("session")
            if not session:
                st.session_state["db_session"] = None
                return
            if isinstance(session, dict):
                access = session.get("access_token")
                refresh = session.get("refresh_token")
            else:
                access = getattr(session, "access_token", None)
                refresh = getattr(session, "refresh_token", None)
            if access and refresh:
                st.session_state["db_session"] = {
                    "access_token": access,
                    "refresh_token": refresh,
                }
            else:
                st.session_state["db_session"] = None

        tab_login, tab_signup = st.sidebar.tabs(["Login", "Registo"])
        with tab_login:
            l_email = st.text_input("Email", key="l_def_email")
            l_pass = st.text_input("Password", type="password", key="l_def_pass")
            if st.button("Entrar", key="btn_login"):
                if not l_email or not l_pass:
                    st.error("Preenche email e password.")
                else:
                    res = conn.sign_in(l_email, l_pass)
                    if isinstance(res, dict) and "error" in res:
                        st.error(res["error"])
                    elif getattr(res, "user", None):
                        st.session_state["db_user"] = res.user
                        _store_session(res)
                        st.success("OK")
                        st.rerun()
                    else:
                        st.error("Falha no login.")

        with tab_signup:
            s_email = st.text_input("Email", key="s_def_email")
            s_pass = st.text_input("Password", type="password", key="s_def_pass")
            if st.button("Criar Conta", key="btn_signup"):
                if not s_email or not s_pass:
                    st.error("Preenche email e password.")
                else:
                    res = conn.sign_up(s_email, s_pass)
                    if isinstance(res, dict) and "error" in res:
                        st.error(res["error"])
                    else:
                        st.success("Conta criada. Faz login.")
    st.sidebar.divider()

def current_form_defaults():
    # Defaults in session_state for widgets
    if "v_name" not in st.session_state: st.session_state["v_name"] = ""
    if "v_price" not in st.session_state: st.session_state["v_price"] = 20000.0
    if "fuel_type" not in st.session_state: st.session_state["fuel_type"] = "Gasolina"
    if "v_consumption" not in st.session_state: st.session_state["v_consumption"] = 6.0
    if "v_year" not in st.session_state: st.session_state["v_year"] = datetime.now().year
    if "v_km_current" not in st.session_state: st.session_state["v_km_current"] = 50000
    if "v_imported" not in st.session_state: st.session_state["v_imported"] = False
    if "v_co2" not in st.session_state: st.session_state["v_co2"] = 120
    if "v_cc" not in st.session_state: st.session_state["v_cc"] = 1600

def clear_vehicle_form():
    st.session_state["editing_id"] = None
    st.session_state["v_name"] = ""
    st.session_state["v_price"] = 20000.0
    st.session_state["fuel_type"] = "Gasolina"
    st.session_state["v_consumption"] = 6.0
    st.session_state["v_year"] = datetime.now().year
    st.session_state["v_km_current"] = 50000
    st.session_state["v_imported"] = False
    st.session_state["v_co2"] = 120
    st.session_state["v_cc"] = 1600

def save_simulation():
    snap = {
        "id": f"sim_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "saved_at": datetime.now().isoformat(),
        "user_name": get_display_user(),
        "lang": st.session_state.get("lang", "pt"),
        "params": asdict(st.session_state.params),
        "vehicles": [asdict(v) for v in st.session_state.vehicles],
    }
    st.session_state.saved_sims.insert(0, snap)

def load_simulation(sim: dict):
    st.session_state["lang"] = sim.get("lang", "pt")
    st.session_state["user_name"] = sim.get("user_name", "")
    p = sim.get("params", {})
    st.session_state["params"] = TcoParams(
        hold_years=int(p.get("hold_years", 10)),
        annual_km=int(p.get("annual_km", 20000)),
        fuel_prices=dict(p.get("fuel_prices", {"Gasolina":1.85,"Diesel":1.70,"GPL":0.95,"Elétrico":0.18})),
        real_cons_adj=float(p.get("real_cons_adj", 0.20)),
        depreciation_schedule_pct=list(p.get("depreciation_schedule_pct", [])),
        depreciation_schedule_bias_pct=float(p.get("depreciation_schedule_bias_pct", 0.0)),
        fixed_costs=dict(p.get("fixed_costs", {})),
    )
    st.session_state["vehicles"] = [Vehicle(**vv) for vv in sim.get("vehicles", [])]
    clear_vehicle_form()

def apply_pending_load():
    pending = st.session_state.get("pending_load_sim")
    if not pending:
        return
    st.session_state["pending_load_sim"] = None
    load_simulation(pending)

def render_cloud_error(raw_error: str):
    err_text = str(raw_error)
    if "PGRST205" in err_text or "schema cache" in err_text or "Could not find the table" in err_text:
        st.error("Cloud Save indisponivel: a tabela `simulations` nao existe.")
        with st.expander("Criar tabela e politicas (SQL)"):
            st.code(
                """
create table if not exists public.simulations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  data jsonb not null,
  created_at timestamp with time zone default timezone('utc', now())
);

alter table public.simulations enable row level security;

create policy "simulations_select_own"
  on public.simulations for select
  using (auth.uid() = user_id);

create policy "simulations_insert_own"
  on public.simulations for insert
  with check (auth.uid() = user_id);
                """.strip(),
                language="sql",
            )
    elif "permission" in err_text.lower() or "RLS" in err_text:
        st.error("Cloud Save bloqueado por permissoes (RLS). Faz login novamente.")
        with st.expander("Politicas recomendadas (SQL)"):
            st.code(
                """
alter table public.simulations enable row level security;

create policy "simulations_select_own"
  on public.simulations for select
  using (auth.uid() = user_id);

create policy "simulations_insert_own"
  on public.simulations for insert
  with check (auth.uid() = user_id);
                """.strip(),
                language="sql",
            )
    else:
        st.error(err_text)

def render_saved_sims(show_header: bool = True):
    if show_header:
        st.subheader(t("saved_sims"))
    if not st.session_state.saved_sims:
        st.info(t("no_saved"))
        return

    for sim in st.session_state.saved_sims[:20]:
        c1, c2, c3 = st.columns([5, 1, 1])
        with c1:
            st.write(f"**{sim.get('id','sim')}** â€” {sim.get('saved_at','')}")
        with c2:
            if st.button(t("load"), key=f"load_{sim.get('id')}"):
                st.session_state["pending_load_sim"] = sim
                st.rerun()
        with c3:
            if st.button(t("delete"), key=f"del_{sim.get('id')}"):
                st.session_state.saved_sims = [
                    s for s in st.session_state.saved_sims if s.get("id") != sim.get("id")
                ]
                st.rerun()



# =========================================================
# Main
# =========================================================
def main():
    st.set_page_config(page_title=t("app_title"), layout="wide")
    init_state()
    apply_pending_load()
    current_form_defaults()
    apply_theme()
    
    # Init Database & Auth
    conn = db.Database()
    render_sidebar_auth(conn)

    hold_years = int(st.session_state.params.hold_years)
    annual_km = int(st.session_state.params.annual_km)
    render_hero(
        t("app_title"),
        t("app_caption"),
        hold_years,
        annual_km,
        len(st.session_state.vehicles),
    )

    # Sidebar assumptions
    with st.sidebar:
        st.selectbox(
            t("config_lang"),
            options=["pt", "en"],
            format_func=lambda x: "Português" if x == "pt" else "English",
            key="lang",
        )
        st.divider()
        st.header(t("advanced_assumptions"))

        st.session_state.params.hold_years = st.slider(t("hold_years"), 1, 25, int(st.session_state.params.hold_years))
        st.session_state.params.annual_km = st.number_input(t("annual_km"), 5000, 100000, int(st.session_state.params.annual_km), step=1000)

        with st.expander(t("fuel_energy_prices")):
            for k in list(st.session_state.params.fuel_prices.keys()):
                unit = "€/kWh" if k == "Elétrico" else "€/L"
                st.session_state.params.fuel_prices[k] = st.number_input(
                    f"{k} ({unit})",
                    min_value=0.0,
                    value=float(st.session_state.params.fuel_prices[k]),
                    format="%.3f",
                    key=f"fuel_price_{k}"
                )

        with st.expander(t("depr_profile")):
            edit_manual = st.checkbox(
                t("edit_depr"),
                value=bool(st.session_state.params.depreciation_schedule_pct),
            )

            st.session_state.params.depreciation_schedule_bias_pct = st.slider(
                t("depr_bias"),
                -5.0, 5.0, float(st.session_state.params.depreciation_schedule_bias_pct), 0.5
            )

            hold_years = int(st.session_state.params.hold_years)
            base_schedule = TCOEngine.default_depreciation_schedule_pct(hold_years)

            if edit_manual:
                raw = st.session_state.params.depreciation_schedule_pct
                if not raw or len(raw) != hold_years:
                    raw = base_schedule[:]  # initialize
                df_edit = pd.DataFrame({"Ano": list(range(1, hold_years + 1)), "Depreciação (%)": raw})
                edited = st.data_editor(
                    df_edit,
                    hide_index=True,
                    use_container_width=True,
                    num_rows="fixed",
                    column_config={
                        "Ano": st.column_config.NumberColumn("Ano", disabled=True, width="small"),
                        "Depreciação (%)": st.column_config.NumberColumn("Depreciação (%)", min_value=0.0, max_value=40.0, step=0.5, format="%.1f", width="small")
                    }
                )
                st.session_state.params.depreciation_schedule_pct = [float(x) for x in edited["Depreciação (%)"].tolist()]
                schedule_preview = [max(0.0, s + float(st.session_state.params.depreciation_schedule_bias_pct)) for s in st.session_state.params.depreciation_schedule_pct]
            else:
                st.session_state.params.depreciation_schedule_pct = []
                schedule_preview = [max(0.0, s + float(st.session_state.params.depreciation_schedule_bias_pct)) for s in base_schedule]

            df_sched = pd.DataFrame({"Ano": list(range(1, len(schedule_preview) + 1)), "Depreciação (%)": schedule_preview})
            st.dataframe(df_sched, use_container_width=True, hide_index=True)
            st.caption(t("depr_note"))

        # Real consumption adjustment
        st.session_state.params.real_cons_adj = st.slider(
            t("real_cons"), 0, 50, int(st.session_state.params.real_cons_adj * 100)
        ) / 100.0

        with st.expander(t("fixed_costs")):
            # Use widget keys to avoid "2-click" update feel
            if "fc_insp" not in st.session_state:
                st.session_state["fc_insp"] = float(st.session_state.params.fixed_costs.get("inspection", 0.0))
            if "fc_tolls" not in st.session_state:
                st.session_state["fc_tolls"] = float(st.session_state.params.fixed_costs.get("tolls_parking", 0.0))

            st.number_input(t("inspection"), min_value=0.0, step=5.0, key="fc_insp")
            st.number_input(t("tolls_parking"), min_value=0.0, step=50.0, key="fc_tolls")
            st.caption("Seguro e IUC são calculados automaticamente.")

            st.session_state.params.fixed_costs["inspection"] = float(st.session_state["fc_insp"])
            st.session_state.params.fixed_costs["tolls_parking"] = float(st.session_state["fc_tolls"])

    # Tabs
    t_manage, t_compare, t_data = st.tabs([t("tab_manage"), t("tab_compare"), t("tab_data")])

    # ---------------- MANAGE TAB ----------------
    with t_manage:
        st.subheader(t("vehicle_details"))

        c1, c2, c3 = st.columns(3)
        with c1:
            st.text_input(t("name"), key="v_name")
            st.number_input(t("price"), min_value=0.0, step=500.0, key="v_price")

        with c2:
            st.selectbox(t("fuel"), ["Gasolina", "Diesel", "GPL", "Elétrico"], key="fuel_type")

            # label updates immediately because NOT inside a form
            fuel = st.session_state["fuel_type"]
            cons_label = t("cons_kwh") if fuel == "Elétrico" else t("cons_l")
            default_cons = 15.0 if fuel == "Elétrico" else 6.0
            min_cons = 1.0 if fuel == "Elétrico" else 0.1

            # If user just switched fuel, adjust consumption default if it looks incompatible
            if "last_fuel_type" not in st.session_state:
                st.session_state["last_fuel_type"] = fuel
            if st.session_state["last_fuel_type"] != fuel:
                st.session_state["v_consumption"] = default_cons
                st.session_state["last_fuel_type"] = fuel

            st.number_input(cons_label, min_value=float(min_cons), step=0.1, key="v_consumption")
            st.number_input(t("year"), 1900, datetime.now().year, key="v_year")

        with c3:
            st.number_input(t("km_current"), 0, 500000, step=1000, key="v_km_current")
            st.toggle(t("imported"), key="v_imported")
            if st.session_state["v_imported"] and st.session_state["fuel_type"] != "Elétrico":
                st.number_input(t("co2"), 0, 400, key="v_co2")
                st.number_input(t("cc"), 0, 6000, step=100, key="v_cc")
            else:
                # CO2/CC não aplicável (mantemos 0 no cálculo sem mexer no estado do widget)
                # (sem alteração de st.session_state aqui para evitar erro de widget)
                pass
        # --- callbacks (evita modificar st.session_state depois dos widgets estarem instanciados) ---
        if 'last_vehicle_error' not in st.session_state: st.session_state['last_vehicle_error'] = ''
        if 'vehicle_success' not in st.session_state: st.session_state['vehicle_success'] = False

        def on_add_update():
            try:
                vid = st.session_state.get('editing_id') or f"v_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
                fuel = st.session_state.get('fuel_type', 'Gasolina')
                # CO2/cc só faz sentido para importado não-elétrico
                imported = bool(st.session_state.get('v_imported', False))
                co2 = float(st.session_state.get('v_co2', 0) or 0) if imported and fuel != 'Elétrico' else 0.0
                cc = int(st.session_state.get('v_cc', 0) or 0) if imported and fuel != 'Elétrico' else 0

                v = Vehicle(
                    id=vid,
                    name=st.session_state.get('v_name') or 'Viatura',
                    price=float(st.session_state.get('v_price', 0.0)),
                    year=int(st.session_state.get('v_year', datetime.now().year)),
                    km_current=int(st.session_state.get('v_km_current', 0)),
                    consumption=float(st.session_state.get('v_consumption', 0.0)),
                    fuel_type=fuel,
                    is_imported=imported,
                    co2=co2,
                    engine_cc=cc,
                )
                v.validate()

                updated = False
                for i, vv in enumerate(st.session_state.vehicles):
                    if vv.id == v.id:
                        st.session_state.vehicles[i] = v
                        updated = True
                        break
                if not updated:
                    st.session_state.vehicles.append(v)

                st.session_state['editing_id'] = None
                st.session_state['last_vehicle_error'] = ''
                st.session_state['vehicle_success'] = True
                clear_vehicle_form()
            except Exception as e:
                st.session_state['last_vehicle_error'] = str(e)
                st.session_state['vehicle_success'] = False

        def on_clear_form():
            st.session_state['editing_id'] = None
            st.session_state['last_vehicle_error'] = ''
            st.session_state['vehicle_success'] = False
            clear_vehicle_form()

        def on_edit_vehicle(vid: str):
            v = next((x for x in st.session_state.vehicles if x.id == vid), None)
            if not v:
                return
            st.session_state['editing_id'] = v.id
            st.session_state['v_name'] = v.name
            st.session_state['v_price'] = float(v.price)
            st.session_state['fuel_type'] = v.fuel_type
            st.session_state['v_consumption'] = float(v.consumption)
            st.session_state['v_year'] = int(v.year)
            st.session_state['v_km_current'] = int(v.km_current)
            st.session_state['v_imported'] = bool(v.is_imported)
            st.session_state['v_co2'] = int(v.co2 or 0)
            st.session_state['v_cc'] = int(v.engine_cc or 0)

        def on_remove_vehicle(vid: str):
            st.session_state.vehicles = [x for x in st.session_state.vehicles if x.id != vid]
            if st.session_state.get('editing_id') == vid:
                st.session_state['editing_id'] = None
                clear_vehicle_form()

        # feedback after actions
        if st.session_state.get('vehicle_success'):
            st.success("OK")
            st.session_state['vehicle_success'] = False
        if st.session_state.get('last_vehicle_error'):
            st.error(st.session_state['last_vehicle_error'])

        cbtn1, cbtn2 = st.columns([1,1])
        with cbtn1:
            st.button(t('add_update'), on_click=on_add_update)

        with cbtn2:
            st.button(t('clear_form'), on_click=on_clear_form)

        st.divider()
        st.subheader(t("vehicles"))
        if not st.session_state.vehicles:
            st.info("Sem viaturas.")
        else:
            for v in st.session_state.vehicles:
                cc1, cc2, cc3 = st.columns([6,1,1])
                with cc1:
                    unit = "kWh/100km" if v.fuel_type == "Elétrico" else "L/100km"
                    st.write(f"**{v.name}** — {euro(v.price)} | {v.fuel_type} | {v.consumption:.1f} {unit} | {v.year} | {v.km_current:,} km".replace(",", " "))
                with cc2:
                    st.button(t('edit'), key=f"edit_{v.id}", on_click=on_edit_vehicle, args=(v.id,))











                with cc3:
                    st.button(t('remove'), key=f"rm_{v.id}", on_click=on_remove_vehicle, args=(v.id,))



    # ---------------- COMPARE TAB ----------------
    with t_compare:
        if not st.session_state.vehicles:
            st.warning("Adiciona pelo menos uma viatura.")
        else:
            results: List[CalculationResult] = []
            for v in st.session_state.vehicles:
                try:
                    results.append(TCOEngine.run(v, st.session_state.params))
                except Exception as e:
                    st.error(f"{v.name}: {e}")

            if results:
                ctrl_left, ctrl_right = st.columns([3, 1])
                with ctrl_left:
                    base_name = st.selectbox(t("base_vehicle"), [r.vehicle_name for r in results], index=0)
                with ctrl_right:
                    if st.button(t("save_sim"), use_container_width=True):
                        save_simulation()
                        st.success("OK")

                with st.expander(t("saved_sims")):
                    render_saved_sims(show_header=False)

                base = next(r for r in results if r.vehicle_name == base_name)
                for r in results:
                    r.delta_total = r.total_cost - base.total_cost
                    r.delta_km = r.cost_per_km - base.cost_per_km

                # Enrich results with vehicle metadata for the leaderboard
                veh_by_name = {v.name: v for v in st.session_state.vehicles}
                for r in results:
                    v = veh_by_name.get(r.vehicle_name)
                    if v is not None:
                        r.fuel_type = v.fuel_type
                        r.year = v.year
                        r.consumption = v.consumption
                        r.is_imported = v.is_imported

                render_leaderboard(results, base_name=base_name)

                # ---------------- CHART 1: Resumo (3 Bars) ----------------
                # Bar 1: TCO Liquido
                # Bar 2: Custos Brutos (Soma de tudo menos revenda)
                # Bar 3: Revenda

                chart_data = []
                for r in results:
                    gross_cost = (r.acquisition_cost + r.energy_cost + r.maint_cost +
                                  r.insurance_fiscality_cost + r.tolls_parking_cost)
                    chart_data.append({"Viatura": r.vehicle_name, "Métrica": "TCO Líquido", "Valor": r.total_cost})
                    chart_data.append({"Viatura": r.vehicle_name, "Métrica": "Custos Brutos", "Valor": gross_cost})
                    chart_data.append({"Viatura": r.vehicle_name, "Métrica": "Valor Revenda", "Valor": r.resale_value})

                df_chart = pd.DataFrame(chart_data)

                fig = go.Figure()
                for i, metric in enumerate(["TCO Líquido", "Custos Brutos", "Valor Revenda"]):
                    subset = df_chart[df_chart["Métrica"] == metric]
                    fig.add_trace(go.Bar(
                        name=metric,
                        x=subset["Viatura"],
                        y=subset["Valor"],
                        text=[f"{euro(v)}" for v in subset["Valor"]],
                        textposition="auto",
                        marker_color=VEHICLE_PALETTE[i % len(VEHICLE_PALETTE)],
                    ))

                fig.update_layout(
                    barmode="group",
                    title=t("chart_title"),
                    yaxis_title="€",
                    uniformtext_minsize=8
                )
                style_plotly(fig)
                st.plotly_chart(fig, use_container_width=True)

                # ---------------- CHART 2: Detalhe (Breakdown) ----------------
                with st.expander("🔎 Ver detalhe dos custos (Gráfico)"):
                     # Build plot dataframe (cost components only)
                    df_plot = pd.DataFrame({
                        r.vehicle_name: {
                            "Aquisição": r.acquisition_cost,
                            "Energia/Combustível": r.energy_cost,
                            "Reparações+Manutenção": r.maint_cost,
                            "Seguro+Fiscalidade": r.insurance_fiscality_cost,
                            "Portagens+Parqueamento": r.tolls_parking_cost,
                            # "Revenda (−)": -r.resale_value, # Omitted in breakdown to show just costs
                        } for r in results
                    }).T

                    fig_sub = go.Figure()
                    for col in df_plot.columns:
                        fig_sub.add_trace(go.Bar(
                            name=col,
                            x=df_plot.index,
                            y=df_plot[col],
                            marker_color=SEG_COLORS.get(col, "#7a8a85"),
                            text=[f"{v:,.0f}".replace(",", " ") for v in df_plot[col].values],
                            textposition="auto"
                        ))
                    fig_sub.update_layout(
                        barmode="stack",
                        title="Detalhe dos Custos Brutos",
                        uniformtext_minsize=8
                    )
                    style_plotly(fig_sub)
                    st.plotly_chart(fig_sub, use_container_width=True)

                # Table with categories as rows and vehicles as columns
                categories = [
                    ("Aquisição", "acquisition_cost"),
                    ("Revenda", "resale_value"),
                    ("Energia/Combustível", "energy_cost"),
                    ("Portagens+Parqueamento", "tolls_parking_cost"),
                    ("Seguro+Fiscalidade", "insurance_fiscality_cost"),
                    ("Reparações+Manutenção", "maint_cost"),
                    ("TCO Total", "total_cost"),
                    ("€/km", "cost_per_km"),
                    ("Consumo no período", "energy_qty"),
                    ("Unidade", "energy_unit"),
                    ("Km no fim", "km_at_end"),
                ]

                # Build table with raw numeric values where we want heatmap colouring;
                # format for display per-row via Styler.format below.
                MONEY_ROWS = {"Aquisição", "Revenda", "Energia/Combustível",
                              "Portagens+Parqueamento", "Seguro+Fiscalidade",
                              "Reparações+Manutenção", "TCO Total"}
                STRING_ATTRS = {"energy_unit"}
                COUNT_ATTRS = {"energy_qty", "km_at_end"}

                table = {}
                for cat, attr in categories:
                    row = {}
                    for r in results:
                        val = getattr(r, attr)
                        if attr in STRING_ATTRS:
                            row[r.vehicle_name] = str(val)
                        elif attr in COUNT_ATTRS:
                            row[r.vehicle_name] = f"{val:,.0f}".replace(",", " ")
                        else:
                            row[r.vehicle_name] = val
                    table[cat] = row

                df_table = pd.DataFrame(table).T

                styler = heatmap_styler(
                    df_table,
                    total_rows=["TCO Total", "€/km"],
                    rate_rows=["€/km"],
                    credit_rows=["Revenda"],
                )

                def _fmt_money(v):
                    try:
                        return euro(float(v))
                    except Exception:
                        return v

                def _fmt_rate(v):
                    try:
                        return f"{float(v):.3f}".replace(".", ",")
                    except Exception:
                        return v

                for row_name in df_table.index:
                    if row_name == "€/km":
                        styler = styler.format(_fmt_rate, subset=pd.IndexSlice[[row_name], :])
                    elif row_name in MONEY_ROWS:
                        styler = styler.format(_fmt_money, subset=pd.IndexSlice[[row_name], :])

                st.subheader(t("comparison_table"))
                st.dataframe(styler, use_container_width=True)

                st.caption(t("disclaimer"))

    # ---------------- DATA TAB ----------------
    with t_data:
        # DB Persistence Section
        if st.session_state["db_user"]:
            st.subheader("Cloud Save")
            if st.button("Guardar Simulação na Cloud"):
                data_to_save = {
                    "lang": st.session_state.get("lang", "pt"),
                    "params": asdict(st.session_state.params),
                    "vehicles": [asdict(v) for v in st.session_state.vehicles],
                    "saved_at": datetime.now().isoformat()
                }
                res = conn.save_simulation(st.session_state["db_user"].id, data_to_save)
                
                # Check outcome (postgrest returns object with 'data', 'error' etc or raises)
                # Supabase-py v2 usually returns an object.
                if hasattr(res, "data") and res.data:
                    st.success("Guardado")
                elif isinstance(res, dict) and "error" in res:
                    render_cloud_error(res["error"])
                else:
                    st.success("Guardado")

            st.markdown("---")
            st.subheader("As minhas simulacoes")
            
            # Load stored simulations
            # This is not optimized (loads all every time), but fine for simple app
            sims_res = conn.get_simulations(st.session_state["db_user"].id)
            
            sims_data = []
            if isinstance(sims_res, dict) and "error" in sims_res:
                render_cloud_error(sims_res["error"])
            elif hasattr(sims_res, "data"):
                sims_data = sims_res.data
            elif isinstance(sims_res, list):
                sims_data = sims_res
            
            if sims_data:
                for s in sims_data:
                     try:
                         # s is a dict with columns: id, created_at, data
                         s_date = s.get("created_at", "")
                         s_id = s.get("id", "")
                         
                         # Parse JSON data if needed (some clients return string, others dict)
                         inner_data = s.get("data")
                         if isinstance(inner_data, str):
                             inner_data = json.loads(inner_data)
                             
                         # Display
                         col_txt, col_btn = st.columns([4, 1])
                         with col_txt:
                             st.write(f"📅 {s_date} | 🆔 {s_id[:8]}")
                         with col_btn:
                             if st.button("Carregar", key=f"load_{s_id}"):
                                 st.session_state["pending_load_sim"] = inner_data
                                 st.rerun()
                     except Exception as e:
                         st.error(f"Erro ao ler simulação {s.get('id')}: {e}")
            else:
                 st.info("Sem simulações na cloud.")
            st.divider()

        # Export scenario
        st.subheader("💾 Local JSON")
        scenario = {
            "user_name": get_display_user(),
            "lang": st.session_state.get("lang", "pt"),
            "params": asdict(st.session_state.params),
            "vehicles": [asdict(v) for v in st.session_state.vehicles],
        }
        js = json.dumps(scenario, ensure_ascii=False, indent=2)
        st.download_button(t("export_json"), data=js.encode("utf-8"), file_name="tco_scenario.json", mime="application/json")

        up = st.file_uploader(t("import_json"), type=["json"])
        if up is not None:
            try:
                loaded = json.loads(up.read().decode("utf-8"))
                st.session_state["pending_load_sim"] = {
                    "lang": loaded.get("lang", "pt"),
                    "user_name": loaded.get("user_name", ""),
                    "params": loaded.get("params", {}),
                    "vehicles": loaded.get("vehicles", []),
                    "id": f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "saved_at": datetime.now().isoformat(),
                }
                st.success("Importado")
                st.rerun()
            except Exception as e:
                st.error(str(e))

        st.divider()

        # Export results
        if st.session_state.vehicles:
            results = []
            for v in st.session_state.vehicles:
                try:
                    results.append(TCOEngine.run(v, st.session_state.params))
                except Exception:
                    pass

            if results:
                df = pd.DataFrame([{
                    "Viatura": r.vehicle_name,
                    "TCO": r.total_cost,
                    "€/km": r.cost_per_km,
                    "Aquisição": r.acquisition_cost,
                    "Revenda": r.resale_value,
                    "Energia": r.energy_cost,
                    "Portagens+Parqueamento": r.tolls_parking_cost,
                    "Seguro+Fiscalidade": r.insurance_fiscality_cost,
                    "Reparações+Manutenção": r.maint_cost,
                    "Consumo período": r.energy_qty,
                    "Unidade": r.energy_unit,
                    "Km fim": r.km_at_end
                } for r in results])

                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(t("export_csv"), data=csv, file_name="tco_results.csv", mime="text/csv")

                pdf_bytes = build_pdf_report(results, get_display_user())
                st.download_button(t("export_pdf"), data=pdf_bytes, file_name="tco_report.pdf", mime="application/pdf")
        else:
            st.info("Sem viaturas para exportar.")

if __name__ == "__main__":
    main()
