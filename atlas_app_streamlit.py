#!/usr/bin/env python3
"""
AquaDock Atlas: Docking Database of Bangladeshi Aquatic Plants
Streamlit Web App – Colorful, Lively & Beautiful Theme

Features:
- Clean, vibrant light theme with soft gradients and shadows
- Optimized search bar with comfortable spacing
- Responsive layout for all screen sizes
- Full functionality: plant selection, profile, compounds, docking atlas

Requirements:
    streamlit, pandas, sqlite3
Place atlas.db in the same folder and run:
    streamlit run aquadock_atlas_streamlit.py
"""

# ------------------------------------------------------------
# PROTOBUF COMPATIBILITY FIX
# ------------------------------------------------------------
import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# Try importing streamlit with error handling
try:
    import streamlit as st
    import pandas as pd
except ImportError as e:
    print(f"Error importing required packages: {e}")
    print("\nPlease install required packages:")
    print("pip install streamlit pandas")
    sys.exit(1)

# ------------------------------------------------------------
# Configuration & Constants
# ------------------------------------------------------------
st.set_page_config(
    page_title="AquaDock Atlas",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "atlas.db"


# ------------------------------------------------------------
# Database Helpers (unchanged, with caching)
# ------------------------------------------------------------
@st.cache_resource
def get_connection():
    """Return a persistent SQLite connection."""
    if not DB_PATH.exists():
        st.error(
            f"**Database not found**\n\n"
            f"`{DB_PATH.name}` is missing from:\n`{BASE_DIR}`\n\n"
            f"Please generate `atlas.db` first using your build script."
        )
        st.stop()
    try:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        st.error(f"Database connection error: {e}")
        st.stop()


def query_one(sql, params=()):
    """Execute query and return first row as dict or None."""
    try:
        conn = get_connection()
        cur = conn.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        st.error(f"Query error: {e}")
        return None


def query_all(sql, params=()):
    """Execute query and return list of dicts."""
    try:
        conn = get_connection()
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        st.error(f"Query error: {e}")
        return []


@st.cache_data(ttl=300, show_spinner="Loading plants...")
def fetch_all_plants():
    """Retrieve all plants."""
    return query_all(
        """
        SELECT plant_id, scientific_name, vernacular_name, family
        FROM plants
        ORDER BY scientific_name
        LIMIT 5000
        """
    )


@st.cache_data(ttl=300, show_spinner="Searching...")
def search_plants_by_field(field, query):
    """Search plants by scientific name, vernacular name, or family."""
    like = f"%{query}%"
    field_map = {
        "Scientific Name": "scientific_name",
        "Vernacular Name": "vernacular_name",
        "Family": "family"
    }
    db_field = field_map.get(field, "scientific_name")
    sql = f"""
        SELECT plant_id, scientific_name, vernacular_name, family
        FROM plants
        WHERE {db_field} LIKE ?
        ORDER BY scientific_name
        LIMIT 500
    """
    return query_all(sql, (like,))


@st.cache_data(ttl=300, show_spinner="Searching by compound...")
def search_plants_by_compound(compound_query):
    """Plants that contain a given compound."""
    like = f"%{compound_query}%"
    return query_all(
        """
        SELECT DISTINCT p.plant_id, p.scientific_name, p.vernacular_name, p.family
        FROM plants p
        JOIN plant_compounds pc ON p.plant_id = pc.plant_id
        JOIN compounds c ON pc.compound_id = c.compound_id
        WHERE c.compound_name LIKE ?
        ORDER BY p.scientific_name
        LIMIT 500
        """,
        (like,),
    )


@st.cache_data(ttl=300, show_spinner="Searching by target...")
def search_plants_by_target(target_query):
    """Plants with docking results against the given target."""
    like = f"%{target_query}%"
    return query_all(
        """
        SELECT DISTINCT p.plant_id, p.scientific_name, p.vernacular_name, p.family
        FROM plants p
        JOIN plant_compounds pc ON p.plant_id = pc.plant_id
        JOIN docking d ON pc.compound_id = d.compound_id
        JOIN targets t ON d.target_id = t.target_id
        WHERE t.target_gene LIKE ?
        ORDER BY p.scientific_name
        LIMIT 500
        """,
        (like,),
    )


@st.cache_data(ttl=300, show_spinner="Loading plant details...")
def get_plant_details(plant_id):
    """Full profile for a single plant."""
    return query_one(
        """
        SELECT scientific_name, family, habit, vernacular_name, medicinal_uses
        FROM plants
        WHERE plant_id = ?
        """,
        (plant_id,),
    )


@st.cache_data(ttl=300, show_spinner="Loading compounds...")
def get_compounds_for_plant(plant_id):
    """All compounds isolated from a given plant."""
    return query_all(
        """
        SELECT c.compound_name
        FROM plant_compounds pc
        JOIN compounds c ON c.compound_id = pc.compound_id
        WHERE pc.plant_id = ?
        ORDER BY c.compound_name
        """,
        (plant_id,),
    )


@st.cache_data(ttl=300, show_spinner="Loading docking data...")
def get_docking_for_plant(plant_id):
    """All docking results for a given plant."""
    return query_all(
        """
        SELECT 
            c.compound_name,
            t.target_gene,
            d.binding_affinity_kcal_mol as affinity
        FROM plant_compounds pc
        JOIN compounds c ON c.compound_id = pc.compound_id
        JOIN docking d ON d.compound_id = c.compound_id
        JOIN targets t ON t.target_id = d.target_id
        WHERE pc.plant_id = ?
        ORDER BY d.binding_affinity_kcal_mol
        """,
        (plant_id,),
    )


@st.cache_data(ttl=300)
def get_all_targets():
    """List of all target genes."""
    rows = query_all("SELECT target_gene FROM targets ORDER BY target_gene")
    return [row["target_gene"] for row in rows]


@st.cache_data(ttl=300)
def get_plant_count():
    """Get total number of plants in database."""
    result = query_one("SELECT COUNT(*) as count FROM plants")
    return result["count"] if result else 0


@st.cache_data(ttl=300)
def get_compound_count():
    """Get total number of compounds in database."""
    result = query_one("SELECT COUNT(*) as count FROM compounds")
    return result["count"] if result else 0


@st.cache_data(ttl=300)
def get_docking_count():
    """Get total number of docking results."""
    result = query_one("SELECT COUNT(*) as count FROM docking")
    return result["count"] if result else 0


def norm(val):
    """Normalize string values."""
    return str(val).strip() if val is not None and str(val).strip() != "" else ""


# ------------------------------------------------------------
# CUSTOM COLORFUL THEME – Fresh, Lively & Professional
# ------------------------------------------------------------
st.markdown(
    """
<style>
    /* ===== GLOBAL STYLES ===== */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #e9edf5 100%);
        font-family: 'Inter', 'Segoe UI', Roboto, sans-serif;
    }

    /* Headers – clean and modern */
    h1, h2, h3 {
        color: #1e3c5c;
        font-weight: 600;
        letter-spacing: -0.02em;
    }
    h1 {
        background: linear-gradient(145deg, #1e3c5c, #2a5a7a);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }

    /* Metric cards – soft shadows, rounded, colorful */
    .metric-card {
        background: white;
        border-radius: 20px;
        padding: 1.2rem 1rem;
        box-shadow: 0 8px 20px rgba(0,30,50,0.08);
        border: 1px solid rgba(255,255,255,0.6);
        backdrop-filter: blur(4px);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        text-align: center;
    }
    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 28px rgba(30,60,90,0.15);
    }
    .metric-label {
        color: #4a6a7c;
        font-size: 0.9rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.3rem;
    }
    .metric-value {
        color: #1e3c5c;
        font-size: 2.2rem;
        font-weight: 700;
        line-height: 1;
    }

    /* Buttons – vibrant & friendly */
    .stButton > button {
        background: linear-gradient(145deg, #4682b4, #3a6e91);
        color: white;
        border: none;
        border-radius: 40px;
        padding: 0.5rem 1.8rem;
        font-weight: 600;
        font-size: 0.95rem;
        letter-spacing: 0.02em;
        box-shadow: 0 6px 14px rgba(70,130,180,0.25);
        transition: all 0.2s ease;
        border: 1px solid rgba(255,255,255,0.2);
    }
    .stButton > button:hover {
        background: linear-gradient(145deg, #3a6e91, #2e566e);
        box-shadow: 0 8px 18px rgba(70,130,180,0.35);
        color: white;
        border: 1px solid rgba(255,255,255,0.3);
    }
    .stButton > button[kind="secondary"] {
        background: white;
        color: #2e566e;
        border: 2px solid #cbd5e0;
        box-shadow: none;
    }
    .stButton > button[kind="secondary"]:hover {
        background: #f0f4f8;
        border-color: #4682b4;
        color: #1e3c5c;
    }

    /* Select boxes – clean, rounded */
    .stSelectbox > div > div {
        background-color: white;
        border-radius: 40px !important;
        border: 1px solid #dce4ec;
        padding: 0.2rem 0.5rem;
        box-shadow: 0 2px 6px rgba(0,0,0,0.02);
    }
    .stSelectbox > div > div:hover {
        border-color: #87b9d0;
    }

    /* Text input – spacious, rounded */
    .stTextInput > div > div > input {
        background-color: white;
        border-radius: 40px !important;
        border: 1px solid #dce4ec;
        padding: 0.6rem 1.2rem;
        font-size: 1rem;
        box-shadow: 0 2px 6px rgba(0,0,0,0.02);
    }
    .stTextInput > div > div > input:focus {
        border-color: #4682b4;
        box-shadow: 0 0 0 3px rgba(70,130,180,0.1);
    }

    /* DataFrames – modern cards */
    .stDataFrame {
        background: white;
        border-radius: 20px;
        padding: 0.5rem;
        box-shadow: 0 8px 20px rgba(0,30,50,0.06);
        border: none;
    }
    .stDataFrame [data-testid="StyledDataFrameCol"] {
        font-weight: 600;
        color: #1e3c5c;
    }

    /* Tabs – friendly underline style */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1.5rem;
        background: transparent;
        border-bottom: 2px solid #e2e8f0;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: #4a6a7c;
        font-weight: 600;
        font-size: 1.05rem;
        padding: 0.6rem 0.2rem;
        margin-bottom: -2px;
        border-bottom: 3px solid transparent;
        transition: color 0.2s, border-color 0.2s;
    }
    .stTabs [aria-selected="true"] {
        color: #1e3c5c !important;
        border-bottom: 3px solid #4682b4 !important;
        font-weight: 700;
    }

    /* Profile cards – soft, airy */
    .profile-card {
        background: white;
        border-radius: 28px;
        padding: 2rem;
        box-shadow: 0 16px 30px rgba(30,60,90,0.06);
        border: 1px solid rgba(255,255,255,0.8);
    }
    .profile-label {
        color: #4a6a7c;
        font-weight: 600;
        font-size: 0.95rem;
    }
    .profile-value {
        color: #1e3c5c;
        font-weight: 500;
        font-size: 1.1rem;
    }

    /* Footer – subtle */
    .footer {
        background: white;
        border-top: 1px solid #e2e8f0;
        padding: 1.2rem 2rem;
        color: #4a6a7c;
        font-size: 0.9rem;
        text-align: center;
        margin-top: 2rem;
        border-radius: 30px 30px 0 0;
        box-shadow: 0 -4px 10px rgba(0,0,0,0.02);
    }

    /* Status indicator */
    .status-badge {
        display: inline-block;
        background: #d4edda;
        color: #155724;
        padding: 0.3rem 1rem;
        border-radius: 40px;
        font-size: 0.85rem;
        font-weight: 600;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# Session State Initialization
# ------------------------------------------------------------
def init_session_state():
    defaults = {
        "search_query": "",
        "search_type": "Scientific Name",
        "selected_plant_id": None,
        "search_triggered": False,
        "target_filter": "(All Targets)",
        "sort_option": "Best affinity (most negative)",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ------------------------------------------------------------
# HEADER – with stats and title
# ------------------------------------------------------------
col1, col2, col3, col4 = st.columns([2.2, 1, 1, 1])

with col1:
    st.markdown(
        "<h1 style='font-size: 2.6rem; margin-bottom: 0;'>💧 AquaDock Atlas</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color: #4a6a7c; font-size: 1.1rem; margin-top: -5px;'>"
        "Docking database of Bangladeshi aquatic plants</p>",
        unsafe_allow_html=True,
    )

with col2:
    plant_count = get_plant_count()
    st.markdown(
        f"""
        <div class='metric-card'>
            <div class='metric-label'>🌱 Plants</div>
            <div class='metric-value'>{plant_count:,}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    compound_count = get_compound_count()
    st.markdown(
        f"""
        <div class='metric-card'>
            <div class='metric-label'>🧪 Compounds</div>
            <div class='metric-value'>{compound_count:,}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col4:
    docking_count = get_docking_count()
    st.markdown(
        f"""
        <div class='metric-card'>
            <div class='metric-label'>🔬 Docking</div>
            <div class='metric-value'>{docking_count:,}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ------------------------------------------------------------
# OPTIMIZED SEARCH BAR – Spacious, aligned, beautiful
# ------------------------------------------------------------
st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)

with st.container():
    # Use columns with explicit ratios and padding
    col_search1, col_search2, col_search3, col_search4, col_search5 = st.columns(
        [1.8, 3.5, 0.9, 0.9, 0.6]
    )

    with col_search1:
        search_type = st.selectbox(
            "🔍 Search by",
            ["Scientific Name", "Vernacular Name", "Family", "Compound Name", "Target Gene"],
            index=["Scientific Name", "Vernacular Name", "Family", "Compound Name", "Target Gene"].index(
                st.session_state.search_type
            ),
            key="search_type_selector",
            help="Select the category to search",
            label_visibility="collapsed",  # Hide label for cleaner look, but we have placeholder
        )
        st.session_state.search_type = search_type

    with col_search2:
        query = st.text_input(
            "Query",
            value=st.session_state.search_query,
            placeholder=f"🔎 Enter {search_type.lower()}...",
            label_visibility="collapsed",
            key="search_input_field",
        )
        st.session_state.search_query = query

    with col_search3:
        search_clicked = st.button("🔍 Search", use_container_width=True, type="primary")

    with col_search4:
        clear_clicked = st.button("🗑 Clear", use_container_width=True)

    with col_search5:
        show_all = st.button("📋 All", use_container_width=True, help="Show all plants")

# Spacer after search
st.markdown("<div style='margin-top: 0.8rem;'></div>", unsafe_allow_html=True)

# Handle search logic
if clear_clicked:
    st.session_state.search_query = ""
    st.session_state.search_triggered = False
    st.session_state.selected_plant_id = None
    st.rerun()

if show_all:
    st.session_state.search_query = ""
    st.session_state.search_triggered = False
    st.rerun()

if search_clicked and st.session_state.search_query:
    st.session_state.search_triggered = True
    st.rerun()

# ------------------------------------------------------------
# MAIN TABS – Clean & intuitive
# ------------------------------------------------------------
tabs = st.tabs(["🌱 Plants Database", "📋 Plant Profile", "🧪 Compounds", "🔬 Docking Atlas"])

# ============ TAB 0: PLANTS DATABASE ============
with tabs[0]:
    with st.spinner("Loading plant database..."):
        if st.session_state.search_query and st.session_state.search_triggered:
            q = st.session_state.search_query
            stype = st.session_state.search_type
            if stype in ["Scientific Name", "Vernacular Name", "Family"]:
                plants = search_plants_by_field(stype, q)
            elif stype == "Compound Name":
                plants = search_plants_by_compound(q)
            elif stype == "Target Gene":
                plants = search_plants_by_target(q)
            else:
                plants = fetch_all_plants()
        else:
            plants = fetch_all_plants()

    if plants:
        df_plants = pd.DataFrame(plants)
        if not df_plants.empty:
            df_plants = df_plants.fillna("")
            st.markdown("### 🌿 Plant Species Inventory")
            if st.session_state.search_query and st.session_state.search_triggered:
                st.success(f"🔍 Found {len(df_plants)} plant(s) matching '{st.session_state.search_query}'")
            else:
                st.info(f"📊 Showing {len(df_plants)} plant species")

            column_config = {
                "plant_id": None,
                "scientific_name": "Scientific Name",
                "vernacular_name": "Vernacular Name(s)",
                "family": "Family",
            }
            event = st.dataframe(
                df_plants[["plant_id", "scientific_name", "vernacular_name", "family"]],
                column_config=column_config,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
            )
            if len(event.selection.rows) > 0:
                idx = event.selection.rows[0]
                selected_id = df_plants.iloc[idx]["plant_id"]
                if st.session_state.selected_plant_id != selected_id:
                    st.session_state.selected_plant_id = selected_id
                    st.session_state.search_triggered = False
                    st.rerun()
            st.caption("💡 Click any row to select a plant and view its details in other tabs")
    else:
        st.warning("😕 No plants found. Try a different search term.")

# ============ TAB 1: PLANT PROFILE – Elegant, readable ============
with tabs[1]:
    if st.session_state.selected_plant_id:
        details = get_plant_details(st.session_state.selected_plant_id)
        if details:
            plant_info = query_one(
                "SELECT scientific_name FROM plants WHERE plant_id = ?",
                (st.session_state.selected_plant_id,)
            )
            plant_name = plant_info["scientific_name"] if plant_info else "Selected Plant"

            st.markdown(f"## 📋 {plant_name}")
            st.markdown("---")

            # Two-column layout with clean styling
            col_left, col_right = st.columns([1, 2])
            with col_left:
                st.markdown("<span class='profile-label'>🌿 Scientific Name</span>", unsafe_allow_html=True)
                st.markdown("<span class='profile-label'>📛 Vernacular Name(s)</span>", unsafe_allow_html=True)
                st.markdown("<span class='profile-label'>👨‍👩‍👧‍👦 Family</span>", unsafe_allow_html=True)
                st.markdown("<span class='profile-label'>🌱 Habit</span>", unsafe_allow_html=True)
            with col_right:
                st.markdown(f"<span class='profile-value'>{norm(details.get('scientific_name', ''))}</span>", unsafe_allow_html=True)
                st.markdown(f"<span class='profile-value'>{norm(details.get('vernacular_name', '')) or 'Not specified'}</span>", unsafe_allow_html=True)
                st.markdown(f"<span class='profile-value'>{norm(details.get('family', '')) or 'Not specified'}</span>", unsafe_allow_html=True)
                st.markdown(f"<span class='profile-value'>{norm(details.get('habit', '')) or 'Not specified'}</span>", unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("### 💊 Medicinal Uses")

            medicinal_uses = norm(details.get('medicinal_uses', ''))
            if medicinal_uses:
                if ';' in medicinal_uses:
                    uses_list = [use.strip() for use in medicinal_uses.split(';') if use.strip()]
                    for use in uses_list:
                        st.markdown(f"• {use}")
                else:
                    st.write(medicinal_uses)
            else:
                st.info("No medicinal use information available for this plant.")

            # Statistics expander
            with st.expander("📊 Plant Statistics", expanded=False):
                compounds = get_compounds_for_plant(st.session_state.selected_plant_id)
                docking = get_docking_for_plant(st.session_state.selected_plant_id)
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Compounds", len(compounds))
                col2.metric("Docking Results", len(docking))
                if docking:
                    affinities = [d['affinity'] for d in docking if d.get('affinity')]
                    if affinities:
                        avg_affinity = sum(affinities) / len(affinities)
                        col3.metric("Avg Binding Affinity", f"{avg_affinity:.2f} kcal/mol")
        else:
            st.error("Plant details not found.")
    else:
        # Elegant placeholder
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(
                """
                <div style='text-align: center; padding: 3rem 1rem; background: white; border-radius: 40px; box-shadow: 0 8px 20px rgba(0,0,0,0.02);'>
                    <h3 style='color: #1e3c5c; margin-bottom: 1rem;'>🌿 No Plant Selected</h3>
                    <p style='color: #4a6a7c; font-size: 1.1rem;'>
                        Click on any plant in the <strong>Plants Database</strong> tab<br>
                        to view its complete profile here.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

# ============ TAB 2: COMPOUNDS ============
with tabs[2]:
    if st.session_state.selected_plant_id:
        compounds = get_compounds_for_plant(st.session_state.selected_plant_id)
        plant_info = query_one(
            "SELECT scientific_name FROM plants WHERE plant_id = ?",
            (st.session_state.selected_plant_id,)
        )
        plant_name = plant_info["scientific_name"] if plant_info else "Selected Plant"

        if compounds:
            df_comp = pd.DataFrame(compounds)
            if not df_comp.empty:
                df_comp.columns = ["Compound Name"]
                st.markdown(f"### 🧪 Compounds from {plant_name}")

                col1, col2 = st.columns([1, 3])
                with col1:
                    st.markdown(
                        f"""
                        <div style='background: white; padding: 1.5rem; border-radius: 24px; border-left: 6px solid #4682b4; box-shadow: 0 6px 16px rgba(0,0,0,0.04);'>
                            <p style='color: #4a6a7c; margin-bottom: 5px; font-weight: 600;'>Total Compounds</p>
                            <p style='color: #1e3c5c; font-size: 2.6rem; font-weight: 700;'>{len(df_comp)}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with col2:
                    st.dataframe(df_comp, use_container_width=True, hide_index=True)
        else:
            st.info(f"🧪 No compounds recorded for {plant_name}.")
    else:
        st.info("👈 **Select a plant** to view its phytochemical compounds.")

# ============ TAB 3: DOCKING ATLAS ============
with tabs[3]:
    if st.session_state.selected_plant_id:
        docking_data = get_docking_for_plant(st.session_state.selected_plant_id)
        plant_info = query_one(
            "SELECT scientific_name FROM plants WHERE plant_id = ?",
            (st.session_state.selected_plant_id,)
        )
        plant_name = plant_info["scientific_name"] if plant_info else "Selected Plant"

        if docking_data:
            df_dock = pd.DataFrame(docking_data)
            if not df_dock.empty:
                df_dock["affinity"] = pd.to_numeric(df_dock["affinity"], errors="coerce")
                df_dock = df_dock.dropna(subset=["affinity"])

                col_f1, col_f2 = st.columns([2, 2])
                with col_f1:
                    all_targets = ["(All Targets)"] + get_all_targets()
                    selected_target = st.selectbox(
                        "🎯 Filter by Target",
                        all_targets,
                        index=all_targets.index(st.session_state.target_filter)
                        if st.session_state.target_filter in all_targets else 0,
                        key="dock_target_filter"
                    )
                    st.session_state.target_filter = selected_target
                with col_f2:
                    sort_options = [
                        "Best affinity (most negative)",
                        "Worst affinity (least negative)",
                        "Compound A→Z",
                        "Target A→Z",
                    ]
                    selected_sort = st.selectbox(
                        "📊 Sort by",
                        sort_options,
                        index=sort_options.index(st.session_state.sort_option),
                        key="dock_sort_option"
                    )
                    st.session_state.sort_option = selected_sort

                # Apply filter & sort
                if selected_target != "(All Targets)":
                    df_dock = df_dock[df_dock["target_gene"] == selected_target]
                if selected_sort == "Compound A→Z":
                    df_dock = df_dock.sort_values(by=["compound_name", "target_gene"])
                elif selected_sort == "Target A→Z":
                    df_dock = df_dock.sort_values(by=["target_gene", "compound_name"])
                elif selected_sort == "Worst affinity (least negative)":
                    df_dock = df_dock.sort_values(by="affinity", ascending=False)
                else:
                    df_dock = df_dock.sort_values(by="affinity", ascending=True)

                st.markdown(f"### 🔬 Docking Results: {plant_name}")

                col_m1, col_m2, col_m3 = st.columns(3)
                col_m1.metric("Total Results", len(df_dock))
                if not df_dock.empty:
                    col_m2.metric("Best Affinity", f"{df_dock['affinity'].min():.3f} kcal/mol")
                    col_m3.metric("Worst Affinity", f"{df_dock['affinity'].max():.3f} kcal/mol")

                st.dataframe(
                    df_dock,
                    column_config={
                        "compound_name": "Compound",
                        "target_gene": "Target Gene",
                        "affinity": st.column_config.NumberColumn(
                            "Binding Affinity (kcal/mol)", format="%.3f"
                        )
                    },
                    use_container_width=True,
                    hide_index=True,
                )

                if not df_dock.empty:
                    csv = df_dock.to_csv(index=False)
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name=f"{plant_name.replace(' ', '_')}_docking_results.csv",
                        mime="text/csv",
                    )
        else:
            st.info(f"🔬 No docking data available for {plant_name}.")
    else:
        st.info("👈 **Select a plant** to view docking results.")

# ------------------------------------------------------------
# FOOTER – Clean & informative
# ------------------------------------------------------------
current_plant = ""
if st.session_state.selected_plant_id:
    plant_info = query_one(
        "SELECT scientific_name FROM plants WHERE plant_id = ?",
        (st.session_state.selected_plant_id,)
    )
    if plant_info:
        current_plant = plant_info["scientific_name"]

status_text = f"Selected: {current_plant}" if current_plant else "Ready — select a plant from the Plants tab"

st.markdown(
    f"""
    <div class="footer">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span><span class="status-badge">● {status_text}</span></span>
            <span style="font-weight: 500;">🌊 Developed by Sheikh Sunzid Ahmed & M. Oliur Rahman</span>
            <span style="color: #4a6a7c;">Department of Botany, University of Dhaka • {datetime.now().year}</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)