#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .context import has_explicit_repo_root, repo_root

import requests

GRAPHQL_URL = "https://api.github.com/graphql"
PAGE_SIZE = 100
DEFAULT_MERGED_BASE_REF = "main"
GITHUB_SEARCH_EARLIEST_DATE = date(2008, 1, 1)
MERGED_PULL_REQUEST_WINDOW_DAYS = 30

OPEN_PULL_REQUESTS_QUERY = """
query($query: String!, $after: String) {
  search(type: ISSUE, query: $query, first: {PAGE_SIZE}, after: $after) {
    nodes {
      ... on PullRequest {
        id
        number
        title
        url
        isDraft
        headRefName
        headRefOid
        baseRefName
        updatedAt
        headRepositoryOwner {
          login
        }
        headRepository {
          name
        }
        reviewThreads(first: {PAGE_SIZE}) {
          totalCount
          nodes {
            isResolved
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
""".replace("{PAGE_SIZE}", str(PAGE_SIZE))

MERGED_PULL_REQUESTS_QUERY = """
query($query: String!, $after: String) {
  search(type: ISSUE, query: $query, first: {PAGE_SIZE}, after: $after) {
    nodes {
      ... on PullRequest {
        id
        number
        title
        url
        headRefName
        headRefOid
        baseRefName
        updatedAt
        mergedAt
        mergeCommit {
          oid
        }
        headRepositoryOwner {
          login
        }
        headRepository {
          name
        }
        reviewThreads(first: {PAGE_SIZE}) {
          totalCount
          nodes {
            isResolved
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
""".replace("{PAGE_SIZE}", str(PAGE_SIZE))

UNRESOLVED_THREADS_QUERY = """
query($owner: String!, $repo: String!, $number: Int!, $after: String) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      id
      number
      title
      url
      headRefName
      headRefOid
      reviewThreads(first: {PAGE_SIZE}, after: $after) {
        nodes {
          id
          isResolved
          isOutdated
          isCollapsed
          path
          line
          diffSide
          startLine
          startDiffSide
          originalLine
          originalStartLine
          subjectType
          comments(first: {PAGE_SIZE}) {
            totalCount
            nodes {
              id
              body
              createdAt
              updatedAt
              url
              author {
                login
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
  }
}
""".replace("{PAGE_SIZE}", str(PAGE_SIZE))

REVIEW_THREAD_STATUS_QUERY = """
query($owner: String!, $repo: String!, $number: Int!, $after: String) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      reviewThreads(first: {PAGE_SIZE}, after: $after) {
        nodes {
          isResolved
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
  }
}
""".replace("{PAGE_SIZE}", str(PAGE_SIZE))

THREAD_COMMENTS_QUERY = """
query($threadId: ID!, $after: String) {
  node(id: $threadId) {
    ... on PullRequestReviewThread {
      comments(first: {PAGE_SIZE}, after: $after) {
        totalCount
        nodes {
          id
          body
          createdAt
          updatedAt
          url
          author {
            login
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
  }
}
""".replace("{PAGE_SIZE}", str(PAGE_SIZE))

ADD_THREAD_REPLY_MUTATION = """
mutation($input: AddPullRequestReviewThreadReplyInput!) {
  addPullRequestReviewThreadReply(input: $input) {
    comment {
      id
      url
      body
    }
  }
}
"""

RESOLVE_THREAD_MUTATION = """
mutation($input: ResolveReviewThreadInput!) {
  resolveReviewThread(input: $input) {
    thread {
      id
      isResolved
    }
  }
}
"""


class GitHubGraphQLClient:
    def __init__(self, token: str | None = None, session: requests.Session | None = None):
        resolved_token = token or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or gh_auth_token()
        if not resolved_token:
            raise RuntimeError("Missing GitHub token. Set GH_TOKEN or GITHUB_TOKEN, or authenticate gh.")
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "Authorization": f"bearer {resolved_token}",
            }
        )

    def execute(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.session.post(
            GRAPHQL_URL,
            json={"query": query, "variables": variables or {}},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        errors = payload.get("errors") or []
        if errors:
            formatted = "; ".join(error.get("message", "Unknown GitHub GraphQL error") for error in errors)
            raise RuntimeError(f"GitHub GraphQL request failed: {formatted}")
        return payload["data"]


def gh_auth_token() -> str | None:
    result = subprocess.run(
        ["gh", "auth", "token", "--hostname", "github.com"],
        capture_output=True,
        text=True,
        check=False,
    )
    token = result.stdout.strip()
    return token or None


def authenticated_login() -> str:
    result = subprocess.run(
        ["gh", "api", "user", "--hostname", "github.com", "--jq", ".login"],
        capture_output=True,
        text=True,
        check=False,
    )
    login = result.stdout.strip()
    if result.returncode != 0 or not login:
        raise RuntimeError("Unable to determine the authenticated GitHub login. Pass --author explicitly or authenticate gh.")
    return login


def repository_default_branch(owner: str, repo: str) -> str:
    result = subprocess.run(
        ["gh", "repo", "view", f"github.com/{owner}/{repo}", "--json", "defaultBranchRef", "--jq", ".defaultBranchRef.name"],
        capture_output=True,
        text=True,
        check=False,
    )
    branch = result.stdout.strip()
    if result.returncode != 0 or not branch or branch == "null":
        raise RuntimeError("Unable to determine the repository default branch. Pass --base explicitly.")
    return branch


def run_git(args: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def parse_repo_slug(value: str) -> tuple[str, str]:
    parts = value.strip().split("/")
    if len(parts) != 2 or not all(parts):
        raise argparse.ArgumentTypeError(f"Expected OWNER/REPO, got: {value!r}")
    return parts[0], parts[1]


def parse_remote_url(url: str) -> tuple[str, str]:
    normalized = url.strip()
    patterns = (
        r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$",
        r"^git@github\.com:(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$",
    )
    for pattern in patterns:
        match = re.match(pattern, normalized)
        if match:
            return match.group("owner"), match.group("repo")
    raise RuntimeError("Unable to parse GitHub repository from remote URL. Pass --repo OWNER/REPO explicitly.")


def parse_search_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"Expected YYYY-MM-DD date, got: {value!r}") from exc


def build_merged_pull_request_search_query(
    owner: str,
    repo: str,
    author: str,
    start_date: date,
    end_date: date,
    base_ref_name: str = DEFAULT_MERGED_BASE_REF,
) -> str:
    search_terms = [
        f"repo:{owner}/{repo}",
        "is:pr",
        "is:merged",
        f"base:{base_ref_name}",
        f"author:{author}",
        f"merged:{start_date.isoformat()}..{end_date.isoformat()}",
    ]
    return " ".join(search_terms)


def resolve_repo_slug(repo: str | None) -> tuple[str, str]:
    if repo:
        return parse_repo_slug(repo)
    env_repo = None if has_explicit_repo_root() else os.environ.get("GITHUB_REPOSITORY")
    if env_repo:
        return parse_repo_slug(env_repo)
    remote_url = run_git(["remote", "get-url", "origin"], cwd=repo_root())
    return parse_remote_url(remote_url)


def normalize_open_pull_request(node: dict[str, Any], owner: str, repo: str) -> dict[str, Any] | None:
    head_owner = ((node.get("headRepositoryOwner") or {}).get("login")) or ""
    head_repo = ((node.get("headRepository") or {}).get("name")) or ""
    same_repository = head_owner == owner and head_repo == repo
    if not same_repository:
        return None

    thread_nodes = (node.get("reviewThreads") or {}).get("nodes") or []
    total_threads = ((node.get("reviewThreads") or {}).get("totalCount")) or 0
    unresolved_count = sum(1 for thread in thread_nodes if not thread.get("isResolved"))
    review_threads_page_info = (node.get("reviewThreads") or {}).get("pageInfo") or {}
    return {
        "id": node["id"],
        "number": node["number"],
        "title": node["title"],
        "url": node["url"],
        "is_draft": node["isDraft"],
        "head_ref_name": node["headRefName"],
        "head_ref_oid": node["headRefOid"],
        "base_ref_name": node["baseRefName"],
        "updated_at": node["updatedAt"],
        "head_repository_owner": head_owner,
        "head_repository_name": head_repo,
        "review_thread_count": total_threads,
        "unresolved_review_thread_count": unresolved_count,
        "review_thread_count_truncated": review_threads_page_info.get("hasNextPage", False),
        "review_thread_end_cursor": review_threads_page_info.get("endCursor"),
    }


def normalize_merged_pull_request(node: dict[str, Any], owner: str, repo: str) -> dict[str, Any] | None:
    merged_at = node.get("mergedAt")
    if not merged_at:
        return None

    head_owner = ((node.get("headRepositoryOwner") or {}).get("login")) or ""
    head_repo = ((node.get("headRepository") or {}).get("name")) or ""
    thread_nodes = (node.get("reviewThreads") or {}).get("nodes") or []
    total_threads = ((node.get("reviewThreads") or {}).get("totalCount")) or 0
    unresolved_count = sum(1 for thread in thread_nodes if not thread.get("isResolved"))
    review_threads_page_info = (node.get("reviewThreads") or {}).get("pageInfo") or {}
    return {
        "id": node["id"],
        "number": node["number"],
        "title": node["title"],
        "url": node["url"],
        "head_ref_name": node.get("headRefName"),
        "head_ref_oid": node.get("headRefOid"),
        "base_ref_name": node["baseRefName"],
        "updated_at": node["updatedAt"],
        "merged_at": merged_at,
        "merge_commit_oid": (node.get("mergeCommit") or {}).get("oid"),
        "head_repository_owner": head_owner,
        "head_repository_name": head_repo,
        "same_repository": head_owner == owner and head_repo == repo,
        "review_thread_count": total_threads,
        "unresolved_review_thread_count": unresolved_count,
        "review_thread_count_truncated": review_threads_page_info.get("hasNextPage", False),
        "review_thread_end_cursor": review_threads_page_info.get("endCursor"),
    }


def count_unresolved_review_threads(
    client: GitHubGraphQLClient,
    owner: str,
    repo: str,
    pull_request_number: int,
    initial_unresolved_count: int,
    after: str | None,
) -> int:
    unresolved_count = initial_unresolved_count
    next_cursor = after

    while next_cursor:
        data = client.execute(
            REVIEW_THREAD_STATUS_QUERY,
            {
                "owner": owner,
                "repo": repo,
                "number": pull_request_number,
                "after": next_cursor,
            },
        )
        pull_request = ((data.get("repository") or {}).get("pullRequest")) or {}
        review_threads = pull_request.get("reviewThreads") or {}
        unresolved_count += sum(1 for thread in review_threads.get("nodes") or [] if not thread.get("isResolved"))
        page_info = review_threads.get("pageInfo") or {}
        next_cursor = page_info.get("endCursor") if page_info.get("hasNextPage") else None

    return unresolved_count


def list_open_pull_requests(
    client: GitHubGraphQLClient,
    owner: str,
    repo: str,
    author: str,
) -> dict[str, Any]:
    search_query = f"repo:{owner}/{repo} is:pr is:open author:{author}"
    pull_requests: list[dict[str, Any]] = []
    after: str | None = None

    while True:
        data = client.execute(OPEN_PULL_REQUESTS_QUERY, {"query": search_query, "after": after})
        search = data["search"]
        for node in search.get("nodes") or []:
            normalized = normalize_open_pull_request(node, owner, repo)
            if normalized is not None:
                if normalized["review_thread_count_truncated"]:
                    normalized["unresolved_review_thread_count"] = count_unresolved_review_threads(
                        client,
                        owner,
                        repo,
                        normalized["number"],
                        normalized["unresolved_review_thread_count"],
                        normalized["review_thread_end_cursor"],
                    )
                normalized.pop("review_thread_end_cursor", None)
                pull_requests.append(normalized)
        page_info = search["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        after = page_info["endCursor"]

    pull_requests.sort(key=lambda item: (item["updated_at"], item["number"]), reverse=True)
    return {
        "repository": f"{owner}/{repo}",
        "author": author,
        "pull_requests": pull_requests,
    }


def list_merged_pull_requests(
    client: GitHubGraphQLClient,
    owner: str,
    repo: str,
    author: str,
    limit: int,
    merged_since: str | None = None,
    base_ref_name: str = DEFAULT_MERGED_BASE_REF,
) -> dict[str, Any]:
    if limit < 1:
        raise ValueError("limit must be greater than zero.")

    lower_bound = parse_search_date(merged_since) if merged_since else GITHUB_SEARCH_EARLIEST_DATE
    pull_requests: list[dict[str, Any]] = []
    seen_pull_request_ids: set[str] = set()
    window_end = datetime.now(timezone.utc).date()

    while window_end >= lower_bound and len(pull_requests) < limit:
        window_start = max(lower_bound, window_end - timedelta(days=MERGED_PULL_REQUEST_WINDOW_DAYS - 1))
        search_query = build_merged_pull_request_search_query(
            owner,
            repo,
            author,
            window_start,
            window_end,
            base_ref_name,
        )
        after: str | None = None

        while True:
            data = client.execute(MERGED_PULL_REQUESTS_QUERY, {"query": search_query, "after": after})
            search = data["search"]
            for node in search.get("nodes") or []:
                normalized = normalize_merged_pull_request(node, owner, repo)
                if normalized is None or normalized["id"] in seen_pull_request_ids:
                    continue
                seen_pull_request_ids.add(normalized["id"])
                if normalized["review_thread_count_truncated"]:
                    normalized["unresolved_review_thread_count"] = count_unresolved_review_threads(
                        client,
                        owner,
                        repo,
                        normalized["number"],
                        normalized["unresolved_review_thread_count"],
                        normalized["review_thread_end_cursor"],
                    )
                normalized.pop("review_thread_end_cursor", None)
                pull_requests.append(normalized)
            page_info = search["pageInfo"]
            if not page_info["hasNextPage"]:
                break
            after = page_info["endCursor"]

        window_end = window_start - timedelta(days=1)

    pull_requests.sort(key=lambda item: (item["merged_at"], item["number"]), reverse=True)
    return {
        "repository": f"{owner}/{repo}",
        "author": author,
        "limit": limit,
        "merged_since": merged_since,
        "pull_requests": pull_requests[:limit],
    }


def normalize_comment(comment: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": comment["id"],
        "author": ((comment.get("author") or {}).get("login")) or "",
        "body": comment["body"],
        "created_at": comment["createdAt"],
        "updated_at": comment["updatedAt"],
        "url": comment["url"],
    }


def fetch_all_thread_comments(
    client: GitHubGraphQLClient,
    thread_id: str,
    initial_comments: list[dict[str, Any]],
    after: str | None,
) -> list[dict[str, Any]]:
    comments = list(initial_comments)
    next_cursor = after

    while next_cursor:
        data = client.execute(
            THREAD_COMMENTS_QUERY,
            {
                "threadId": thread_id,
                "after": next_cursor,
            },
        )
        thread = data.get("node")
        if thread is None:
            raise RuntimeError(f"Review thread {thread_id} was not found while fetching comment history.")
        comment_connection = thread["comments"]
        comments.extend(comment_connection.get("nodes") or [])
        page_info = comment_connection.get("pageInfo") or {}
        next_cursor = page_info.get("endCursor") if page_info.get("hasNextPage") else None

    return comments


def normalize_thread(thread: dict[str, Any], comments: list[dict[str, Any]]) -> dict[str, Any]:
    latest_comment = comments[-1] if comments else None
    return {
        "thread_id": thread["id"],
        "path": thread["path"],
        "line": thread.get("line"),
        "diff_side": thread.get("diffSide"),
        "start_line": thread.get("startLine"),
        "start_diff_side": thread.get("startDiffSide"),
        "original_line": thread.get("originalLine"),
        "original_start_line": thread.get("originalStartLine"),
        "subject_type": thread.get("subjectType"),
        "is_outdated": thread["isOutdated"],
        "is_collapsed": thread["isCollapsed"],
        "comment_count": len(comments),
        "url": latest_comment["url"] if latest_comment else None,
        "comments": [normalize_comment(comment) for comment in comments],
    }


def list_unresolved_threads(
    client: GitHubGraphQLClient,
    owner: str,
    repo: str,
    pull_request_number: int,
) -> dict[str, Any]:
    threads: list[dict[str, Any]] = []
    pull_request_meta: dict[str, Any] | None = None
    after: str | None = None

    while True:
        data = client.execute(
            UNRESOLVED_THREADS_QUERY,
            {
                "owner": owner,
                "repo": repo,
                "number": pull_request_number,
                "after": after,
            },
        )
        repository = data.get("repository")
        if repository is None or repository.get("pullRequest") is None:
            raise RuntimeError(f"Pull request #{pull_request_number} was not found in {owner}/{repo}.")

        pull_request = repository["pullRequest"]
        if pull_request_meta is None:
            pull_request_meta = {
                "id": pull_request["id"],
                "number": pull_request["number"],
                "title": pull_request["title"],
                "url": pull_request["url"],
                "head_ref_name": pull_request["headRefName"],
                "head_ref_oid": pull_request["headRefOid"],
            }

        review_threads = pull_request["reviewThreads"]
        for thread in review_threads.get("nodes") or []:
            if thread["isResolved"]:
                continue
            comment_connection = thread.get("comments") or {}
            comments = comment_connection.get("nodes") or []
            comments_page_info = comment_connection.get("pageInfo") or {}
            if comments_page_info.get("hasNextPage"):
                comments = fetch_all_thread_comments(
                    client, thread["id"], comments, comments_page_info.get("endCursor")
                )
            threads.append(normalize_thread(thread, comments))

        page_info = review_threads["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        after = page_info["endCursor"]

    assert pull_request_meta is not None
    return {
        "repository": f"{owner}/{repo}",
        "pull_request": pull_request_meta,
        "unresolved_thread_count": len(threads),
        "review_threads": threads,
    }


def build_reply_request(thread_id: str, body: str, resolve: bool) -> tuple[str, dict[str, Any]]:
    reply_input = {
        "pullRequestReviewThreadId": thread_id,
        "body": body,
    }
    if not resolve:
        return ADD_THREAD_REPLY_MUTATION, {"input": reply_input}
    return (
        ADD_THREAD_REPLY_MUTATION,
        {
            "input": reply_input,
        },
    )


def reply_to_thread(
    client: GitHubGraphQLClient,
    thread_id: str,
    body: str,
    resolve: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    mutation, variables = build_reply_request(thread_id, body, resolve)
    if dry_run:
        result = {
            "thread_id": thread_id,
            "body": body,
            "resolve": resolve,
            "dry_run": True,
            "variables": variables,
        }
        if resolve:
            result["resolve_variables"] = {"input": {"threadId": thread_id}}
        return result

    data = client.execute(mutation, variables)
    result: dict[str, Any] = {
        "thread_id": thread_id,
        "resolve": resolve,
        "dry_run": False,
        "reply": data["addPullRequestReviewThreadReply"]["comment"],
    }
    if resolve:
        try:
            resolve_data = client.execute(RESOLVE_THREAD_MUTATION, {"input": {"threadId": thread_id}})
            result["thread"] = {
                "id": resolve_data["resolveReviewThread"]["thread"]["id"],
                "is_resolved": resolve_data["resolveReviewThread"]["thread"]["isResolved"],
            }
        except Exception as exc:
            result["thread"] = {
                "id": thread_id,
                "is_resolved": False,
            }
            result["resolve_error"] = str(exc)
    return result


def read_body_text(args: argparse.Namespace) -> str:
    if args.body is not None:
        return args.body
    if args.body_file == "-":
        return sys.stdin.read()
    return Path(args.body_file).read_text(encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect and update GitHub PR review threads.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_open_prs = subparsers.add_parser("list-open-prs", help="List same-repo open pull requests by author.")
    list_open_prs.add_argument("--repo", help="Repository slug in OWNER/REPO form.")
    list_open_prs.add_argument("--author", help="GitHub login. Defaults to the authenticated gh user.")

    list_merged_prs = subparsers.add_parser("list-merged-prs", help="List merged pull requests by author.")
    list_merged_prs.add_argument("--repo", help="Repository slug in OWNER/REPO form.")
    list_merged_prs.add_argument("--author", help="GitHub login. Defaults to the authenticated gh user.")
    list_merged_prs.add_argument("--limit", type=int, default=50)
    list_merged_prs.add_argument("--base", help="Base branch. Defaults to the repository's default branch.")
    list_merged_prs.add_argument("--merged-since", help="GitHub search date for merged:>=, such as 2026-06-01.")

    list_threads = subparsers.add_parser("list-unresolved-threads", help="List unresolved review threads for a PR.")
    list_threads.add_argument("--repo", help="Repository slug in OWNER/REPO form.")
    list_threads.add_argument("--pr", type=int, required=True, dest="pull_request_number")

    reply_thread = subparsers.add_parser("reply-thread", help="Reply to a review thread and optionally resolve it.")
    reply_thread.add_argument("--thread-id", required=True)
    body_group = reply_thread.add_mutually_exclusive_group(required=True)
    body_group.add_argument("--body")
    body_group.add_argument("--body-file")
    reply_thread.add_argument("--resolve", action="store_true")
    reply_thread.add_argument("--dry-run", action="store_true")

    return parser


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2))


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "reply-thread":
            client = GitHubGraphQLClient()
            body = read_body_text(args)
            print_json(reply_to_thread(client, args.thread_id, body, resolve=args.resolve, dry_run=args.dry_run))
            return 0

        owner, repo = resolve_repo_slug(getattr(args, "repo", None))
        client = GitHubGraphQLClient()
        if args.command in {"list-open-prs", "list-merged-prs"}:
            args.author = args.author or authenticated_login()

        if args.command == "list-open-prs":
            print_json(list_open_pull_requests(client, owner, repo, args.author))
            return 0

        if args.command == "list-merged-prs":
            base = args.base or repository_default_branch(owner, repo)
            print_json(list_merged_pull_requests(client, owner, repo, args.author, args.limit, args.merged_since, base))
            return 0

        if args.command == "list-unresolved-threads":
            print_json(list_unresolved_threads(client, owner, repo, args.pull_request_number))
            return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    parser.error(f"Unhandled command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
