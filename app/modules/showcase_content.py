"""
Project Showcase / Presentation Mode content (non-UI, no Streamlit
dependency).

This module holds the static educational text, workflow description,
slide outline, and project-statistics logic for the Project Showcase
page. It never fabricates a result: every "statistic" is either a
genuinely computed value (e.g. counting real module files) or a
clearly documented constant (e.g. the current verified test count,
which is updated only when tests actually change -- see
CURRENT_VERIFIED_TEST_COUNT below).

ACADEMIC HONESTY: every section here is written to make clear that
BioVault is a COMPUTATIONAL EDUCATIONAL SIMULATION. It never claims
real DNA synthesis, sequencing, physical storage, or laboratory
validation.
"""

from pathlib import Path

from app.modules.dna_encoder import BITS_TO_BASE, BITS_PER_BASE

APP_TITLE = "BioVault"
APP_SUBTITLE = "DNA Digital Data Storage & Error Simulation Platform"

INTRO_TEXT = (
    "BioVault is an educational software platform that demonstrates how "
    "digital data can be encoded into DNA sequences, analyzed, corrupted "
    "through simulation, recovered using redundancy/error-correction "
    "techniques, and verified using digital integrity checks."
)

SOFTWARE_SIMULATION_NOTICE = "Software Simulation -- Not Laboratory DNA Storage"

PROBLEM_STATEMENT = """
Traditional digital storage depends on physical storage systems such as
hard drives, SSDs, data centers, magnetic storage, and optical storage.

DNA is being studied as a possible high-density information-storage
medium because biological molecules can represent information using
molecular sequences.

BioVault demonstrates the underlying **computational concept** -- how
data could be mapped to and from DNA-like sequences, and what happens
when that data is corrupted and recovered -- without physically
synthesizing or sequencing any real DNA.
"""

OBJECTIVES = [
    "Convert digital data into DNA bases.",
    "Decode DNA back into the original digital data.",
    "Simulate DNA mutations.",
    "Demonstrate redundancy and recovery.",
    "Analyze DNA characteristics.",
    "Calculate theoretical storage capacity.",
    "Measure computational performance.",
    "Verify recovered data using SHA-256.",
    "Demonstrate an end-to-end DNA storage workflow.",
    "Generate reproducible experiment reports.",
]

WORKFLOW_STAGES = [
    "Digital File",
    "Binary Data",
    "DNA Encoding",
    "A C G T Sequence",
    "DNA Analysis",
    "Simulated Mutation",
    "Redundancy / Recovery",
    "DNA Decoding",
    "Recovered File",
    "SHA-256 Verification",
]

ENCODING_EXAMPLE_BINARY = "00 01 10 11"
ENCODING_EXAMPLE_DNA = " ".join(BITS_TO_BASE[chunk] for chunk in ENCODING_EXAMPLE_BINARY.split())

WHY_FOUR_BASES_TEXT = (
    "DNA contains four primary bases: Adenine (A), Cytosine (C), Guanine "
    "(G), and Thymine (T). Because there are exactly four possible symbols, "
    "two binary bits can represent one base in BioVault's simplified "
    "computational encoding model: 2 bits -> 1 DNA base."
)

LIVE_DEMO_CHECKLIST = [
    "Upload a small file",
    "Encode the file",
    "View the DNA sequence",
    "Check GC content",
    "Run mutation simulation",
    "Apply redundancy",
    "Recover the data",
    "Verify SHA-256",
    "Compare original and recovered data",
    "Generate experiment report",
]

# A suggested, illustrative starting point for a live demonstration --
# explicitly NOT presented as an experimentally proven optimal setting.
DEMO_RECOMMENDATION = {
    "Demo file": "Small .txt file",
    "Corruption type": "Substitution",
    "Corruption rate": "5-10%",
    "Redundancy": "2 extra copies",
    "Recovery strategy": "Majority Vote",
    "Random seed": 42,
}
DEMO_RECOMMENDATION_LABEL = "Suggested demonstration configuration (illustrative, not proven optimal)"

DEMO_RESULT_EXPLANATION = {
    "Before corruption": [
        "A DNA sequence exists",
        "DNA length is calculated",
        "GC% is shown",
        "A file hash (SHA-256) exists",
    ],
    "After corruption": [
        "The DNA sequence may change",
        "Sequence length may change for insertion/deletion",
        "Integrity checks may report a failure",
    ],
    "After recovery": [
        "The important result is EXACT BYTE RECOVERY, not merely a recovery percentage",
    ],
}

RECOVERY_PERCENTAGE_TEACHING_POINT = (
    "A recovery percentage alone does not prove that the original file was "
    "recovered. BioVault therefore compares the original and recovered "
    "bytes directly and uses SHA-256 verification before ever reporting "
    "'Successfully Recovered.'"
)

SCIENTIFIC_CONCEPTS = [
    ("DNA as an information medium", "DNA contains sequence information represented by four bases."),
    ("Information encoding", "Digital binary information is mapped to DNA bases."),
    ("Mutation", "Substitution, insertion, and deletion are simulated computationally."),
    ("Redundancy", "Additional copies are used to demonstrate the concept of information recovery."),
    ("Error correction", "Algorithms can detect or correct certain simulated errors."),
    ("Integrity verification", "SHA-256 is used to verify whether recovered digital data exactly matches the original."),
    ("Information density", "The project demonstrates the theoretical relationship between bits and DNA bases."),
]

# What BioVault explicitly does NOT do -- academic-honesty statement.
LIMITATIONS_DOES_NOT = [
    "Synthesize DNA",
    "Chemically store DNA",
    "Perform DNA sequencing",
    "Use laboratory instruments",
    "Perform biological experiments",
    "Validate DNA synthesis accuracy",
    "Validate sequencing accuracy",
    "Model complete biological storage systems",
    "Predict real-world commercial cost",
    "Prove that DNA storage is superior to existing storage technologies",
]
LIMITATIONS_STATEMENT = "BioVault is a computational educational simulation."

ARCHITECTURE_DIAGRAM = """
Streamlit UI
     |
UI Modules
     |
Pure Python Modules
     |
Encoding / Decoding
Mutation / Recovery
Analysis / Capacity
Integrity / Performance
Experiment Pipeline
     |
Test Suite
"""

ARCHITECTURE_KEY_MODULES = [
    "dna_encoder.py",
    "dna_decoder.py",
    "dna_mutator.py",
    "dna_error_correction.py",
    "dna_integrity.py",
    "redundancy_simulation.py",
    "capacity_analysis.py",
    "performance_analysis.py",
    "experiment_pipeline.py",
]

# Historical phase timeline -- a static, documented record of this
# project's actual development stages (matches the phase-by-phase work
# actually completed).
PROJECT_TIMELINE = [
    (1, "Foundation"),
    (2, "File Upload"),
    (3, "DNA Encoding"),
    (4, "DNA Decoding"),
    (5, "Mutation Simulation"),
    (6, "Error Correction"),
    (7, "Storage Analysis"),
    (8, "Visualization"),
    (9, "Export / Import"),
    (10, "Benchmarking"),
    (11, "Documentation"),
    (12, "Final Dashboard"),
    (13, "Testing / QA"),
    (14, "File Identity"),
    (15, "Performance & Resources"),
    (16, "Encoding Model Comparison"),
    (17, "DNA Integrity"),
    (18, "Reliability & Redundancy"),
    (19, "DNA Capacity & Storage"),
    (20, "End-to-End Experiment"),
    (21, "Project Showcase & Viva Preparation"),
    (22, "Release Readiness & Setup Verification"),
]

# This is a manually documented, verified value -- NOT dynamically
# computed at runtime (running pytest from inside the Streamlit app
# would be slow and fragile). It must only be updated when tests are
# actually added or removed, and must never overstate the real,
# last-verified `pytest -q` result.
CURRENT_VERIFIED_TEST_COUNT = 621

SLIDE_OUTLINE = [
    {
        "title": "1. Title",
        "bullets": [
            "BioVault -- DNA Digital Data Storage & Error Simulation Platform",
            "Educational computational simulation",
            "Presented by: (your name / team)",
        ],
        "speaker_note": "Introduce yourself and the project name; state upfront that this is a software simulation.",
    },
    {
        "title": "2. Introduction",
        "bullets": [
            "What BioVault is: a Streamlit app simulating DNA data storage",
            "Who it's for: students and educators exploring DNA storage concepts",
            "Why it matters: bridges biotechnology and computer science ideas",
        ],
        "speaker_note": "Keep this brief -- one or two sentences setting context before the problem statement.",
    },
    {
        "title": "3. Problem Statement",
        "bullets": [
            "Conventional storage relies on physical media (HDD, SSD, etc.)",
            "DNA is being researched as a high-density storage medium",
            "BioVault demonstrates the concept computationally, without a lab",
        ],
        "speaker_note": "Emphasize 'studied as a possible medium', not an established replacement.",
    },
    {
        "title": "4. DNA as an Information Medium",
        "bullets": [
            "DNA has four bases: A, C, G, T",
            "Four symbols = 2 bits of information each (log2(4) = 2)",
            "This is the mathematical basis for BioVault's encoding",
        ],
        "speaker_note": "A good place to show the theoretical density explanation from the Capacity page.",
    },
    {
        "title": "5. BioVault Objectives",
        "bullets": OBJECTIVES[:5] + ["...and more (see full objectives list)"],
        "speaker_note": "List the top objectives; mention the rest are in the app's Project Showcase page.",
    },
    {
        "title": "6. System Architecture",
        "bullets": [
            "Modular Python: UI modules + pure logic modules",
            "No single giant file -- each concept has its own module",
            "Business logic is fully unit-tested independent of the UI",
        ],
        "speaker_note": "Show the architecture diagram; mention the test suite as evidence of correctness.",
    },
    {
        "title": "7. DNA Encoding and Decoding",
        "bullets": [
            "Fixed mapping: 00->A, 01->C, 10->G, 11->T",
            "Every byte becomes exactly 4 bases, no padding",
            "Decoding is the exact reverse -- fully reversible",
        ],
        "speaker_note": "Demo: encode a small file live and show the resulting DNA sequence.",
    },
    {
        "title": "8. Mutation and Error Correction",
        "bullets": [
            "Substitution, insertion, deletion simulated computationally",
            "Phase 6 checksum-based error correction (limited, single error per block)",
            "Insertions/deletions are especially hard to correct (alignment shifts)",
        ],
        "speaker_note": "Demo: introduce a substitution and show detection; explain why insert/delete is harder.",
    },
    {
        "title": "9. Redundancy and Integrity Verification",
        "bullets": [
            "Multiple whole copies + majority/agreement voting",
            "SHA-256 hashing to detect any change",
            "'Successfully Recovered' only after an actual byte comparison",
        ],
        "speaker_note": "This is the key academic-honesty teaching point -- percentage is not proof.",
    },
    {
        "title": "10. Capacity and Performance Analysis",
        "bullets": [
            "Theoretical vs. actual DNA length comparison",
            "Storage/redundancy overhead calculations",
            "Real execution time and memory measured on this computer",
        ],
        "speaker_note": "Clarify: theoretical density is not the same as practical, usable density.",
    },
    {
        "title": "11. Live Demonstration",
        "bullets": [
            "Upload -> Encode -> Corrupt -> Recover -> Verify",
            "Use the DNA Storage Experiment page for one end-to-end run",
            "Show the downloadable experiment report",
        ],
        "speaker_note": "Follow the Live Demo checklist; keep the file small so it runs quickly.",
    },
    {
        "title": "12. Conclusion and Future Scope",
        "bullets": [
            "Recap: a computational bridge between biotech and CS concepts",
            "Clearly a simulation -- not laboratory-validated",
            "Future work: better codes, realistic error models, lab validation",
        ],
        "speaker_note": "End by restating the academic-honesty distinction between simulation and real DNA storage.",
    },
]

FUTURE_SCOPE = [
    "More advanced DNA error-correction codes",
    "Fountain-code-based DNA storage simulation",
    "GC-content optimization",
    "Homopolymer avoidance algorithms",
    "More realistic synthesis/sequencing error models",
    "Larger benchmark datasets",
    "Laboratory validation in future research",
    "Integration with experimental sequencing workflows",
    "Improved physical-cost models",
    "Cloud-based experiment sharing",
]

PROJECT_CONCLUSION = (
    "BioVault demonstrates a computational workflow for representing "
    "digital data as DNA sequences and studying encoding, mutation, "
    "redundancy, recovery, storage characteristics, and digital integrity "
    "verification. It provides an educational bridge between "
    "biotechnology concepts and computer-based information processing. "
    "BioVault does not claim commercial readiness or laboratory validation."
)


def _count_module_files() -> dict:
    """Dynamically count real module/page files in app/modules/ -- a
    genuinely computed statistic, not a hardcoded guess."""
    modules_dir = Path(__file__).resolve().parent
    all_py_files = [f for f in modules_dir.glob("*.py") if f.name != "__init__.py"]
    ui_files = [f for f in all_py_files if f.name.startswith("ui_")]
    logic_files = [f for f in all_py_files if not f.name.startswith("ui_")]
    return {
        "total_module_files": len(all_py_files),
        "ui_page_count": len(ui_files),
        "logic_module_count": len(logic_files),
    }


def get_project_statistics() -> dict:
    """Return a dict of project statistics for the Showcase page.

    Module/page counts are computed by actually counting real files on
    disk. Phase count and test count are documented constants (see
    CURRENT_VERIFIED_TEST_COUNT's docstring for why) -- both are kept
    conservative and are never claimed to exceed what has actually been
    verified.
    """
    file_counts = _count_module_files()
    return {
        "phases_completed": len(PROJECT_TIMELINE),
        "verified_test_count": CURRENT_VERIFIED_TEST_COUNT,
        "total_module_files": file_counts["total_module_files"],
        "ui_page_count": file_counts["ui_page_count"],
        "logic_module_count": file_counts["logic_module_count"],
        "dna_base_count": len(BITS_TO_BASE),
        "bits_per_base": BITS_PER_BASE,
    }
