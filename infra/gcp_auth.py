"""GCP認証ヘルパー - Streamlit Cloud / FastAPI / ローカル環境の全てに対応"""
from google.oauth2 import service_account
from google.auth import default
import logging

logger = logging.getLogger(__name__)


def get_credentials():
    """
    GCP認証情報を取得する。
    1. Streamlit Secrets に gcp_service_account があればそれを使用（Streamlit Cloud）
    2. なければ ADC（Application Default Credentials）を使用（ローカル / Cloud Run）
    """
    # Streamlit Cloud: Secrets からサービスアカウント情報を取得
    try:
        import streamlit as st
        if "gcp_service_account" in st.secrets:
            logger.info("Using Streamlit Secrets for GCP authentication")
            credentials = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=[
                    "https://www.googleapis.com/auth/bigquery",
                    "https://www.googleapis.com/auth/cloud-platform",
                ],
            )
            return credentials
    except (ImportError, Exception) as e:
        logger.debug("Streamlit Secrets not available: %s", e)

    # ローカル環境 / Cloud Run: ADC を使用
    try:
        logger.info("Using Application Default Credentials")
        credentials, project = default()
        return credentials
    except Exception as e:
        logger.error(f"Failed to get default credentials: {e}")
        return None
