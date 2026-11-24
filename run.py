"""Send every test recording to Spelly's /api/assess and keep the answers.

    export SPELLY_API_KEY=...
    python run.py --out results/my-run/responses.jsonl.gz

Each recording is one request, scored as American English. Answers are written one per line as
{"id", "status", "body"}, with the audio clips the API sends back left out. A run can be stopped
and started again: recordings already answered are skipped. Each recording uses one API unit, so the full
test needs 2,500; with a free trial key (100 units), run the first 100 with --limit 100.
"""
import argparse
import gzip
import json
import os
import time
from pathlib import Path

import requests

API = "https://spelly.ch/api/assess"
LANGUAGE = "en-US"


def without_audio(value):
    """The answer without its base64 audio clips, which are large and not needed for scoring."""
    if isinstance(value, dict):
        return {k: without_audio(v) for k, v in value.items() if not k.endswith("_base64")}
    if isinstance(value, list):
        return [without_audio(v) for v in value]
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--limit", type=int, help="only the first N recordings (a free trial key has 100 units)")
    args = parser.parse_args()

    key = os.environ["SPELLY_API_KEY"]
    recordings = [json.loads(line) for line in (args.data / "test.jsonl").open(encoding="utf-8")]
    if args.limit:
        recordings = recordings[: args.limit]
    done = set()
    if args.out.exists():
        with gzip.open(args.out, "rt", encoding="utf-8") as f:
            done = {json.loads(line)["id"] for line in f}
    args.out.parent.mkdir(parents=True, exist_ok=True)

    with gzip.open(args.out, "at", encoding="utf-8") as out:
        for n, rec in enumerate(recordings, 1):
            if rec["id"] in done:
                continue
            while True:
                with (args.data / "audio" / f"{rec['id']}.wav").open("rb") as audio:
                    r = requests.post(
                        API,
                        headers={"X-API-Key": key},
                        data={"reference_text": rec["text"].lower(), "language": LANGUAGE},
                        files={"audio": (f"{rec['id']}.wav", audio, "audio/wav")},
                        timeout=120,
                    )
                if r.status_code != 429:
                    break
                time.sleep(5)
            if r.status_code == 402:
                # The key's units are used up: stop here rather than record an error for every recording left.
                print(f"units used up after {n - 1} recordings; run again with more units to continue")
                break
            try:
                body = without_audio(r.json())
            except ValueError:  # an error page from a proxy rather than the API
                body = {"detail": f"HTTP {r.status_code}"}
            out.write(json.dumps({"id": rec["id"], "status": r.status_code, "body": body}, ensure_ascii=False) + "\n")
            out.flush()
            if n % 100 == 0:
                print(f"{n}/{len(recordings)}")


if __name__ == "__main__":
    main()
