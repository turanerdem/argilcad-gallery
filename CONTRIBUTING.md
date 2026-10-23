# Contributing

## Submitting a model

Models come in **through ArgilCAD**, not through pull requests: build your
model in [ArgilCAD](https://argildesign.com/argilcad/) with a registered
account and choose **Share to gallery** (coming soon). You will be asked for a
title, a short description, a licence, and to accept the
[Contributor Terms](TERMS.md).

Every submission is reviewed by Argil Design. Nothing appears in the gallery
until it has been approved; you will see the outcome in ArgilCAD. Pull
requests opened from outside this repository are closed automatically.

## Content policy

The gallery does not accept:

- weapons, weapon parts or accessories (including suppressors and magazines),
  or anything made to harm;
- brands, logos, characters or protected designs that you do not own, and
  product names in titles;
- personal data — in the title, the description, the prompt or the model;
- anything unlawful, hateful or sexual.

Code is in English — variable names, comments and part labels — so it reads
the same everywhere; a submission in another language is translated during
review, without changing its geometry.

Models should build in a reasonable time (the checks allow five minutes),
come out as closed solids, and run as plain build123d scripts outside
ArgilCAD.

## Reporting a model

Write to support@argildesign.com with the model's `id` (in its README).

## For maintainers

Entries are written by Argil Design's publishing tool, which builds the code
in ArgilCAD and draws every picture in the app. Then:

```sh
python -m venv .venv && .venv/bin/pip install -r tools/requirements.txt
.venv/bin/python tools/gallery.py generate     # index.jsonl, READMEs, REUSE.toml
.venv/bin/python tools/gallery.py check        # schema, media, policy, licences, build
.venv/bin/reuse lint
```

CI runs the same checks on every pull request (`validate.yml`), a monthly
rebuild of every model against the pinned engine (`reverify.yml`), and purges
the CDN after a merge (`publish.yml`). A model must build as a plain
build123d script (`tools/runtime.py`); one that leans on anything only
ArgilCAD provides is refused before it gets here.
