import json

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from voice_agents.console import pipeline
from voice_agents.console.server import create_app


def events(response) -> list[dict]:
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ALLOWED_TO_NUMBERS", "+19727652721")
    return TestClient(create_app(store_path=tmp_path / "agents.json", sample_pause=0))


def test_sample_pipeline_builds_persona_and_org_agents(client):
    evs = events(client.post("/api/pipeline", json={"personas": 3, "source": "sample"}))

    assert [e["stage"] for e in evs][0] == "input"
    assert evs[-1]["stage"] == "ready"
    built = [e["agent"] for e in evs if "agent" in e]
    assert [a["kind"] for a in built] == ["legislator"] * 3 + ["survey", "lobbyist"]
    assert len({a["persona"]["name"] for a in built[:3]}) == 3
    assert all(a["payload"]["agent_phone_number_id"] == "<ELEVENLABS_PHONE_NUMBER_ID>" for a in built)
    assert len(client.get("/api/agents").json()) == 5


def test_agents_persist_across_restarts(tmp_path):
    path = tmp_path / "agents.json"
    first = TestClient(create_app(store_path=path, sample_pause=0))
    first.post("/api/pipeline", json={"personas": 1, "source": "sample"})
    second = TestClient(create_app(store_path=path, sample_pause=0))
    assert len(second.get("/api/agents").json()) == 3
    assert second.delete("/api/agents").json() == {"ok": True}
    assert second.get("/api/agents").json() == []


def test_persona_errors_show_up_in_trace():
    def broken(made):
        raise RuntimeError("no credits")

    from voice_agents.cli import load_demo
    evs = list(pipeline.run(load_demo(), persona_count=2, next_persona=broken, source_label="x"))
    assert evs[-1]["status"] == "error"
    assert "no credits" in evs[-1]["message"]


def test_call_refuses_number_outside_allowlist(client, monkeypatch):
    client.post("/api/pipeline", json={"personas": 1, "source": "sample"})
    agent = client.get("/api/agents").json()[0]
    monkeypatch.setenv("ALLOWED_TO_NUMBERS", "+15550000000")
    res = client.post(f"/api/agents/{agent['id']}/call")
    assert res.status_code == 403


def test_pipeline_rejects_too_many_personas(client):
    assert client.post("/api/pipeline", json={"personas": 50}).status_code == 422


def test_index_serves_ui(client):
    assert "Mobilize" in client.get("/").text
    assert client.get("/static/app.js").status_code == 200

