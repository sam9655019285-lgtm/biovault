"""
User Guide / Help content for BioVault (non-UI, no Streamlit dependency).

This module holds only plain-Python content (strings, dicts, lists)
describing how the *actual implemented* features of BioVault work --
it does not compute anything and does not describe features that
don't exist in the codebase. Keeping this separate from
ui_documentation.py means the content can be unit-tested (e.g. "does
the encoding section mention the real 2-bit mapping?") without any
Streamlit dependency.
"""

SECTIONS = [
    {
        "id": "welcome",
        "title": "1. Welcome to BioVault",
        "content": """
BioVault is an **educational simulation platform** that demonstrates how
digital files could theoretically be stored as DNA sequences.

**What BioVault does:**
- Converts an uploaded file into binary, then into a DNA base sequence (A, T, G, C).
- Lets you simulate DNA storage errors (mutations) and try to correct them.
- Analyzes storage efficiency and visualizes the results.
- Lets you export/import DNA sequences and generate a project report.
- Lets you benchmark different stages of an experiment side by side.

**DNA digital data storage, in short:** each DNA base can represent 2 bits
of information (since there are 4 possible bases, just like there are 4
possible 2-bit values: 00, 01, 10, 11). Storing data "in DNA" means
encoding binary data as a sequence of these bases.

**Intended purpose:** this project is a teaching tool for biotechnology,
bioinformatics, and engineering students -- it is **not** a real DNA
synthesis, sequencing, or laboratory system.
""",
    },
    {
        "id": "getting_started",
        "title": "2. Getting Started",
        "content": """
**Sidebar navigation:** use the sidebar on the left to move between pages.
Each page builds on data from earlier pages, so the recommended order is
top to bottom.

**1. Upload a file** -- go to **File Upload**, choose a small `.txt`,
`.png`, `.jpg`, or `.jpeg` file (5 MB or smaller). You'll see its
filename, type, size, and a preview.

**2. Encode it into DNA** -- go to **DNA Encoding** and click
**Encode to DNA**. The file's bytes are converted to binary, then to a
DNA sequence, with statistics and a preview shown.

**3. Decode it back** -- go to **DNA Decoding** and click
**Decode DNA to File**. The DNA sequence is converted back to binary and
then to bytes, and compared byte-for-byte against the original so you can
confirm exact recovery and download the result.

You don't need to re-upload your file on later pages -- each page reads
the results already stored from the page before it.

**File identity check:** when you upload a file, BioVault also records a
short content "fingerprint" for it (a checksum of its bytes). This lets
later pages tell your file apart from a *different* file that just
happens to have the same filename, so you never see results left over
from a different upload. This is a simple, self-contained safety check
built directly into the app -- it does not require or use any separate
external storage or user sign-in of any kind.
""",
    },
    {
        "id": "dna_encoding",
        "title": "3. DNA Encoding",
        "content": """
BioVault encodes binary data into DNA using a fixed, documented 2-bit
mapping:

| Bits | Base |
|------|------|
| 00   | A    |
| 01   | C    |
| 10   | G    |
| 11   | T    |

**Why 1 base = 2 bits:** there are exactly 4 possible DNA bases (A, T, G,
C), and exactly 4 possible 2-bit combinations (00, 01, 10, 11) -- so each
base can uniquely represent one 2-bit chunk.

**Padding:** every file byte is 8 bits, which is always evenly divisible
into four 2-bit chunks. Because of this, BioVault's encoder **never needs
to pad** the data -- every byte always becomes exactly 4 DNA bases, with
no bits ever discarded or invented.
""",
    },
    {
        "id": "dna_decoding",
        "title": "4. DNA Decoding",
        "content": """
Decoding reverses the encoding mapping exactly:

| Base | Bits |
|------|------|
| A    | 00   |
| C    | 01   |
| G    | 10   |
| T    | 11   |

Every 4 DNA bases are converted back into one original byte.

**Honest error handling:**
- If the DNA sequence contains any character other than A, T, G, or C,
  decoding stops with a clear error -- it is never silently ignored or
  "fixed".
- If the sequence's length isn't a whole multiple of 4 bases (so the
  resulting binary isn't a whole number of bytes), decoding stops with a
  clear "incompatible length" error rather than guessing at missing or
  extra bits.
- After decoding, BioVault does a byte-for-byte comparison against the
  original file and only reports "exact recovery successful" when every
  byte truly matches.
""",
    },
    {
        "id": "mutation",
        "title": "5. Mutation Simulation",
        "content": """
The **Mutation Simulator** page introduces simulated errors into a DNA
sequence to show what happens to data recovery when storage errors occur.

**Substitution:** each base independently has a chance (based on the
mutation rate) of being replaced with a *different* base -- it is never
replaced with itself. The sequence length never changes.

**Insertion:** at each possible "gap" between bases (and after the last
base), there's a chance of a random extra base being inserted. The
sequence normally grows longer.

**Deletion:** each base independently has a chance of being removed. The
sequence normally gets shorter (and can become empty at a 100% rate, but
never goes negative in length).

**Mutation rate:** a percentage (0-100%) controlling how likely each of
the above events is, per base (or per gap, for insertion).

**Random seed:** an optional fixed number you can set so the same
mutation settings always produce the same result -- useful for
reproducible demonstrations.

**Effect on decoding:** substitutions keep the sequence the same length,
so decoding usually still "succeeds" technically -- but the recovered
file may not exactly match the original. Insertions and deletions change
the sequence length, which often makes the Phase 4 decoder fail outright
(incompatible length), since the DNA no longer divides evenly into whole
bytes.
""",
    },
    {
        "id": "error_correction",
        "title": "6. Error Correction",
        "content": """
The **Error Correction** page uses a simplified, transparent **block
checksum** method -- not any kind of advanced or biologically accurate
DNA-repair technology.

**How protection works:** the DNA sequence is split into fixed-size
blocks. Each block's bases are summed to a numeric checksum value, which
is re-encoded as one DNA base and repeated (based on the redundancy size)
right after its block.

**What can be detected:** any block whose recalculated checksum doesn't
match its stored checksum is flagged as containing an error. A sequence
whose total length doesn't match what's expected (a sign of insertion or
deletion) is flagged as a structural error.

**What can be corrected:** at most **one** substitution error per block,
and only when exactly one possible single-base fix restores a matching
checksum.

**Important limitations:**
- **Insertions and deletions cannot be corrected** -- they break the
  fixed block layout entirely, so only a length mismatch is reported.
- Because the checksum only has 4 possible values, **larger blocks are
  more likely to have checksum collisions** -- cases where more than one
  possible fix matches the stored checksum by coincidence. When that
  happens, BioVault refuses to guess and reports the block as
  uncorrectable rather than risk a wrong "silent" fix.
- Multiple errors within the same block are often uncorrectable for the
  same reason.
""",
    },
    {
        "id": "storage_analysis",
        "title": "7. Storage Analysis",
        "content": """
The **Storage Analysis** page computes simple, transparent statistics
about the encoding and redundancy scheme:

**Bits per nucleotide:** always 2, since each DNA base represents exactly
one 2-bit chunk in this project's encoding scheme.

**Raw theoretical efficiency:** `(original data bits / DNA storage bits) x 100`.
For this scheme, this is always exactly 100%, because no padding is ever
needed -- but this is **not** a claim that DNA is more compact than the
original file (it still takes 4 DNA bases to store 1 byte).

**Redundancy overhead:** how many extra bases the Phase 6 checksum
redundancy adds, as a percentage of the original DNA length. Smaller
blocks generally mean *more* total redundancy bases (more blocks, each
needing its own checksum), even though smaller blocks make single-error
correction more reliable.

**Theoretical capacity vs. practical overhead:** theoretical capacity (2
bits x DNA length) assumes every base is doing useful work. It does not
account for redundancy bases, real DNA synthesis/sequencing costs,
primers, or addressing/indexing metadata -- none of which are modeled by
this project.
""",
    },
    {
        "id": "visualization",
        "title": "8. Visualization",
        "content": """
The **DNA Visualization** page charts data that already exists from the
other pages -- it never invents numbers:

- **Base composition:** a bar chart and table of A/T/G/C counts and
  percentages for the encoded DNA sequence.
- **DNA length comparison:** a bar chart comparing Original, Mutated
  (if available), and Protected (if available) sequence lengths.
- **Mutation analytics:** metrics and a bar chart of substitutions,
  insertions, and deletions, shown only when a Mutation Simulator result
  exists.
- **Error-correction analytics:** metrics and a bar chart of
  corrected vs. uncorrectable errors, shown only when an Error
  Correction result exists.
- **Storage overhead:** metrics and a bar chart of encoded vs.
  redundancy bases, shown only when a Storage Analysis result exists.
""",
    },
    {
        "id": "export_import",
        "title": "9. Export & Import",
        "content": """
The **Export & Import** page lets you save and reload data as plain
files:

**DNA text export:** download the Original, Mutated, Protected, and/or
Corrected DNA sequences as `.txt` files -- each button only appears when
that sequence actually exists.

**Metadata JSON:** a `metadata.json` file with real values only (source
filename, sizes, mutation settings, correction stats, efficiency
figures); unavailable fields are written as JSON `null`, and raw
uploaded file bytes are never included.

**Analysis CSV:** an `analysis.csv` file (`Metric,Value` rows) opening
cleanly in a spreadsheet app; missing values are left blank rather than
shown as a misleading `0`.

**Text report:** click **Generate BioVault Report** to build a readable
`biovault_report.txt` covering file info, encoding, mutation, error
correction, storage efficiency, visualization, and limitations.

**Importing DNA:** upload a `.txt` file containing a DNA sequence.
Import rules:
- Only *surrounding* whitespace is trimmed -- internal spaces, blank
  lines, or any character other than A/T/G/C cause the import to be
  rejected outright (never silently cleaned up).
- Empty files are rejected.
- After a successful import, you can click **Validate Imported DNA**
  (shows length, base counts, and whether the length is compatible with
  decoding) and **Attempt Decode Imported DNA** (uses the same Phase 4
  decoder -- decoding failures are shown honestly, and success is never
  claimed to match any specific original file unless actually compared).
- Importing a sequence **never overwrites** your original encoded DNA
  from the DNA Encoding page.
""",
    },
    {
        "id": "benchmarking",
        "title": "10. Benchmarking",
        "content": """
The **Benchmarking** page compares the DNA sequence at each stage of your
experiment side by side: **Original** (Phase 3), **Mutated** (Phase 5),
**Protected** (Phase 6, before correction), and **Corrected** (Phase 6,
after correction).

It shows a comparison table, a sequence-length chart, and a short written
interpretation (shortest sequence, storage overhead, whether correction
restored the original length, and whether recovery was actually
confirmed successful).

**Why some values show "Not available":** each stage's data only exists
if you've actually run that page. If you haven't run the Mutation
Simulator yet, for example, every "Mutated" cell shows "Not available"
instead of a fabricated `0` -- because a zero-length sequence and "this
was never generated" are not the same thing.
""",
    },
    {
        "id": "performance",
        "title": "11. Performance & Resources",
        "content": """
The **Performance & Resources** page lets you generate small, medium, or
large test data (not a real uploaded file) and run it through encoding,
decoding, mutation, error correction, and storage analysis, timing each
step on your own computer.

**Why larger files take longer:** encoding, decoding, mutation, and error
correction all process the data one base (or byte) at a time, so a file
with more bytes simply means more work to do -- this is expected, not a
bug.

**Why results vary between computers:** the exact same code can run at
different speeds depending on your computer's hardware, your Python
version, what else your computer is doing at the same time, the file
size, and the mutation/error-correction settings used. Every number on
this page is labeled *"Measured on this computer"* -- it is never a
fixed or hardcoded value, and you should expect different numbers on a
different computer, or even a different run on the same computer.

**Why previews are shortened:** DNA sequences, binary strings, and
imported text can be thousands of characters long for medium/large
files. Displaying all of it would slow the browser down for no real
benefit, so long previews are cut short with a note explaining how much
is hidden. This only affects what's shown on screen -- the complete data
is always kept and used for decoding, validation, error correction,
export, import, and file recovery. The file identity (content-hash)
check introduced earlier also keeps working exactly as before; nothing
about performance optimization changes how results are matched to files.
""",
    },
    {
        "id": "encoding_comparison",
        "title": "12. Encoding Model Comparison",
        "content": """
The **Encoding Model Comparison** page lets you compare BioVault's real
encoding against a few clearly labeled **educational, simulated**
alternatives, using the file you've already uploaded and encoded.

**Model A -- Basic Binary-to-DNA (the real, default encoding):** this is
the exact same 00->A, 01->C, 10->G, 11->T mapping used everywhere else in
BioVault. It is fully **reversible** -- decoding it recovers your exact
original file, and this page actually confirms that recovery rather than
assuming it.

**Model B -- GC-Balanced (simulated):** demonstrates one simple strategy
for nudging **GC content** (the percentage of G/C bases, as opposed to
A/T) toward a balanced 50%, by choosing between two different valid
base-mapping tables per block. This is a **simulated, analysis-only**
model: the choice made per block isn't stored anywhere, so this
demonstration sequence is **not reversible** and is never used to recover
a file.

**Model C -- Homopolymer Analysis:** measures "homopolymer runs" -- the
same base repeated several times in a row (e.g. `AAAA`). Long runs like
this can be harder for real DNA sequencing hardware to count accurately.
This model only measures the existing sequence; it doesn't change
anything.

**Model D -- GC-Content Analysis:** reports base-composition statistics
(GC%, AT%, longest repeated-base run, invalid-character count) as a
standalone reference row.

**Reversible vs. analysis-only:** the page always labels each model
clearly. Only Model A is reversible. Models B, C, and D are
analysis-only/simulated and are **never** used by the real upload ->
encode -> decode -> export pipeline -- they exist purely for educational
comparison.
""",
    },
    {
        "id": "dna_integrity",
        "title": "13. DNA Integrity Check",
        "content": """
The **DNA Integrity Check** page checks the current DNA sequence for
validity, structural completeness, and -- when the original file is
available -- confirmed byte-for-byte recovery.

**Validation vs. corruption detection:** *validation* asks "is this
even a well-formed DNA sequence?" (only A/T/G/C characters, a length
that divides evenly into whole bytes). *Corruption detection* goes
further: it asks "does decoding this sequence actually give back the
exact original file?" A sequence can be perfectly valid (well-formed)
and still be corrupted (it decodes to the wrong bytes).

**Warning vs. definite corruption:** unusual GC content or a long run
of the same repeated base (a "homopolymer run") are shown as
**warnings** -- risk indicators drawn from real DNA-storage research --
never as proof that something is actually broken. Only a structural
problem (invalid characters, wrong length) or an actual byte mismatch
against a known original is reported as an **error**.

**Why hashes detect changes but don't repair data:** a SHA-256 hash
changes completely if even one byte changes, so comparing hashes is a
reliable way to detect that something changed. But a hash cannot be
"reversed" to recover what the original data was -- only redundancy
added *before* damage occurs (like the Error Correction page's
checksums) has any chance of restoring lost information.

**Why insertions and deletions are especially difficult:** BioVault's
2-bit encoding relies on reading DNA in fixed groups of 4 bases per
byte. Adding or removing even one base shifts every group that comes
after it, so the whole rest of the sequence reads incorrectly -- this
page reports that as **Incomplete** rather than guessing a fix.

**Recovery confirmation:** the page only ever shows "Successfully
Recovered" after actually comparing the recovered bytes against the
original file and finding them identical. If no original file is
available for comparison, the honest answer is **"Unable to Verify"**
-- never a guess.

**Safe demonstration scenarios:** the page also offers a few controlled
scenarios (a substitution, an insertion, a deletion, an invalid
character, an empty sequence, a truncated sequence) that always run on
a *copy* of the real sequence -- your actual stored DNA sequence is
never changed by these demonstrations.
""",
    },
    {
        "id": "reliability_redundancy",
        "title": "14. Reliability & Redundancy",
        "content": """
The **Reliability & Redundancy** page is an **educational simulation**
demonstrating a general data-storage idea: storing additional redundant
information can increase the ability to detect or recover from data loss
or corruption. It does not measure or predict real laboratory DNA-storage
performance.

**What redundancy means:** keeping more copies (or more information)
than the strict minimum needed, so that if some of it is damaged, the
extra copies can help figure out what the original probably was.

**Why DNA storage may need redundancy:** any real physical storage and
retrieval process can introduce errors. Having more than one copy means
a single damaged copy doesn't necessarily mean the data is lost --
*if* enough of the other copies still agree.

**How repeated information can help:** if 3 independent copies of a
sequence are each corrupted in different, unrelated places, then at
most positions at least 2 of the 3 copies will still agree. Comparing
corresponding bases across copies and picking whichever base most
copies agree on is called **majority voting**.

**Storage overhead:** keeping extra copies costs extra storage. Storing
1 extra copy roughly doubles the total DNA needed; 3 extra copies
roughly quadruples it. This page always shows both the reliability
benefit and the storage cost side by side -- more redundancy is not
automatically "better" once storage cost is taken into account.

**Limitations of majority voting:**
- If copies disagree with no clear majority (e.g. a 1-1 split, or a
  3-way tie), that position is honestly marked **unresolved** rather
  than guessed at.
- A "resolved" majority vote is not automatically *correct* -- if two
  copies happen to be corrupted identically at the same position, their
  matching (wrong) answer can out-vote a single correct copy. This page
  never reports a recovery as confirmed based on the recovery
  percentage alone -- only an actual byte-for-byte comparison against
  the original file can do that.

**Why insertions/deletions are especially difficult:** majority voting
compares bases position-by-position, which only works when every copy
is the same length. An insertion or deletion shifts everything after
it, breaking that alignment -- this page detects that situation and
reports recovery as unavailable/failed rather than comparing the wrong
positions and producing a misleading result.

**Redundancy vs. error correction:** this page's majority-vote and
agreement-based strategies store multiple **whole copies**. The
existing **Error Correction** page instead adds a small **checksum**
next to blocks of a single sequence. Both are forms of redundancy in
the general sense, but they are different techniques with different
costs and failure modes -- this page also lets you try the existing
Phase 6 method for direct comparison.

**Why this is a simulation:** every scenario here uses BioVault's own
simulated DNA sequences and Python's own random-number generator to
introduce controlled corruption -- it does not model real DNA
synthesis, storage, or sequencing physics, and its results should never
be interpreted as laboratory performance data.
""",
    },
    {
        "id": "capacity_storage",
        "title": "15. DNA Capacity & Storage",
        "content": """
The **DNA Capacity & Storage** page is an educational exploration of DNA
information density, theoretical storage capacity, and how BioVault's
actual encoding compares -- written to be understandable whether you're
new to information theory or already studying biotechnology.

**The 2-bit theoretical DNA capacity:** DNA has exactly 4 possible bases
(A, C, G, T). A symbol chosen from 4 equally likely possibilities carries
log2(4) = **2 bits** of information -- the same 2-bit-per-base constant
BioVault's real encoder already uses. This is a **theoretical** ceiling,
not a claim that every real DNA-storage system achieves 2 *useful*
bits/base once real-world constraints are considered.

**DNA length calculations:** the theoretical relationship is
`DNA bases = bytes x 8 bits/byte / 2 bits/base = bytes x 4`. The page's
File Size Calculator applies this to any size you enter, using binary
units (1 KB = 1024 bytes) labeled explicitly.

**Actual versus theoretical encoding:** when a file has been uploaded
and encoded, the page compares BioVault's REAL, **measured** encoded DNA
length (from the actual encoder -- the source of truth for real
encoding) against the pure theoretical figure for the same file size,
showing any difference as "encoding overhead." For this project's fixed
2-bit scheme, the two always match exactly (no padding is ever added).

**Storage overhead & redundancy overhead:** the page reuses the exact
same formulas already used elsewhere in BioVault -- Phase 18's
whole-copy redundancy math (Reliability & Redundancy page) and Phase 6's
checksum-based error-correction math (Error Correction page) -- rather
than introducing a second, possibly-disagreeing definition of either.

**Conventional storage comparison:** illustrative example sizes (1 TB,
10 TB, 100 TB, 1 PB) are compared against the theoretical DNA bases
needed for the same digital size. These are **illustrative educational
examples**, not live commercial capacities, and no technology is ranked.

**Cost assumptions:** the optional cost estimator only ever uses
numbers YOU enter (or clearly documented example defaults) -- it never
hardcodes a current market price, and every result is labeled
**"Illustrative estimate -- not a current market quote."**

**Physical-density assumptions:** the optional mass estimate uses an
adjustable, clearly labeled ASSUMPTION for the average molecular weight
per DNA base -- it does not represent a measured value, and does not
account for synthesis, purification, sequencing, packaging, or other
real laboratory losses.

**Theoretical vs. practical capacity:** real DNA storage systems must
also handle synthesis/sequencing errors, GC-content and homopolymer
constraints (see the Encoding Model Comparison and DNA Integrity Check
pages), indexing/addressing, error-correction codes, additional
redundancy, and physical handling -- every one of these reduces how much
of the theoretical 2-bits/base ends up usable in practice. **Theoretical
density is not the same as practical, usable density**, and this page
never claims otherwise.

**Limitations:** all figures here are simulation/theory/illustrative-
estimate results computed by this software -- none of them represent an
independently measured or laboratory-validated real-world outcome.
""",
    },
    {
        "id": "dna_storage_experiment",
        "title": "16. DNA Storage Experiment",
        "content": """
The **DNA Storage Experiment** page combines every stage BioVault already
implements into one reproducible, end-to-end run: encoding, DNA analysis,
storage/capacity analysis, redundancy, corruption, recovery, integrity
verification, and performance measurement -- producing one structured
result and a downloadable research-style report.

**It reuses, not reimplements:** every stage calls the exact same
existing function used on that stage's own dedicated page (the real
encoder/decoder, Phase 16's GC/homopolymer analysis, Phase 7's storage
math, Phase 19's capacity math, Phase 18's redundancy/corruption/recovery,
Phase 17's integrity classification, and Phase 15's timing/memory
measurement). There is no second encoding algorithm and no duplicated
formula anywhere in this page.

**Reproducibility:** giving the same file, redundancy level, corruption
settings, and random seed always produces the same DNA sequence, the
same corruption, and the same recovery outcome -- this is what makes the
experiment a genuine, repeatable demonstration rather than a one-off.

**Honest overall status:** the page reports one of four outcomes --
**Successfully Recovered** (only when the recovered bytes are actually
identical to the original, confirmed by byte comparison and SHA-256
hash), **Recovery Failed** (recovery was attempted but the bytes differ),
**Unable to Verify** (no comparison could be made), or **Simulation
Completed - Recovery Not Available** (an insertion/deletion broke the
alignment majority/agreement voting needs). The recovery *percentage*
shown during the run measures how many DNA positions were confidently
resolved by voting -- it is never treated as proof of correctness by
itself.

**Experiment report:** a full plain-text report can be downloaded,
containing every real value the experiment actually produced (never a
hardcoded example), clearly labeled as an educational simulation.

**What this page is not:** it does not perform real DNA synthesis or
sequencing, and running it is not a substitute for laboratory
experimental validation.
""",
    },
    {
        "id": "project_showcase",
        "title": "17. Project Showcase",
        "content": """
The **Project Showcase** page is the main presentation/demonstration page,
designed for college project reviews, biotechnology engineering seminars,
viva voce, classroom demos, and exhibitions.

It walks through the project's purpose, objectives, how BioVault works
(digital file -> binary -> DNA encoding -> analysis -> mutation ->
redundancy/recovery -> decoding -> recovered file -> SHA-256
verification), a worked encoding example matching the real encoder, a
Live Demo checklist for running an actual demonstration on the other
pages, the biotechnology concepts demonstrated, an explicit "what
BioVault does NOT do" academic-honesty section, the software
architecture, a project development timeline, project statistics, a
suggested 12-slide presentation outline (with speaker notes), a future-
scope list, and a concise conclusion.

**Live Demonstration:** the Showcase page does not automatically run
anything -- it guides you through using the real pages (File Upload, DNA
Encoding, Mutation Simulator, Reliability & Redundancy, DNA Integrity
Check, DNA Storage Experiment) yourself, step by step, so what you see
during a demo is always the actual application running, not a canned
example.

**Presentation Outline:** a ready-to-use 12-slide structure (Title,
Introduction, Problem Statement, DNA as an Information Medium,
Objectives, Architecture, Encoding/Decoding, Mutation/Error Correction,
Redundancy/Integrity, Capacity/Performance, Live Demonstration,
Conclusion) with bullet points and short speaker-note suggestions for
each slide.
""",
    },
    {
        "id": "viva_preparation",
        "title": "18. Viva Preparation",
        "content": """
The **Viva Preparation** page provides a local, offline question-and-
answer bank (30+ questions) for oral exam / project review preparation,
organized into six categories: Basic Biotechnology, Computer/Encoding,
Error Handling, Integrity, Storage/Capacity, and Project.

You can browse by category, select a specific question, reveal its
answer with a **Show Answer** button, or jump to a random question.
A simple progress indicator tracks how many questions you've reviewed
this session. No internet connection is required -- the entire question
bank is stored locally in the application.

Answers are written concisely and are factually conservative,
consistent with the rest of BioVault: they never claim real DNA
synthesis, sequencing, physical storage, or laboratory validation.
""",
    },
    {
        "id": "environment_setup_check",
        "title": "19. Environment & Setup Check",
        "content": """
The **Environment & Setup Check** page answers one simple question:
"Is BioVault ready to run on this computer?"

It performs a few fast, local checks -- no internet connection is used
and nothing on your computer is modified:

- **Python version:** confirms you're running a supported Python version.
- **Dependencies:** confirms `streamlit` and `pandas` (needed to run the
  app) are installed, and separately notes whether `pytest` (needed
  only to run the test suite) is available.
- **Project structure:** confirms the expected `app/`, `app/modules/`,
  and `tests/` folders exist.
- **Core module imports:** confirms a representative sample of
  BioVault's own modules (the real encoder/decoder, mutation, error
  correction, integrity, redundancy, capacity, and experiment-pipeline
  logic) import without error.

If everything passes, the page shows a simple "✅ ready to run" message.
If something is missing, it shows exactly what failed along with plain-
language troubleshooting steps (e.g. "run `pip install -r
requirements.txt`"). This page is meant for beginners setting up
BioVault for the first time, or troubleshooting a setup on a new
computer -- it deliberately never runs the test suite itself, since
that would be slow and is a separate, more thorough check
(`python -m pytest -q`) meant to be run from a terminal.
""",
    },
    {
        "id": "workflow",
        "title": "20. Recommended Workflow",
        "content": """
```
Upload file
  -> Encode DNA
  -> Simulate mutations
  -> Apply error correction
  -> Analyze storage
  -> View visualization
  -> Run benchmarking
  -> Export results
  -> Import and decode when required
```

Every stage after "Upload file" and "Encode DNA" is optional and builds
on the DNA sequence generated by DNA Encoding -- you can stop at any
point, and pages that need data you haven't generated yet will tell you
clearly what to run first.
""",
    },
    {
        "id": "limitations",
        "title": "21. Limitations and Important Notes",
        "content": """
- BioVault is an **educational software simulation only**.
- It does **not** perform real DNA synthesis, sequencing, or any
  laboratory procedure.
- Every result depends on the simplified algorithms actually implemented
  in this project (a fixed 2-bit encoding, a basic block-checksum
  correction scheme, computational storage-efficiency estimates) -- not
  on real biochemical measurements.
- When data is missing (no file uploaded, no mutation run, etc.), pages
  say so explicitly rather than guessing or filling in fake numbers.
- Simulation results should **not** be interpreted as laboratory
  guarantees or used to make real-world DNA storage decisions.
""",
    },
]


QUICK_START = """
1. **File Upload** -- upload a small `.txt`, `.png`, or `.jpg` file.
2. **DNA Encoding** -- click **Encode to DNA**.
3. **DNA Decoding** -- click **Decode DNA to File** to confirm exact recovery.
4. Explore **Mutation Simulator**, **Error Correction**, **Storage Analysis**,
   **DNA Visualization**, **Benchmarking**, and **Export & Import** in any order --
   each page tells you clearly if it needs a page you haven't run yet.
"""


COMMON_PROBLEMS = [
    {
        "problem": "No file uploaded",
        "explanation": (
            "Most pages need a file from **File Upload** and an encoded DNA "
            "sequence from **DNA Encoding** first. If you see a message like "
            "\"Please upload a file...\", start there."
        ),
    },
    {
        "problem": "Invalid DNA characters",
        "explanation": (
            "BioVault only accepts A, T, G, C (any case). If you paste or "
            "import text containing any other character, it will be rejected "
            "with a clear error rather than silently cleaned up."
        ),
    },
    {
        "problem": "Empty DNA import",
        "explanation": (
            "An uploaded `.txt` file for import must contain at least one "
            "valid DNA character after surrounding whitespace is trimmed. An "
            "empty or whitespace-only file is rejected."
        ),
    },
    {
        "problem": "DNA length not compatible with decoding",
        "explanation": (
            "Decoding needs the DNA sequence length to be a multiple of 4 "
            "bases (so the binary divides evenly into whole bytes). "
            "Insertions/deletions from mutation can break this -- the "
            "decoder will report the mismatch honestly instead of guessing."
        ),
    },
    {
        "problem": "No mutation result available",
        "explanation": (
            "Pages that show mutation data (Storage Analysis, Visualization, "
            "Error Correction, Benchmarking) only display it after you've run "
            "the **Mutation Simulator** page for the current file/DNA sequence."
        ),
    },
    {
        "problem": "No protected sequence available",
        "explanation": (
            "The \"Protected DNA\" export and benchmark rows only appear "
            "after you've run **Error Correction**, which is what actually "
            "generates the redundancy-protected sequence."
        ),
    },
    {
        "problem": 'Benchmark values showing "Not available"',
        "explanation": (
            "This means that particular stage (Mutated, Protected, or "
            "Corrected) hasn't been generated yet for the current file -- "
            "it is shown honestly instead of a misleading `0`."
        ),
    },
    {
        "problem": "Export buttons not appearing",
        "explanation": (
            "Each export button (Mutated DNA, Protected DNA, Corrected DNA) "
            "only appears once its source data actually exists in session "
            "state for the current file. Run the corresponding page first."
        ),
    },
]


GLOSSARY = {
    "Nucleotide": "One unit of DNA -- in this project, one of A, T, G, or C.",
    "DNA sequence": "An ordered string of nucleotides (e.g. \"ACGT\").",
    "Encoding": "Converting binary data into a DNA sequence (Phase 3: 2 bits -> 1 base).",
    "Decoding": "Converting a DNA sequence back into binary/bytes (Phase 4).",
    "Mutation": "A simulated error introduced into a DNA sequence (substitution, insertion, or deletion).",
    "Substitution": "A mutation where one base is replaced with a different base; sequence length is unchanged.",
    "Insertion": "A mutation where an extra base is added; sequence length increases.",
    "Deletion": "A mutation where a base is removed; sequence length decreases.",
    "Checksum": "A small value calculated from a block of DNA, used to detect (and sometimes correct) errors.",
    "Redundancy": "Extra checksum bases added to a DNA sequence so errors can be detected/corrected.",
    "Storage overhead": "The extra DNA bases added by redundancy, shown as a percentage of the original length.",
    "Error correction": "Attempting to fix detected errors using the stored checksum information.",
}


def get_sections() -> list:
    """Return the list of documentation section dicts (id, title, content)."""
    return SECTIONS


def get_section_by_id(section_id: str):
    """Return a single section dict by its id, or None if not found."""
    for section in SECTIONS:
        if section["id"] == section_id:
            return section
    return None


def get_quick_start() -> str:
    """Return the Quick Start guide text."""
    return QUICK_START


def get_common_problems() -> list:
    """Return the list of common-problem dicts (problem, explanation)."""
    return COMMON_PROBLEMS


def get_glossary() -> dict:
    """Return the glossary as a dict of term -> definition."""
    return GLOSSARY
