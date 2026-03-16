from __future__ import annotations
import streamlit as st
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from config.app_config import APP
from config.cloud_config import CloudConfig
from ui.components.sidebar import render_sidebar
from ui.components.chat import render_chat


def main() -> None:
    st.set_page_config(
        layout="wide",
        page_title=APP.title + " " + APP.version,
        page_icon="👑",
    )
    st.session_state.setdefault("memory", None)
    st.session_state.setdefault("pending_prompt", None)
    st.session_state.setdefault("pending_display", None)

    cfg, selected_company, companies = render_sidebar()

    if selected_company is None:
        st.title(APP.title)
        st.info("👈 左側のメニューから、分析対象の企業を選択してください。")
        return

    base_dir = "data/" + companies[selected_company]
    if not os.path.isdir(base_dir):
        st.error("企業データフォルダが見つかりません: " + base_dir)
        return

    render_chat(selected_company=selected_company, cfg=cfg, base_dir=base_dir)


if __name__ == "__main__":
    main()
