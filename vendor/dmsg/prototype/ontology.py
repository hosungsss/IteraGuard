"""Evidence-bound, conservative scenario ontology for synthetic demonstrations.

Facts are assertions ABOUT the supplied transcript, not externally established facts.
No caller identity, crime, bank state, or verification outcome is inferred here.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from .core import Directness, Origin, Evidence, Kind

@dataclass(frozen=True)
class OntologyEdge:
    subject: str
    predicate: str
    object: str
    source_span: tuple[int, int]
    epistemic_status: str

@dataclass(frozen=True)
class OntologyAssessment:
    edges: tuple[OntologyEdge, ...]
    contradictions: tuple[str, ...]
    independent_verification: bool
    external_action_performed: bool


def assess_evidence(spans: Iterable[Evidence]) -> OntologyAssessment:
    """No semantic detector: only graphs pre-annotated evidence with provenance."""
    src = tuple(spans)
    edges: list[OntologyEdge] = []
    conflicts: list[str] = []
    for e in src:
        if not isinstance(e, Evidence):
            raise TypeError('UNVERIFIED_EVIDENCE_TYPE')
        relation = {
            Directness.DIRECT_REQUEST: 'REQUESTS',
            Directness.REPORTED_OR_QUOTED: 'REPORTS',
            Directness.NEGATED_OR_WARNING: 'WARNS_AGAINST',
            Directness.UNCLEAR: 'AMBIGUOUSLY_MENTIONS',
        }[e.directness]
        edges.append(OntologyEdge(
            subject='TEXT_SPEAKER_CLAIM', predicate=relation, object=e.kind.value,
            source_span=(e.start, e.end),
            epistemic_status='PREANNOTATED_SIMULATION' if e.origin is Origin.FIXTURE_ANNOTATED else (
                'HUMAN_LABEL_UNATTESTED' if e.origin is Origin.HUMAN_CONFIRMED else 'MODEL_PROPOSAL_UNVERIFIED'
            )))
    for i, a in enumerate(src):
        for b in src[i+1:]:
            if a.start < b.end and b.start < a.end:
                if a.directness != b.directness or a.kind != b.kind:
                    conflicts.append('CONFLICTING_OVERLAPPING_ANNOTATIONS')
    return OntologyAssessment(tuple(edges),tuple(sorted(set(conflicts))),False,False)
