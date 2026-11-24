# Spelly on speechocean762

How Spelly's pronunciation assessment compares with expert human raters on
[speechocean762](https://www.openslr.org/101/), a public set of English recordings by learners whose first
language is Mandarin. Spelly was never trained on any of speechocean762.

This repository has everything needed to check the numbers on
[spelly.ch/docs/benchmark](https://spelly.ch/docs/benchmark): Spelly's answers for all 2,500 test
recordings, the script that scores them against the raters, and the scripts to run the test again yourself.

## Results (24 November 2026)

All 2,500 test recordings were scored as American English by the same scoring that answers `POST /api/assess`,
run directly rather than over the network. Two were refused because nothing could be heard in them.

**Sound by sound.** A sound counts as flagged when Spelly did not hear it as the expected sound. The raters
scored each sound 0 to 2: below 1 is wrong, 2 is right.

| | Raters: wrong | Raters: right |
| --- | --- | --- |
| Spelly flags it | 1,538 | 3,707 |
| Spelly accepts it | 393 | 34,745 |

- 79.6% of the wrong sounds are flagged; 9.6% of the right sounds are flagged.
- F1 0.43. The raters also scored many sounds as "accented" (1); they are left out above.
  Counting them as errors, 50.3% of Spelly's flags match the raters (F1 0.46).

**Agreement with the raters' scores (Pearson).**

| Level | |
| --- | --- |
| Sound | 0.44 |
| Word accuracy | 0.41 |
| Sentence accuracy | 0.53 |
| Sentence accuracy and speaking rate, equal weight, nothing fitted | 0.61 |

Speaking rate is the number of expected sounds per second between the first and the last word. Both values
come from the API's answer. Spelly reports them separately; they are combined here only because the raters'
sentence score also rewards a smooth, steady pace.

## Files

| Path | What it is |
| --- | --- |
| `data/test.jsonl` | The 2,500 test recordings: id, text and the raters' scores for the sentence, each word and each sound |
| `results/2026-11-24/responses.jsonl.gz` | Spelly's answer for each recording, in the API's format, with the scores and sounds and without the audio clips |
| `results/2026-11-24/scores.json` | The output of `score.py` for that run |
| `score.py` | Scores a set of answers against the raters |
| `run.py` | Sends every recording to the API and saves the answers |
| `prepare.py` | Downloads speechocean762 and writes the test recordings as WAV files |

## Checking the published numbers

Python 3.10 or newer:

```bash
pip install -r requirements.txt
python score.py results/2026-11-24/responses.jsonl.gz
```

## Running it again

You need a Spelly API key and about 520 MB of disk space for the corpus. Each recording costs one unit.

**A free trial key:** sign up at [spelly.ch/operators/trial-signup](https://spelly.ch/operators/trial-signup),
open the link we email you and create your API key in the console. No credit card. The trial has 100 units,
enough for the first 100 recordings (add `--limit 100` to `run.py`); the full test needs 2,500. A trial key may
send 60 requests a minute, and `run.py` waits when it is told to slow down.

```bash
pip install -r requirements.txt
python prepare.py
export SPELLY_API_KEY=your-key
python run.py --out results/my-run/responses.jsonl.gz
python score.py results/my-run/responses.jsonl.gz
```

`run.py` can be stopped and started again; it skips recordings it has already answered.

## How sounds are matched

Spelly answers in IPA; the raters scored the 39 CMU phones. `score.py` turns each expected Spelly sound into CMU
phones (diphthongs and affricates are one phone) and lines them up with the raters' phones by edit distance.
A flap counts as a t or d, and a glottal stop as a t, as American English says them.

## Limits

- One language and one group of learners: English, read by speakers of Mandarin.
- Read sentences, not free speech.
- The raters are the reference. Where they let a missing sound pass, a correct flag by Spelly counts as a
  false alarm.

## Sources

- Zhang, J., Zhang, Z., Wang, Y., Yan, Z., Song, Q., Huang, Y., Li, K., Povey, D., & Wang, Y. (2021).
  speechocean762: An open-source non-native English speech corpus for pronunciation assessment.
  Proc. Interspeech 2021. https://arxiv.org/abs/2104.01378
- `data/test.jsonl` is derived from speechocean762, released under CC BY 4.0.
