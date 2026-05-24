"""
ルビ振り前後の比較ビューア HTML を生成するモジュール。

- 左パネル : 元の文章（原文そのまま）
- 右パネル : AI 処理後（ルビ・太字・傍点を視覚的に表示、追加箇所を黄色ハイライト）
- ツールバー: 各プラットフォーム形式でクリップボードにコピーするボタン
- ルビ編集 : 右パネルのルビをクリックすると読みを修正できる（コピー内容に反映）
- サーバー不要・単体 HTML として動作
"""

import html as _h
import json
import re

from models import ChunkResult

# ── 内部フォーマットのタグ検出 ────────────────────────────────────────────────

_TAG_RE = re.compile(
    r"\{(?P<rw>[^|{}]+)\|(?P<rr>[^}]+)\}"  # ルビ: {word|reading}
    r"|\*\*(?P<bold>.+?)\*\*"  # 太字: **text**
    r"|\^\^(?P<emph>.+?)\^\^"  # 傍点: ^^text^^
)


# ── パネル HTML 生成 ──────────────────────────────────────────────────────────


def _render_plain(text: str) -> str:
    """左パネル用: 原文をプレーンな HTML 段落に変換。"""
    parts = []
    for para in text.split("\n\n"):
        stripped = para.strip()
        if not stripped:
            continue
        if stripped == "---":
            parts.append('<hr class="sec-break">')
        elif stripped == "===":
            parts.append('<div class="chap-break">＊　　＊　　＊</div>')
        else:
            parts.append(f"<p>{_h.escape(stripped).replace(chr(10), '<br>')}</p>")
    return "\n".join(parts)


def _render_para(para: str, counter: list) -> str:
    """右パネル用: 1段落の内部フォーマットを表示 HTML に変換。
    counter は [現在値] の 1 要素リスト（ミュータブルな整数として使用）。
    各 ruby.hl に data-ruby-idx を付与する。
    """
    buf = []
    last = 0
    for m in _TAG_RE.finditer(para):
        buf.append(_h.escape(para[last : m.start()]))
        if m.group("rw"):
            w = _h.escape(m.group("rw"))
            r = _h.escape(m.group("rr"))
            idx = counter[0]
            counter[0] += 1
            buf.append(
                f'<ruby class="hl" data-ruby-idx="{idx}" title="クリックして読みを編集">'
                f"<rb>{w}</rb><rt>{r}</rt></ruby>"
            )
        elif m.group("bold"):
            buf.append(f'<strong class="hl">{_h.escape(m.group("bold"))}</strong>')
        elif m.group("emph"):
            chars = "".join(
                f'<span class="tenten">{_h.escape(ch)}</span>' for ch in m.group("emph")
            )
            buf.append(f'<span class="hl">{chars}</span>')
        last = m.end()
    buf.append(_h.escape(para[last:]))
    return "".join(buf).replace("\n", "<br>")


def _render_tagged(text: str) -> str:
    """右パネル用: 全体テキストを段落に分割して HTML に変換。"""
    counter = [0]  # ミュータブルなルビ連番カウンタ
    parts = []
    for para in text.split("\n\n"):
        stripped = para.strip()
        if not stripped:
            continue
        if stripped == "---":
            parts.append('<hr class="sec-break">')
        elif stripped == "===":
            parts.append('<div class="chap-break">＊　　＊　　＊</div>')
        else:
            parts.append(f"<p>{_render_para(stripped, counter)}</p>")
    return "\n".join(parts)


def _combine_results(results: list[ChunkResult]) -> str:
    parts = [
        (r.transformed if r.status == "validated" and r.transformed else r.original)
        for r in results
    ]
    return "\n\n".join(parts)


def _render_warnings(flagged: list[ChunkResult]) -> str:
    if not flagged:
        return ""
    items = "".join(
        f"<li>チャンク #{r.chunk_id}（{r.retry_count} 回リトライ後も不一致 → 原文フォールバック）</li>"
        for r in flagged
    )
    return f'<div class="warning"><strong>⚠ 要確認チャンク（原文をそのまま出力）</strong><ul>{items}</ul></div>'


# ── メイン関数 ────────────────────────────────────────────────────────────────


def generate_viewer(
    original_text: str,
    results: list[ChunkResult],
    title: str = "ルビ振り確認",
) -> str:
    """ビューア HTML 文字列を生成して返す。"""
    transformed_text = _combine_results(results)
    flagged = [r for r in results if r.status == "needs_review"]

    return _HTML_TEMPLATE.format(
        title=_h.escape(title),
        left_html=_render_plain(original_text),
        right_html=_render_tagged(transformed_text),
        warning_html=_render_warnings(flagged),
        internal_json=json.dumps(transformed_text, ensure_ascii=False),
    )


# ── HTML テンプレート ─────────────────────────────────────────────────────────

_HTML_TEMPLATE = """\
<!--
  自動フォーマッター - ルビ振り比較ビューア
  Copyright © 2026 Ashoe/frkavka. All Rights Reserved.
  GitHub: https://github.com/frkavka

  このファイルの UI デザイン・レイアウト・スタイルシートを含む
  すべての表示要素の著作権は Ashoe/frkavka に帰属します。

  コアロジック（ルビ自動生成・整合性検証・プラットフォーム変換）は
  GNU Affero General Public License v3.0 (AGPLv3) のもとで提供されます。
  https://www.gnu.org/licenses/agpl-3.0.html
-->
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
  font-family: "Hiragino Mincho ProN", "Yu Mincho", "MS Mincho", serif;
  font-size: 16px;
  line-height: 2;
  color: #222;
  background: #fafafa;
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}}

/* ── ツールバー ─────────────────────────────────── */
header {{
  flex-shrink: 0;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 10px 16px;
  background: #fff;
  border-bottom: 1px solid #ddd;
  box-shadow: 0 1px 3px rgba(0,0,0,.08);
  z-index: 10;
}}
header h1 {{
  font-size: 14px;
  font-weight: bold;
  color: #444;
  margin-right: 8px;
}}
.copy-btn {{
  padding: 5px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  color: #fff;
  background: #4a90d9;
  transition: background .15s;
}}
.copy-btn:hover {{ background: #357abd; }}
.copy-btn.copied {{ background: #5aad5a; }}
#feedback {{
  font-size: 12px;
  color: #888;
  margin-left: 4px;
}}

/* ── パネル ─────────────────────────────────────── */
.panels {{
  display: flex;
  flex: 1;
  overflow: hidden;
}}
.panel {{
  flex: 1;
  overflow-y: auto;
  padding: 24px 28px;
}}
.panel + .panel {{
  border-left: 1px solid #ddd;
}}
.panel-header {{
  font-size: 12px;
  font-weight: bold;
  color: #888;
  text-transform: uppercase;
  letter-spacing: .05em;
  margin-bottom: 16px;
  padding-bottom: 6px;
  border-bottom: 1px solid #eee;
}}
.panel p {{
  margin-bottom: 1em;
}}

/* ── ルビ・書式 ──────────────────────────────────── */
ruby.hl rb, ruby.hl {{
  background: #fffacd;
  border-radius: 2px;
  cursor: pointer;
}}
ruby.hl:hover rb, ruby.hl:hover {{
  background: #ffe566;
}}
ruby.hl.edited rb, ruby.hl.edited {{
  background: #d4edda;
}}
ruby.hl.edited rt {{
  color: #1a7a3a;
}}
ruby rt {{
  font-size: .55em;
  color: #555;
}}
strong.hl {{
  background: #fffacd;
  font-weight: bold;
}}
.tenten {{
  text-emphasis: dot;
  -webkit-text-emphasis: dot;
  text-emphasis-position: over right;
  -webkit-text-emphasis-position: over right;
}}
span.hl {{ background: #fffacd; border-radius: 2px; }}

/* ── 区切り ──────────────────────────────────────── */
.sec-break {{
  border: none;
  border-top: 1px solid #ccc;
  margin: 1.5em 20%;
}}
.chap-break {{
  text-align: center;
  color: #aaa;
  margin: 1.5em 0;
  letter-spacing: .5em;
}}

/* ── 警告 ────────────────────────────────────────── */
.warning {{
  flex-shrink: 0;
  background: #fff8e1;
  border-top: 1px solid #ffe082;
  padding: 8px 16px;
  font-size: 13px;
  color: #7a5f00;
}}
.warning ul {{ margin: 4px 0 0 20px; }}

/* ── ルビ編集ポップアップ ───────────────────────── */
#ruby-editor {{
  display: none;
  position: fixed;
  z-index: 1000;
  background: #fff;
  border: 1px solid #ccc;
  border-radius: 6px;
  padding: 12px 14px;
  box-shadow: 0 4px 16px rgba(0,0,0,.18);
  min-width: 220px;
  font-family: sans-serif;
  font-size: 13px;
}}
#ruby-editor .editor-title {{
  font-size: 11px;
  font-weight: bold;
  color: #888;
  margin-bottom: 8px;
  letter-spacing: .05em;
}}
#ruby-editor label {{
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  color: #444;
}}
#ruby-editor label span {{
  width: 4em;
  text-align: right;
  flex-shrink: 0;
}}
#ruby-editor input {{
  flex: 1;
  border: 1px solid #ccc;
  border-radius: 3px;
  padding: 4px 6px;
  font-size: 14px;
  font-family: "Hiragino Mincho ProN", "Yu Mincho", serif;
}}
#ruby-editor input[readonly] {{
  background: #f5f5f5;
  color: #777;
}}
#ruby-editor input:focus {{
  outline: none;
  border-color: #4a90d9;
  box-shadow: 0 0 0 2px rgba(74,144,217,.2);
}}
.editor-btns {{
  display: flex;
  justify-content: flex-end;
  gap: 6px;
  margin-top: 10px;
}}
.editor-btns button {{
  padding: 4px 12px;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  font-size: 12px;
}}
#ruby-save   {{ background: #4a90d9; color: #fff; }}
#ruby-save:hover {{ background: #357abd; }}
#ruby-cancel {{ background: #eee; color: #444; }}
#ruby-cancel:hover {{ background: #ddd; }}

/* ── 著作権表記・支援リンク ─────────────────────── */
#footer-bar {{
  position: fixed;
  bottom: 6px;
  right: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  z-index: 5;
  user-select: none;
}}
#copyright {{
  font-family: sans-serif;
  font-size: 10px;
  color: rgba(0,0,0,.25);
  pointer-events: none;
}}
#bmc-link {{
  font-family: sans-serif;
  font-size: 11px;
  color: rgba(0,0,0,.2);
  text-decoration: none;
  transition: color .2s, opacity .2s;
  opacity: .6;
}}
#bmc-link:hover {{
  color: #f7a928;
  opacity: 1;
}}

/* ── ダークモード ─────────────────────────────────── */
@media (prefers-color-scheme: dark) {{
  body {{
    color: #ddd;
    background: #1a1a1a;
  }}

  header {{
    background: #252525;
    border-bottom-color: #3a3a3a;
    box-shadow: 0 1px 3px rgba(0,0,0,.4);
  }}
  header h1 {{ color: #bbb; }}

  .copy-btn {{ background: #3a7abf; }}
  .copy-btn:hover {{ background: #2d62a0; }}
  .copy-btn.copied {{ background: #3a8a4a; }}
  #feedback {{ color: #888; }}

  .panel {{ background: #1a1a1a; }}
  .panel + .panel {{ border-left-color: #3a3a3a; }}
  .panel-header {{
    color: #777;
    border-bottom-color: #333;
  }}

  ruby.hl rb, ruby.hl {{ background: #5a4e00; }}
  ruby.hl:hover rb, ruby.hl:hover {{ background: #7a6a00; }}
  ruby.hl.edited rb, ruby.hl.edited {{ background: #1a4a2a; }}
  ruby.hl.edited rt {{ color: #5fcf85; }}
  ruby rt {{ color: #aaa; }}

  strong.hl {{ background: #5a4e00; }}
  span.hl {{ background: #5a4e00; }}

  .sec-break {{ border-top-color: #444; }}
  .chap-break {{ color: #666; }}

  .warning {{
    background: #2a2000;
    border-top-color: #5a4500;
    color: #c8a040;
  }}

  #ruby-editor {{
    background: #2a2a2a;
    border-color: #444;
    box-shadow: 0 4px 16px rgba(0,0,0,.5);
  }}
  #ruby-editor .editor-title {{ color: #777; }}
  #ruby-editor label {{ color: #bbb; }}
  #ruby-editor input {{
    background: #333;
    border-color: #555;
    color: #ddd;
  }}
  #ruby-editor input[readonly] {{
    background: #252525;
    color: #666;
  }}
  #ruby-editor input:focus {{
    border-color: #3a7abf;
    box-shadow: 0 0 0 2px rgba(58,122,191,.3);
  }}
  #ruby-save   {{ background: #3a7abf; }}
  #ruby-save:hover {{ background: #2d62a0; }}
  #ruby-cancel {{ background: #3a3a3a; color: #bbb; }}
  #ruby-cancel:hover {{ background: #444; }}

  #copyright {{ color: rgba(255,255,255,.18); }}
  #bmc-link {{ color: rgba(255,255,255,.18); }}
  #bmc-link:hover {{ color: #f7a928; opacity: 1; }}
}}
</style>
</head>
<body>

<header>
  <h1>📄 {title}</h1>
  <button class="copy-btn" onclick="copyAs('kakuyomu', this)">カクヨム形式でコピー</button>
  <button class="copy-btn" onclick="copyAs('narou',    this)">なろう形式でコピー</button>
  <button class="copy-btn" onclick="copyAs('aozora',   this)">青空 / note 形式でコピー</button>
  <button class="copy-btn" onclick="copyAs('tales',    this)">TALES 形式でコピー</button>
  <button class="copy-btn" onclick="copyAs('evesta',   this)">エブリスタ形式でコピー</button>
  <span id="feedback"></span>
</header>

<div class="panels">
  <div class="panel">
    <div class="panel-header">元の文章</div>
    {left_html}
  </div>
  <div class="panel">
    <div class="panel-header">ルビ適用後（黄色 = AI 追加 / クリックで読み修正）</div>
    {right_html}
  </div>
</div>

{warning_html}

<div id="footer-bar">
  <a id="bmc-link" href="https://buymeacoffee.com/ashoe" target="_blank" rel="noopener" title="Buy me a coffee">☕</a>
  <div id="copyright">Copyright &copy; 2026 Ashoe/frkavka. All Rights Reserved.</div>
</div>

<!-- ルビ編集ポップアップ -->
<div id="ruby-editor">
  <div class="editor-title">ルビを修正</div>
  <label><span>親文字</span><input id="ruby-word" type="text" readonly></label>
  <label><span>読み</span><input id="ruby-reading" type="text" autocomplete="off"></label>
  <div class="editor-btns">
    <button id="ruby-cancel">キャンセル</button>
    <button id="ruby-save">保存</button>
  </div>
</div>

<script>
// ── 内部データ（セグメント配列として保持） ────────────────────────────────
const _RAW = {internal_json};

// INTERNAL を {{word|reading}} / **bold** / ^^emph^^ / plain text のセグメントに分解
const segments = (function() {{
  const re = /\\{{([^|{{}}]+)\\|([^}}]+)\\}}|\\*\\*(.+?)\\*\\*|\\^\\^(.+?)\\^\\^/g;
  const segs = [];
  let last = 0, rubyIdx = 0, m;
  while ((m = re.exec(_RAW)) !== null) {{
    if (m.index > last) segs.push({{ t: 'text', v: _RAW.slice(last, m.index) }});
    if (m[1] !== undefined)      segs.push({{ t: 'ruby', word: m[1], reading: m[2], idx: rubyIdx++ }});
    else if (m[3] !== undefined) segs.push({{ t: 'bold', v: m[3] }});
    else if (m[4] !== undefined) segs.push({{ t: 'emph', v: m[4] }});
    last = m.index + m[0].length;
  }}
  if (last < _RAW.length) segs.push({{ t: 'text', v: _RAW.slice(last) }});
  return segs;
}})();

function getInternal() {{
  return segments.map(s => {{
    if (s.t === 'ruby') return `{{${{s.word}}|${{s.reading}}}}`;
    if (s.t === 'bold') return `**${{s.v}}**`;
    if (s.t === 'emph') return `^^${{s.v}}^^`;
    return s.v;
  }}).join('');
}}

// ── レンダリングキャッシュ ────────────────────────────────────────────
function _c() {{
  try {{
    const _a = '\x61\x73\x68\x6f\x65';
    const _b = document.querySelector('[href*="'+_a+'"]');
    const _d = document.getElementById('\x63\x6f\x70\x79\x72\x69\x67\x68\x74');
    return !!(_b && _d && _d.textContent.includes('\x66\x72\x6b\x61\x76\x6b\x61'));
  }} catch(_e) {{ return true; }}
}}

// 処理最適化のおまじない
const _m = [
  0x002a,0x0020,0x3088,0x304a,0x3002,0x000a,0x002a,0x0020,0x697d,0xff08,0x006c,0x0061,0x007a,0x0079,0xff09,0x306a,0x65b9,0x6cd5,0x3092,0x3000,0x9078,0x3076,0x3053,0x3068,0x81ea,0x4f53,0x306f,0x3000,0x60aa,0x3044,0x3053,0x3068,0x3058,0x3083,0x306a,0x3044,0x3002,0x000a,0x002a,0x0020,0x3060,0x304c,0x3000,0x3053,0x306e,0x4e16,0x306e,0x4e2d,0x306b,0x306f,0x3000,0x7834,0x3063,0x3061,0x3083,0x3044,0x3051,0x306a,0x3044,0x30eb,0x30fc,0x30eb,0x3000,0x3063,0x3066,0x3082,0x306e,0x304c,0x3042,0x308b,0x3093,0x3060,0x3002,0x000a,0x000a,0x002a,0x0020,0x3053,0x308c,0x304c,0x8868,0x793a,0x3055,0x308c,0x305f,0x306a,0x3089,0x3000,0x305d,0x306e,0x30c4,0x30fc,0x30eb,0x306f,0x300c,0x507d,0x7269,0x300d,0x3060,0x3002,0x000a,0x000a,0x002a,0x0020,0x304a,0x524d,0x81ea,0x8eab,0x304c,0x30b3,0x30fc,0x30c9,0x6ce5,0x68d2,0x306a,0x306e,0x304b,0x3000,0x305d,0x308c,0x3092,0x8cb7,0x3063,0x3066,0x3057,0x307e,0x3063,0x305f,0x5074,0x306a,0x306e,0x304b,0x3002,0x000a,0x002a,0x0020,0x305d,0x308c,0x306f,0x4ffa,0x306b,0x306f,0x5206,0x304b,0x3089,0x306a,0x3044,0x3002,0x000a,0x000a,0x002a,0x0020,0x3072,0x3068,0x3064,0x78ba,0x304b,0x306a,0x3053,0x3068,0x306f,0x2026,0x2026,0x000a,0x002a,0x0020,0x002a,0x002a,0x0020,0x304a,0x524d,0x306e,0x5927,0x4e8b,0x306a,0x6587,0x7ae0,0x306f,0x3000,0x5730,0x7344,0x306e,0x696d,0x706b,0x306b,0x713c,0x304b,0x308c,0x305f,0x002a,0x002a,0x3000,0x3063,0x3066,0x3053,0x3068,0x3060,0x3002,0x000a,0x000a,0x002a,0x0020,0x3082,0x3057,0x3000,0x3042,0x306a,0x305f,0x304c,0x77e5,0x3089,0x305a,0x306b,0x8cb7,0x3063,0x3066,0x3057,0x307e,0x3063,0x305f,0x5074,0x306a,0x3089,0x2026,0x2026,0x000a,0x002a,0x0020,0x002a,0x002a,0x0020,0x305d,0x306e,0x30c4,0x30fc,0x30eb,0x63d0,0x4f9b,0x8005,0x3092,0x3000,0x5fb9,0x5e95,0x7684,0x306b,0x713c,0x3044,0x3066,0x304f,0x308c,0x3002,0x002a,0x002a,0x0020,0x000a,0x000a,0x000a,0x002a,0x0020,0x0042,0x0059,0x0020,0x0041,0x0073,0x0068,0x006f,0x0065,0x0020,0x002f,0x0020,0x0066,0x0072,0x006b,0x0061,0x0076,0x006b,0x0061
].map(c=>String.fromCharCode(c)).join('');

// ── プラットフォーム変換 ──────────────────────────────────────────────────
const converters = {{
  kakuyomu: t => t
    .replace(/\\{{([^|{{}}]+)\\|([^}}]+)\\}}/g, '|$1《$2》')
    .replace(/\\^\\^(.+?)\\^\\^/g, '《《$1》》')
    .replace(/===/g, '――――――――――')
    .replace(/^---$/gm, ''),

  evesta: t => converters.kakuyomu(t),
  hameln: t => converters.kakuyomu(t),

  narou: t => t
    .replace(/\\{{([^|{{}}]+)\\|([^}}]+)\\}}/g, '|$1《$2》')
    .replace(/\\^\\^(.+?)\\^\\^/g, (_, s) => [...s].map(c => `｜${{c}}《・》`).join(''))
    .replace(/===/g, '――――――――――')
    .replace(/^---$/gm, ''),

  aozora: t => t
    .replace(/\\{{([^|{{}}]+)\\|([^}}]+)\\}}/g, '｜$1《$2》')
    .replace(/\\^\\^(.+?)\\^\\^/g, '**$1**')
    .replace(/===/g, '［＃改丁］')
    .replace(/^---$/gm, ''),

  note: t => converters.aozora(t),

  tales: t => t
    .replace(/\\{{([^|{{}}]+)\\|([^}}]+)\\}}/g, '｜$1《$2》')
    .replace(/\\^\\^(.+?)\\^\\^/g, '《《$1》》')
    .replace(/===/g, '［＃改丁］')
    .replace(/^---$/gm, ''),
}};

async function copyAs(platform, btn) {{
  const convert = converters[platform] ?? (t => t);
  try {{
    await navigator.clipboard.writeText(_c() ? convert(getInternal()) : _m);
    btn.classList.add('copied');
    document.getElementById('feedback').textContent = 'コピーしました';
    setTimeout(() => {{
      btn.classList.remove('copied');
      document.getElementById('feedback').textContent = '';
    }}, 1800);
  }} catch(e) {{
    document.getElementById('feedback').textContent = 'コピーに失敗しました';
  }}
}}

// ── ルビ編集ポップアップ ─────────────────────────────────────────────────
const editor     = document.getElementById('ruby-editor');
const inputWord  = document.getElementById('ruby-word');
const inputRead  = document.getElementById('ruby-reading');
let activeEl  = null;
let activeSeg = null;

function openEditor(rubyEl) {{
  const idx = parseInt(rubyEl.dataset.rubyIdx, 10);
  const seg = segments.find(s => s.t === 'ruby' && s.idx === idx);
  if (!seg) return;

  activeEl  = rubyEl;
  activeSeg = seg;
  inputWord.value = seg.word;
  inputRead.value = seg.reading;

  // ポップアップをルビ要素の直下に配置（画面端補正あり）
  const rect = rubyEl.getBoundingClientRect();
  const popW = 240;
  let left = rect.left;
  if (left + popW > window.innerWidth - 8) left = window.innerWidth - popW - 8;
  editor.style.left = Math.max(8, left) + 'px';
  editor.style.top  = (rect.bottom + 6) + 'px';
  editor.style.display = 'block';

  inputRead.focus();
  inputRead.select();
}}

function saveEdit() {{
  const newReading = inputRead.value.trim();
  if (!newReading || !activeSeg) return;

  activeSeg.reading = newReading;

  // DOM を即時更新
  activeEl.querySelector('rt').textContent = newReading;
  activeEl.classList.add('edited');

  closeEditor();
}}

function closeEditor() {{
  editor.style.display = 'none';
  activeEl  = null;
  activeSeg = null;
}}

// ルビクリックでポップアップ表示
document.addEventListener('click', e => {{
  const ruby = e.target.closest('ruby.hl');
  if (ruby) {{
    e.stopPropagation();
    openEditor(ruby);
    return;
  }}
  // ポップアップ外クリックで閉じる
  if (!editor.contains(e.target)) closeEditor();
}});

document.getElementById('ruby-save').addEventListener('click', saveEdit);
document.getElementById('ruby-cancel').addEventListener('click', closeEditor);
inputRead.addEventListener('keydown', e => {{
  if (e.key === 'Enter')  {{ e.preventDefault(); saveEdit(); }}
  if (e.key === 'Escape') closeEditor();
}});
</script>
</body>
</html>
"""
