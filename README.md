# わんコメ × AITuberKit 連携システム

Python で実装された OneComme (わんコメ) と AITuberKit を連携させる中間プログラムです。
Windows 上で `run.bat` をダブルクリックするだけで起動でき、OneComme から受信したコメントを AITuberKit へ送信して AI 応答をトリガーします。

## 主な機能

- 優先度付きコメント処理 (トリガーワード・初訪問判定)
- 2 段階 AI 判断 (軽量判定 → LLM 判定)
- 優先度付きキューと CPU ロード制御
- 初訪問者向け挨拶と会話履歴タグ挿入
- AITuberKit External Adapter への REST API 呼び出し
- ログ出力 (`logs/system.log`) と統計 (`logs/stats.json`)

## セットアップ手順

1. **Python と仮想環境の準備**
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **設定ファイルの作成**
   ```powershell
   copy .env.example .env
   ```
   `.env` を開き、環境に合わせて以下を設定します。

   | 項目 | 説明 |
   | ---- | ---- |
   | `ONECOMME_WS_URL` | わんコメ WebSocket URL。`{STREAM_ID}` を含めると `ONECOMME_STREAM_IDS` の各 ID が差し込まれます (例: `ws://localhost:11180/api/director/{STREAM_ID}`) |
   | `ONECOMME_STREAM_IDS` | 視聴 URL などから取得できる配信 ID をカンマ区切りで指定 (例: `4011...,5e46...,c1af...`) |
   | `ONECOMME_WS_URLS` | (任意) 完全な WebSocket URL を複数列挙したい場合に使用。`ONECOMME_WS_URL` と併用可能 |
   | `AITUBERKIT_BASE_URL` | AITuberKit のベース URL |
   | `AITUBERKIT_CLIENT_ID` | External Adapter の Client ID |
   | その他 | コメント判定・キュー・ログなどの設定 |

3. **起動**
   仮想環境を有効化した状態、もしくは `run.bat` をダブルクリックして起動します。
   ```powershell
   run.bat
   ```

4. **停止**
   コンソールで `Ctrl + C` を押すか、ウィンドウを閉じて終了します。

## ローカルテスト

開発時は次のコマンドでユニットテストを実行できます。

```bash
python -m unittest discover tests
```

## フォルダ構成

```
onecomme-aituberkit-bridge/
├── .env.example             # 設定ファイルのサンプル
├── README.md                # 本ドキュメント
├── requirements.txt         # 依存パッケージ
├── run.bat                  # Windows 用起動スクリプト
├── run.py                   # エントリポイント (Windows 以外向け)
├── src/
│   ├── aituberkit_client.py # AITuberKit REST クライアント
│   ├── config.py            # 設定読み込み
│   ├── judge.py             # コメント判定ロジック
│   ├── logger.py            # ログ・統計管理
│   ├── main.py              # メインイベントループ
│   ├── monitor.py           # CPU モニター
│   ├── onecomme_client.py   # OneComme WebSocket クライアント
│   ├── prompt_builder.py    # プロンプト生成
│   └── queue_manager.py     # 優先度付きキュー
└── tests/
    └── test_judge.py        # 判定ロジックのユニットテスト
```

## 注意事項

- `.env` は必ず UTF-8 で保存してください。
- AITuberKit 側で External Adapter 機能を有効化し、指定した `clientId` を設定してください。
- 高負荷時にはコメント処理が一時停止したり、LLM 判定がスキップされることがあります。

## ライセンス

本リポジトリ内のコードは、提供された仕様に基づいて作成されています。利用ポリシーに従ってご利用ください。
