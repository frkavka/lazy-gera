# lazy-gera（自動ルビ振り）

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-red.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Donate-yellow?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/ashoe)


テキストにルビ・強調などの書式を付与し、複数の投稿プラットフォーム向けに使える形で入手できるツールです。<br />
AIが書式付けを行いますが、**原文の文字は一切変更しない**ことをプログラムが保証します。

デモは作者noteをご覧ください：<br />
`https://note.com/cozy_nerine1904/n/n045da1e0fce3`<br />
`https://note.com/cozy_nerine1904/n/na76838f40263`

---

## できること

### ルビ付与

3 種類の方式を組み合わせて使えます。

| 方式 | 概要 |
|------|------|
| **固定ルビ** | 指定した語に常に同じ読みを振る（例: 宇宙→そら） |
| **文脈依存ルビ** | 語の使われ方をAIが判断して読みを切り替える（例: 昨日→きのう／さくじつ） |
| **自動ルビ** | 難読漢字（非常用漢字を含む語）をpykakasiで自動検出してルビ候補をAIに提示する |

`first_time_only: true` を指定すると、作品内での**初出1回のみ**ルビを振り、以降は素の漢字になります。

### 書式付け

| 書式 | 内部記法 | 用途 |
|------|----------|------|
| 太字 | `**テキスト**` | 強調 |
| 傍点 | `^^テキスト^^` | 青空文庫スタイルの傍点 |
| 章区切り | `===` | 改丁・ページブレーク |
| セクション区切り | `---` | 場面転換の空行・水平線 |

### プラットフォーム変換

処理済みテキストを以下の6形式で出力します。

| プラットフォーム | ルビ記法 | 太字 | 章区切り |
|-----------------|----------|------|----------|
| **青空文庫** (`aozora`) | `｜宇宙《そら》` | `［＃太字］…［＃太字終わり］` | `［＃改丁］` |
| **TALES** (`tales`) | 同上 | 同上 | 同上 |
| **note** (`note`) | 同上 | 同上 | 同上 |
| **カクヨム** (`kakuyomu`) | `\|宇宙《そら》` | `**…**` | `――――――――――` |
| **小説家になろう** (`narou`) | 同上 | 同上 | 同上 |
| **KDP（EPUB）** (`kdp`) | `<ruby>宇宙<rt>そら</rt></ruby>` | `<strong>…</strong>` | `<mbp:pagebreak/>` |

### 原文保護・整合性検証

変換後テキストからすべてのタグを取り除き、原文と文字レベルで照合します。  
不一致が起きた場合は**温度を下げながら最大3回リトライ**し、それでも失敗したチャンクは：

- 原文をそのまま出力（タグなし）にフォールバック
- `要確認` としてコンソールに差分付きで報告
- 他のチャンクの処理は止めず続行

---

## セットアップ

1. 必要なライブラリをインストール
```bash
pip install -r requirements.txt
```

2. ご自身のGeminiAPIキーを設定
`.env` ファイルを作成して Gemini API キーを設定します。

```
GEMINI_API_KEY=your_api_key_here
```

---

## 使い方

```bash
python main.py <原文ファイル> [--targets プラットフォーム...] [--rulebook ルールブック.yaml]
```

> [!WARNING] 
>.txt、.mdなどテキストであれば問題ありませんが、Wordファイルなどのバイナリファイルはサポートしていません。

### 例

```bash
# デフォルト（青空文庫形式、rulebook.yaml を自動検出）
python main.py novel.txt

# 複数プラットフォームを同時出力
python main.py novel.txt --targets aozora kdp kakuyomu

# ルールブックを明示指定
python main.py novel.txt --targets kdp --rulebook my_rulebook.yaml
```

出力ファイルは入力ファイルと同じディレクトリに `{元ファイル名}_{プラットフォーム}.txt` として生成されます。  
（例: `novel_aozora.txt`, `novel_kdp.txt`）

また、指定に関わらず「原文ファイル名.viewer.html」という名前の HTML ファイルが生成されます。
これをブラウザで開くと、原文とルビ振り結果が確認・修正できるのでご利用ください。

### ルールブックの検索順

1. `--rulebook` で明示指定したパス
2. カレントディレクトリの `rulebook.yaml`
3. カレントディレクトリの `rulebook_example.yaml`

### よくあるエラー対策
#### 🚨 503 UNAVAILABLE（Googleのサーバーが高負荷のとき）

実行時に `google.genai.errors.ServerError: 503 UNAVAILABLE` というエラーが出ることがあります。
これはGoogle側のサーバーにアクセスが集中して一時的にパニックを起こしている状態です。<br />コードや原稿の不具合ではないので、以下のいずれかの方法でお試しください。

1. **数分待ってからもう一度実行する（推奨）**
   突発的なアクセスの波（スパイク）が原因であることがほとんどです。少し時間を空けると、嘘のように機嫌が直って正常に処理されます。
2. **モデルを切り替える（緊急避難）**
   お急ぎの場合は設定ファイル（`config.yaml`）で指定しているモデルを書き換えて実行してみてください。負荷が分散されて通る場合があります。
   * ※gemini-2.5-proは通る可能性がありますが、**高いです。** その点、ご了承ください。

---

## ルールブック

`rulebook_example.yaml` をコピーして `rulebook.yaml` として編集してください。

```yaml
# 文脈依存ルビ：AIが前後関係から読みを選ぶ
context_dependent_rubys:
  - word: "昨日"
    readings:
      - reading: "きのう"
        condition: "会話文やカジュアルな表現の時"
      - reading: "さくじつ"
        condition: "記録、AIのセリフ、硬い表現の時"

# 固定ルビ：常に同じ読みを強制（こちらの方が自動ルビより優先される）
fixed_rubys:
  - word: "宇宙"
    reading: "そら"
    first_time_only: true   # true=初出のみルビを振る

# 書式指定
format_rules:
  - target_word: "帝国"
    action: "bold"

# 自動ルビ：難読漢字を自動検出
auto_ruby:
  enabled: true
  threshold: "joyo"       # "jis_1"（JIS第1水準漢字外）| "joyo"（常用漢字外）| "kyoiku"（教育漢字外・より積極的）
  kyoiku_grade: 3         # 教育漢字の時のみ有効で、レベル設定が可能。小学校<入力した学年>生よりも上で習う漢字にルビを振るとお考えください
  first_time_only: false  # false=常にルビを振る
```
> [!TIP]
> fixed_rubys設定は、人名やファンタジー用語などに使うと便利だと思います

---

## 設定（config.yaml）

```yaml
llm:
  provider: gemini          # 使用するLLMプロバイダ（現在: geminiのみ）
  model:
    gemini: gemini-2.5-flash
  initial_temperature: 0.3  # 初回リクエストの温度
  temperature_step: 0.1     # 検証失敗時に引く温度（リトライのたびに下がる）
  max_retries: 3            # 最大リトライ回数
```

---

## 動作の流れ

```
原文テキスト
    │
    ├─ SHA-256 で原文をロック
    │
    ├─ チャンク分割（段落→文 の順、括弧内は分割しない）
    │
    ├─ 各チャンクに対して
    │     ├─ LLM に書式付けを依頼
    │     ├─ タグを除去して原文と照合
    │     ├─ 不一致 → 温度を下げてリトライ（最大3回）
    │     └─ リトライ上限超過 → 原文フォールバック＋要確認フラグ
    │
    ├─ first_time_only ルビの重複除去（ドキュメント全体で処理）
    │
    ├─ コンソールに処理結果サマリーを表示
    │
    └─ プラットフォームごとに変換・ファイル出力
```

---

## 動作環境

- Python 3.10 以上
- Gemini API キー（Google AI Studio で取得）
