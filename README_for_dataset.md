# KeyBench

This data is posted in three places:

* <a href="https://doi.org/10.5061/dryad.bk3j9kdsn">doi.org/10.5061</a>
* <a href="https://doi.org/10.7910/DVN/CZNUZN">doil.org/10.7910</a>
* <a href="https://drive.google.com/file/d/17LEj3Ybwyt_oDq-vjcxmOo065lhC7KVo/view?usp=sharing">Google Drive</a>

This resource is intended to encourage the community to build tools to
extract keywords.  Many papers on ArXiv list keywords on the first
page, typically near the abstract.  The proposed resource scrapes
these keywords, and uses them as the gold standard for a prediction
task.  An evaluation compares three baselines for predicting the gold
standard: (1) VitaLity, (2) topics from Semantic Scholar and (3) a
chatbot.  The resource is intended to challenge the community to beat
these baselines.  To make it easier for the community to build such
systems, the resource includes a number of fields for 117,877 papers
from Semantic Scholar: (a) title, (b) abstract, (c) authors, (d)
citing sentences, and (e) ids to make it easier to join with data in
resources such as ArXiv, Semantic Scholar, ACL Anthology, PubMed, etc.
We hope the community will show that citing sentences are useful
because of the wisdom of the crowd. Good keywords are likely to be
used by many authors.

For more details, see <a href="https://github.com/kwchurch/KeyBench">github<a/>.
A draft paper is posted <a href="https://github.com/kwchurch/KeyBench/blob/main/draft.pdf">here</a>.

The paper mentions $G$, $V$ and $S$ labels:

<table>
<tr><th>Symbol</th><th>Description</th><th>json field</th></tr>
<tr><td>$G$</td><td>Gold labels</td></td>keywords_from_pdf</td></tr>
<tr><td>$V$</td><td><a href="https://vitality-vis.github.io/">VitaLITy</a> labels</td></td>keywords_from_vitality</td></tr>
<tr><td>$S$</td><td>Semantic Scholar Topics</td></td>keywords_from_s2</td></tr>
</table>

There are two types of labels under $S$: $S_m$ (mention) and $S_c$ (cited for).  See discussion in paper
for more details about those labels.  These labels are based on three publicly available files from AWS:
 * <a href="https://us-west-2.console.aws.amazon.com/s3/buckets/ai2-s2-research-public?prefix=topics_db_04272026/topic_papers_pdp/">topic_papers_pdp</a>
 * <a href="https://us-west-2.console.aws.amazon.com/s3/buckets/ai2-s2-research-public?prefix=topics_db_04272026/topics_list/">topics_list</a>
 * <a href="https://us-west-2.console.aws.amazon.com/s3/buckets/ai2-s2-research-public?prefix=topics_db_04272026/all_descriptions/">descriptions of topics</a>

The task is to predict the $G$ labels from titles, abstracts and citing sentences in the json file.

Many values are missing (not in json).

The github mentioned above provides code for evaluation.

