"""
Viva/oral-exam question bank (non-UI, no Streamlit dependency).

This module holds a static, local question-and-answer bank for viva
voce / project-review preparation. It requires no internet access and
never depends on any live experiment result -- every answer here is a
fixed, general explanation of a concept BioVault demonstrates, written
concisely for a second-year Biotechnology Engineering student.

Answers are kept factually conservative and consistent with the rest
of the project: BioVault is described as a computational educational
simulation, never as a system that performs real DNA synthesis,
sequencing, or laboratory validation.
"""

CATEGORY_BASIC_BIOTECH = "Basic Biotechnology"
CATEGORY_ENCODING = "Computer / Encoding"
CATEGORY_ERROR_HANDLING = "Error Handling"
CATEGORY_INTEGRITY = "Integrity"
CATEGORY_STORAGE_CAPACITY = "Storage / Capacity"
CATEGORY_PROJECT = "Project"

CATEGORIES = (
    CATEGORY_BASIC_BIOTECH,
    CATEGORY_ENCODING,
    CATEGORY_ERROR_HANDLING,
    CATEGORY_INTEGRITY,
    CATEGORY_STORAGE_CAPACITY,
    CATEGORY_PROJECT,
)

# Each entry: (id, category, question, answer). IDs are stable strings
# so a specific question can always be referenced/tested reliably.
QUESTIONS = [
    # --- Basic Biotechnology --------------------------------------------------
    {
        "id": "bio-1",
        "category": CATEGORY_BASIC_BIOTECH,
        "question": "What is DNA?",
        "answer": (
            "DNA (deoxyribonucleic acid) is the molecule that carries genetic "
            "information in living organisms, made up of a sequence of four "
            "chemical bases."
        ),
    },
    {
        "id": "bio-2",
        "category": CATEGORY_BASIC_BIOTECH,
        "question": "What are the four DNA bases?",
        "answer": "Adenine (A), Cytosine (C), Guanine (G), and Thymine (T).",
    },
    {
        "id": "bio-3",
        "category": CATEGORY_BASIC_BIOTECH,
        "question": "What is DNA data storage?",
        "answer": (
            "A research area exploring whether digital information can be "
            "encoded into sequences of DNA bases and later read back, because "
            "DNA can be extremely dense and long-lasting compared to some "
            "conventional media."
        ),
    },
    {
        "id": "bio-4",
        "category": CATEGORY_BASIC_BIOTECH,
        "question": "Why are four bases useful for information representation?",
        "answer": (
            "Four symbols can represent exactly 2 bits of information each "
            "(log2(4) = 2), similar to how two binary digits (00, 01, 10, 11) "
            "represent four possibilities -- this is the basis of BioVault's "
            "simplified 2-bits-per-base encoding model."
        ),
    },
    {
        "id": "bio-5",
        "category": CATEGORY_BASIC_BIOTECH,
        "question": "What is a mutation?",
        "answer": (
            "A change in a DNA sequence. BioVault simulates three simplified "
            "types computationally: substitution (a base changes), insertion "
            "(an extra base appears), and deletion (a base is removed)."
        ),
    },
    # --- Computer / Encoding ---------------------------------------------------
    {
        "id": "enc-1",
        "category": CATEGORY_ENCODING,
        "question": "What is binary data?",
        "answer": "Digital information represented using only two symbols, 0 and 1 (bits).",
    },
    {
        "id": "enc-2",
        "category": CATEGORY_ENCODING,
        "question": "Why does BioVault use 2 bits per DNA base?",
        "answer": (
            "Because there are exactly 4 possible DNA bases, and 2 binary bits "
            "can represent exactly 4 possibilities (00, 01, 10, 11) -- so each "
            "base can uniquely stand for one 2-bit chunk."
        ),
    },
    {
        "id": "enc-3",
        "category": CATEGORY_ENCODING,
        "question": "What is the mapping used by BioVault?",
        "answer": "00 -> A, 01 -> C, 10 -> G, 11 -> T (the fixed table in dna_encoder.py).",
    },
    {
        "id": "enc-4",
        "category": CATEGORY_ENCODING,
        "question": "How is DNA decoded back to bytes?",
        "answer": (
            "Each base is mapped back to its 2-bit chunk using the reverse of "
            "the encoding table, and every 4 bases (8 bits) are reassembled "
            "into one original byte."
        ),
    },
    {
        "id": "enc-5",
        "category": CATEGORY_ENCODING,
        "question": "Why must encoding and decoding be reversible?",
        "answer": (
            "Because the whole point of storing data is to be able to recover "
            "the exact original file later -- a mapping that loses information "
            "(is not one-to-one and reversible) cannot guarantee exact recovery."
        ),
    },
    # --- Error Handling ----------------------------------------------------------
    {
        "id": "err-1",
        "category": CATEGORY_ERROR_HANDLING,
        "question": "What is substitution?",
        "answer": "A simulated error where one DNA base is replaced by a different base, without changing the sequence length.",
    },
    {
        "id": "err-2",
        "category": CATEGORY_ERROR_HANDLING,
        "question": "What is insertion?",
        "answer": "A simulated error where an extra DNA base is added into the sequence, increasing its length.",
    },
    {
        "id": "err-3",
        "category": CATEGORY_ERROR_HANDLING,
        "question": "What is deletion?",
        "answer": "A simulated error where a DNA base is removed from the sequence, decreasing its length.",
    },
    {
        "id": "err-4",
        "category": CATEGORY_ERROR_HANDLING,
        "question": "What is redundancy?",
        "answer": (
            "Storing more information than the strict minimum needed -- for "
            "example, multiple whole copies of a DNA sequence -- so that if "
            "part of it is damaged, the extra copies can help recover it."
        ),
    },
    {
        "id": "err-5",
        "category": CATEGORY_ERROR_HANDLING,
        "question": "What is error correction?",
        "answer": (
            "A technique that adds a small amount of extra information (like a "
            "checksum) so that certain errors can be detected, and in limited "
            "cases, corrected -- BioVault implements a simplified single-"
            "substitution-per-block checksum scheme."
        ),
    },
    {
        "id": "err-6",
        "category": CATEGORY_ERROR_HANDLING,
        "question": "Why can insertion/deletion be difficult for position-based recovery?",
        "answer": (
            "Comparing multiple copies base-by-base (majority voting) only "
            "works when every copy has the same length. An insertion or "
            "deletion shifts every base after it, so a straightforward "
            "position comparison would compare unrelated positions -- BioVault "
            "detects this and reports recovery as unavailable rather than "
            "guessing."
        ),
    },
    # --- Integrity -----------------------------------------------------------------
    {
        "id": "int-1",
        "category": CATEGORY_INTEGRITY,
        "question": "What is SHA-256?",
        "answer": (
            "A cryptographic hash function that turns any input data into a "
            "fixed-length 256-bit fingerprint; even a single changed byte "
            "produces a completely different hash."
        ),
    },
    {
        "id": "int-2",
        "category": CATEGORY_INTEGRITY,
        "question": "Why is hashing used?",
        "answer": (
            "To quickly and reliably check whether two pieces of data are "
            "identical, without needing to compare every byte by hand -- if "
            "two hashes match, the data is (for all practical purposes) the same."
        ),
    },
    {
        "id": "int-3",
        "category": CATEGORY_INTEGRITY,
        "question": "Why is byte comparison important?",
        "answer": (
            "It is the actual proof of correctness: two files can look similar "
            "(e.g. a high recovery percentage) while still not being byte-for-"
            "byte identical -- only comparing every byte confirms exact recovery."
        ),
    },
    {
        "id": "int-4",
        "category": CATEGORY_INTEGRITY,
        "question": "What does 'Successfully Recovered' mean in BioVault?",
        "answer": (
            "It means the recovered bytes were actually compared to the "
            "original file's bytes and found to be exactly identical -- "
            "BioVault never shows this status based on a percentage or a "
            "hash comparison alone without an actual byte comparison."
        ),
    },
    # --- Storage / Capacity --------------------------------------------------------
    {
        "id": "cap-1",
        "category": CATEGORY_STORAGE_CAPACITY,
        "question": "What is information density?",
        "answer": "A measure of how much information can be stored per unit of storage medium -- in BioVault's model, expressed as bits per DNA base.",
    },
    {
        "id": "cap-2",
        "category": CATEGORY_STORAGE_CAPACITY,
        "question": "What does 2 bits/base mean?",
        "answer": "Each DNA base in BioVault's simplified model can represent one of 4 possibilities, which is exactly 2 bits of information (log2(4) = 2).",
    },
    {
        "id": "cap-3",
        "category": CATEGORY_STORAGE_CAPACITY,
        "question": "What is storage overhead?",
        "answer": "The extra storage used beyond the strict minimum, e.g. from redundancy (extra copies) or error-correction checksums, usually expressed as a percentage.",
    },
    {
        "id": "cap-4",
        "category": CATEGORY_STORAGE_CAPACITY,
        "question": "Why is theoretical DNA capacity different from practical DNA storage?",
        "answer": (
            "The theoretical 2-bits/base figure ignores real-world constraints "
            "such as synthesis/sequencing errors, GC-content limits, "
            "homopolymer runs, indexing, error correction, and physical "
            "handling -- every one of these reduces how much of the "
            "theoretical capacity is actually usable in practice."
        ),
    },
    # --- Project ----------------------------------------------------------------------
    {
        "id": "proj-1",
        "category": CATEGORY_PROJECT,
        "question": "What is the main purpose of BioVault?",
        "answer": (
            "To provide a hands-on, computational educational simulation that "
            "demonstrates how digital data could be represented as DNA, and "
            "what happens when that data is corrupted, protected with "
            "redundancy/error correction, and verified for integrity."
        ),
    },
    {
        "id": "proj-2",
        "category": CATEGORY_PROJECT,
        "question": "What is the biggest limitation of this project?",
        "answer": (
            "It is a pure software simulation: it does not perform real DNA "
            "synthesis or sequencing, so it cannot capture the real physical "
            "and chemical error sources of an actual laboratory DNA-storage "
            "system."
        ),
    },
    {
        "id": "proj-3",
        "category": CATEGORY_PROJECT,
        "question": "Does BioVault physically store data in DNA?",
        "answer": "No. BioVault only simulates the process computationally in software -- no DNA is ever synthesized, sequenced, or physically stored.",
    },
    {
        "id": "proj-4",
        "category": CATEGORY_PROJECT,
        "question": "How is BioVault different from a real DNA storage laboratory?",
        "answer": (
            "A real laboratory physically synthesizes DNA molecules, stores "
            "them, and later sequences them to read the data back, dealing "
            "with real chemical/physical error sources. BioVault represents "
            "all of this with plain text strings and Python logic, so it can "
            "demonstrate the underlying concepts without any lab equipment."
        ),
    },
    {
        "id": "proj-5",
        "category": CATEGORY_PROJECT,
        "question": "What happens if the DNA sequence is corrupted?",
        "answer": (
            "Depending on the type and amount of corruption, BioVault will "
            "report the sequence as corrupted, incomplete, or partially/fully "
            "recovered -- using redundancy and/or error correction where "
            "available, and always confirming the true outcome with an exact "
            "byte comparison rather than assuming success."
        ),
    },
    {
        "id": "proj-6",
        "category": CATEGORY_PROJECT,
        "question": "What future improvements could be made?",
        "answer": (
            "More advanced error-correction codes, GC-content and homopolymer-"
            "avoidance strategies, more realistic synthesis/sequencing error "
            "models, larger benchmark datasets, and eventually real laboratory "
            "validation -- see the project's Future Scope section."
        ),
    },
]

_QUESTIONS_BY_ID = {q["id"]: q for q in QUESTIONS}


class VivaQuestionsError(Exception):
    """Raised when a viva-question lookup is invalid."""


def get_categories() -> tuple:
    """Return the fixed tuple of question categories, in display order."""
    return CATEGORIES


def get_all_questions() -> list:
    """Return every question in the bank (a copy of the list)."""
    return list(QUESTIONS)


def get_questions_by_category(category: str) -> list:
    """Return all questions in `category`, or an empty list if unknown."""
    return [q for q in QUESTIONS if q["category"] == category]


def get_question_by_id(question_id: str) -> dict:
    """Return the single question with `question_id`.

    Raises VivaQuestionsError if no such question exists, rather than
    returning None and letting a caller silently mishandle it.
    """
    if question_id not in _QUESTIONS_BY_ID:
        raise VivaQuestionsError(f"No question with id {question_id!r}.")
    return _QUESTIONS_BY_ID[question_id]


def get_question_count() -> int:
    """Return the total number of questions in the bank."""
    return len(QUESTIONS)
