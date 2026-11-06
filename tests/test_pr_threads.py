import io
import os
import subprocess
from contextlib import redirect_stderr, redirect_stdout
import sys
from pathlib import Path
from unittest import mock

from unittest import TestCase

from agentics_tools.tools import context, pr_threads

class PullRequestReviewThreadsScriptTests(TestCase):
    def setUp(self):
        self.module = pr_threads
        context.set_repo_root(None)
        self.addCleanup(context.set_repo_root, None)

    def test_token_lookup_uses_graphql_host_despite_enterprise_default(self):
        session = mock.Mock()
        session.headers = {}
        session.post.return_value.json.return_value = {"data": {"viewer": {"login": "contributor"}}}
        with (
            mock.patch.dict(os.environ, {"GH_HOST": "enterprise.example"}, clear=True),
            mock.patch.object(
                self.module.subprocess,
                "run",
                return_value=subprocess.CompletedProcess([], 0, "synthetic-token\n", ""),
            ) as run,
        ):
            client = self.module.GitHubGraphQLClient(session=session)
            client.execute("query { viewer { login } }")

        self.assertEqual(run.call_args.args[0], ["gh", "auth", "token", "--hostname", "github.com"])
        self.assertEqual(session.post.call_args.args[0], "https://api.github.com/graphql")
        self.assertEqual(session.headers["Authorization"], "bearer synthetic-token")

    def test_author_defaults_to_authenticated_github_login(self):
        with mock.patch.object(
            self.module.subprocess,
            "run",
            return_value=subprocess.CompletedProcess([], 0, "someone-new\n", ""),
        ) as run:
            self.assertEqual(self.module.authenticated_login(), "someone-new")
        self.assertEqual(run.call_args.args[0], ["gh", "api", "user", "--hostname", "github.com", "--jq", ".login"])

    def test_missing_authenticated_login_explains_author_override(self):
        with mock.patch.object(
            self.module.subprocess,
            "run",
            return_value=subprocess.CompletedProcess([], 1, "", "not authenticated"),
        ):
            with self.assertRaisesRegex(RuntimeError, "Pass --author explicitly"):
                self.module.authenticated_login()

    def test_list_commands_resolve_default_author_and_preserve_explicit_author(self):
        for command in ("list-open-prs", "list-merged-prs"):
            operation = "list_open_pull_requests" if command == "list-open-prs" else "list_merged_pull_requests"
            for author in (None, "explicit-author"):
                with self.subTest(command=command, author=author):
                    argv = ["pr-threads", command, "--repo", "example/repository"]
                    if author:
                        argv.extend(["--author", author])
                    with (
                        mock.patch.object(sys, "argv", argv),
                        mock.patch.object(self.module, "GitHubGraphQLClient"),
                        mock.patch.object(self.module, "authenticated_login", return_value="current-login") as login,
                        mock.patch.object(self.module, "repository_default_branch", return_value="main"),
                        mock.patch.object(self.module, operation, return_value={"pull_requests": []}) as listing,
                        redirect_stdout(io.StringIO()),
                    ):
                        self.assertEqual(self.module.main(), 0)
                    self.assertEqual(listing.call_args.args[3], author or "current-login")
                    self.assertEqual(login.call_count, 0 if author else 1)

    def test_merged_cli_discovers_default_base_and_preserves_override(self):
        for explicit_base in (None, "release"):
            argv = ["pr-threads", "list-merged-prs", "--repo", "example/repository", "--author", "contributor"]
            if explicit_base:
                argv.extend(["--base", explicit_base])
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(self.module, "GitHubGraphQLClient"),
                mock.patch.object(self.module, "repository_default_branch", return_value="develop") as default,
                mock.patch.object(self.module, "list_merged_pull_requests", return_value={}) as listing,
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(self.module.main(), 0)
            self.assertEqual(listing.call_args.args[6], explicit_base or "develop")
            self.assertEqual(default.call_count, 0 if explicit_base else 1)

    def test_default_branch_query_binds_repository_and_rejects_empty_defaults(self):
        for stdout, returncode in (("develop\n", 0), ("", 1), ("null\n", 0)):
            with self.subTest(stdout=stdout, returncode=returncode):
                with mock.patch.object(
                    self.module.subprocess,
                    "run",
                    return_value=subprocess.CompletedProcess([], returncode, stdout, ""),
                ) as run:
                    if stdout.strip() == "develop":
                        self.assertEqual(self.module.repository_default_branch("example", "repository"), "develop")
                    else:
                        with self.assertRaisesRegex(RuntimeError, "Pass --base explicitly"):
                            self.module.repository_default_branch("example", "repository")
                self.assertEqual(run.call_args.args[0][3], "github.com/example/repository")

    def test_merged_search_uses_selected_base(self):
        client = mock.Mock()
        client.execute.return_value = {"search": {"nodes": [], "pageInfo": {"hasNextPage": False}}}
        today = self.module.datetime.now(self.module.timezone.utc).date().isoformat()
        self.module.list_merged_pull_requests(client, "example", "repository", "contributor", 1, today, "develop")
        self.assertIn("base:develop", client.execute.call_args.args[1]["query"])

    def test_selected_checkout_origin_overrides_ambient_ci_repository(self):
        with (
            mock.patch.object(self.module, "has_explicit_repo_root", return_value=True),
            mock.patch.object(self.module, "repo_root", return_value=Path("/selected/repository")),
            mock.patch.object(self.module, "run_git", return_value="git@github.com:selected/repository.git") as git,
            mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": "ambient/wrong-repo"}),
        ):
            self.assertEqual(self.module.resolve_repo_slug(None), ("selected", "repository"))
        git.assert_called_once_with(["remote", "get-url", "origin"], cwd=Path("/selected/repository"))

    def test_explicit_repo_flag_overrides_selected_checkout_and_ci_environment(self):
        with (
            mock.patch.object(self.module, "has_explicit_repo_root", return_value=True),
            mock.patch.object(self.module, "run_git") as git,
            mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": "ambient/wrong-repo"}),
        ):
            self.assertEqual(self.module.resolve_repo_slug("requested/repository"), ("requested", "repository"))
        git.assert_not_called()

    def test_ambient_ci_repository_is_retained_without_explicit_checkout(self):
        with (
            mock.patch.object(self.module, "has_explicit_repo_root", return_value=False),
            mock.patch.object(self.module, "run_git") as git,
            mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": "ci/repository"}),
        ):
            self.assertEqual(self.module.resolve_repo_slug(None), ("ci", "repository"))
        git.assert_not_called()

    def test_parse_remote_url_supports_https_and_ssh(self):
        https_actual = self.module.parse_remote_url("https://github.com/example-org/example-repo.git")
        ssh_actual = self.module.parse_remote_url("git@github.com:example-org/example-repo.git")

        https_expected = ("example-org", "example-repo")
        ssh_expected = ("example-org", "example-repo")

        self.assertEqual(https_actual, https_expected)
        self.assertEqual(ssh_actual, ssh_expected)

    def test_cli_does_not_print_credentials_from_rejected_remote_urls(self):
        credential = "synthetic-credential-sentinel"
        for userinfo in (f"account:{credential}", credential):
            remote = f"https://{userinfo}@github.com/example-org/example-repo.git"
            output, error = io.StringIO(), io.StringIO()
            with (
                self.subTest(userinfo=userinfo),
                mock.patch.object(sys, "argv", ["pr-threads", "list-open-prs"]),
                mock.patch.object(self.module, "has_explicit_repo_root", return_value=True),
                mock.patch.object(self.module, "repo_root", return_value=Path("/selected/repository")),
                mock.patch.object(self.module, "run_git", return_value=remote),
                mock.patch.object(self.module, "GitHubGraphQLClient") as client,
                redirect_stdout(output),
                redirect_stderr(error),
            ):
                self.assertEqual(self.module.main(), 1)
            self.assertIn("Pass --repo OWNER/REPO explicitly", error.getvalue())
            self.assertNotIn(credential, error.getvalue() + output.getvalue())
            self.assertNotIn(remote, error.getvalue() + output.getvalue())
            client.assert_not_called()

    def test_list_open_pull_requests_filters_forks_and_counts_unresolved_threads(self):
        fake_client = mock.Mock()
        fake_client.execute.side_effect = [
            {
                "search": {
                    "nodes": [
                        {
                            "id": "pr_1",
                            "number": 101,
                            "title": "Recent",
                            "url": "https://example.com/pr/101",
                            "isDraft": False,
                            "headRefName": "feature-recent",
                            "headRefOid": "sha-recent",
                            "baseRefName": "main",
                            "updatedAt": "2026-04-11T00:00:00Z",
                            "headRepositoryOwner": {"login": "example-org"},
                            "headRepository": {"name": "example-repo"},
                            "reviewThreads": {
                                "totalCount": 2,
                                "nodes": [
                                    {"isResolved": False},
                                    {"isResolved": True},
                                ],
                                "pageInfo": {
                                    "hasNextPage": False,
                                    "endCursor": None,
                                },
                            },
                        },
                        {
                            "id": "pr_2",
                            "number": 102,
                            "title": "Fork",
                            "url": "https://example.com/pr/102",
                            "isDraft": False,
                            "headRefName": "fork-branch",
                            "headRefOid": "sha-fork",
                            "baseRefName": "main",
                            "updatedAt": "2026-04-10T00:00:00Z",
                            "headRepositoryOwner": {"login": "someone-else"},
                            "headRepository": {"name": "forked-repo"},
                            "reviewThreads": {
                                "totalCount": 1,
                                "nodes": [{"isResolved": False}],
                                "pageInfo": {
                                    "hasNextPage": False,
                                    "endCursor": None,
                                },
                            },
                        },
                    ],
                    "pageInfo": {
                        "hasNextPage": True,
                        "endCursor": "cursor-1",
                    },
                }
            },
            {
                "search": {
                    "nodes": [
                        {
                            "id": "pr_3",
                            "number": 100,
                            "title": "Older",
                            "url": "https://example.com/pr/100",
                            "isDraft": True,
                            "headRefName": "feature-older",
                            "headRefOid": "sha-older",
                            "baseRefName": "main",
                            "updatedAt": "2026-04-09T00:00:00Z",
                            "headRepositoryOwner": {"login": "example-org"},
                            "headRepository": {"name": "example-repo"},
                            "reviewThreads": {
                                "totalCount": 0,
                                "nodes": [],
                                "pageInfo": {
                                    "hasNextPage": False,
                                    "endCursor": None,
                                },
                            },
                        }
                    ],
                    "pageInfo": {
                        "hasNextPage": False,
                        "endCursor": None,
                    },
                }
            },
        ]

        actual = self.module.list_open_pull_requests(fake_client, "example-org", "example-repo", "contributor")

        expected_numbers = [101, 100]
        actual_numbers = [pull_request["number"] for pull_request in actual["pull_requests"]]

        self.assertEqual(actual["repository"], "example-org/example-repo")
        self.assertEqual(actual["author"], "contributor")
        self.assertEqual(actual_numbers, expected_numbers)
        self.assertEqual(actual["pull_requests"][0]["unresolved_review_thread_count"], 1)

    def test_list_open_pull_requests_fetches_remaining_thread_pages_for_exact_count(self):
        fake_client = mock.Mock()
        fake_client.execute.side_effect = [
            {
                "search": {
                    "nodes": [
                        {
                            "id": "pr_1",
                            "number": 101,
                            "title": "Recent",
                            "url": "https://example.com/pr/101",
                            "isDraft": False,
                            "headRefName": "feature-recent",
                            "headRefOid": "sha-recent",
                            "baseRefName": "main",
                            "updatedAt": "2026-04-11T00:00:00Z",
                            "headRepositoryOwner": {"login": "example-org"},
                            "headRepository": {"name": "example-repo"},
                            "reviewThreads": {
                                "totalCount": 101,
                                "nodes": [
                                    {"isResolved": True},
                                ],
                                "pageInfo": {
                                    "hasNextPage": True,
                                    "endCursor": "thread-page-1",
                                },
                            },
                        }
                    ],
                    "pageInfo": {
                        "hasNextPage": False,
                        "endCursor": None,
                    },
                }
            },
            {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "nodes": [
                                {"isResolved": False},
                                {"isResolved": False},
                            ],
                            "pageInfo": {
                                "hasNextPage": False,
                                "endCursor": None,
                            },
                        }
                    }
                }
            },
        ]

        actual = self.module.list_open_pull_requests(fake_client, "example-org", "example-repo", "contributor")

        self.assertEqual(actual["pull_requests"][0]["unresolved_review_thread_count"], 2)
        self.assertTrue(actual["pull_requests"][0]["review_thread_count_truncated"])

    def test_build_merged_pull_request_search_query_targets_main_date_window(self):
        actual = self.module.build_merged_pull_request_search_query(
            "example-org",
            "example-repo",
            "contributor",
            self.module.parse_search_date("2026-04-01"),
            self.module.parse_search_date("2026-04-30"),
        )

        self.assertIn("repo:example-org/example-repo", actual)
        self.assertIn("is:merged", actual)
        self.assertIn("base:main", actual)
        self.assertIn("author:contributor", actual)
        self.assertIn("merged:2026-04-01..2026-04-30", actual)

    def test_list_merged_pull_requests_includes_forks_and_counts_unresolved_threads(self):
        fake_client = mock.Mock()
        fake_client.execute.side_effect = [
            {
                "search": {
                    "nodes": [
                        {
                            "id": "pr_201",
                            "number": 201,
                            "title": "Merged same repo",
                            "url": "https://example.com/pr/201",
                            "headRefName": "merged-same-repo",
                            "headRefOid": "sha-201",
                            "baseRefName": "main",
                            "updatedAt": "2026-04-11T00:00:00Z",
                            "mergedAt": "2026-04-11T01:00:00Z",
                            "mergeCommit": {"oid": "merge-sha-201"},
                            "headRepositoryOwner": {"login": "example-org"},
                            "headRepository": {"name": "example-repo"},
                            "reviewThreads": {
                                "totalCount": 2,
                                "nodes": [
                                    {"isResolved": False},
                                    {"isResolved": True},
                                ],
                                "pageInfo": {
                                    "hasNextPage": False,
                                    "endCursor": None,
                                },
                            },
                        },
                        {
                            "id": "pr_202",
                            "number": 202,
                            "title": "Merged fork",
                            "url": "https://example.com/pr/202",
                            "headRefName": "merged-fork",
                            "headRefOid": "sha-202",
                            "baseRefName": "main",
                            "updatedAt": "2026-04-10T00:00:00Z",
                            "mergedAt": "2026-04-10T01:00:00Z",
                            "mergeCommit": {"oid": "merge-sha-202"},
                            "headRepositoryOwner": {"login": "someone-else"},
                            "headRepository": {"name": "forked-repo"},
                            "reviewThreads": {
                                "totalCount": 101,
                                "nodes": [
                                    {"isResolved": False},
                                ],
                                "pageInfo": {
                                    "hasNextPage": True,
                                    "endCursor": "thread-page-1",
                                },
                            },
                        },
                    ],
                    "pageInfo": {
                        "hasNextPage": False,
                        "endCursor": None,
                    },
                }
            },
            {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "nodes": [
                                {"isResolved": False},
                                {"isResolved": True},
                            ],
                            "pageInfo": {
                                "hasNextPage": False,
                                "endCursor": None,
                            },
                        }
                    }
                }
            },
        ]

        actual = self.module.list_merged_pull_requests(
            fake_client,
            "example-org",
            "example-repo",
            "contributor",
            limit=2,
            merged_since="2026-04-01",
        )

        actual_numbers = [pull_request["number"] for pull_request in actual["pull_requests"]]

        self.assertEqual(actual["repository"], "example-org/example-repo")
        self.assertEqual(actual["merged_since"], "2026-04-01")
        self.assertEqual(actual_numbers, [201, 202])
        self.assertTrue(actual["pull_requests"][0]["same_repository"])
        self.assertFalse(actual["pull_requests"][1]["same_repository"])
        self.assertEqual(actual["pull_requests"][0]["merge_commit_oid"], "merge-sha-201")
        self.assertEqual(actual["pull_requests"][1]["merge_commit_oid"], "merge-sha-202")
        self.assertEqual(actual["pull_requests"][0]["unresolved_review_thread_count"], 1)
        self.assertEqual(actual["pull_requests"][1]["unresolved_review_thread_count"], 2)
        self.assertTrue(actual["pull_requests"][1]["review_thread_count_truncated"])

    def test_list_merged_pull_requests_applies_limit_after_merge_ordering(self):
        fake_client = mock.Mock()
        fake_client.execute.side_effect = [
            {
                "search": {
                    "nodes": [
                        {
                            "id": "pr_201",
                            "number": 201,
                            "title": "Recently updated older merge",
                            "url": "https://example.com/pr/201",
                            "headRefName": "older-merge",
                            "headRefOid": "sha-201",
                            "baseRefName": "main",
                            "updatedAt": "2026-04-15T00:00:00Z",
                            "mergedAt": "2026-04-10T00:00:00Z",
                            "headRepositoryOwner": {"login": "example-org"},
                            "headRepository": {"name": "example-repo"},
                            "reviewThreads": {
                                "totalCount": 0,
                                "nodes": [],
                                "pageInfo": {
                                    "hasNextPage": False,
                                    "endCursor": None,
                                },
                            },
                        }
                    ],
                    "pageInfo": {
                        "hasNextPage": True,
                        "endCursor": "cursor-1",
                    },
                }
            },
            {
                "search": {
                    "nodes": [
                        {
                            "id": "pr_202",
                            "number": 202,
                            "title": "Newest merge",
                            "url": "https://example.com/pr/202",
                            "headRefName": "newest-merge",
                            "headRefOid": "sha-202",
                            "baseRefName": "main",
                            "updatedAt": "2026-04-09T00:00:00Z",
                            "mergedAt": "2026-04-12T00:00:00Z",
                            "headRepositoryOwner": {"login": "example-org"},
                            "headRepository": {"name": "example-repo"},
                            "reviewThreads": {
                                "totalCount": 0,
                                "nodes": [],
                                "pageInfo": {
                                    "hasNextPage": False,
                                    "endCursor": None,
                                },
                            },
                        }
                    ],
                    "pageInfo": {
                        "hasNextPage": False,
                        "endCursor": None,
                    },
                }
            },
        ]

        actual = self.module.list_merged_pull_requests(
            fake_client,
            "example-org",
            "example-repo",
            "contributor",
            limit=1,
        )

        self.assertEqual([pull_request["number"] for pull_request in actual["pull_requests"]], [202])
        self.assertEqual(fake_client.execute.call_count, 2)

    def test_list_merged_pull_requests_stops_after_requested_limit_window(self):
        fake_client = mock.Mock()
        fake_client.execute.return_value = {
            "search": {
                "nodes": [
                    {
                        "id": "pr_201",
                        "number": 201,
                        "title": "Older merge",
                        "url": "https://example.com/pr/201",
                        "headRefName": "older-merge",
                        "headRefOid": "sha-201",
                        "baseRefName": "main",
                        "updatedAt": "2026-04-09T00:00:00Z",
                        "mergedAt": "2026-04-10T00:00:00Z",
                        "mergeCommit": {"oid": "merge-sha-201"},
                        "headRepositoryOwner": {"login": "example-org"},
                        "headRepository": {"name": "example-repo"},
                        "reviewThreads": {
                            "totalCount": 0,
                            "nodes": [],
                            "pageInfo": {
                                "hasNextPage": False,
                                "endCursor": None,
                            },
                        },
                    },
                    {
                        "id": "pr_202",
                        "number": 202,
                        "title": "Newest merge",
                        "url": "https://example.com/pr/202",
                        "headRefName": "newest-merge",
                        "headRefOid": "sha-202",
                        "baseRefName": "main",
                        "updatedAt": "2026-04-09T00:00:00Z",
                        "mergedAt": "2026-04-12T00:00:00Z",
                        "mergeCommit": {"oid": "merge-sha-202"},
                        "headRepositoryOwner": {"login": "example-org"},
                        "headRepository": {"name": "example-repo"},
                        "reviewThreads": {
                            "totalCount": 0,
                            "nodes": [],
                            "pageInfo": {
                                "hasNextPage": False,
                                "endCursor": None,
                            },
                        },
                    },
                ],
                "pageInfo": {
                    "hasNextPage": False,
                    "endCursor": None,
                },
            }
        }

        actual = self.module.list_merged_pull_requests(
            fake_client,
            "example-org",
            "example-repo",
            "contributor",
            limit=1,
        )

        self.assertEqual([pull_request["number"] for pull_request in actual["pull_requests"]], [202])
        self.assertEqual(actual["pull_requests"][0]["merge_commit_oid"], "merge-sha-202")
        self.assertEqual(fake_client.execute.call_count, 1)

    def test_list_unresolved_threads_filters_resolved_threads(self):
        fake_client = mock.Mock()
        fake_client.execute.side_effect = [
            {
                "repository": {
                    "pullRequest": {
                        "id": "pr_101",
                        "number": 101,
                        "title": "Recent",
                        "url": "https://example.com/pr/101",
                        "headRefName": "feature-recent",
                        "headRefOid": "sha-recent",
                        "reviewThreads": {
                            "nodes": [
                                {
                                    "id": "thread-resolved",
                                    "isResolved": True,
                                    "isOutdated": False,
                                    "isCollapsed": False,
                                    "path": "app.py",
                                    "line": 10,
                                    "diffSide": "RIGHT",
                                    "startLine": None,
                                    "startDiffSide": None,
                                    "originalLine": 10,
                                    "originalStartLine": None,
                                    "subjectType": "LINE",
                                    "comments": {
                                        "totalCount": 1,
                                        "nodes": [],
                                    },
                                },
                                {
                                    "id": "thread-open-1",
                                    "isResolved": False,
                                    "isOutdated": False,
                                    "isCollapsed": False,
                                    "path": "app.py",
                                    "line": 12,
                                    "diffSide": "RIGHT",
                                    "startLine": None,
                                    "startDiffSide": None,
                                    "originalLine": 12,
                                    "originalStartLine": None,
                                    "subjectType": "LINE",
                                    "comments": {
                                        "totalCount": 1,
                                        "nodes": [
                                            {
                                                "id": "comment-1",
                                                "body": "Please fix this.",
                                                "createdAt": "2026-04-10T00:00:00Z",
                                                "updatedAt": "2026-04-10T00:00:00Z",
                                                "url": "https://example.com/comment/1",
                                                "author": {"login": "reviewer"},
                                            }
                                        ],
                                        "pageInfo": {
                                            "hasNextPage": False,
                                            "endCursor": None,
                                        },
                                    },
                                },
                            ],
                            "pageInfo": {
                                "hasNextPage": True,
                                "endCursor": "cursor-1",
                            },
                        },
                    }
                }
            },
            {
                "repository": {
                    "pullRequest": {
                        "id": "pr_101",
                        "number": 101,
                        "title": "Recent",
                        "url": "https://example.com/pr/101",
                        "headRefName": "feature-recent",
                        "headRefOid": "sha-recent",
                        "reviewThreads": {
                            "nodes": [
                                {
                                    "id": "thread-open-2",
                                    "isResolved": False,
                                    "isOutdated": True,
                                    "isCollapsed": False,
                                    "path": "other.py",
                                    "line": 30,
                                    "diffSide": "RIGHT",
                                    "startLine": 28,
                                    "startDiffSide": "RIGHT",
                                    "originalLine": 30,
                                    "originalStartLine": 28,
                                    "subjectType": "LINE",
                                    "comments": {
                                        "totalCount": 1,
                                        "nodes": [
                                            {
                                                "id": "comment-2",
                                                "body": "Outdated comment.",
                                                "createdAt": "2026-04-10T00:00:00Z",
                                                "updatedAt": "2026-04-10T00:00:00Z",
                                                "url": "https://example.com/comment/2",
                                                "author": {"login": "reviewer"},
                                            }
                                        ],
                                        "pageInfo": {
                                            "hasNextPage": False,
                                            "endCursor": None,
                                        },
                                    },
                                }
                            ],
                            "pageInfo": {
                                "hasNextPage": False,
                                "endCursor": None,
                            },
                        },
                    }
                }
            },
        ]

        actual = self.module.list_unresolved_threads(fake_client, "example-org", "example-repo", 101)

        expected_thread_ids = ["thread-open-1", "thread-open-2"]
        actual_thread_ids = [thread["thread_id"] for thread in actual["review_threads"]]

        self.assertEqual(actual["unresolved_thread_count"], 2)
        self.assertEqual(actual_thread_ids, expected_thread_ids)
        self.assertTrue(actual["review_threads"][1]["is_outdated"])

    def test_list_unresolved_threads_fetches_remaining_thread_comments(self):
        fake_client = mock.Mock()
        fake_client.execute.side_effect = [
            {
                "repository": {
                    "pullRequest": {
                        "id": "pr_101",
                        "number": 101,
                        "title": "Recent",
                        "url": "https://example.com/pr/101",
                        "headRefName": "feature-recent",
                        "headRefOid": "sha-recent",
                        "reviewThreads": {
                            "nodes": [
                                {
                                    "id": "thread-open-1",
                                    "isResolved": False,
                                    "isOutdated": False,
                                    "isCollapsed": False,
                                    "path": "app.py",
                                    "line": 12,
                                    "diffSide": "RIGHT",
                                    "startLine": None,
                                    "startDiffSide": None,
                                    "originalLine": 12,
                                    "originalStartLine": None,
                                    "subjectType": "LINE",
                                    "comments": {
                                        "totalCount": 2,
                                        "nodes": [
                                            {
                                                "id": "comment-1",
                                                "body": "First comment.",
                                                "createdAt": "2026-04-10T00:00:00Z",
                                                "updatedAt": "2026-04-10T00:00:00Z",
                                                "url": "https://example.com/comment/1",
                                                "author": {"login": "reviewer"},
                                            }
                                        ],
                                        "pageInfo": {
                                            "hasNextPage": True,
                                            "endCursor": "comment-page-1",
                                        },
                                    },
                                }
                            ],
                            "pageInfo": {
                                "hasNextPage": False,
                                "endCursor": None,
                            },
                        },
                    }
                }
            },
            {
                "node": {
                    "comments": {
                        "totalCount": 2,
                        "nodes": [
                            {
                                "id": "comment-2",
                                "body": "Second comment.",
                                "createdAt": "2026-04-11T00:00:00Z",
                                "updatedAt": "2026-04-11T00:00:00Z",
                                "url": "https://example.com/comment/2",
                                "author": {"login": "maintainer"},
                            }
                        ],
                        "pageInfo": {
                            "hasNextPage": False,
                            "endCursor": None,
                        },
                    }
                }
            },
        ]

        actual = self.module.list_unresolved_threads(fake_client, "example-org", "example-repo", 101)

        self.assertEqual(actual["review_threads"][0]["comment_count"], 2)
        self.assertEqual(
            [comment["id"] for comment in actual["review_threads"][0]["comments"]],
            ["comment-1", "comment-2"],
        )

    def test_reply_to_thread_builds_dry_run_payload(self):
        fake_client = mock.Mock()

        actual = self.module.reply_to_thread(
            fake_client,
            "thread-123",
            "Applied a targeted fix.",
            resolve=True,
            dry_run=True,
        )

        expected_variables = {
            "input": {
                "pullRequestReviewThreadId": "thread-123",
                "body": "Applied a targeted fix.",
            }
        }

        self.assertEqual(actual["variables"], expected_variables)
        self.assertEqual(actual["resolve_variables"], {"input": {"threadId": "thread-123"}})
        fake_client.execute.assert_not_called()

    def test_reply_to_thread_posts_reply_and_resolves(self):
        fake_client = mock.Mock()
        fake_client.execute.side_effect = [
            {
                "addPullRequestReviewThreadReply": {
                    "comment": {
                        "id": "comment-123",
                        "url": "https://example.com/comment/123",
                        "body": "Applied a targeted fix.",
                    }
                }
            },
            {
                "resolveReviewThread": {
                    "thread": {
                        "id": "thread-123",
                        "isResolved": True,
                    }
                }
            },
        ]

        actual = self.module.reply_to_thread(
            fake_client,
            "thread-123",
            "Applied a targeted fix.",
            resolve=True,
            dry_run=False,
        )

        self.assertEqual(actual["reply"]["id"], "comment-123")
        self.assertTrue(actual["thread"]["is_resolved"])
        self.assertEqual(fake_client.execute.call_count, 2)

    def test_reply_to_thread_returns_partial_success_when_resolve_fails(self):
        fake_client = mock.Mock()
        fake_client.execute.side_effect = [
            {
                "addPullRequestReviewThreadReply": {
                    "comment": {
                        "id": "comment-123",
                        "url": "https://example.com/comment/123",
                        "body": "Applied a targeted fix.",
                    }
                }
            },
            RuntimeError("Resolve failed"),
        ]

        actual = self.module.reply_to_thread(
            fake_client,
            "thread-123",
            "Applied a targeted fix.",
            resolve=True,
            dry_run=False,
        )

        self.assertEqual(actual["reply"]["id"], "comment-123")
        self.assertFalse(actual["thread"]["is_resolved"])
        self.assertEqual(actual["resolve_error"], "Resolve failed")
