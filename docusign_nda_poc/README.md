# DocuSign NDA POC

DocuSign API を使用した署名機能の検証用スクリプト集です。

## 概要

DocuSign eSignature REST API の基本機能を検証するためのサンプルです。

### 主な機能

- JWT Grant 認証によるアクセストークン取得
- Signing Group（複数人に送信、1人署名で完了）対応
  - アンカータグ方式（PDF内に署名位置を埋め込み）
  - Free Form 方式（署名者が位置を選択）
- **Template 方式**（PDFをDocuSign上に保存して再利用）
  - テンプレート作成・管理
  - テンプレートからの署名依頼送信
- エンベロープステータス確認
- 署名済みPDFのダウンロード
- Webhook（DocuSign Connect）によるイベント受信

## ディレクトリ構成

```
docusign_nda_poc/
├── README.md                 # このファイル
├── config.py                 # DocuSign API 設定
├── run_tests.py              # テストランナー（メニュー形式）
├── webhook_server.py         # Webhook テスト用 FastAPI サーバー
├── auth/
│   └── jwt_auth.py           # JWT 認証ハンドラー
├── models/
│   ├── nda_request.py        # リクエスト/レスポンスモデル
│   └── webhook_event.py      # Webhook イベントモデル
├── services/
│   ├── envelope_service.py   # エンベロープ操作サービス
│   ├── template_service.py   # テンプレート操作サービス
│   └── webhook_service.py    # Webhook 処理サービス
├── tests/
│   ├── test_auth.py                      # JWT 認証テスト
│   ├── test_envelope_recipient_group.py  # Signing Group テスト（Anchor）
│   ├── test_envelope_free_form.py        # Signing Group テスト（Free Form）
│   ├── test_check_status.py              # ステータス確認/PDF取得
│   ├── test_template_create.py           # テンプレート作成
│   └── test_template_send.py             # テンプレートから送信
└── webhook_output/           # 受信した Webhook データの保存先
```

## 前提条件

1. Python 3.10 以上
2. DocuSign Developer Account
3. 以下の情報が設定済みであること（`config.py` で参照）:
   - Integration Key (Client ID)
   - User ID (Impersonated User)
   - RSA Private Key (`app/private.key`)

## セットアップ

```bash
# 依存パッケージのインストール
pip install docusign_esign fastapi uvicorn

# または uv を使用
uv pip install docusign_esign fastapi uvicorn
```

## 起動方法

### メニュー形式で実行

```bash
cd "/home/k-tanimoto/source/scripts/Quickstart App-1-python"
python docusign_nda_poc/run_tests.py

# または uv を使用
uv run docusign_nda_poc/run_tests.py
```

### 個別テストを直接実行

```bash
# テスト番号を引数で指定

# --- PDF Upload 方式 ---
python docusign_nda_poc/run_tests.py 1  # JWT 認証テスト
python docusign_nda_poc/run_tests.py 2  # Signing Group テスト（Anchor）
python docusign_nda_poc/run_tests.py 3  # Signing Group テスト（Free Form）
python docusign_nda_poc/run_tests.py 4  # ステータス確認

# --- Template 方式 ---
python docusign_nda_poc/run_tests.py 5  # テンプレート作成
python docusign_nda_poc/run_tests.py 6  # テンプレートから送信
```

## 2つの実装方式

### PDF Upload 方式（Test 2-3）

署名依頼のたびにPDFをアップロードする方式です。

```
[サービス側] PDF生成 → [DocuSign] アップロード → 署名依頼送信
```

**メリット:**
- 動的にPDFを生成できる
- テンプレート管理が不要

**デメリット:**
- 毎回PDFをアップロードする必要がある
- サービス側でPDFを保持する必要がある

### Template 方式（Test 5-6）

PDFをDocuSign上にテンプレートとして保存し、再利用する方式です。

```
[初回] PDF → DocuSign にテンプレート作成（Test 5）
[以降] テンプレートID指定 → 署名依頼送信（Test 6）
```

**メリット:**
- PDFアップロードが不要（テンプレートID指定のみ）
- サービス側でPDFを保持しなくてよい
- 署名依頼が高速

**デメリット:**
- VCごとにテンプレート管理が必要
- テンプレート更新時は再作成

## テスト内容

### Test 1: JWT 認証テスト

DocuSign への JWT 認証が正常に動作するか確認します。

- アクセストークンの取得
- Account ID / Base URI の取得
- トークンキャッシュの動作確認

**初回実行時**: Consent（同意）が必要な場合、URL が表示されます。ブラウザで開いて承認してください。

### Test 2: Signing Group テスト（Anchor）

複数人に署名依頼を送信し、**誰か1人が署名すれば完了**となるエンベロープを作成します。

- 入力: 1名以上の署名者（メールアドレス、名前）
- 全員に署名依頼メールが送信される
- 1人が署名すると、他のメンバーには完了通知が届く
- 署名位置: PDF内のアンカータグ `/sn1/` で自動配置

**実装詳細**: DocuSign の `SigningGroup` API を使用。エンベロープ作成時に一時的な Signing Group を動的に作成し、送信後に削除する方式（アカウント上限50グループを回避）。

> **注意**: DocuSign SDK の `RecipientGroup` クラスは全員にメールが届かないため使用不可。`SigningGroup` を使用すること。

### Test 3: Signing Group テスト（Free Form）

Test 2 と同様の Signing Group 機能ですが、署名位置を署名者が自分で選択します。

- 入力: 1名以上の署名者（メールアドレス、名前）
- 署名位置: 署名者がPDF上で自分でドラッグ配置
- アンカータグが埋め込まれていないPDF（ユーザーアップロードPDF等）に対応

### Test 4: ステータス確認 / PDF 取得

既存のエンベロープのステータスを確認し、完了していれば署名済みPDFをダウンロードします。

- 入力: Envelope ID（Test 2/3/6 実行後に保存される）
- 出力: `tests/signed_XXXXXXXX.pdf`

### Test 5: テンプレート作成

PDFをDocuSign上にテンプレートとして保存します。

- 入力: PDF ファイル、テンプレート名
- 出力: Template ID（`tests/last_template_id.txt` に保存）
- 署名位置はアンカータグ `/sn1/` で指定

### Test 6: テンプレートから送信

既存のテンプレートを使って署名依頼を送信します。

- 入力: Template ID、署名者情報
- PDFアップロード不要（DocuSign上のテンプレートを使用）
- 単一署名者 / Signing Group（複数署名者）どちらも対応

## Template 方式のコード例

### テンプレート作成

```python
from docusign_nda_poc.services.template_service import TemplateService

service = TemplateService()

# PDFをテンプレートとして登録
template_info = service.create_template(
    document_base64=pdf_base64,
    document_name="contract.pdf",
    template_name="My Template",
    template_description="サンプルテンプレート",
)

# Template ID を保存
template_id = template_info.template_id
```

### 署名依頼送信

```python
# 単一署名者
response = service.create_envelope_from_template(
    template_id=template_id,
    signer_email="signer@example.com",
    signer_name="署名者",
)

# Signing Group（複数人に送信、1人署名で完了）
response = service.create_envelope_from_template_with_signing_group(
    template_id=template_id,
    signers=[
        {"name": "署名者A", "email": "a@example.com"},
        {"name": "署名者B", "email": "b@example.com"},
    ],
)
```

### テンプレート更新・削除

```python
# ドキュメントを更新
service.update_template_document(
    template_id=template_id,
    document_base64=new_pdf_base64,
    document_name="contract_v2.pdf",
)

# テンプレートを削除
service.delete_template(template_id)
```

## アンカータグについて

署名欄の配置には**アンカータグ方式**を使用しています。

```
PDF内のテキスト    →  APIで指定    →  署名欄が自動配置
    /sn1/              /sn1/
```

### 現在の設定（サンプルPDF用）

| 用途 | アンカータグ | 備考 |
|------|-------------|------|
| 署名欄 | `/sn1/` | サンプルPDFに埋め込み済み |
| 日付欄 | `/sn1/` + オフセット | 暫定対応 |

### カスタムPDFを使用する場合

署名位置を自動配置するには、PDF内にアンカータグを埋め込む必要があります。

例:
- 署名欄: `/sn1/` を署名位置に白文字で記載
- 日付欄: `/dn1/` を日付位置に白文字で記載

アンカータグを埋め込まないPDFの場合は、Free Form方式（Test 3）を使用してください。

## 注意事項

- **秘密鍵の管理**: `private.key` は `.gitignore` に含まれています。絶対にコミットしないでください。
- **送信者への通知**: DocuSign の仕様により、API 実行ユーザー（送信者）にも通知メールが届きます。本番では通知設定の調整が必要です。
- **デモ環境**: 現在はデモ環境（`demo.docusign.net`）を使用しています。

## Webhook テスト

DocuSign Connect からの Webhook を受信するためのテストサーバーを用意しています。

### Webhook 設定方法

このPOCでは **API経由（EventNotification）** でWebhookを設定します。管理画面での設定は不要です。

#### メリット
- エンベロープごとに個別のWebhook URLを設定可能
- 管理画面へのアクセス権限が不要
- 本番環境と同じ方式でテスト可能

### Webhook サーバーの起動

```bash
# サーバー起動
uv run docusign_nda_poc/webhook_server.py

# 別ターミナルで ngrok を起動
ngrok http 8000
```

### Webhook を使用したテスト手順

1. Webhook サーバーを起動（上記コマンド）
2. ngrok を起動して公開URL を取得
3. Signing Group テスト（Test 3）を実行
4. Webhook URL の入力を求められたら、ngrok の URL + `/webhook/docusign` を入力
   - 例: `https://xxxx.ngrok-free.app/webhook/docusign`
5. 署名完了時、Webhook が自動的に呼び出される

### Webhook 受信の確認方法

```bash
# 受信したWebhookファイルの一覧
ls -la docusign_nda_poc/webhook_output/

# 受信データの内容を確認
cat docusign_nda_poc/webhook_output/xml_payload_*.json

# ブラウザで確認（サーバー起動中）
# http://localhost:8000/webhooks
```

### Webhook エンドポイント

| エンドポイント | メソッド | 説明 |
|---------------|---------|------|
| `/` | GET | ヘルスチェック |
| `/webhook/docusign` | POST | Webhook 受信 |
| `/webhooks` | GET | 受信した Webhook 一覧 |
| `/webhooks/{filename}` | GET | 個別の Webhook データ |

### 受信データの確認

Webhook で受信したデータは `webhook_output/` ディレクトリに保存されます:
- `raw_*.json` - 生のペイロード
- `processed_*.json` - 処理結果
- `signed_*.pdf` - 署名済み PDF（completed 時）

### Webhook イベントの処理

`WebhookService` は以下のイベントを処理します:

| イベント | 処理内容 |
|---------|---------|
| `envelope-completed` | 署名済み PDF をダウンロード |
| `envelope-declined` | 拒否者情報を記録 |
| `envelope-voided` | 無効化を記録 |

### API経由での Webhook 設定（コード例）

```python
from docusign_nda_poc.models.nda_request import NDARequest, WebhookConfig

# Webhook URL を設定してエンベロープを作成
nda_request = NDARequest(
    document_base64=document_base64,
    document_name="NDA.pdf",
    signers=[Signer(name="田中太郎", email="tanaka@example.com")],
    webhook_config=WebhookConfig(
        url="https://your-server.com/webhook/docusign",
        envelope_events=["completed", "declined", "voided"],
        include_documents=False,  # True にすると署名済みPDFがペイロードに含まれる
    ),
)

# または fluent API を使用
nda_request = NDARequest(...).set_webhook(
    url="https://your-server.com/webhook/docusign"
)
```

### HMAC 署名検証（本番用）

本番環境では HMAC 署名検証を有効にしてください。

**注意**: API経由（EventNotification）の場合、HMACキーはDocuSign管理画面のConnectセクションで生成する必要があります。

```python
# webhook_server.py
webhook_service = WebhookService(hmac_key="your-hmac-key-from-docusign")
```

DocuSign Connect 設定で HMAC キーを生成し、`X-DocuSign-Signature-1` ヘッダーで検証します。

## 関連ドキュメント

- [DocuSign eSignature REST API](https://developers.docusign.com/docs/esign-rest-api/)
- [JWT Grant Authentication](https://developers.docusign.com/platform/auth/jwt/)
- [Templates API](https://developers.docusign.com/docs/esign-rest-api/reference/templates/)
