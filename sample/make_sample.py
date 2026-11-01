#!/usr/bin/env python3
"""Build a small, case-covering sample of keywords7.json.

Usage: make_sample.py keywords7.json OUT_DIR [--target 5000] [--k 3] [--seed 42]

Stage 1 (coverage): greedy set cover. Every record is mapped to a set of
"case" features; records are picked until each feature has at least k examples
(or all of them, when fewer than k exist). The extreme records for each length
measure are always kept.

Stage 2 (fill): the rest of the sample is drawn at random, proportionally
within each combination of fields, so ordinary records stay represented.

Records are copied unchanged, in their original order.
"""
import argparse
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path


def bucket(n, edges):
    """Label n with the first edge it does not exceed, e.g. <=10."""
    for e in edges:
        if n <= e:
            return f"<={e}"
    return f">{edges[-1]}"


def kw_format(s):
    x = s.lower().lstrip(" \t—–-·•∗†_([“")
    rules = [
        ("pacs", r"pacs"),
        ("msc", r"(\d{4} )?(msc|mathematics subject|ams)"),
        ("jel", r"jel"),
        ("acm_ccs", r"(acm|ccs|categories)"),
        ("index_terms", r"index terms"),
        ("author_keywords", r"author keywords"),
        ("additional_keywords", r"additional keywords"),
        ("keywords_and_phrases", r"(key ?words) and"),
        ("keywords_colon", r"key ?words?\s*:"),
        ("keywords_dash", r"key ?words?\s*[—–-]"),
        ("keywords_bare", r"key ?words?\b"),
    ]
    for name, pat in rules:
        if re.match(pat, x):
            return name
    return "other"


def first_char(s):
    c = s[:1]
    if c.isupper():
        return "upper"
    if c.islower():
        return "lower"
    if c.isdigit():
        return "digit"
    return f"punct:{c!r}"


def arxiv_format(a):
    if re.fullmatch(r"\d{4}\.\d{4,5}", a):
        return "new"
    if re.fullmatch(r"[a-z-]+(\.[A-Z]{2})?/\d{7}", a):
        return "old"
    return "other"


def features(key, v, dup_titles, dup_kw):
    """Return the set of case labels a record belongs to."""
    f = set()
    fields = tuple(sorted(v))
    f.add(f"fields={fields}")
    f.add(f"id_digits={len(key)}")

    e = v.get("externalids")
    if e is None:
        f.add("ext=missing")
    else:
        f.add("ext_schema=" + ("upper" if "CorpusId" in e else "lower"))
        f.add(f"ext_pattern={tuple(sorted(k for k, x in e.items() if x is not None))}")
        for k, x in e.items():
            f.add(f"ext_type={k}:{type(x).__name__}")
        a = e.get("arxiv") or e.get("ArXiv")
        if isinstance(a, str):
            f.add("arxiv_format=" + arxiv_format(a))

    kw = v.get("keywords_from_pdf")
    if kw is not None:
        fmt = kw_format(kw)
        f.add(f"kw_format={fmt}")
        f.add(f"kw_format_by_fields={fmt}|{fields}")
        f.add(f"kw_first_char={first_char(kw)}")
        f.add(f"kw_len={bucket(len(kw), [10, 30, 100, 300, 1000])}")
        for name, sep in [(";", ";"), (",", ","), ("·", "·"), ("—", "—"), ("/", "/"),
                          (" - ", " - "), ("•", "•"), ("|", "|")]:
            if sep in kw:
                f.add(f"kw_sep={name}")
        if not kw.isascii():
            f.add("kw_non_ascii")
        if kw in dup_kw:
            f.add("kw_duplicated")

    if "citing_sentences" in v:
        cs = v["citing_sentences"]
        f.add(f"n_citing={bucket(len(cs), [0, 1, 2, 3, 5, 10, 30])}")
        for s in cs:
            f.add(f"citing_len={bucket(len(s), [10, 30, 300, 1000, 5000])}")

    if "authors" in v:
        au = v["authors"]
        f.add(f"n_authors={bucket(len(au), [0, 1, 2, 5, 10, 50, 500])}")
        if any(not a.get("authorId") for a in au):
            f.add("author_null_id")
        if any(not (a.get("name") or "").isascii() for a in au):
            f.add("author_non_ascii")

    if "abstract" in v:
        f.add(f"abstract_len={bucket(len(v['abstract']), [50, 200, 1000, 2500, 5000])}")
    if "title" in v:
        t = v["title"]
        f.add(f"title_len={bucket(len(t), [10, 30, 100, 200])}")
        if not t.isascii():
            f.add("title_non_ascii")
        if t in dup_titles:
            f.add("title_duplicated")

    s2 = v.get("keywords_from_s2")
    if s2 is not None:
        f.add(f"s2_mentions={bucket(len(s2['mentions']), [1, 5, 20, 100])}")
        f.add(f"s2_cited_for={bucket(len(s2['cited_for']), [0, 5, 20, 100])}")

    vit = v.get("VitaLITy")
    if vit is not None:
        f.add(f"vit_decade={str(vit['Year'])[:3]}0s")
        f.add(f"vit_n_keywords={bucket(len(vit['Keywords']), [1, 3, 5, 10])}")
        c = vit["Citations"]
        f.add("vit_citations=" + (bucket(int(c), [0, 9, 99, 999]) if c.isdigit() else "non_numeric"))
        f.add(f"vit_source={vit['Source']}")
        if any(re.search(r" \d{4}$", a) for a in vit["Authors"]):
            f.add("vit_author_disambiguated")
    return f


def extremes(d, n=3):
    """Keys of the n smallest and largest records on each length measure."""
    measures = {
        "keywords_from_pdf": lambda v: len(v["keywords_from_pdf"]) if "keywords_from_pdf" in v else None,
        "abstract": lambda v: len(v["abstract"]) if "abstract" in v else None,
        "title": lambda v: len(v["title"]) if "title" in v else None,
        "authors": lambda v: len(v["authors"]) if "authors" in v else None,
        "citing_sentences": lambda v: len(v["citing_sentences"]) if "citing_sentences" in v else None,
        "longest_citing": lambda v: max(map(len, v["citing_sentences"])) if v.get("citing_sentences") else None,
    }
    keep = set()
    for m in measures.values():
        vals = sorted(((m(v), k) for k, v in d.items() if m(v) is not None))
        keep.update(k for _, k in vals[:n] + vals[-n:])
    return keep


def greedy_cover(feats, k, seed_keys):
    """Pick records until every feature has min(k, its frequency) examples."""
    freq = Counter(x for fs in feats.values() for x in fs)
    need = {x: min(k, c) for x, c in freq.items()}
    chosen = list(seed_keys)
    for key in chosen:
        for x in feats[key]:
            if x in need:
                need[x] -= 1
                if need[x] <= 0:
                    del need[x]
    by_feature = defaultdict(list)
    for key, fs in feats.items():
        for x in fs:
            by_feature[x].append(key)
    picked = set(chosen)
    while need:
        # Rarest open feature first, so singletons are forced in early, then
        # the record that closes the most other open features.
        x = min(need, key=lambda z: (freq[z], z))
        cands = [c for c in by_feature[x] if c not in picked]
        best = max(cands, key=lambda c: (sum(y in need for y in feats[c]), c))
        picked.add(best)
        chosen.append(best)
        for y in feats[best]:
            if y in need:
                need[y] -= 1
                if need[y] <= 0:
                    del need[y]
    return chosen, freq


def proportional_fill(d, picked, target, rng):
    strata = defaultdict(list)
    for k, v in d.items():
        strata[tuple(sorted(v))].append(k)
    room = target - len(picked)
    if room <= 0:
        return []
    pool = {s: sorted(set(ks) - picked) for s, ks in strata.items()}
    total = sum(map(len, pool.values()))
    quota = {s: room * len(ks) / total for s, ks in pool.items()}
    take = {s: int(q) for s, q in quota.items()}
    left = room - sum(take.values())
    for s in sorted(quota, key=lambda s: (take[s] - quota[s], s))[:left]:
        take[s] += 1
    out = []
    for s, ks in pool.items():
        out.extend(rng.sample(ks, min(take[s], len(ks))))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("source")
    p.add_argument("out_dir")
    p.add_argument("--target", type=int, default=5000)
    p.add_argument("--k", type=int, default=3)
    p.add_argument("--seed", type=int, default=42)
    a = p.parse_args()

    with open(a.source, encoding="utf-8") as fh:
        d = json.load(fh)

    titles = Counter(v["title"] for v in d.values() if "title" in v)
    kws = Counter(v["keywords_from_pdf"] for v in d.values() if "keywords_from_pdf" in v)
    dup_titles = {t for t, c in titles.items() if c > 1}
    dup_kw = {t for t, c in kws.items() if c > 1}

    feats = {k: features(k, v, dup_titles, dup_kw) for k, v in d.items()}
    chosen, freq = greedy_cover(feats, a.k, sorted(extremes(d)))
    picked = set(chosen)
    fill = proportional_fill(d, picked, a.target, random.Random(a.seed))
    picked |= set(fill)

    sample = {k: v for k, v in d.items() if k in picked}  # keeps source order
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "keywords7_sample.json").write_text(
        json.dumps(sample, indent=4), encoding="utf-8")  # same layout as the source

    got = Counter(x for k in sample for x in feats[k])
    report = {
        "source_records": len(d),
        "sample_records": len(sample),
        "coverage_records": len(chosen),
        "fill_records": len(fill),
        "k": a.k,
        "seed": a.seed,
        "n_features": len(freq),
        "features_covered": sum(x in got for x in freq),
        "features": {x: {"full": freq[x], "sample": got[x]} for x in sorted(freq)},
    }
    (out / "coverage_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print({k: v for k, v in report.items() if k != "features"})


if __name__ == "__main__":
    main()
