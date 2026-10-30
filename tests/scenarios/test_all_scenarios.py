import pytest
from app.services.scenario_service import load_scenario, SCENARIOS
from app.models.entities import EvidenceFile, TimelineEvent, IngestionRun, ParsingLedger

def test_load_all_three_scenarios(db_session):
    for scenario_id in SCENARIOS.keys():
        res = load_scenario(db_session, scenario_id)
        assert res["scenario_id"] == scenario_id
        assert len(res["evidence_ids"]) >= 1
        assert len(res["ingestion_ids"]) >= 1

    # Verify database state after loading scenarios
    total_ev = db_session.query(EvidenceFile).count()
    assert total_ev >= 6  # 2 files per scenario across 3 scenarios

    total_events = db_session.query(TimelineEvent).count()
    assert total_events > 0

    # Verify all ledgers reconciled
    ledgers = db_session.query(ParsingLedger).all()
    assert len(ledgers) >= 6
    for lg in ledgers:
        assert lg.reconciled is True
        assert lg.total_records == (lg.parsed_count + lg.partial_count + lg.ambiguous_count + lg.unparsed_count)
