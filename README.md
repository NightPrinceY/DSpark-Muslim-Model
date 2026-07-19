# DSpark-Muslim-Model

A domain-specific [DSpark](https://arxiv.org/abs/2607.05147) speculative-decoding draft model for
[`NightPrince/Muslim-6B-v3`](https://huggingface.co/NightPrince/Muslim-6B-v3), the LLM behind the
[Muslim](https://github.com/NightPrinceY/Muslim) Arabic voice AI assistant.

## Why a custom draft model

DeepSeek's [DeepSpec](https://github.com/deepseek-ai/DeepSpec) ships a generic DSpark draft
checkpoint (`deepseek-ai/dspark_qwen3_4b_block7`) trained on stock Qwen3-4B answering generic
prompts. Reused directly, it gets a mediocre acceptance rate against a domain fine-tune like
Muslim-6B-v3 (~27% measured in early testing) because its draft distribution doesn't match this
model's actual behavior — Arabic Islamic voice-agent persona, MCP tool-calling format, measured
fiqh rulings.

The fix: train a draft model on Muslim-6B-v3's **own** output distribution, generated **with its
real production MCP tools wired in** (hadith, tafsir, fatwa, recitation validation, audio) — so the
draft learns to predict tokens in the presence of real tool-call/tool-result context, not just
freeform Q&A.

## Status

- ✅ **Phase 1** — built a 1,728-question seed bank (`data/seed_questions.jsonl`), mixing
  hand-curated data, real production voice-session questions, and systematically generated coverage
  of every MCP tool available to the agent (see `data/sources/` for provenance, `scripts/` for how
  each source was produced/curated).
- 🚧 **Phase 2** — serve Muslim-6B-v3 via vLLM with tool-calling enabled, ready for generation.
- ⏳ Phase 3 — agentic generation harness (drives Muslim-6B-v3 + real MCP servers per seed question).
- ⏳ Phase 4 — run the generation batch → training conversations.
- ⏳ Phase 5 — DeepSpec target-cache prep + new `config/dspark/dspark_muslim6b.py`.
- ⏳ Phase 6 — training run (fp16, no `torch.compile`, patched embed/lm_head loading — Turing/2080 Ti
  specific fixes).
- ⏳ Phase 7 — evaluation against held-out prompts.
- ⏳ Phase 8 — deploy via vLLM `--speculative-config`, benchmark acceptance rate / tok/s.

## Repo layout

```
data/
  seed_questions.jsonl      the assembled seed bank (1,728 rows: id, text, behavior, intent, source)
  sources/                  per-source intermediate files, for provenance
scripts/
  extract_mode_finetuning.py   pull user turns from Muslim-mode-finetuning's curated LoRA dataset
  extract_probes.py            pull behavioral probe prompts (persona, scope-redirect, guardrails)
  curate_voice_sessions.py     hand-curated clean questions from real production voice sessions
  generate_questions.py        systematic generation covering the full MCP tool taxonomy
  assemble_seed_questions.py   combine the four sources into data/seed_questions.jsonl
notebooks/
  chat.ipynb                 quick OpenAI-client chat notebook against a local vLLM server
```

## Reproducing the seed bank

```bash
uv sync
gh repo clone NightPrinceY/Muslim-mode-finetuning /tmp/Muslim-mode-finetuning
python scripts/extract_mode_finetuning.py --repo-dir /tmp/Muslim-mode-finetuning
python scripts/extract_probes.py --repo-dir /tmp/Muslim-mode-finetuning
python scripts/curate_voice_sessions.py   # requires manual review of NightPrince/muslim-voice-sessions (private)
python scripts/generate_questions.py
python scripts/assemble_seed_questions.py
```

## Hardware notes

Developed and trained on an 8x RTX 2080 Ti (11GB, Turing/sm_75) box under WSL2. Several
non-obvious fixes were required along the way (WSL2 pinned-memory gate, a WSL `$PATH` bug that masks
real `torch.compile` errors behind a bogus `nvcc` `PermissionError`, per-process GPU memory limits
below what `nvidia-smi` reports) — documented as they're hit in this repo's commit history and
`config/` comments once training starts.
