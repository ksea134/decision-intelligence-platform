"""
infra/file_loader.py

【修正履歴】
- 2026-03-16: load_smart_cards() で空ファイルの場合はデフォルト値を維持するよう修正
"""
from __future__ import annotations
import copy, csv, logging, os, re
from pathlib import Path
from typing import Any
from config.app_config import PATHS
from domain.models import CompanyAssets, LoadedDirectory

logger = logging.getLogger(__name__)

try:
    import pypdf
    _PDF_READY = True
except ImportError:
    _PDF_READY = False

_RE_UNSAFE_FNAME = re.compile(r"[^\w\-]")
_RE_UNSAFE_ID    = re.compile(r"[^a-zA-Z0-9_]")

def load_companies(csv_path: str) -> dict[str, str]:
    companies: dict[str, str] = {}
    path = Path(csv_path)
    if not path.exists():
        logger.warning("companies.csv not found: %s", csv_path)
        return companies
    try:
        with path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) >= 2:
                    companies[row[0].strip()] = row[1].strip()
    except Exception as exc:
        logger.error("companies.csv read error: %s", exc)
    return companies

def load_company_assets(base_dir: str) -> CompanyAssets:
    dirs = _resolve_dirs(base_dir)
    prompt_dir       = load_directory(dirs["prompts"],      (".txt", ".md", ".pdf"), False)
    knowledge_dir    = load_directory(dirs["knowledge"],    (".txt", ".md", ".pdf"), False)
    intro_dir        = load_directory(dirs["introduction"], (".txt", ".md"),          False)
    structured_dir   = load_directory(dirs["structured"],   (".csv", ".txt"),         True)
    unstructured_dir = load_directory(dirs["unstructured"], (".txt", ".md", ".pdf"),  True)
    smart_cards      = load_smart_cards(dirs["smart_cards"])
    return CompanyAssets(
        intro_text=intro_dir.content,
        prompt_text=prompt_dir.content,
        prompt_files=prompt_dir.files,
        knowledge_text=knowledge_dir.content,
        knowledge_files=knowledge_dir.files,
        structured_text=structured_dir.content,
        structured_files=structured_dir.files,
        unstructured_text=unstructured_dir.content,
        unstructured_files=unstructured_dir.files,
        smart_cards=smart_cards,
        dirs=dirs,
    )

def load_directory(directory_path: str, extensions: tuple[str, ...], add_filename_tag: bool) -> LoadedDirectory:
    base = Path(directory_path)
    if not base.exists() or not base.is_dir():
        return LoadedDirectory(content="", files=[])
    content_parts: list[str] = []
    files: list[str] = []
    for file_path in sorted(base.iterdir(), key=lambda p: p.name):
        if file_path.name.startswith("."):
            continue
        if file_path.suffix.lower() not in extensions:
            continue
        text = _read_file(file_path)
        if text is None:
            continue
        if add_filename_tag:
            suffix = "(PDF)" if file_path.suffix.lower() == ".pdf" else ""
            tag = f"\n[FILE_NAME{suffix}: {file_path.name}]\n"
            content_parts.append(f"{tag}{text}")
        else:
            content_parts.append(text)
        files.append(file_path.name)
    return LoadedDirectory(content="\n".join(content_parts).strip(), files=files)

def load_smart_cards(smart_cards_dir: str) -> list[dict[str, Any]]:
    """
    スマートカードの読み込み。
    
    企業別の smart_cards/ ディレクトリにカスタムプロンプトがあれば上書きする。
    
    【修正】空ファイルの場合はデフォルト値を維持する。
    これにより、空の .md/.txt ファイルが存在しても Gemini API エラーを防げる。
    """
    from infra._smart_card_defaults import DEFAULT_SMART_CARDS
    cards = copy.deepcopy(DEFAULT_SMART_CARDS)
    base = Path(smart_cards_dir)
    if not base.exists():
        return cards
    for card in cards:
        for ext in (".md", ".txt"):
            candidate = base / f"{card['id']}{ext}"
            if candidate.exists():
                try:
                    content = candidate.read_text(encoding="utf-8").strip()
                    # 【修正】空のファイルの場合はデフォルト値を維持（Gemini API 400エラー防止）
                    if content:
                        card["prompt_template"] = content
                    else:
                        logger.warning(
                            "smart card file is empty, using default: %s (default: %s)",
                            candidate, card["prompt_template"][:50] + "..."
                        )
                except Exception as exc:
                    logger.warning("smart card read error (%s): %s", candidate, exc)
                break
    return cards

def safe_filename(name: str) -> str:
    return _RE_UNSAFE_FNAME.sub("_", name)

def safe_dom_id(name: str) -> str:
    return _RE_UNSAFE_ID.sub("", name)

def _resolve_dirs(base_dir: str) -> dict[str, str]:
    return {
        "structured":   os.path.join(base_dir, PATHS.structured),
        "unstructured": os.path.join(base_dir, PATHS.unstructured),
        "prompts":      os.path.join(base_dir, PATHS.prompts),
        "knowledge":    os.path.join(base_dir, PATHS.knowledge),
        "introduction": os.path.join(base_dir, PATHS.introduction),
        "templates":    os.path.join(base_dir, PATHS.templates),
        "smart_cards":  os.path.join(base_dir, PATHS.smart_cards),
    }

def _read_file(path: Path) -> str | None:
    try:
        if path.suffix.lower() == ".pdf":
            return _read_pdf(path)
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.warning("file read error (%s): %s", path.name, exc)
        return None

def _read_pdf(path: Path) -> str | None:
    if not _PDF_READY:
        return None
    try:
        reader = pypdf.PdfReader(str(path))
        return "".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        logger.warning("PDF read error (%s): %s", path.name, exc)
        return None
