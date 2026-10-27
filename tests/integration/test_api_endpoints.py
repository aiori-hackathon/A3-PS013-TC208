import pytest

def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert data["app"] == "TraceLens"
    assert data["database_connected"] is True

def test_dashboard_summary_endpoint(client):
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert "evidence_files_count" in data
    assert "total_source_records" in data
    assert "timeline_events_count" in data

def test_scenarios_list_and_load_api(client):
    # List scenarios
    res_list = client.get("/api/scenarios")
    assert res_list.status_code == 200
    scenarios = res_list.json()
    assert len(scenarios) == 3

    # Load scenario 1
    res_load = client.post("/api/scenarios/scenario-01/load")
    assert res_load.status_code == 200
    load_data = res_load.json()
    assert load_data["scenario_id"] == "scenario-01"

    # Query timeline events
    res_events = client.get("/api/events")
    assert res_events.status_code == 200
    events_data = res_events.json()
    assert events_data["total_count"] > 0
    assert len(events_data["events"]) > 0

    first_event = events_data["events"][0]
    # Check source line traceability endpoint
    res_src = client.get(f"/api/events/{first_event['event_id']}/source")
    assert res_src.status_code == 200
    src_data = res_src.json()
    assert src_data["raw_text"] is not None
    assert src_data["source_line"] > 0
    assert src_data["sha256_baseline"] is not None

def test_evaluation_benchmark_api(client):
    client.post("/api/scenarios/scenario-01/load")
    res = client.post("/api/evaluation/run", json={"scenario_name": "scenario-01"})
    assert res.status_code == 201
    data = res.json()
    assert "traceability_rate" in data
    assert "parsing_accuracy" in data
    assert data["traceability_rate"] == 100.0

def test_report_generation_api(client):
    client.post("/api/scenarios/scenario-01/load")
    res = client.post("/api/reports", json={"title": "API Test Report", "format": "PDF"})
    assert res.status_code == 201
    data = res.json()
    assert "report_id" in data
    assert "download_url" in data

    # Test download
    dl_res = client.get(data["download_url"])
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/pdf"
    assert len(dl_res.content) > 100
