# keywords7 sample

`keywords7_sample.json` is a 5,000-record sample of `keywords7.json`, which has
117,877 records (352 MB).  Since that is too large for GitHub, we are distributing this small
sample here.

For access to the full dataset, see <a href="../README_for_dataset.md">here</a>.

## Format

The sample has the same format as the full file: a JSON object mapping a paper
ID to a record. Records are unchanged and appear in their original order, so
code written for the sample also runs on the full file.

```python
import json

with open("keywords7_sample.json") as f:
    papers = json.load(f)
```

No field is present in every record, so use `.get()` or check for a field
before reading it.

| Field | Records in full file | Type |
|---|---|---|
| `externalids` | 117,874 | object of paper IDs |
| `title`, `url` | 116,491 | string |
| `authors` | 116,491 | list of `{authorId, name}` |
| `citing_sentences` | 92,677 | list of strings |
| `abstract` | 76,608 | string |
| `keywords_from_s2` | 73,772 | `{mentions, cited_for}`, lists of strings |
| `VitaLITy` | 50,834 | `{Title, Authors, Keywords, Year, Source, Citations, Abstract}` |
| `keywords_from_pdf` | 24,901 | string |

Things to watch for:

- `externalids` has two schemas: lowercase (`arxiv`, `mag`, `doi`, ...) and
  capitalized (`ArXiv`, `MAG`, `DOI`, ..., plus `CorpusId`).
- One record has the empty string as its paper ID.
- `keywords_from_pdf` is raw text from the PDF. It includes headers such as
  `Keywords:` and `Index Terms`, several separators, and non-keyword material
  such as PACS and MSC codes.

## How the sample was made

`make_sample.py` works in two stages:

1. **Coverage (483 records).** Each record is mapped to the cases it
   represents: field combination, `externalids` pattern, keyword format and
   separators, length and count ranges, non-ASCII text, duplicates, and so on.
   Records are selected until each of the 398 cases has at least 3 examples, or
   all of its examples if there are fewer than 3. The shortest and longest
   records on each length measure are also kept.
2. **Random fill (4,517 records).** The rest are drawn at random, in proportion
   to how common each field combination is.

`coverage_report.json` lists every case with its count in the full file and in
the sample.

The sample covers all 398 cases and all 35 field combinations. Plain random
samples of the same size covered 281-292 cases and 22-25 combinations.

## Limitations

Because of stage 1, rare cases are over-represented. Most field frequencies are
within about 1 percentage point of the full file, but `keywords_from_pdf`
appears in 23.6% of sample records and 21.1% of full-file records. Use the
sample for development and testing, and use the full file for statistics.

## Reproducing the sample

```bash
python3 make_sample.py keywords7.json output_dir --target 5000 --k 3 --seed 42
```
