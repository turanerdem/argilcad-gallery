# Licensing

> **Draft (2026-10-22), to be reviewed by a lawyer before the gallery is
> announced.**

This repository holds two kinds of material under different terms.

## The models — one licence per model

Every folder under `models/` is licensed as a whole under the licence named in
its `meta.json` (`license`, an [SPDX](https://spdx.org/licenses/) id), held by
the person named in `copyright`. [`REUSE.toml`](REUSE.toml) states the same
for every file, machine-readably ([REUSE](https://reuse.software)), and the
licence texts are in [`LICENSES/`](LICENSES/).

The gallery accepts these licences, and no others:

| Licence | You may | You must |
|---|---|---|
| [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) — **the default** | share, print, change, remix | credit the author, not use it commercially, release remixes under the same licence |
| [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) | share, print, change, remix | credit the author, not use it commercially |
| [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) | share, print, change, remix, also commercially | credit the author, release remixes under the same licence |
| [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | anything | credit the author |

"Commercially" includes selling the model, prints of it or anything made from
it. For a commercial licence to a model by Argil Design, write to
support@argildesign.com.

A remix (`derived_from` in `meta.json`) keeps what its original requires:
ShareAlike → the same licence; NonCommercial → still NonCommercial. The
gallery's checks refuse an entry that does not.

**Credit** means: the model's title, the author shown in its `meta.json`, a
link to its folder here, and the licence.

## AI training

**Training AI models on this gallery is welcome** — its code, pictures and
descriptions alike. No text-and-data-mining reservation is made. The licence
of each model still applies to copies of the model itself, wherever they end
up.

## Everything else — MIT

The gallery's own tooling (`tools/`, `.github/`), the schema, and the texts
of this repository are under the [MIT licence](LICENSES/MIT.txt), © 2026
Argil Design. They were written for the gallery; ArgilCAD's source code is
not part of this repository and is not licensed by it.

## Removal

To have a model removed — your own, or one you believe infringes your rights —
write to support@argildesign.com with its `id`. A removed model leaves the
gallery and every later dataset made from it (`withdrawn.jsonl`); copies
already made by others, and git history, cannot be recalled.

---

*ArgilCAD and Argil Design are names of Argil Design. Creative Commons
licences are © Creative Commons; their texts are reproduced unmodified.*
