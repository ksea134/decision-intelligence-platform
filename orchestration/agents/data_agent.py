from __future__ import annotations
import logging
from dataclasses import dataclass
from domain.models import CloudDataResult, CompanyAssets
from infra.bigquery_service import fetch_bq_schema, execute_bq_sql
from infra.gcs_service import fetch_gcs_documents
from infra.file_loader import load_company_assets
from config.cloud_config import CloudConfig
from config.app_config import APP

logger = logging.getLogger(__name__)


@dataclass
class DataContext:
    """
    All data needed for a single reasoning cycle.
    Passed from DataAgent to ReasoningEngine.
    """
    assets: CompanyAssets
    bq_result: CloudDataResult
    gcs_result: CloudDataResult
    chat_disabled: bool

    @property
    def bq_connected(self) -> bool:
        return self.bq_result.is_connected

    @property
    def has_any_data(self) -> bool:
        has_local = bool(
            self.assets.structured_text.strip()
            or self.assets.unstructured_text.strip()
        )
        return self.bq_connected or not self.gcs_result.is_error or has_local


class DataAgent:
    """
    Data retrieval agent.

    Responsible for fetching all data sources and assembling DataContext.
    Implements the cloud-priority logic from SPEC_v1.md section 2-4:

    - BQ connected  -> suppress local structured data
    - GCS connected -> suppress local unstructured data
    - Both failed   -> use local data as-is
    - Both failed + no local -> disable chat
    """

    def __init__(self, cfg: CloudConfig) -> None:
        self._cfg = cfg
        self._schema_cache: CloudDataResult | None = None
        self._gcs_cache: CloudDataResult | None = None

    def fetch_all(self, base_dir: str) -> DataContext:
        """
        Load all data sources and return a DataContext.

        Args:
            base_dir: Company data folder path. e.g. "data/mazda"

        Returns:
            DataContext with all data sources loaded and priority applied.
        """
        assets = load_company_assets(base_dir)
        bq_result = self._fetch_schema()
        gcs_result = self._fetch_gcs()
        assets = self._apply_cloud_priority(assets, bq_result, gcs_result)

        has_local = bool(
            assets.structured_text.strip()
            or assets.unstructured_text.strip()
        )
        all_cloud_down = bq_result.is_error and gcs_result.is_error
        chat_disabled = all_cloud_down and not has_local

        return DataContext(
            assets=assets,
            bq_result=bq_result,
            gcs_result=gcs_result,
            chat_disabled=chat_disabled,
        )

    def execute_sql(self, sql: str):
        """Execute SQL on BigQuery. Returns SQLResult or None."""
        return execute_bq_sql(self._cfg.project_id, sql)

    def invalidate_cache(self) -> None:
        """Clear cached schema and GCS results."""
        self._schema_cache = None
        self._gcs_cache = None

    # ----------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------

    def _fetch_schema(self) -> CloudDataResult:
        if self._schema_cache is None:
            schema, result = fetch_bq_schema(
                self._cfg.project_id,
                self._cfg.dataset_id,
            )
            self._schema_cache = result
            self._schema_dict = schema
        return self._schema_cache

    def _fetch_gcs(self) -> CloudDataResult:
        if self._gcs_cache is None:
            self._gcs_cache = fetch_gcs_documents(
                self._cfg.gcs_bucket,
                self._cfg.gcs_prefix,
            )
        return self._gcs_cache

    def _apply_cloud_priority(
        self,
        assets: CompanyAssets,
        bq_result: CloudDataResult,
        gcs_result: CloudDataResult,
    ) -> CompanyAssets:
        """
        Apply cloud-priority logic.
        When cloud data is available, suppress the corresponding local data.
        """
        if bq_result.is_connected:
            return CompanyAssets(
                intro_text=assets.intro_text,
                prompt_text=assets.prompt_text,
                prompt_files=assets.prompt_files,
                knowledge_text=assets.knowledge_text,
                knowledge_files=assets.knowledge_files,
                structured_text="",
                structured_files=[],
                unstructured_text="" if gcs_result.is_connected else assets.unstructured_text,
                unstructured_files=[] if gcs_result.is_connected else assets.unstructured_files,
                smart_cards=assets.smart_cards,
                dirs=assets.dirs,
            )
        if gcs_result.is_connected:
            return CompanyAssets(
                intro_text=assets.intro_text,
                prompt_text=assets.prompt_text,
                prompt_files=assets.prompt_files,
                knowledge_text=assets.knowledge_text,
                knowledge_files=assets.knowledge_files,
                structured_text=assets.structured_text,
                structured_files=assets.structured_files,
                unstructured_text="",
                unstructured_files=[],
                smart_cards=assets.smart_cards,
                dirs=assets.dirs,
            )
        return assets
