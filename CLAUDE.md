# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DocuSign NDA POC - DCP（Digital Community Platform）向けのNDA締結機能検証プロジェクト。DocuSign eSignature REST API を JWT Grant 認証で使用。

## Commands

```bash
# テストを実行（メニュー形式）
uv run docusign_nda_poc/run_tests.py

# 個別テスト
uv run docusign_nda_poc/run_tests.py 1  # JWT認証
uv run docusign_nda_poc/run_tests.py 2  # 単一署名者
uv run docusign_nda_poc/run_tests.py 3  # Signing Group（複数署名者、1人署名で完了）
uv run docusign_nda_poc/run_tests.py 4  # ステータス確認/PDF取得

# Webhookサーバー起動
uv run docusign_nda_poc/webhook_server.py
# 別ターミナルで ngrok http 8000
```

## Architecture

```
docusign_nda_poc/
├── auth/jwt_auth.py          # JWT認証（トークンキャッシュ付き）
├── services/
│   ├── envelope_service.py   # エンベロープ作成・管理
│   └── webhook_service.py    # Webhook処理
├── models/
│   ├── nda_request.py        # NDARequest, WebhookConfig, EnvelopeResponse
│   └── webhook_event.py      # Webhookイベントパース・HMAC検証
└── tests/                    # 対話式テストスクリプト
```

## Key Implementation Details

### Signing Group（複数署名者、1人署名で完了）

`EnvelopeService.create_envelope_with_signing_group()` は：
1. SigningGroupsApi で一時的なSigning Groupを動的作成
2. そのsigning_group_idでエンベロープを送信
3. 送信後にSigning Groupを削除（アカウント上限50回避）

**重要**: DocuSign の `RecipientGroup` は全員にメールが届かない。「複数人にメール、1人署名で完了」の要件には `SigningGroup` を使用する。

### Webhook設定

管理画面ではなく API経由（EventNotification）で設定。NDARequest に WebhookConfig を渡すとエンベロープ作成時にWebhook URLが登録される。

### アンカータグ

署名欄配置はPDF内のテキストマーカーを使用。サンプルPDFは `/sn1/` を使用。本番では VC/Pharma がアップロードするPDFのアンカータグガイドラインが必要。

## Environment

- デモ環境: `demo.docusign.net`
- 認証サーバー: `account-d.docusign.com`
- 秘密鍵: `app/private.key`（gitignore済み）

## 実装時のルール

外部APIやSDKを使用する機能を実装する際は、以下を守ること：

1. **実装前にAPIの動作仕様を確認する** - クラス名やメソッド名だけで判断せず、公式ドキュメントで実際の動作を確認してから実装に入る
2. **最小限のコードで動作確認してから本実装する** - 思い込みで本実装に入らず、まず小さなテストで期待通りの動作をするか検証する
3. **要件の重要ポイントを検証対象として認識する** - 例：「複数人へのメール送信が必須」なら、その点が満たされるかを必ず確認する
