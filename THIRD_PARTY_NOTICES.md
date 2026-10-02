# Third-party material

This repository contains material that I did not write. Each item keeps its own terms.

## NEORV32 RTL

- **Where:** `data/RTL_data/` (18 files), `data/RTL_heldout/` (26 files), `bahavioral_patterns_of_assets/data/RTL_data/` (a copy
  of `data/RTL_data/`).
- **Source:** the NEORV32 RISC-V processor by Stephan Nolting and the NEORV32 contributors, hardware version 1.11.4.3
  (`hw_version_c = x"01110403"`). The files are byte-identical to the copy in
  [Ajoad/LAsset-Security-Assets](https://github.com/Ajoad/LAsset-Security-Assets) (`SoC/neorv32 RTL/`, commit `dae43f1`).
- **License:** BSD 3-Clause. The full text is in [`third_party/NEORV32_LICENSE`](third_party/NEORV32_LICENSE), and
  each file keeps its SPDX header.

## LAsset reference lists

- **Where:** `data/ground_truth/` (`manual_gt_neorv32.json`, `lasset_initial.json`, `lasset_refined.json`), a copy of
  `manual_gt_neorv32.json` in `bahavioral_patterns_of_assets/ground_truth/`, and `data/LAsset_initial_results/`.
- **Source:** [Ajoad/LAsset-Security-Assets](https://github.com/Ajoad/LAsset-Security-Assets), commit `dae43f1`.
  - The manual reference comes from the sheet "Assets (Manual)" of `SoC/Asset_Dataset_Statistics_NEORV32.xlsx`.
    `src/gt_extract.py` converts it.
  - LAsset's own lists come from `SoC/Spec.+RTL/` and the RTL-only folder.
- **Paper:** LAsset, arXiv:2601.02624 (DATE 2026).
- **Terms:** the upstream repository has no license file. The lists are included only so that the scores in this
  repository can be checked with the same reference. They are not mine. Several pre-registrations here pin them by
  hash, so they are kept unchanged. I will remove them at the authors' request.

## Worked examples inside prompts

Some prompts (for example `assetgen_meta/prompt_opt/v1/exec_prompt.txt` and the `src/icl_examples_*.py` files) embed
short RTL excerpts of two open IPs as worked examples. Both were taken from the `IP/` folder of the LAsset repository.
Comments were removed when the prompts were built, which also removed the license headers, so they are named here:

- **omsp_gpio** from openMSP430, Copyright (c) 2009 Olivier Girard. BSD-style license.
- **tiny_aes**, Copyright (c) 2012 Homer Hsing. Apache License 2.0.

## Not included

- The NEORV32 datasheet PDFs, the NEORV32 git checkout (`neorv32/`), and the LAsset repository's `IP/` folder.
- No paper PDF is included. Papers are cited by reference only.
