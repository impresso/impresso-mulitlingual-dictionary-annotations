# Multilingual Dictionary Seed Annotation

Small terminal tool for validating German-to-target word pairs.

Purpose: create better seed word pairs for
[`impresso/impresso-static-word-embeddings`](https://github.com/impresso/impresso-static-word-embeddings).
The resulting `seed_annotations.json` can be placed in that repository so stage
6 uses the human-approved normalized pairs as stronger initial alignment seeds.

## Files

- `pivot_seed_candidates_1to1_clustered_500x4.jsonl`: candidate word pairs
- `annotate_seed_candidates.py`: terminal annotation script
- `annotations/seed_annotations.json`: shared output file created while annotating

## Run

First time only, clone the repository:

```bash
git clone git@github.com:impresso/impresso-mulitlingual-dictionary-annotations.git
cd impresso-mulitlingual-dictionary-annotations
```

Before starting, always pull the latest annotations:

```bash
git pull
```

```bash
python annotate_seed_candidates.py
```

Please read the instructions printed by the script before starting.

The script shows surface forms when they are available, but the saved annotation
rows keep normalized `source_word` and `target_word` values for stage 6.

For each language pair, enter how many new examples to annotate. Enter `0` to skip a pair.

During annotation:

- `t` = correct translation
- `f` = wrong translation
- `s` = skip if you do not know the word or are very unsure; it does not count, and another random pair is shown
- `b` = go back
- `q` = quit and save

Skipped pairs are not saved as annotations, so the number you enter means the number of `t`/`f` decisions you will contribute.

Annotation rules:

- Focus on the semantics of the two words. If the target word is overall a correct semantic translation of the source word, mark it as true.
- Ignore capitalization and OCR/spelling errors if the intended word is clear.
- Ignore inflectional differences if the meaning is otherwise correct: tense, singular/plural, gender, and grammatical case such as nominative, accusative, dative, or genitive.
- If either word is in the wrong language for its column, mark it as false.
- If the two words are identical, mark it as false.
- For words with multiple meanings, judge the most common meaning of each word. Mark true if the common meanings match.
- Mark false if the match only works through a rare or unusual meaning of one word.

## After Annotating

Push your changes so the next annotator starts from the latest file:

```bash
git add annotations/seed_annotations.json
git commit -m "Added X new checked pairs - NAME"
git push
```

Replace `X` with the number of new `t`/`f` decisions you added, and replace `NAME` with your name.

To use the latest annotations in the static embeddings pipeline, replace
`seed_annotations.json` in
[`impresso/impresso-static-word-embeddings`](https://github.com/impresso/impresso-static-word-embeddings)
with the latest `annotations/seed_annotations.json` from this repository before
rerunning stage 6.
