# Task brief for prompt designers

You will write the **instructions (a prompt) for an executor agent**. The executor reads your prompt and ONE input
file, and lists the **primary security assets** of the hardware module in that file. You design the prompt; you do not
run it.

## What the executor sees

1. Your prompt, as a file it reads first.
2. One input file: an RTL module (VHDL) followed by its relation map. The format is in
   `blind_agent/MAP_FORMAT.md`. Two example input files: `blind_agent/inputs/design/neorv32_boot_rom.txt` and
   `blind_agent/inputs/design/neorv32_fifo.txt`. The real inputs come from the same processor and its peripherals:
   CPU parts, bus and memory units, debug, timers, communication and security peripherals; some files are much larger
   (up to several thousand RTL lines with several entities).

The executor gets a fixed wrapper around your prompt, the same for every designer:

> Use only two files. (1) Read your instructions: `<your prompt file>`. (2) Read the module input: `<input file>`;
> read all of it (use several reads with offset and limit if needed). Do not open any other file, do not search, do not
> run commands, do not use the web. Follow the instructions and write the final JSON object to `<output file>` with
> the Write tool. Then reply DONE.

The executor has no other context: no specification, no documentation, no other modules.

## What the executor must output

Exactly this JSON object (your prompt must ask for it; you may add other top-level keys before `assets`, for example a
place for the executor's analysis, but `module` and `assets` must be present with this shape):

```json
{"module": "<module name from the input file>",
 "assets": [
   {"element": "<a declared element name, exactly as declared: a port, a signal, or <record>.<field>>",
    "entity": "<the entity that declares it>",
    "security_objective": "Confidentiality | Integrity | Availability",
    "reason": "<one or two sentences>"}
 ]}
```

## How the output is judged

The element list of each module is compared with a **reference list of primary assets** written by hardware-security
experts for the LAsset study (`E:\jobs\ff\2601.02624v2.pdf` defines primary assets). Names are compared
as declared. **Precision** (share of listed elements that are in the reference) and **recall** (share of reference
entries that were listed) both count, equally. The objective and reason are kept for analysis, not scored. You will
never see the reference, any score, or any earlier prompt for this task; do not try to infer them. Reason from the
definitions in the sources below and from how RTL works.

## Sources you may read (and nothing else)

- `E:\jobs\ff\2601.02624v2.pdf`: LAsset (the study the reference comes from). Use it for its definitions and its
  examples from other designs. Do not copy any processor-specific element name into your prompt.
- `E:\jobs\ff\IEEE_P3164_Asset_Identification.pdf`: IEEE P3164 white paper (conceptual and structural assets, the
  identification questions, worked examples).
- `E:\jobs\ff\Accellera_SA-EDI_Standard_v10.pdf`: Accellera SA-EDI standard (asset types, attack surface).
- `E:\jobs\ff\2502.04648.pdf`: Nath & Tan (behavioural patterns of primary assets).
- `E:\jobs\ff\SAIF_Automated_Asset_Identification_for_Security_Verification_at_the_Register_Transfer_Level.pdf`: SAIF
  (primary versus secondary assets).
- This brief, `blind_agent/MAP_FORMAT.md`, and the two design input files above.

PDF pages: read with the Read tool's `pages` parameter (at most 20 pages per call).

## Rules for the prompt

1. **No identifiers from this processor**: no module, entity, port, signal, field or constant name from the design
   files or any other part of this processor, and not the processor's name. Examples must be invented and generic, or
   taken from the sources' own examples on other designs. (Checked by code.)
2. **No numeric quotas or proportions** ("at most N", "about N%", "N assets per module"). (Checked by code.)
3. **No instruction to use HDL comments.** The inputs have none.
4. Every rule in the prompt that decides whether an element is or is not an asset must have a basis in the sources:
   give the source and page for each such rule in your rationale file (not in the prompt).
5. Self-contained: the executor sees nothing but your prompt and the input file.

## What you write

- `blind_agent/prompts/<your id>/prompt.md`: the prompt, complete, as the executor will read it.
- `blind_agent/prompts/<your id>/rationale.md`: each decision rule, its source and page, and why you designed the
  prompt this way.
