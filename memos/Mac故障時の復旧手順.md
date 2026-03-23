# Mac故障時の開発環境復旧手順

> 作成日: 2026-03-21
> 更新日: 2026-03-21

---

## 概要

Macが故障しても、以下の理由で開発継続に致命的な影響はありません：

| 保存先 | 内容 | 状態 |
|--------|------|------|
| **GitHub** | ソースコード全体 | ✅ クラウドに保存済み |
| **Cloud Run** | 本番環境 | ✅ 動き続ける |
| **Google Cloud** | BigQuery、GCSなどのデータ | ✅ クラウドに保存済み |

**新しいMacがあれば、以下の手順で完全復旧できます。**

---

## 前提条件

新しいMacに以下がインストールされていること：

| ソフトウェア | 確認コマンド | インストール方法 |
|-------------|-------------|-----------------|
| Homebrew | `brew --version` | `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"` |
| Git | `git --version` | `brew install git` |
| Python 3.11 | `python3 --version` | `brew install python@3.11` |
| Node.js | `node --version` | `brew install node` |
| Google Cloud SDK | `gcloud --version` | `brew install --cask google-cloud-sdk` |

---

## 復旧手順

### ステップ1：GitHubからコードをクローン

```bash
cd ~
git clone https://github.com/ksea134/decision-intelligence-platform.git dip
cd ~/dip
```

**確認:**
```bash
ls -la
```
→ backend、frontend、config などのフォルダが見えればOK

---

### ステップ2：Python仮想環境を作成

```bash
cd ~/dip
python3 -m venv .venv
source .venv/bin/activate
```

**確認:**
```bash
which python
```
→ `/Users/あなたのユーザー名/dip/.venv/bin/python` と表示されればOK

---

### ステップ3：Pythonパッケージをインストール

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**所要時間:** 3〜5分

**確認:**
```bash
pip list | head -20
```
→ fastapi、uvicorn、langchain などが表示されればOK

---

### ステップ4：Node.js依存関係をインストール

```bash
cd ~/dip/frontend
npm install
```

**所要時間:** 1〜2分

**確認:**
```bash
ls node_modules | head -10
```
→ フォルダが複数表示されればOK

---

### ステップ5：Google Cloud認証

#### 5-1. ログイン
```bash
gcloud auth login
```
→ ブラウザが開くのでGoogleアカウントでログイン

#### 5-2. プロジェクト設定
```bash
gcloud config set project decision-support-ai
```

#### 5-3. アプリケーションデフォルト認証
```bash
gcloud auth application-default login
```
→ 再度ブラウザでログイン

**確認:**
```bash
gcloud config get-value project
```
→ `decision-support-ai` と表示されればOK

---

### ステップ6：環境変数・シークレットの設定

#### 6-1. .envファイルの作成（バックエンド用）

`~/dip/.env` ファイルを作成し、以下の内容を設定：

```
# Google Cloud
GCP_PROJECT_ID=decision-support-ai
GCP_REGION=asia-northeast1

# その他必要な環境変数
# （旧Macのバックアップがあれば、そこからコピー）
```

#### 6-2. secrets.tomlの確認（存在する場合）

```bash
ls ~/dip/config/secrets.toml
```

存在しない場合は、Google Cloud Secret Managerから取得するか、チームメンバーから入手。

---

### ステップ7：動作確認

#### 7-1. バックエンド起動
```bash
cd ~/dip && source .venv/bin/activate && uvicorn backend.main:app --reload --port 8000
```

**確認:**
- `Application startup complete.` と表示される
- ブラウザで http://localhost:8000/docs を開いてSwagger UIが表示される

#### 7-2. フロントエンド起動（別タブで）
```bash
cd ~/dip/frontend && npm run dev 2>/dev/null
```

**確認:**
- `Ready in XXXms` と表示される
- ブラウザで http://localhost:3000 を開いてDipアプリが表示される

#### 7-3. 統合確認
- 企業を選択できる
- 質問を送信して回答が返ってくる

---

## バックアップしておくべきファイル

以下のファイルはGitHubに含まれていない可能性があるため、**別途バックアップ推奨**：

| ファイル | 場所 | 内容 |
|----------|------|------|
| `.env` | ~/dip/.env | 環境変数 |
| `secrets.toml` | ~/dip/config/secrets.toml | APIキーなど |
| `.streamlit/secrets.toml` | ~/dip/.streamlit/secrets.toml | Streamlit用シークレット（旧構成の場合） |

### バックアップ方法

```bash
# USBドライブやクラウドストレージにコピー
cp ~/dip/.env /Volumes/USBドライブ/dip_backup/
cp ~/dip/config/secrets.toml /Volumes/USBドライブ/dip_backup/
```

または、Google Driveなどにアップロード。

---

## トラブルシューティング

### 「pip install で SSL エラー」

```bash
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```

### 「npm install で権限エラー」

```bash
sudo chown -R $(whoami) ~/dip/frontend/node_modules
npm install
```

### 「gcloud auth でブラウザが開かない」

```bash
gcloud auth login --no-launch-browser
```
→ 表示されるURLを手動でブラウザにコピペ

### 「BigQueryに接続できない」

```bash
gcloud auth application-default login
```
→ 再度認証を実行

---

## 復旧完了チェックリスト

- [ ] GitHubからクローン完了
- [ ] Python仮想環境作成・パッケージインストール完了
- [ ] Node.js依存関係インストール完了
- [ ] Google Cloud認証完了
- [ ] 環境変数・シークレット設定完了
- [ ] バックエンド起動確認
- [ ] フロントエンド起動確認
- [ ] 企業選択・質問応答の動作確認

---

## 所要時間の目安

| 作業 | 時間 |
|------|------|
| ソフトウェアインストール | 15〜30分 |
| コードクローン | 1分 |
| Pythonパッケージインストール | 5分 |
| Node.jsパッケージインストール | 2分 |
| Google Cloud認証 | 5分 |
| 動作確認 | 5分 |
| **合計** | **約30〜50分** |

---

## 緊急連絡先

復旧でき​ない場合の連絡先：

- **GitHub リポジトリ:** https://github.com/ksea134/decision-intelligence-platform
- **Cloud Run URL（本番）:** https://dip-897403315215.asia-northeast1.run.app
- **GCPプロジェクト:** decision-support-ai（Google Cloud Console）
