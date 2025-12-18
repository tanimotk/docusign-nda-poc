# DocuSign NDA POC

DocuSign API を使用した NDA（秘密保持契約）締結機能の検証用スクリプト集です。

## 概要

このPOCは、DCP（Digital Community Platform）における NDA 締結フローを DocuSign API で実装するための検証を目的としています。

### 主な機能

- JWT Grant 認証によるアクセストークン取得
- 単一署名者へのエンベロープ送信
- Signing Group（複数署名者、1人署名で完了）対応
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
│   └── webhook_service.py    # Webhook 処理サービス
├── tests/
│   ├── test_auth.py                      # JWT 認証テスト
│   ├── test_envelope_simple.py           # 単一署名者テスト
│   ├── test_envelope_recipient_group.py  # Signing Group テスト
│   └── test_check_status.py              # ステータス確認/PDF取得
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
python docusign_nda_poc/run_tests.py 1  # JWT 認証テスト
python docusign_nda_poc/run_tests.py 2  # 単一署名者テスト
python docusign_nda_poc/run_tests.py 3  # Signing Group テスト
python docusign_nda_poc/run_tests.py 4  # ステータス確認
```

## テスト内容

### Test 1: JWT 認証テスト

DocuSign への JWT 認証が正常に動作するか確認します。

- アクセストークンの取得
- Account ID / Base URI の取得
- トークンキャッシュの動作確認

**初回実行時**: Consent（同意）が必要な場合、URL が表示されます。ブラウザで開いて承認してください。

### Test 2: 単一署名者テスト

1人の署名者に対してエンベロープを送信します。

- 入力: 署名者のメールアドレス、名前
- 使用PDF: `app/static/demo_documents/World_Wide_Corp_lorem.pdf`
- 署名依頼メールが送信されます

### Test 3: Signing Group テスト

複数の署名者を指定し、**誰か1人が署名すれば完了**となるエンベロープを送信します。

- 入力: 2名以上の署名者（メールアドレス、名前）
- 全員に署名依頼メールが送信される
- 1人が署名すると、他のメンバーには完了通知が届く

これは仕様書の「Academia/Startup側の複数TOメンバーのうち1人が署名すればOK」要件に対応しています。

**実装詳細**: DocuSign の `SigningGroup` API を使用。エンベロープ作成時に一時的な Signing Group を動的に作成し、送信後に削除する方式（アカウント上限50グループを回避）。

> **注意**: DocuSign SDK の `RecipientGroup` クラスは全員にメールが届かないため使用不可。`SigningGroup` を使用すること。

### Test 4: ステータス確認 / PDF 取得

既存のエンベロープのステータスを確認し、完了していれば署名済みPDFをダウンロードします。

- 入力: Envelope ID（Test 2/3 実行後に保存される）
- 出力: `tests/signed_XXXXXXXX.pdf`

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

### 本番環境への対応（TODO）

VC/Pharma がアップロードする NDA PDF に埋め込むアンカータグを事前に決定し、ガイドラインとして提供する必要があります。

例:
- 署名欄: `/sn1/` を署名位置に白文字で記載
- 日付欄: `/dn1/` を日付位置に白文字で記載

詳細は `models/nda_request.py` の TODO コメントを参照してください。

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

## 次のステップ

1. FastAPI Clean Architecture への統合
2. 本番環境用アンカータグの決定
3. 通知設定の調整
4. HMAC 署名検証の有効化

## 関連ドキュメント

- [Notion 仕様書: DocuSign連携・NDA締結機能](https://www.notion.so/DocuSign-NDA-2b933e5f7882813eb1f4e0782e63902f)
- [DocuSign eSignature REST API](https://developers.docusign.com/docs/esign-rest-api/)
- [JWT Grant Authentication](https://developers.docusign.com/platform/auth/jwt/)
