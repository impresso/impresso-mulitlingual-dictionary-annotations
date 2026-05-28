# Multilingual Dictionary Seed Annotation

Small terminal tool for validating German-to-target word pairs.

Purpose: create better seed word pairs for aligning monolingual static word embeddings, improving the final multilingual embedding space and dictionary.

## Files

- `pivot_seed_candidates_1to1_clustered_500x4.jsonl`: candidate word pairs
- `annotate_seed_candidates.py`: terminal annotation script
- `annotations/seed_annotations.json`: shared output file created while annotating

## Run

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
- `b` = go back
- `q` = quit and save

## After Annotating

Push your changes so the next annotator starts from the latest file:

```bash
git add annotations/seed_annotations.json
git commit -m "Add seed annotations"
git push
```
