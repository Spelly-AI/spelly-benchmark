"""Download speechocean762 from OpenSLR and write the test recordings as 16 kHz WAV files.

    python prepare.py --out data

Writes data/audio/<id>.wav for the 2,500 test recordings. The raters' scores are already in
data/test.jsonl, taken from the corpus's scores.json.

speechocean762 (OpenSLR 101) is released under CC BY 4.0 by Zhang et al. (2021).
"""
import argparse
import tarfile
import urllib.request
from pathlib import Path

URL = "https://www.openslr.org/resources/101/speechocean762.tar.gz"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("data"))
    parser.add_argument("--cache", type=Path, default=Path("data/download"))
    args = parser.parse_args()

    args.cache.mkdir(parents=True, exist_ok=True)
    archive = args.cache / "speechocean762.tar.gz"
    if not archive.exists():
        print(f"downloading {URL} (about 520 MB)")
        urllib.request.urlretrieve(URL, archive)
    corpus = args.cache / "speechocean762"
    if not corpus.exists():
        with tarfile.open(archive) as tar:
            tar.extractall(args.cache, filter="data")

    audio = args.out / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    count = 0
    for line in (corpus / "test" / "wav.scp").read_text().splitlines():
        if not line.strip():
            continue
        uid, path = line.split(maxsplit=1)
        target = audio / f"{uid}.wav"
        if not target.exists():
            target.write_bytes((corpus / path).read_bytes())
        count += 1
    print(f"{count} test recordings in {audio}")


if __name__ == "__main__":
    main()
