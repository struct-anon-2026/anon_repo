"""StructAgent — agent interface stub.

This module defines the *observable* interface of the StructAgent
H/E/C/Q loop, as described in the paper § 3-§ 4. It is intentionally a
stub: the internal pipeline (~40 modules covering layout analysis, OCR
caching, axis adjudication, cross-sheet aggregation, 3D consistency
checking, and FEM export) is not released in this anonymous repository.

The stub is sufficient to:

  - Reconstruct the input/output contract of the agent loop.
  - Reimplement the agent on top of a different set of vision tools, by
    satisfying the dataclasses and protocol defined here.
  - Cross-check that the metrics in ../../data/metrics/ are computed
    from outputs of the same shape as defined here.

The stub is *not* sufficient to re-run the exact pipeline that produced
the released metrics. Those metrics are the verifiable artifact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


# ---------------------------------------------------------------------------
# I/O contract
# ---------------------------------------------------------------------------


@dataclass
class Sheet:
    """A single scanned blueprint sheet."""

    sheet_id: str
    floor_label: str | None
    image_path: str  # path or URI; pipeline-specific
    dpi: int


@dataclass
class Region:
    """A spatial region on a sheet, used as the unit of inspection."""

    sheet_id: str
    bbox_norm: tuple[float, float, float, float]  # (x0, y0, x1, y1) in [0,1]
    region_kind: str  # "axis_band" | "column_zone" | "beam_zone" | "table" | "title_block"


@dataclass
class Evidence:
    """A piece of evidence produced by a tool call on a Region."""

    region: Region
    tool: str  # "ocr" | "axis_detect" | "column_detect" | "beam_detect" | "section_lookup" | ...
    payload: dict  # tool-specific structured output
    confidence: float


@dataclass
class Entity:
    """A first-class structural entity (axis, column, beam, ...)."""

    entity_id: str
    kind: str  # "axis" | "column" | "beam" | "opening" | ...
    geometry: dict  # kind-specific; see ../../data/gt/README.md schema
    attributes: dict  # kind-specific; e.g. section label, span endpoints
    supporting_evidence: list[Evidence] = field(default_factory=list)


@dataclass
class ConstraintViolation:
    """A check-step finding that triggers re-inspection."""

    constraint_id: str  # e.g. "C_axis.span_px_ratio", "C_geo.column_inside_grid", "C_3D.beam_endpoint_on_column"
    severity: str  # "warning" | "error"
    affected_entities: list[str]
    suggested_regions: list[Region]  # where to revisit


@dataclass
class WorldModel:
    """The accumulated belief state across the H/E/C/Q loop."""

    sheets: list[Sheet]
    entities: list[Entity]
    open_questions: list[str]
    pending_revisits: list[Region]


# ---------------------------------------------------------------------------
# Protocol for the agent loop
# ---------------------------------------------------------------------------


class StructAgentProtocol(Protocol):
    """The observable interface of the StructAgent loop.

    Reference implementation is withheld; see paper § 3 and § 4 for the
    algorithm description.
    """

    # H — Hypothesize: propose next region to inspect given current state.
    def hypothesize(self, world: WorldModel) -> Region | None: ...

    # E — Evidence: call vision/OCR tools on the chosen region.
    def evidence(self, region: Region) -> list[Evidence]: ...

    # C — Check: validate the proposed update against entity-level constraints.
    def check(self, world: WorldModel, new_evidence: list[Evidence]) -> list[ConstraintViolation]: ...

    # Q — Question: if constraints are violated, generate revisit queries.
    def question(self, violations: list[ConstraintViolation]) -> list[Region]: ...

    # Step: one iteration of H -> E -> C -> Q -> integrate.
    def step(self, world: WorldModel) -> WorldModel: ...

    # Terminate when no open hypotheses and no pending revisits, or budget exhausted.
    def is_done(self, world: WorldModel, step_count: int, budget: int) -> bool: ...


# ---------------------------------------------------------------------------
# State machine pseudo-code (informative)
# ---------------------------------------------------------------------------

PSEUDOCODE = """
function run_agent(sheets, budget):
    world = WorldModel(sheets=sheets, entities=[], open_questions=[], pending_revisits=[])
    step = 0
    while not is_done(world, step, budget):
        # H — pick a region: priority queue ordered by
        #   1) pending_revisits (from previous C step), then
        #   2) hypotheses derived from current world (which axes still missing,
        #      which floors not yet processed, which columns lack section label, ...)
        region = hypothesize(world)
        if region is None:
            break

        # E — call vision/OCR tools (zoom-in, axis detector, column detector,
        #   beam detector, OCR on bbox). May call multiple tools per region.
        new_evidence = evidence(region)

        # Tentatively integrate evidence into a candidate updated world.
        candidate = integrate(world, new_evidence)

        # C — run constraint checks at entity level:
        #   C_axis: axis labels match span_px ratio, no duplicates, monotonic positions
        #   C_geo:  columns inside grid envelope, beams span valid axis pairs
        #   C_anno: section labels resolve in schema
        #   C_3D:   beam endpoints supported by columns/walls; verticals continuous
        violations = check(candidate, new_evidence)

        if violations:
            # Q — emit revisit queries, push to pending queue.
            world.pending_revisits.extend(question(violations))
            # do not commit candidate; only commit evidence that passed
            world = commit_partial(world, new_evidence, violations)
        else:
            world = candidate

        step += 1
    return world
"""
