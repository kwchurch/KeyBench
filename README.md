# KeyBench
A benchmark for a keyword prediction task: input academic paper --> output keywords

Examples of scoring

```sh
python KeyBench_score.py --KeyBench $HOME/to_go/keywords7.json --candidates $HOME/to_go/keywords7.json  --candidate_jsonpath '$..VitaLITy..Keywords[*]' --output /tmp/vitality.json
python KeyBench_score.py --KeyBench $HOME/to_go/keywords7.json --candidates $HOME/to_go/keywords7.json  --candidate_jsonpath '$..keywords_from_s2..mentions[*]' --output /tmp/s2.mentions.json
python KeyBench_score.py --KeyBench $HOME/to_go/keywords7.json --candidates $HOME/to_go/keywords7.json  --candidate_jsonpath '$..keywords_from_s2..cited_for[*]' --output /tmp/s2.cited_for.json
KeyBench_score.py --KeyBench $HOME/to_go/keywords7.json --candidates keywords_from_bot.json  --candidate_jsonpath '$..keywords_from_bot[*]' --output /tmp/bot.json
```

Example of creating candidates with a bot:

```sh
echo 252873724 256697363 39955946 |
tr ' ' '\n' |
python keywords_from_bot.py --KeyBench $HOME/to_go/keywords7.json --output /tmp/keywords_from_bot.json
```

This tool takes one or more CorpusIds as input, and outputs keywords for each of them (in a format that can be scored by KeyBench_score).

CorpusIds are primary keys for semantic scholar.  we assume there are titles and abstracts for these CorpusIds in the argument to --KeyBench.
