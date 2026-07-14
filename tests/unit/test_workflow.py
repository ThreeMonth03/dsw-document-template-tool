"""Tests for workflow orchestration helpers."""

from __future__ import annotations

from dsw_document_template_tool._regression import parallel as regression_parallel


class _FakeRenderClient:
    def __init__(self, label: str):
        self.label = label
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_render_subjects_in_parallel_uses_isolated_clients(monkeypatch) -> None:
    """Baseline and candidate renders should not share one requests session."""

    main_client = object()
    created_clients: list[_FakeRenderClient] = []
    seen_clients: list[tuple[str, _FakeRenderClient]] = []

    def clone_client(client):
        assert client is main_client
        render_client = _FakeRenderClient(f"render-{len(created_clients)}")
        created_clients.append(render_client)
        return render_client

    def render(label: str):
        def render_(client: _FakeRenderClient) -> str:
            seen_clients.append((label, client))
            return f"{label}:{client.label}"

        return render_

    monkeypatch.setattr(regression_parallel, "clone_authenticated_client", clone_client)

    baseline_html, candidate_html = regression_parallel.render_subjects_in_parallel(
        client=main_client,
        baseline_render=render("baseline"),
        candidate_render=render("candidate"),
    )

    assert baseline_html.startswith("baseline:render-")
    assert candidate_html.startswith("candidate:render-")
    assert len(created_clients) == 2
    assert len({id(client) for _, client in seen_clients}) == 2
    assert all(client.closed for client in created_clients)
