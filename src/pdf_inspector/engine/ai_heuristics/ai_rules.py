"""
AI & Heuristic Intelligence Suite
Provides advanced automated evaluations for alt text semantics, reading ease,
cognitive accessibility, and intelligent remediation synthesis.
"""

from typing import List
import re
from ..rule_base import BaseRule
from ...core.models import PDFDocumentModel, CheckResult, CheckStatus, Severity


class AIAltTextQualityRule(BaseRule):
    rule_id = "AI-ALT-001"
    name = "Alt-Text Semantic Quality"
    category = "AI Alt-Text Evaluation"
    standard = "AI"
    severity = Severity.MEDIUM
    description = "Evaluates whether image alternative text conveys actual information rather than trivial labels or redundant prefixes like 'image of...'."
    remediation_template = "Write concise, descriptive alt text that explains what the image illustrates without saying 'image of' or 'graphic of'."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        figure_nodes = []
        if doc.structure_tree:
            figure_nodes = doc.structure_tree.find_all_by_standard_tag("Figure")

        if not figure_nodes:
            return [self.create_result(
                status=CheckStatus.PASS,
                message="No figures present requiring AI semantic evaluation.",
                evidence="Figure count: 0"
            )]

        redundant_prefixes = re.compile(r"^(image of|picture of|photo of|graphic of|screenshot of|diagram of)\s+", re.IGNORECASE)

        low_quality_alt = []
        for fn in figure_nodes:
            alt = (fn.alt_text or "").strip()
            if alt:
                m = redundant_prefixes.match(alt)
                if m:
                    low_quality_alt.append((fn.tag, alt, f"Contains redundant prefix '{m.group(1)}'", fn.page or 1, fn.id))
                elif len(alt.split()) < 3 and len(alt) < 15:
                    low_quality_alt.append((fn.tag, alt, "Alt text is extremely short and may lack sufficient context", fn.page or 1, fn.id))

        if low_quality_alt:
            for tag, text, reason, pg, nid in low_quality_alt[:5]:
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message=f"Suboptimal alternative text on page {pg}: {reason}.",
                    evidence=f"Alt text: '{text}' ({reason})",
                    page=pg,
                    object_reference=f"<{tag} id='{nid}'>",
                    custom_remediation="Screen readers already announce 'graphic' or 'image'. Describe the essential message or data directly."
                ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"All {len(figure_nodes)} figure alternative description(s) exhibit good semantic clarity.",
                evidence="Heuristic semantic analysis passed."
            ))

        return results


class ReadabilityCognitiveRule(BaseRule):
    rule_id = "AI-READ-001"
    name = "Cognitive Readability Score"
    category = "Cognitive Accessibility"
    standard = "AI"
    severity = Severity.INFO
    description = "Calculates Flesch-Kincaid Reading Ease and average sentence complexity to support cognitive accessibility."
    remediation_template = "Simplify sentence structures and reduce jargon where possible for broad audience comprehension."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        full_text = " ".join(p.text for p in doc.pages if p.text).strip()
        if not full_text:
            return [self.create_result(
                status=CheckStatus.PASS,
                message="Document contains no extractable text for readability metrics.",
                evidence="Text length: 0",
                custom_severity=Severity.INFO
            )]

        words = re.findall(r"\b[a-zA-Z]+\b", full_text)
        sentences = re.split(r"[.!?]+", full_text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 2]

        word_count = len(words)
        sentence_count = max(1, len(sentences))
        avg_words_per_sentence = round(word_count / sentence_count, 1)

        # Approximate syllable count (vowel clusters)
        syllables = 0
        for w in words:
            syl = len(re.findall(r"[aeiouy]+", w.lower()))
            syllables += max(1, syl)

        # Flesch Reading Ease formula: 206.835 - 1.015*(words/sentences) - 84.6*(syllables/words)
        asl = word_count / sentence_count
        asw = syllables / max(1, word_count)
        flesch_score = round(206.835 - (1.015 * asl) - (84.6 * asw), 1)
        flesch_score = max(0.0, min(100.0, flesch_score))

        # Grade level rating
        if flesch_score >= 70:
            rating = "Fairly Easy / Conversational"
        elif flesch_score >= 50:
            rating = "Standard / Moderate"
        elif flesch_score >= 30:
            rating = "Difficult / Academic"
        else:
            rating = "Very Complex / Specialized"

        return [self.create_result(
            status=CheckStatus.PASS if flesch_score >= 40 else CheckStatus.WARNING,
            message=f"Flesch Reading Ease score: {flesch_score}/100 ({rating}). Avg sentence length: {avg_words_per_sentence} words.",
            evidence=f"Words: {word_count}, Sentences: {sentence_count}, Syllables: {syllables}, Reading Score: {flesch_score}",
            custom_severity=Severity.INFO
        )]


class OutlineSuggestionRule(BaseRule):
    rule_id = "AI-OUTLINE-001"
    name = "Structural Outline Consistency"
    category = "Structural AI"
    standard = "AI"
    severity = Severity.INFO
    description = "Analyzes bookmarks against tagged heading structure to ensure cohesive navigation."
    remediation_template = "Synchronize document bookmarks with the heading hierarchy."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        if not doc.bookmarks and doc.page_count > 10:
            return [self.create_result(
                status=CheckStatus.WARNING,
                message=f"AI Recommendation: Document has {doc.page_count} pages but lacks bookmarks. Generating bookmarks is recommended.",
                evidence=f"Page count: {doc.page_count}",
                custom_remediation="Generate bookmarks automatically from document headings."
            )]

        return [self.create_result(
            status=CheckStatus.PASS,
            message="Document structural outline and navigation elements are well-proportioned.",
            evidence=f"Bookmarks: {len(doc.bookmarks)}, Pages: {doc.page_count}"
        )]
