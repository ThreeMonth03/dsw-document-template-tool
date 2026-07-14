"""Run baseline and candidate renders with isolated API clients."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from ..api import DSWApiClient
from ..tdk import TemplateToolError


def render_subjects_in_parallel(
    *,
    client: DSWApiClient,
    baseline_render: Callable[[DSWApiClient], str],
    candidate_render: Callable[[DSWApiClient], str],
) -> tuple[str, str]:
    """Render both subjects concurrently without sharing a requests session."""

    def run_isolated(render: Callable[[DSWApiClient], str]) -> str:
        render_client = clone_authenticated_client(client)
        try:
            return render(render_client)
        finally:
            render_client.close()

    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="dsw-render") as executor:
        baseline_future = executor.submit(run_isolated, baseline_render)
        candidate_future = executor.submit(run_isolated, candidate_render)
        return baseline_future.result(), candidate_future.result()


def clone_authenticated_client(client: DSWApiClient) -> DSWApiClient:
    """Clone API connection settings and bearer token for one render worker."""

    if client.token is None:
        raise TemplateToolError("Parallel render requires an authenticated DSW client")
    render_client = DSWApiClient(
        api_url=client.api_url,
        verify_ssl=client.verify_ssl,
    )
    render_client.set_token(client.token)
    return render_client
