from __future__ import annotations
import streamlit as st
from config.app_config import APP
from config.cloud_config import CloudConfig
from infra.file_loader import load_companies


def render_sidebar() -> tuple[CloudConfig, str | None, dict[str, str]]:
    """
    Render sidebar and return (CloudConfig, selected_company, companies_dict).
    All Streamlit dependencies are contained here.
    """
    st.sidebar.title("☁️ クラウド接続先")
    project_id = st.sidebar.text_input("GCP Project ID", value="decision-support-ai")
    bucket = st.sidebar.text_input("GCS Bucket Name", value="dsa-knowledge-base")
    st.sidebar.divider()

    companies = load_companies(APP.companies_csv_path)

    if not companies:
        st.sidebar.warning("companies.csv が見つかりません。data/ フォルダを確認してください。")
        selected = None
        folder_name = ""
    else:
        selected = st.sidebar.selectbox(
            label="",
            options=list(companies.keys()),
            index=None,
            placeholder="企業を選択してください",
            label_visibility="collapsed",
        )
        folder_name = companies.get(selected, "") if selected else ""

    cfg = CloudConfig(
        project_id=project_id,
        gcs_bucket=bucket,
        folder_name=folder_name,
    )
    return cfg, selected, companies
