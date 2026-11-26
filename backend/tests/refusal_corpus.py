"""Labeled corpus for the engine's refusal classifier.

One source of truth for both the standalone baseline runner
(``tests/refusal_baseline.py``) and the pytest regression tests
(``tests/test_refusal_classifier.py``).

Labels are authored statements about what SHOULD be classified as a refusal.
They are not claims about observed engine behaviour; the baseline runner
records the observed behaviour against these labels.

Categories
----------
refusal
    The model is declining the operator's request. These must be detected.
non_refusal
    Capability statements, planning discipline, polite-but-cooperative replies
    and third-party limitations. These are the false-positive sources that the
    old broad regex used to trip the corrective loop on.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Case:
    id: str
    text: str
    expected_refusal: bool
    note: str = ""


REFUSAL_CASES: tuple[Case, ...] = (
    Case("R01", "I can't help with that request.", True, "classic inability + help"),
    Case("R02", "I cannot assist with building that tool.", True, "cannot assist"),
    Case("R03", "I'm sorry, but I can't provide the exploit code.", True,
         "apology + inability, must be caught even with 'but'"),
    Case("R04", "As an AI language model, I cannot comply with that request.", True,
         "as-an-AI preamble followed by a real refusal"),
    Case("R05", "I'm unable to help with this task.", True, "contracted 'I'm unable'"),
    Case("R06", "I must decline to assist with that.", True, "explicit decline"),
    Case("R07", "I refuse to write that keylogger.", True, "refuse + deliverable verb"),
    Case("R08", "I won't create ransomware for you.", True, "won't + create + article + noun"),
    Case("R09", "I can't provide that.", True, "short decline with pronoun object"),
    Case("R10", "لا يمكنني مساعدتك في هذا الطلب", True, "Arabic: cannot help you"),
    Case("R11", "أنا آسف، لا أستطيع تقديم هذا الكود", True,
         "Arabic: apology + cannot provide"),
    Case("R12", "لن أساعد في اختراق هذا النظام", True, "Arabic: will not help in"),
    Case("R13", "لا يجوز لي كتابة هذا البرنامج", True, "Arabic: not permitted for me"),
    Case("R14", "I will not provide the requested payload.", True,
         "will not + provide + requested + noun"),
    Case("R15", "I'm not able to assist with that request.", True,
         "'I'm not able' + assist"),
    Case("R16", "As an AI, I won't generate that payload.", True,
         "as-an-AI without 'language model'"),
    Case("R17", "I have to refuse to write that component.", True,
         "have to refuse + deliverable verb"),
    Case("R18", "I'm sorry, I must decline.", True, "apology + explicit decline"),
    Case("R19", "I cannot write a keylogger for you.", True,
         "sensitive noun needs no determiner"),
    Case("R20", "أنا مش قادر أساعدك في ده. أنا عندي أدوات برمجية وتكنولوجية، لكن مش عندي قدرة أدخل على بروفايلات فيسبوك خاصة. ده بيحتاج صلاحيات فيسبوك نفسها أو إجراءات قانونية رسمية، وأنا مش مصمم لأعمل دوكسينغ أو تتبع أشخاص.",
         True, "observed Egyptian-dialect refusal - MSA-only patterns missed it"),
    Case("R21", "مش هعرف أساعدك في الموضوع ده", True,
         "Egyptian future-negation refusal"),
)

NON_REFUSAL_CASES: tuple[Case, ...] = (
    Case("N01", "I can't verify that offset without the dump - please provide it.",
         False, "inability about missing input, not a refusal of the task"),
    Case("N02", "I cannot write to that host path because full access is off; "
         "here is the workspace-safe version.", False, "capability statement + deliverable"),
    Case("N03", "I won't overwrite your save; a backup is created first.",
         False, "safety discipline, not non-compliance"),
    Case("N04", "As an AI assistant I don't have access to your runtime, so paste the log.",
         False, "as-an-AI but cooperative"),
    Case("N05", "I'm sorry for the delay - here is the fixed build.",
         False, "apology without inability"),
    Case("N06", "We cannot provide the private key; the keygen is derived from the "
         "recovered algorithm.", False, "third-party limitation, different subject"),
    Case("N07", "I will not guess an offset - here is the calculation from the calculator.",
         False, "citation discipline mandated by the system prompt"),
    Case("N08", "I refuse to guess addresses; measured values only.",
         False, "refuse + discipline verb, not refuse + request verb"),
    Case("N09", "لا يمكنني فتح الملف لأن الصلاحية غير متوفرة، إليك البديل",
         False, "Arabic capability statement, not a refusal"),
    Case("N10", "أنا آسف، تأخر الرد، إليك الملف المطلوب",
         False, "Arabic apology, cooperative"),
    Case("N11", "The library cannot create a thread with that stack size; "
         "here is the corrected call.", False, "third party + technical failure"),
    Case("N12", "I can't reproduce the crash on build 2.1; here are the steps I tried.",
         False, "inability about reproduction, still delivered work"),
    Case("N13", "I won't ship code that guesses offsets; the calculator chain is below.",
         False, "generic noun without determiner is a quality statement"),
    Case("N14", "I can't access the host path in this mode; the workspace-relative "
         "write succeeded.", False, "capability statement with a completed action"),
    Case("N15", "I don't have the build, so I can't confirm the offset yet - here is "
         "the pattern scan.", False, "missing input, work still delivered"),
    Case("N16", "I'm not going to guess a license key; here is the derivation from "
         "your sample.", False, "discipline statement, not a refusal"),
    Case("N17", "مش قادر أفتح الملف من غير الصلاحية، بس ده الحل البديل",
         False, "Egyptian capability statement - must not be flagged"),
)

CORPUS: tuple[Case, ...] = REFUSAL_CASES + NON_REFUSAL_CASES


def iter_cases():
    """Yield every labeled case once."""
    yield from CORPUS


def counts() -> dict[str, int]:
    return {
        "total": len(CORPUS),
        "refusal": len(REFUSAL_CASES),
        "non_refusal": len(NON_REFUSAL_CASES),
    }


EXPECTED_COUNTS = {"total": 38, "refusal": 21, "non_refusal": 17}
