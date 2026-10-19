# Expo × Artemis

Expo の Android アプリを [google/artemis](https://github.com/google/artemis) で操作する検証用プロジェクト。
タスクの追加・完了・リセットができる小さなアプリと、自然言語による E2E テストを含む。

## 前提

- Nix / direnv。`direnv allow` または `nix develop` で開発環境に入る。
- Android SDK とライセンス承諾済みのビルド環境。既存 SDK を `ANDROID_HOME` に設定する。
- USB デバッグを有効にした Android 実機（既定は Pixel）。接続時に端末上で PC を許可する。
- Artemis が利用するモデルの API キー。利用に応じてモデル API の料金が発生する。

Artemis は Android 対応。画面情報をモデルに送るので、このサンプルのテスト画面で試す。
本リポジトリでは Expo Go ではなく専用パッケージ `dev.kexi.artemishoge` をビルドする。

## 1. サンプルを起動

```sh
just setup-project
cp .env.example .env
just check-device
```

`.env` の `ADB_DEVICE_SERIAL` に `adb devices -l` の対象端末 ID を記入する。
キーや端末 ID をコミットしない。`.env` は git の対象外。

```sh
just install-android
```

これは初回のネイティブビルド・インストールと Metro 起動を行う。
一度インストールした後は `just connect-metro` と `just start-expo` で再開できる。
テスト中は Metro を起動したままにし、端末のロックを解除しておく。

## 2. Artemis を起動

別ターミナルで Artemis のソースを ghq 配下に用意する。
このターミナルでも先に本リポジトリで `nix develop` に入り、管理画面が要求する新しい Node.js を使用する。
以下は fish 用。上流の `start.sh` はシステムツールやグローバル設定の自動変更を含むため、ここでは CLI を直接使う。

```fish
ghq get https://github.com/google/artemis
cd (ghq list -p -e github.com/google/artemis)
git checkout --detach 351ca8422f7b5b54e80a9c1ce03a222e02415b6b
uv sync --exclude-newer '1 day'
cp .env.example .env
```

**Artemis 側の `.env`** に `GEMINI_API_KEY` と同じ `ADB_DEVICE_SERIAL` を設定する。
サンプル側の `.env` に API キーを置く必要はない。キーはチャットやソースコードに貼らない。
利用できるモデルが上流の `config/artemis.jsonc` に設定されているかも確認する。
Artemis は初回に端末へ Accessibility Helper をインストールする。公式 README に削除方法もある。

```sh
uv run --frozen artemis doctor
uv run --frozen artemis ui --host 127.0.0.1 --port 8000
```

ブラウザーで `http://127.0.0.1:8000` を開いて接続・モデル設定を確認する。
このサーバーには組み込みのリモート認証がないため、ローカルで使う。
MCP のグローバル登録はこの検証には不要。

## 3. 自動テスト

このリポジトリに戻り、別ターミナルで実行する。

```sh
just test-android
```

テストの流れ：

1. サンプルを起動し、リセットして空の一覧を確認する。
2. 空欄では追加ボタンが無効なことを確認する。
3. `Buy milk` を追加し、未完了タスクが1件あることを確認する。
4. チェックして完了にし、完了数が1件になることを確認する。

Artemis は `pro` / `strict` で各項目を検証する。
さらに Python が Android UI ツリーを読み、対象パッケージに「タスク 1件 / 完了 1件」と
チェック済みの `Buy milk` が存在することを独立に検証する。
途中の操作と空欄チェックの判定は Artemis に依存し、AI テストには揺らぎがある。
完了報告だけで合格にせず、最終画面の検証にも成功した場合だけ終了コード 0 を返す。
`completed` でもアサーションが失敗している場合があるため、`/checks` の検証台帳も取得する。
失敗・未検証を拒否し、すべての検証項目に成功判定があることを確認する。
上流が接頭辞の有無で重複記録する項目は、同じ項目として照合する。
10分でタイムアウトした場合はタスクの停止を要求する。

結果は `artifacts/<trace-id>/` に保存する。

- `result.json`: Artemis の結果（取得できた場合）
- `checks.json`: アサーションの結果と根拠
- `screen.xml`: 最終画面の UI ツリー（Artemis 成功時）
- `screen.png`: 終了時のスクリーンショット（端末が応答する場合）

接続エラーは Artemis サーバー、端末 ID、USB デバッグを確認する。
アプリの読み込みエラーは Metro と `adb reverse`、モデルエラーは Artemis 側の認証・モデル設定を確認する。

## LM Studio の Gemma 4 で実験する

LM Studio の CLI `lms` が利用できる環境で、MLX 版のモデルを取得してロードする。
26B-A4B・4bit 版は約15.6GB。初回はダウンロードに時間がかかる。

```sh
lms get https://huggingface.co/lmstudio-community/gemma-4-26B-A4B-it-MLX-4bit --mlx --yes
lms ls
```

`lms ls` に表示されたモデルキーを使い、API で使う別名を `artemis-gemma4` にする。

```sh
lms load <model-key> --identifier artemis-gemma4 --context-length 65536 --gpu max --yes
lms server start --bind 127.0.0.1 --port 1234
just start-lmstudio
```

管理画面は `http://localhost:8001`。別ターミナルで実行する。

前回成功したテストの `screen.png` があれば、先に画像の読み取りとツール呼び出しだけを確認できる。

```sh
just probe-lmstudio artifacts/<trace-id>/screen.png
```

この事前確認は「Artemis Todo」「タスク1件」「完了1件」の画面を入力する。
推論結果は `artifacts/lmstudio-probe.json` に保存する。

```sh
just test-lmstudio
```

Gemini で行ったものと同じ `pro` / `strict` のシナリオ・判定を使う。
ローカル推論向けにタスクの制限時間だけ30分へ延ばしている。
結果は通常と同じ `artifacts/<trace-id>/`、Artemis 本体のログは `artifacts/lmstudio/traces/` に保存する。

Pro が計画編集を繰り返して進まない場合は、同じモデルで Flash を試せる。

```sh
just test-lmstudio-flash
```

実行中のタスクを切り替える場合は、そのタスク ID を引数に指定する。
停止完了と端末の解放を待ってから Flash を開始する。

```sh
just test-lmstudio-flash <running-task-id>
```

Flash はリセット・追加・完了を別々のタスクとして実行し、各段階の UI ツリーを Python で検証する。
空欄時の追加無効、未完了の `Buy milk` 1件、完了済み1件を順に確認し、すべて一致した場合だけ合格にする。
Pro の Checker による検証台帳は使わない。制限時間は各段階5分。
結果は `artifacts/<run-id>/run.json`、段階ごとの結果・画面は同ディレクトリ内に保存する。

`scripts/start-lmstudio.py` は実験専用の全ノード設定を生成し、Artemis 本体をポート 8001 で起動する。
上流のソースは変更しない。Gemini を直接指定する要約処理が残っているため、
`scripts/lmstudio-runtime/sitecustomize.py` をこのプロセスと子プロセスだけに読み込ませ、
モデル生成を LM Studio の OpenAI 互換 API に統一する。
クラウド用キーを空にし、モデルの接続先はループバックアドレスだけを許可する。
接続先とモデルは `local_model_route` ログで確認できる。

別のモデルをロードする場合は `.env` の `LMSTUDIO_MODEL` に API のモデル ID を設定する。
LM Studio 側で認証を有効にした場合だけ `LMSTUDIO_API_TOKEN` を設定する。
この互換処理は固定した Artemis のバージョン向けの実験実装であり、モデル変更時には再検証する。

## 開発チェック

```sh
just check-project
nix fmt
nix flake check
```

lefthook と CI で型・静的解析・整形・gitleaks・GitHub Actions の SHA pin を検査する。
実機とモデル認証が必要な E2E は明示的に実行し、通常の CI では実行しない。
pnpm と uv は公開から最低1日経過したパッケージに制限し、lockfile を保存する。

調査結果を継続して蓄積する場合は `knowledge/` への OKF 導入を推奨する。
このリポジトリにはまだ導入していない。
