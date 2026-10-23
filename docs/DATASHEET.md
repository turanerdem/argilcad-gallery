# Datasheet — ArgilCAD Gallery

A living data card, after *Datasheets for Datasets* (Gebru et al.). Kept
from the first entry so that a dataset made from the gallery later has its
history written down rather than reconstructed.

## Motivation

The gallery shows what ArgilCAD makes, lets anyone open and change a model's
code, and accumulates text ↔ CAD-code ↔ geometry examples for research on
generating parametric CAD from language.

## Composition

- One entry per folder in `models/`: a build123d Python script (`model.py`,
  the source of truth), its description (`meta.json`, schema in `schema/`), a
  GLB preview, four renders from fixed cameras in a plain look (iso, front,
  top, right; 512 px), a thumbnail and a social card in the Studio look, and a
  turntable or animation (animated WebP).
- `meta.json` records exact geometry measured by the CAD kernel (bounding box,
  volume, area, topology counts, parts), the engine versions, and a
  fingerprint for finding duplicates.
- Everything but `model.py` is derived from it and can be regenerated, at any
  resolution or from any angle.

## Collection

- **Owner's models** (`consent.terms_version: "owner"`): made by Argil Design
  in ArgilCAD, with ArgilCAD's AI, an AI assistant over MCP, the user's own AI,
  or by hand — `source.kind` says which.
- **Submissions** (from ArgilCAD, after review): under the
  [Contributor Terms](../TERMS.md); `consent` records what was agreed.
- Edit histories (prompts, intermediate code, errors) are collected only with
  explicit consent, are **not** in this repository, and are kept by Argil
  Design.

## Known limitations and biases

- Early entries are Argil Design's own marketing models: toys, desk objects
  and mechanisms are over-represented.
- Much of the code was written by large language models (`source.kind` in
  `app_llm`, `mcp`, `own_ai`). Their providers' terms may restrict using that
  output to train competing models; a dataset user must filter by `source`
  where that matters.
- Titles and descriptions are written in English and Turkish by the author or
  Argil Design; prompts, where shared, are as typed.

## Uses

Showcase and remix. Research and training on text-to-CAD, CAD editing and
code repair. Not for: anything the content policy excludes.

## Splits

None are published yet. When they are, near-duplicates and remixes
(`fingerprint`, `derived_from`) stay on one side of a split, and an
evaluation set is kept out of this public repository.

## Maintenance

Argil Design, support@argildesign.com. Withdrawn entries are listed in
`withdrawn.jsonl` and left out of every later snapshot. Snapshots will be
versioned as GitHub releases (`data-vYYYY.MM`).
