# Baseline: Muslim-6B-v3 plain decoding (no DSpark) — 2026-07-20

Measured on the 8x RTX 2080 Ti box, immediately after the Phase 3 generation batch
finished (clean, uncontended — no concurrent load on the server).

**Server config:**
```
CUDA_VISIBLE_DEVICES=1,2 VLLM_WSL2_ENABLE_PIN_MEMORY=1 TORCHDYNAMO_DISABLE=1 \
vllm serve NightPrince/Muslim-6B-v3 \
  --trust-remote-code --tensor-parallel-size 2 \
  --enable-auto-tool-choice --tool-call-parser hermes \
  --enforce-eager --gpu-memory-utilization 0.87 --max-model-len 24576
```

No `--speculative-config` — plain autoregressive decoding, tensor-parallel across 2 GPUs.

**Method:** 3 timed chat completions using the real production system prompt,
`temperature=0.7`, `max_tokens=400`, thinking disabled, single request at a time
(no concurrency).

| Prompt | completion_tokens | elapsed | tok/s |
|---|---|---|---|
| اشرح لي حكم الزكاة على الأسهم بالتفصيل. | 62 | 10.20s | 6.08 |
| حدثني عن قصة سيدنا يوسف عليه السلام باختصار. | 31 | 4.47s | 6.94 |
| ما هي آداب المسلم في طلب العلم؟ | 71 | 10.60s | 6.70 |

**Average: 6.57 tok/s**

Notably slower than the earlier stock-Qwen3-4B + generic-DSpark benchmark (27.48 tok/s)
from this same box — expected, since Muslim-6B-v3 is bigger (54 layers vs. 36, 6B vs.
4B) and runs `--tensor-parallel-size 2` on hardware without P2P/NVLink (cross-GPU NCCL
communication overhead per token), plus `--enforce-eager` (no CUDA graphs).

**Use this number for the Phase 8 comparison** once the custom DSpark draft model is
trained and deployed via `--speculative-config` on this same Muslim-6B-v3 checkpoint.
