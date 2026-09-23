"""
BioVault -- entry point.

Run with:  streamlit run app.py

This file only wires together page config + the homepage UI module.
Future phases will add sidebar navigation to additional pages (file
upload, DNA encoding, mutation simulator, dashboard, education, etc.)
without needing to touch this file much.
"""

import streamlit as st

from app.config import APP_TITLE, PAGE_CONFIG
from app.modules.ui_home import render_home
from app.modules.ui_upload import render_upload
from app.modules.ui_dna_encoding import render_dna_encoding
from app.modules.ui_dna_decoding import render_dna_decoding
from app.modules.ui_dna_mutation import render_dna_mutation
from app.modules.ui_error_correction import render_error_correction
from app.modules.ui_storage_analysis import render_storage_analysis
from app.modules.ui_dna_visualization import render_dna_visualization
from app.modules.ui_data_export import render_data_export
from app.modules.ui_benchmarking import render_benchmarking
from app.modules.ui_encoding_comparison import render_encoding_comparison
from app.modules.ui_dna_integrity import render_dna_integrity
from app.modules.ui_redundancy_simulation import render_redundancy_simulation
from app.modules.ui_capacity_analysis import render_capacity_analysis
from app.modules.ui_experiment_pipeline import render_experiment_pipeline
from app.modules.ui_performance_analysis import render_performance_analysis
from app.modules.ui_environment_check import render_environment_check
from app.modules.ui_project_showcase import render_project_showcase
from app.modules.ui_viva import render_viva
from app.modules.ui_documentation import render_documentation
from app.modules.ui_project_summary import render_project_summary
from app.modules.ui_about import render_about

st.set_page_config(**PAGE_CONFIG)

PAGES = {
    "🏠 Home": render_home,
    "🎓 Project Showcase": render_project_showcase,
    "🏠 Final Dashboard": render_project_summary,
    "📁 File Upload": render_upload,
    "🧬 DNA Encoding": render_dna_encoding,
    "🧬 DNA Decoding": render_dna_decoding,
    "🧬 Mutation Simulator": render_dna_mutation,
    "🛡️ Error Correction": render_error_correction,
    "📊 Storage Analysis": render_storage_analysis,
    "📈 DNA Visualization": render_dna_visualization,
    "📦 Export & Import": render_data_export,
    "📊 Benchmarking": render_benchmarking,
    "🧬 Encoding Model Comparison": render_encoding_comparison,
    "🧪 DNA Integrity Check": render_dna_integrity,
    "🧬 Reliability & Redundancy": render_redundancy_simulation,
    "💾 DNA Capacity & Storage": render_capacity_analysis,
    "🧪 DNA Storage Experiment": render_experiment_pipeline,
    "⚙️ Performance & Resources": render_performance_analysis,
    "🎤 Viva Preparation": render_viva,
    "📚 User Guide": render_documentation,
    "🛠️ Environment & Setup Check": render_environment_check,
    "ℹ️ About BioVault": render_about,
}

st.sidebar.title(f"🧬 {APP_TITLE}")
selected_page = st.sidebar.radio("Navigate", list(PAGES.keys()))

PAGES[selected_page]()
