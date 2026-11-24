"""Compare Spelly's answers with the speechocean762 raters.

    python score.py results/2026-11-24/responses.jsonl.gz

Sound level: each sound the raters scored (one of 39 CMU phones, 0 to 2) is matched with the sound Spelly
expected at that place. Spelly "flags" a sound when it did not hear it as the expected sound: another sound,
a close sound, or nothing. The raters' "wrong" sounds are those scored below 1, their "right" sounds those
scored 2; sounds scored as accented are left out of the first table and counted as errors in the second.

Correlations (Pearson): sound (right 1, close 0.5, otherwise 0) against the raters' 0-2; word accuracy
against the raters' word accuracy; sentence accuracy against the raters' sentence accuracy and total.
Sentence with speaking rate: Spelly's accuracy and its speaking rate (expected sounds per second between
the first and the last word), each standardised and averaged with equal weight. Nothing is fitted.
"""
import gzip
import json
import sys
import unicodedata
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr

# IPA to the CMU phones the raters used. Pairs first (diphthongs, affricates, r-coloured vowels).
PAIRS = {("e", "ɪ"): "EY", ("a", "ɪ"): "AY", ("ɑ", "ɪ"): "AY", ("ɔ", "ɪ"): "OY", ("o", "ɪ"): "OY", ("a", "ʊ"): "AW",
         ("æ", "ʊ"): "AW", ("o", "ʊ"): "OW", ("ə", "ʊ"): "OW", ("t", "ʃ"): "CH", ("d", "ʒ"): "JH", ("ɜ", "ɹ"): "ER",
         ("ə", "ɹ"): "ER", ("ə", "˞"): "ER", ("ɜ", "˞"): "ER"}
SINGLE = {"i": "IY", "ɪ": "IH", "ɨ": "IH", "e": "EY", "ɛ": "EH", "æ": "AE", "a": "A", "ɑ": "AA", "ɒ": "AA",
          "ɔ": "AO", "o": "OW", "ʊ": "UH", "u": "UW", "ʉ": "UW", "ʌ": "AH", "ə": "AH", "ɐ": "AH", "ɜ": "ER",
          "p": "P", "b": "B", "t": "T", "d": "D", "k": "K", "ɡ": "G", "g": "G", "f": "F", "v": "V", "θ": "TH",
          "ð": "DH", "s": "S", "z": "Z", "ʃ": "SH", "ʒ": "ZH", "h": "HH", "m": "M", "n": "N", "ŋ": "NG", "l": "L",
          "ɹ": "R", "r": "R", "ɾ": "DX", "ʔ": "Q", "j": "Y", "w": "W"}
# A flap or glottal stop is how American English says t (and d) in many places; a bare a is either open vowel.
COMPATIBLE = {"DX": {"T", "D"}, "Q": {"T"}, "A": {"AA", "AE"}}


def to_cmu(ipa: str) -> list:
    chars = [c for c in unicodedata.normalize("NFD", ipa)
             if c == "˞" or unicodedata.category(c) not in ("Mn", "Lm", "Sk")]
    out, i = [], 0
    while i < len(chars):
        if tuple(chars[i:i + 2]) in PAIRS:
            out.append(PAIRS[tuple(chars[i:i + 2])])
            i += 2
        else:
            out.append("R" if chars[i] == "˞" else SINGLE.get(chars[i], "X:" + chars[i]))
            i += 1
    return out


def same(rated: str, ours: str) -> bool:
    return ours == rated or rated in COMPATIBLE.get(ours, ())


def align(rated: list, ours: list) -> list:
    """For each rated phone, the index of our phone lined up with it, or None (edit distance)."""
    n, m = len(rated), len(ours)
    d = np.zeros((n + 1, m + 1), dtype=np.int32)
    d[:, 0], d[0, :] = np.arange(n + 1), np.arange(m + 1)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i, j] = min(d[i - 1, j] + 1, d[i, j - 1] + 1, d[i - 1, j - 1] + (not same(rated[i - 1], ours[j - 1])))
    i, j, got = n, m, [None] * n
    while i > 0 and j > 0:
        if d[i, j] == d[i - 1, j - 1] + (not same(rated[i - 1], ours[j - 1])):
            got[i - 1] = j - 1
            i, j = i - 1, j - 1
        elif d[i, j] == d[i - 1, j] + 1:
            i -= 1
        else:
            j -= 1
    return got


def matrix(flagged, error, correct) -> dict:
    tp, fn = int((flagged & error).sum()), int((~flagged & error).sum())
    fp, tn = int((flagged & correct).sum()), int((~flagged & correct).sum())
    precision, recall = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": round(precision, 4), "recall": round(recall, 4),
            "false_alarm_rate": round(fp / max(fp + tn, 1), 4),
            "f1": round(2 * precision * recall / max(precision + recall, 1e-9), 4)}


def r(a, b) -> float:
    return round(float(pearsonr(a, b)[0]), 4)


def main() -> None:
    answers = [json.loads(line) for line in gzip.open(sys.argv[1], "rt", encoding="utf-8")]
    rated = {rec["id"]: rec for rec in map(json.loads, Path("data/test.jsonl").open(encoding="utf-8"))}

    sound_ours, sound_rated, word_ours, word_rated, sentences = [], [], [], [], []
    refused = unmatched = 0
    for answer in answers:
        if answer["status"] != 200:
            refused += 1
            continue
        body, raters = answer["body"], rated[answer["id"]]
        words = body["analyzed_text"]
        expected = [d for w in words for d in w["phoneme_details"] if d["is_reference"]]
        timed = [w for w in words if w["start_time"] is not None and w["end_time"] is not None]
        span = timed[-1]["end_time"] - timed[0]["start_time"] if len(timed) > 1 else 0
        rate = len(expected) / span if span > 0 else np.nan
        sentences.append((body["accuracy"], rate, raters["sentence"]["accuracy"], raters["sentence"]["total"]))
        if len(words) != len(raters["words"]):
            unmatched += 1
            continue
        for ours, theirs in zip(words, raters["words"]):
            word_ours.append(ours["accuracy"])
            word_rated.append(theirs["accuracy"])
            cmu, score = [], []
            for d in (d for d in ours["phoneme_details"] if d["is_reference"]):
                value = 1.0 if d["predicted"] == d["phoneme"] else 0.5 if d["is_close"] else 0.0
                for phone in to_cmu(d["phoneme"]):
                    cmu.append(phone)
                    score.append(value)
            for k, j in enumerate(align([p.rstrip("012") for p in theirs["phones"]], cmu)):
                if j is not None:
                    sound_ours.append(score[j])
                    sound_rated.append(theirs["phones_accuracy"][k])

    ours, theirs = np.array(sound_ours), np.array(sound_rated)
    flagged = ours < 1
    s = np.array(sentences, dtype=float)
    acc, rate = s[:, 0], s[:, 1]
    standard = lambda x: (x - np.nanmean(x)) / np.nanstd(x)
    # A recording with fewer than two timed words has no speaking rate; its accuracy stands alone.
    mixed = np.nanmean(np.vstack([standard(acc), standard(rate)]), axis=0)

    report = {
        "recordings": len(answers), "refused": refused, "word_count_differs": unmatched,
        "sounds_wrong_vs_right": matrix(flagged, theirs < 1, theirs >= 2),
        "sounds_not_right_vs_right": matrix(flagged, theirs < 2, theirs >= 2),
        "pearson": {
            "sound": r(ours, theirs),
            "word": r(word_ours, word_rated),
            "sentence_vs_accuracy": r(acc, s[:, 2]),
            "sentence_vs_total": r(acc, s[:, 3]),
            "sentence_with_speaking_rate_vs_accuracy": r(mixed, s[:, 2]),
            "sentence_with_speaking_rate_vs_total": r(mixed, s[:, 3]),
        },
    }
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
