set dotenv-load

# 利用可能なコマンドを表示する
default:
    @just --list

# Expo とテストクライアントの依存関係を揃える
setup-project:
    pnpm install --frozen-lockfile
    uv sync --locked
    lefthook install

# Android 端末の接続を確認する
check-device:
    adb devices -l

# USB 接続した端末に Android アプリをビルドしてインストールする
install-android:
    pnpm exec expo run:android --device "$ADB_DEVICE_SERIAL"

# USB 接続した実機から Metro に接続できるようにする
connect-metro:
    adb -s "$ADB_DEVICE_SERIAL" reverse tcp:8081 tcp:8081

# インストール済みアプリ向けに Metro を起動する
start-expo:
    pnpm start

# Artemis の自然言語テストと最終画面の検証を実行する
test-android:
    uv run --locked python scripts/test-android.py

# 型・静的解析・整形・シークレットを検査する
check-project:
    pnpm typecheck
    pnpm lint
    pnpm format:check
    uv run --locked ruff check scripts tests
    uv run --locked ruff format --check scripts tests
    uv run --locked python -m pytest tests
    just --fmt --check
    gitleaks dir . --redact

# ソースと justfile を整形する
format-project:
    pnpm format
    uv run --locked ruff format scripts tests
    just --fmt
