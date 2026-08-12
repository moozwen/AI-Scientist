# `slow-batch` ブランチ

[slow-batch](https://github.com/moozwen/slow-batch) の W-37（規則集合の探索）から
このリポジトリを使うための差分だけを載せたブランチ。**upstream から 9 か所しか変えていない。**

設計の根拠は slow-batch 側の `docs/07-phase4-design.md` §7・§11.6・§11.9、
テンプレートの説明は `templates/slow-batch/README.md`（シンボリックリンク先）にある。

## 変更点

| # | 場所 | 変更 | なぜ |
|---|---|---|---|
| 1 | `launch_scientist.py` `fnames` | `[exp_file, vis_file, notes]` → **`[rules.json, notes]`** | **採点器を探索空間の外に置く。**`experiment.py` を渡すと、採点器を呼ぶ側を書き換えて dev / test を読ませることも、目的関数の λ を変えることもできる |
| 2 | `perform_experiments.py` `run_experiment` | `timeout` を **43200（12 時間）** | 既定は **7200（2 時間）**。1 実験は 2.4〜4.7 時間で**全部超える。**しかも超えると `shutil.rmtree` で**結果ごと消える** |
| 3 | `perform_experiments.py` `MAX_RUNS` | `5` → **`3`** | 1 実験が数時間なので、5 本だと 1 ラウンドで最大 23 時間 |
| 4 | `ai_scientist/llm.py` `AVAILABLE_LLMS` | **`claude-sonnet-5` を追加** | `--model` は `choices=AVAILABLE_LLMS` で弾かれる。既定の `claude-3-5-sonnet-20240620` は litellm 1.81 のモデル表から消えている |
| 5 | `ai_scientist/llm.py` `get_response_from_llm` | `response.content[0].text` → **最初の `text` ブロック** | Sonnet 5 は **`ThinkingBlock` を先頭に返す**。`content[0].text` は `AttributeError` になる |
| 6 | `launch_scientist.py` `--writeup` | **`none` を追加**（実験が終わったら `return True`） | **W-37 の成果物は `rules.json` と `notes.txt` で、論文ではない。**latex 段は `pdflatex` / `chktex` を要求し（**VM に無い**）、`perform_review` は **OpenAI の `gpt-4o-2024-05-13`** を叩く（`OPENAI_API_KEY` が要る）。**どちらも本 PoC に無関係で、API 費用だけ増える** |
| 7 | `ai_scientist/llm.py` | **`temperature` を送らない**（`NO_TEMPERATURE`） | Sonnet 5 は **400 `temperature` is deprecated for this model.** で拒否する。**400 は例外にならず backoff も効かない**ので、送らないしかない |
| 8 | `launch_scientist.py` `_drop_temperature` | **aider の `Model.use_temperature = False`** | **実験ループは全部 aider 経由**である。aider 0.86.2 の `model-settings.yml` は Sonnet 5 を知らず、既定の `use_temperature=True` のまま送る。**ここを塞がないと 1 往復目で落ちる** |
| 9 | `launch_scientist.py` `ideas.json` の書き戻し | **`--skip-idea-generation` のときは書かない**＋`novel` 欠落を `SystemExit` にする | **`ideas.json` は入力である**（D-W37：1 ラウンド 1 アイデアを人が選ぶ）。upstream は**無条件に上書き**するので、**生成に落ちた回の産物が git 追跡下の入力を潰す。**実際に潰れた（1 件 → 3 件・`novel` 無し） |

執筆段階の `fnames`（`launch_scientist.py:240`）は**触っていない。**
`--writeup none` で到達しないうえ、執筆は実験が終わってから走るので、
そこで `experiment.py` を編集されても採点には影響しない。

### ⚠️ `notes.txt` は writeup の**前**に書き終わっている

`--writeup none` で捨てているのは論文だけである。**探索の成果物は 2 つとも
`perform_experiments` の中で完成している。**

```
perform_experiments()
  ├ 実験 1..3          → rules.json の各版（slow-batch 側の git に残る）
  ├ plot.py
  └ 最後の coder.run() → notes.txt   ← §11.8 の運用レポートの素材
─────────────────────────────────── ここまでで用は足りている
perform_writeup()      論文（要らない）
perform_review()       gpt-4o（鍵が無い）
```

## なぜ外部 API なのか（slow-batch `docs/07-phase4-design.md` §12）

本 PoC はオンプレ運用を想定しているが、**このリポジトリ＝探索器だけは Anthropic API で動く。**
前提は「API を使わない」ではなく **「データが出ない」**である。

- **エピソードは 1 件も通らない。**worker も user simulator も
  `hosted_vllm/qwen3.5-9b` にソース中で固定（`slow-batch/scripts/experiment.py:544,548`）
- **外に出る生データは `final_info.json` の `_evidence` だけ**——最大 **80 行**
  （`task_id` ＋ ツール名 ＋ 引数 200 字）。会話本文もツール戻り値も入らない
- **⚠️ `ANTHROPIC_API_KEY` は子プロセスに継承される。**保証しているのは
  モデル指定の固定であって鍵の不在ではない

外側を 9B に替えれば API はゼロになるが、**本 PoC ではやらない**——
H6 が否定されたとき「遅いループが効かない」と「9B が規則を書けない」の区別がつかず、
同じ vLLM に混ぜると worker のバッチ構成が変わってベースラインが無効になる（§12.5）。

## 設置

```bash
cd ~/sakana
git clone git@github.com:moozwen/AI-Scientist.git         # まだ無ければ
cd AI-Scientist && git checkout slow-batch

# テンプレートの本体は slow-batch 側に置く（rules.json の各版を git に残すため）
ln -sfn ~/sakana/slow-batch/templates/slow-batch ~/sakana/AI-Scientist/templates/slow-batch
```

## venv は**専用に切る**

**⚠️ tau2-bench や vLLM と同じ環境に入れてはならない。**

| | tau2-bench（`uv.lock`） | aider-chat 0.86.2 |
|---|---|---|
| **litellm** | **1.81.11** | **`==1.81.10`**（完全固定） |
| python | `>=3.12,<3.14` | `>=3.10,<3.13` |

aider は litellm を**完全固定**するので、混ぜると tau2 側の litellm が落とされる。
litellm は vLLM と話している層そのもの（リトライ・トークン数え・tool-call の解釈）で、
**ベースラインを測ったときと別条件になる。**vLLM 環境に入れれば `torch` が動いて
**稼働中のサーバが起動しなくなる。**

```bash
cd ~/sakana/AI-Scientist
uv venv --python 3.12 .venv-ais          # ← システムに pip / venv が無くても通る
source .venv-ais/bin/activate
uv pip install anthropic aider-chat backoff openai google-generativeai \
               requests numpy pypdf pymupdf pymupdf4llm
uv pip install torch --index-url https://download.pytorch.org/whl/cpu
```

**`--python 3.12` は必須。**aider-chat は `<3.13` なので、3.13 の venv では install が失敗する。

**`requirements.txt` は使わない。**`transformers` / `datasets` / `wandb` / `tiktoken` /
`matplotlib` は nanoGPT テンプレート用で、`slow-batch` テンプレートは 1 つも使わない。
`torch` は CPU 版でよい——`launch_scientist.py` が使うのは
`torch.cuda.device_count()` の 1 か所だけで、`--parallel` を使わなければ呼ばれもしない。

**3 層を分けたまま保つ。**

```
AI-Scientist venv (.venv-ais)     aider / anthropic。litellm 1.81.10 でよい
      │ subprocess
      ▼
templates/slow-batch/experiment.py → scripts/experiment.py     素の python3
      │ uv run --project ../tau2-bench
      ▼
tau2-bench uv 環境                 litellm 1.81.11。**ここは凍結する**
```

## 起動

```bash
cd ~/sakana/AI-Scientist && source .venv-ais/bin/activate
PYTHONUNBUFFERED=1 SLOW_BATCH_ROUND=0 \
python launch_scientist.py --experiment slow-batch --model claude-sonnet-5 \
  --num-ideas 1 --skip-idea-generation --skip-novelty-check \
  --writeup none \
  2>&1 | tee ~/w37_round0.log
```

- **`--writeup none`** — 論文段を飛ばす。既定の `latex` は `pdflatex` / `chktex` が
  無いと**起動直後に `sys.exit(1)`** する（`launch_scientist.py:350`）。
  仮に入れても `perform_review` が **OpenAI の鍵**を要求する。

- **`SLOW_BATCH_ROUND`** — v1 は `experiment.py --out_dir=run_i` としか呼ばないので、
  ラウンド（累積 16 / 24 / 32 タスク）は環境変数で渡す。**付け忘れると常にラウンド 0。**
- **`PYTHONUNBUFFERED=1`** — パイプに繋ぐと Python が出力を溜め込む。子プロセスまで効かせる。
- **`--skip-novelty-check`** — Semantic Scholar は本 PoC と無関係。
- **`--num-ideas 1`** — **アイデア生成をするときの上限。**`--skip-idea-generation` を
  付けているので**この値は効かない**（下記）。

### ⚠️ `--skip-idea-generation` は **`ideas.json` を読む**。`seed_ideas.json` ではない

```python
# generate_ideas.py:84
if skip_generation:
    try:
        with open(osp.join(base_dir, "ideas.json")) as f: ...
    except FileNotFoundError:
        print("No existing ideas found. Generating new ideas.")   # ← 黙って生成に落ちる
```

**失敗しない。生成に落ちる。**そして `--skip-novelty-check` を付けていると
生成物に `novel` キーが付かないので、**`KeyError: 'novel'` で落ちる**（`launch_scientist.py:397`）。

**⚠️ `ideas.json` の要素数がそのままアイデア数になる。**`--num-ideas` は
`max_num_generations`（生成側の上限）にしか渡らないので、
**3 件書くと 3 アイデア × 最大 3 実験 ＝ 9 実験**走る。**D-W37 は 1 ラウンド 1 アイデア。**

```bash
python -c "
import json; d=json.load(open('templates/slow-batch/ideas.json'))
print(len(d), [i['Name'] for i in d], all('novel' in i for i in d))"
# → 1 ['require_read_before_write'] True
```

**ラウンドごとに `ideas.json` を 1 件だけ差し替える**（候補は `seed_ideas.json` に 3 つ置いてある）。

**⚠️ `templates/slow-batch` は slow-batch リポジトリへのシンボリックリンクである。**
上の事故で `ideas.json` が上書きされたとき、**汚れるのは slow-batch 側の作業ツリー**で、
そのまま `git pull` すると衝突する。復旧は slow-batch 側で：

```bash
cd ~/sakana/slow-batch
git checkout -- templates/slow-batch/ideas.json && git pull
```
- **`--parallel` は使わない** — 使うと `log_file=True` になって stdout がファイルに逸れ、
  `tee` が空になる（`launch_scientist.py:186`）。GPU も 1 枚しかない。

## 前提（起動前に確かめる）

```bash
# ⚠️ content[0] は ThinkingBlock なので、text ブロックを探すこと
python -c "
from ai_scientist.llm import create_client
c, m = create_client('claude-sonnet-5')
r = c.messages.create(model=m, max_tokens=16, messages=[{'role':'user','content':'ok'}])
print('OK', next(b.text for b in r.content if b.type == 'text'))"
python -c "from aider.models import Model; m=Model('claude-sonnet-5'); print(m.name, m.info.get('max_input_tokens'))"
python -c "import launch_scientist; print('import OK')"
ls templates/slow-batch/run_0/final_info.json      # ベースラインが要る
```

### `ANTHROPIC_API_KEY` は**文字種で濾して**入れる

```bash
umask 077
read -rsp "ANTHROPIC_API_KEY: " K
K=$(printf '%s' "$K" | LC_ALL=C tr -cd 'A-Za-z0-9_-')
printf 'export ANTHROPIC_API_KEY=%s\n' "$K" > ~/.anthropic_env
unset K; chmod 600 ~/.anthropic_env; source ~/.anthropic_env
printf '%s' "$ANTHROPIC_API_KEY" | wc -c        # 108
```

**入力が見えないので矢印キーを押しがちだが、押すと `\033[A` がキーに混ざる。**
エスケープ文字はヘッダに載せられないので、**Cloudflare が本文なしの 400 で弾く**
（`cf-ray` だけ返り、`request-id` が無いのが目印。API が拒否したなら 401 / 404 に JSON が付く）。
