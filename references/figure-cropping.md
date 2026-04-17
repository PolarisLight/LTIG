# Figure And Table Cropping

## Purpose

This workflow exists because full-page PDF renders are usually bad knowledge-base assets.

The target is:

- one tight method figure
- one or two tight main results tables
- explicit low-confidence handling when auto-cropping fails

## What To Extract

### Method figure

Prefer the figure that best explains the paper's overall method:

- framework
- overview
- architecture
- pipeline
- overall diagram

Usually this lives in the first `2-8` pages.

### Results tables

Prefer the main comparison tables, not:

- ablations
- runtime tables
- seed sensitivity tables
- appendix overflow tables

Usually this lives in the experiment section.

## Default Workflow

1. Run `scripts/extract_paper_key_regions.py`.
2. Inspect the generated JSON sidecar for page number, area ratio, confidence, and source.
3. Accept only `high` or `medium` confidence crops by default.
4. If a crop is `low` confidence, rerun with manual regions instead of keeping the auto output.

Example:

```bash
python /path/to/extract_paper_key_regions.py --pdf "/path/to/paper.pdf" --out-dir "/path/to/assets/paper_figures/已入库"
```

Manual override example:

```bash
python /path/to/extract_paper_key_regions.py \
  --pdf "/path/to/paper.pdf" \
  --out-dir "/path/to/assets/paper_figures/已入库" \
  --manual-method "3,42,78,575,455" \
  --manual-table "6,38,48,575,295"
```

Override format:

- `page,x0,y0,x1,y1`

## Acceptance Rules

Reject the crop as a final asset when any of these happen:

- crop area is close to a full page
- the detector could not anchor on a `Figure` or `Table` caption
- the crop clearly includes surrounding paragraphs that are not part of the figure or table
- the crop misses figure labels, axes, headers, or key table columns

Practical threshold:

- if the crop area is more than about `70%` of the full page, treat it as low confidence

## Naming Conventions

Prefer:

- `<stem>_figure_main.png`
- `<stem>_table_main_1.png`
- `<stem>_table_main_2.png`
- `<stem>_regions.json`

This keeps the note body predictable.

## Failure Policy

When auto-cropping fails:

1. keep the JSON sidecar
2. do not pretend the crop is acceptable
3. rerun with manual coordinates
4. only fall back to full-page rendering for temporary debugging, not for final note assets
