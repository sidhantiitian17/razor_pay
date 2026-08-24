"""Dataset build orchestration and truth group construction (§3.5, I5, I8).

Takes `n` and `seed`, allocates cohort quotas, runs all injectors deterministically,
constructs the dataset, and builds the ground truth ledger and CSV exports.
"""

from __future__ import annotations

import csv
import json
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from engine.core.generator.allocate import allocate_cohorts
from engine.core.generator.cohorts import (
    COHORT_INJECTORS,
    IdCounters,
    InjectedCohort,
)
from engine.core.models import (
    BankTxn,
    GatewayPayout,
    LedgerEntry,
    TruthGroup,
    TruthLink,
    validate_group_cardinality,
)

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class GeneratedDataset:
    """Complete synthesized reconciliation dataset and ground truth."""

    bank_txns: list[BankTxn]
    gateway_payouts: list[GatewayPayout]
    ledger_entries: list[LedgerEntry]
    truth_groups: list[TruthGroup]
    truth_links: list[TruthLink]

    @property
    def bank_by_id(self) -> dict[str, BankTxn]:
        """Dictionary lookup mapping bank_id to BankTxn."""
        return {b.bank_id: b for b in self.bank_txns}

    @property
    def payout_by_id(self) -> dict[str, GatewayPayout]:
        """Dictionary lookup mapping payout_id to GatewayPayout."""
        return {p.payout_id: p for p in self.gateway_payouts}

    @property
    def ledger_by_id(self) -> dict[str, LedgerEntry]:
        """Dictionary lookup mapping ledger_id to LedgerEntry."""
        return {entry.ledger_id: entry for entry in self.ledger_entries}

    @property
    def group_by_id(self) -> dict[str, TruthGroup]:
        """Dictionary lookup mapping group_id to TruthGroup."""
        return {g.group_id: g for g in self.truth_groups}

    def to_json(self) -> str:
        """Serialize complete dataset to a deterministic JSON string."""
        data = {
            "bank_txns": [b.model_dump(mode="json") for b in self.bank_txns],
            "gateway_payouts": [p.model_dump(mode="json") for p in self.gateway_payouts],
            "ledger_entries": [entry.model_dump(mode="json") for entry in self.ledger_entries],
            "truth_groups": [g.model_dump(mode="json") for g in self.truth_groups],
            "truth_links": [t.model_dump(mode="json") for t in self.truth_links],
        }
        return json.dumps(data, indent=2, sort_keys=True)

    def write_csvs(self, target_dir: Path) -> None:
        """Write source records to CSVs and ground truth to JSON in target_dir."""
        target_dir.mkdir(parents=True, exist_ok=True)

        # 1. bank_txns.csv
        bank_csv = target_dir / "bank_txns.csv"
        with bank_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "bank_id",
                    "posted_at",
                    "value_date",
                    "amount_paise",
                    "utr",
                    "narration",
                    "currency",
                ],
            )
            writer.writeheader()
            for b in self.bank_txns:
                writer.writerow(b.model_dump(mode="json"))

        # 2. gateway_payouts.csv
        payout_csv = target_dir / "gateway_payouts.csv"
        with payout_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "payout_id",
                    "created_at",
                    "settled_at",
                    "amount_paise",
                    "fee_paise",
                    "tax_paise",
                    "utr",
                    "status",
                    "currency",
                ],
            )
            writer.writeheader()
            for p in self.gateway_payouts:
                writer.writerow(p.model_dump(mode="json"))

        # 3. ledger_entries.csv
        ledger_csv = target_dir / "ledger_entries.csv"
        with ledger_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "ledger_id",
                    "journal_id",
                    "entry_date",
                    "amount_paise",
                    "account",
                    "reference",
                    "currency",
                ],
            )
            writer.writeheader()
            for entry in self.ledger_entries:
                writer.writerow(entry.model_dump(mode="json"))

        # 4. ground_truth.json
        truth_json = target_dir / "ground_truth.json"
        with truth_json.open("w", encoding="utf-8") as f:
            f.write(self.to_json())


def _derive_truth_links(truth_groups: list[TruthGroup]) -> list[TruthLink]:
    """Derive link-level ground truth from TruthGroups (§4.1)."""
    links: list[TruthLink] = []

    for group in truth_groups:
        # Bank <-> Payout links
        if group.bank_ids and group.payout_ids:
            # First payout is the true settlement match for the bank
            for b_id in group.bank_ids:
                for idx, p_id in enumerate(group.payout_ids):
                    is_match = idx == 0
                    links.append(
                        TruthLink(
                            link_type="bank_payout",
                            left_id=b_id,
                            right_id=p_id,
                            is_match=is_match,
                        )
                    )

        # Payout <-> Ledger links
        if group.payout_ids and group.ledger_ids:
            for p_id in group.payout_ids:
                for l_id in group.ledger_ids:
                    links.append(
                        TruthLink(
                            link_type="payout_ledger",
                            left_id=p_id,
                            right_id=l_id,
                            is_match=True,
                        )
                    )

    return links


def generate_dataset(n: int, seed: int) -> GeneratedDataset:
    """Generate a complete synthetic dataset for reconciliation.

    Args:
        n: Total number of base cases (must be >= 50).
        seed: Deterministic random seed.

    Returns:
        GeneratedDataset container with all sources and truth groups.
    """
    rng = random.Random(seed)
    counters = IdCounters()
    allocations = allocate_cohorts(n)

    injections: list[InjectedCohort] = []
    case_idx = 0

    for cohort, count in allocations.items():
        injector = COHORT_INJECTORS[cohort]
        for _ in range(count):
            injected = injector(counters, rng, case_idx)
            injections.append(injected)
            case_idx += 1

    bank_txns: list[BankTxn] = []
    gateway_payouts: list[GatewayPayout] = []
    ledger_entries: list[LedgerEntry] = []
    truth_groups: list[TruthGroup] = []

    for inj in injections:
        bank_txns.extend(inj.bank_txns)
        gateway_payouts.extend(inj.gateway_payouts)
        ledger_entries.extend(inj.ledger_entries)
        truth_groups.append(inj.truth_group)

        # Validate I8 cardinality
        validate_group_cardinality(
            inj.truth_group.kind,
            len(inj.truth_group.bank_ids),
            len(inj.truth_group.payout_ids),
            len(inj.truth_group.ledger_ids),
        )

    # Sort each entity list deterministically by ID
    bank_txns.sort(key=lambda b: b.bank_id)
    gateway_payouts.sort(key=lambda p: p.payout_id)
    ledger_entries.sort(key=lambda entry: entry.ledger_id)
    truth_groups.sort(key=lambda g: g.group_id)

    truth_links = _derive_truth_links(truth_groups)

    return GeneratedDataset(
        bank_txns=bank_txns,
        gateway_payouts=gateway_payouts,
        ledger_entries=ledger_entries,
        truth_groups=truth_groups,
        truth_links=truth_links,
    )
