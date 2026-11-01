# KeyBench
A benchmark for a keyword prediction task: input academic paper --> output keywords

## Downloading the full Dataset as well as a sample

Dataset is discussed <a href="README_for_dataset.md">here</a>.
That link also explains how to download the larger collection of 117,877 json records (352 MB).
Since that collection is too large for for GitHub, there is a small (teaser) sample <a href="sample">here</a>.

## Scraping PDFs

We limited scraping to papers from ArXiv because it is easy to
download documents from there.  We chose arXiv papers that overlapped
with s2orc and/or VitaLITy.  A small sample of these pdfs are posted <a href="sample_docs">here</a>,
as well as several additional files.  For example, for <a href="sample_docs/125950001.pdf">pdf from arXiv</a>
there are three additional files:

* <a href="sample_docs/125950001.json">json version of pdf (using PyMuPDF)</a>
* <a href="sample_docs/125950001.json.keywords2">keywords extracted from above</a>
* <a href="sample_docs/125950001.citing_sentences">citing sentences (from Semantic Scholar)</a>

The strings in <a href="sample_docs/125950001.json.keywords2">keywords extracted from above</a>
are used to create the keywords_from_pdf field in the collection.

The code for extracting <a href="sample_docs/125950001.json.keywords2">keywords extracted from above</a>
from <a href="sample_docs/125950001.json">json version of pdf (using PyMuPDF)</a> is <a href="scrape">here</a>.
The code selects papers that mention the term "Keyword" on the first page.  It extracts text lines in relevant text blocks,
using simple heuristics expressed in terms of jsonpath patterns.

Documentation for PyMuPDF is available <a href="https://pymupdf.readthedocs.io/en/latest/">here</a>.

## Evaluating Quality of Keywords from PDFs

This tool was used to extract samples of arXiv papers and keywords using an interface
that makes it easy to judge the results.  The interface code was written by a bot,
and is posted <a href="scrape/extract_arxiv_keywords.py">here</a>.

Two judges evaluated about 500 papers.  See <a href="eval">here</a> for their judgments.
Note that the scraping tool outputs strings like this:

<pre>
Keywords:
 short-arc orbit determination, asteroids, Near-Earth Object, Minor Planet Center
 </pre>

The evaluation script turns that string in a list of four keywords:

 * short-arc orbit determination
 * asteroids
 * Near-Earth Object
 * Minor Planet Center

using a set of simple heuristics.  It turns out that this last step is more challenging than one
might have thought.  The bot could have done a better job of removing leading strings like "Keywords:",
as well as splitting keywords.  There are more ways to do this than one might have imagined.  The benchmark does not get
into these details, but there is considerable room for improvement there.

## Examples of scoring

```sh
python KeyBench_score.py --KeyBench $HOME/to_go/keywords7.json --candidates $HOME/to_go/keywords7.json  --candidate_jsonpath '$..VitaLITy..Keywords[*]' --output /tmp/vitality.json
python KeyBench_score.py --KeyBench $HOME/to_go/keywords7.json --candidates $HOME/to_go/keywords7.json  --candidate_jsonpath '$..keywords_from_s2..mentions[*]' --output /tmp/s2.mentions.json
python KeyBench_score.py --KeyBench $HOME/to_go/keywords7.json --candidates $HOME/to_go/keywords7.json  --candidate_jsonpath '$..keywords_from_s2..cited_for[*]' --output /tmp/s2.cited_for.json
KeyBench_score.py --KeyBench $HOME/to_go/keywords7.json --candidates keywords_from_bot.json  --candidate_jsonpath '$..keywords_from_bot[*]' --output /tmp/bot.json
```

## Example of creating candidates with a bot:

```sh
echo 252873724 256697363 39955946 |
tr ' ' '\n' |
python keywords_from_bot.py --KeyBench $HOME/to_go/keywords7.json --output /tmp/keywords_from_bot.json
```

This tool takes one or more CorpusIds as input, and outputs keywords for each of them (in a format that can be scored by KeyBench_score).

CorpusIds are primary keys for semantic scholar.  we assume there are titles and abstracts for these CorpusIds in the argument to --KeyBench.
