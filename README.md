# Multilingual Dictionary Seed Annotation

Small terminal tool for validating German-to-target word pairs.

Purpose: create better seed word pairs for aligning monolingual static word embeddings, improving the final multilingual embedding space and dictionary.

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

For each language pair, enter how many new examples to annotate. Enter `0` to skip a pair.

During annotation:

- `t` = correct translation
- `f` = wrong translation
- `s` = skip if you do not know the word or are very unsure; it does not count, and another random pair is shown
- `b` = go back
- `q` = quit and save

Skipped pairs are not saved as annotations, so the number you enter means the number of `t`/`f` decisions you will contribute.

Annotation rules:

- Ignore capitalization.
- Ignore OCR/spelling errors in either word if the intended word is clear.
- Ignore singular/plural differences if the meaning is otherwise correct.
- If a word is in the wrong language, mark it as false.
- If the source word has several common meanings, mark it as false immediately, even if the shown translation is correct for one of those meanings.
- If you know both words and the translation is only sort of correct, but not really correct, mark it as false.

## After Annotating

Push your changes so the next annotator starts from the latest file:

```bash
git add annotations/seed_annotations.json
git commit -m "Add seed annotations"
git push
```
