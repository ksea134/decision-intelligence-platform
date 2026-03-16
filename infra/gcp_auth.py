"""GCP認証ヘルパー - Streamlit Cloud と ローカル環境の両方に対応"""
import streamlit as st
from google.oauth2 import service_account
from google.auth import default
import logging

logger = logging.getLogger(__name__)


def get_credentials():
    """
    GCP認証情報を取得する。
    1. Streamlit Secrets に gcp_service_account があればそれを使用
    2. なければ ADC（Application Default Credentials）を使用
    """
    try:
        # Streamlit Cloud: Secrets からサービスアカウント情報を取得
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
    except Exception as e:
        logger.warning(f"Failed to load credentials from Streamlit Secrets: {e}")
    
    # ローカル環境: ADC を使用
    try:
        logger.info("Using Application Default Credentials")
        credentials, project = default()
        return credentials
    except Exception as e:
        logger.error(f"Failed to get default credentials: {e}")
        return None
