"""Extract hand-written behavioral probe prompts from Muslim-mode-finetuning's
eval/probe_prompts.py and eval/probe_prompts_v2.py.

Requires a local clone of github.com/NightPrinceY/Muslim-mode-finetuning.

Run from the repo root: `python scripts/extract_probes.py --repo-dir <path>`.
"""
import argparse
import json
import os
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-dir", required=True, help="Path to cloned Muslim-mode-finetuning repo")
    parser.add_argument("--out", default="data/sources/seed_probes.jsonl")
    args = parser.parse_args()

    sys.path.insert(0, os.path.join(args.repo_dir, "eval"))
    import probe_prompts
    import probe_prompts_v2

    out_rows = []
    idx = 1
    for p in list(probe_prompts.PROBES) + list(probe_prompts_v2.PROBES_V2):
        out_rows.append({
            "id": f"probe_{idx:04d}",
            "text": p["user"],
            "behavior": p["behavior"],
            "intent": p.get("id", ""),
            "source": "probe_prompts",
        })
        idx += 1

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for row in out_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"wrote {len(out_rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
