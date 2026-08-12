# `slow-batch` ブランチ

[slow-batch](https://github.com/moozwen/slow-batch) の W-37（規則集合の探索）から
このリポジトリを使うための差分だけを載せたブランチ。**upstream から 4 か所しか変えていない。**

設計の根拠は slow-batch 側の `docs/07-phase4-design.md` §7・§11.6・§11.9、
テンプレートの説明は `templates/slow-batch/README.md`（シンボリックリンク先）にある。

## 変更点

| # | 場所 | 変更 | なぜ |
|---|---|---|---|
| 1 | `launch_scientist.py` `fnames` | `[exp_file, vis_file, notes]` → **`[rules.json, notes]`** | **採点器を探索空間の外に置く。**`experiment.py` を渡すと、採点器を呼ぶ側を書き換えて dev / test を読ませることも、目的関数の λ を変えることもできる |
| 2 | `perform_experiments.py` `run_experiment` | `timeout` を **43200（12 時間）** | 既定は **7200（2 時間）**。1 実験は 2.4〜4.7 時間で**全部超える。**しかも超えると `shutil.rmtree` で**結果ごと消える** |
| 3 | `perform_experiments.py` `MAX_RUNS` | `5` → **`3`** | 1 実験が数時間なので、5 本だと 1 ラウンドで最大 23 時間 |
| 4 | `ai_scientist/llm.py` `AVAILABLE_LLMS` | **`claude-sonnet-5` を追加** | `--model` は `choices=AVAILABLE_LLMS` で弾かれる。既定の `claude-3-5-sonnet-20240620` は litellm 1.81 のモデル表から消えている |

`launch_scientist.py:236`（執筆段階の `fnames`）は**触っていない。**
執筆は実験が終わってから走るので、そこで `experiment.py` を編集されても採点には影響しない。

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
python3 -m venv .venv-ais && source .venv-ais/bin/activate && pip install -U pip
pip install anthropic aider-chat backoff openai google-generativeai \
            requests numpy pypdf pymupdf pymupdf4llm
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

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
  2>&1 | tee ~/w37_round0.log
```

- **`SLOW_BATCH_ROUND`** — v1 は `experiment.py --out_dir=run_i` としか呼ばないので、
  ラウンド（累積 16 / 24 / 32 タスク）は環境変数で渡す。**付け忘れると常にラウンド 0。**
- **`PYTHONUNBUFFERED=1`** — パイプに繋ぐと Python が出力を溜め込む。子プロセスまで効かせる。
- **`--skip-novelty-check`** — Semantic Scholar は本 PoC と無関係。
- **`--num-ideas 1`** — 1 ラウンド 1 アイデア。
- **`--parallel` は使わない** — 使うと `log_file=True` になって stdout がファイルに逸れ、
  `tee` が空になる（`launch_scientist.py:186`）。GPU も 1 枚しかない。

## 前提（起動前に確かめる）

```bash
python -c "
from ai_scientist.llm import create_client
c, m = create_client('claude-sonnet-5')
print('OK', c.messages.create(model=m, max_tokens=16,
      messages=[{'role':'user','content':'ok'}]).content[0].text)"
python -c "from aider.models import Model; m=Model('claude-sonnet-5'); print(m.name, m.info.get('max_input_tokens'))"
python -c "import launch_scientist; print('import OK')"
ls templates/slow-batch/run_0/final_info.json      # ベースラインが要る
```
