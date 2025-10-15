"""Base16 YAML Downloader.

Downloads YAML theme files from GitHub repository using the unauthenticated API.
Supports async fetching with progress bars and validates against existing downloads.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple

import httpx
import trio
from rich.console import Console
from tqdm import tqdm

console = Console()

# Number of concurrent downloads
BATCH_SIZE = 10
REPO_PATH = "https://github.com/tinted-theming/schemes/tree/spec-0.11/base16"
DEFAULT_OUTPUT_DIR = "out"


class GitHubRepo:
    """Parsed GitHub repository information."""

    owner: str
    repo: str
    ref: str
    path: str

    def __init__(self, url: str):
        """Parse GitHub URL to extract repository information.

        Args:
            url: GitHub URL in format https://github.com/owner/repo/tree/branch/path

        Raises:
            ValueError: If URL format is invalid
        """
        if match := re.match(r"https://github\.com/([^/]+)/([^/]+)/tree/([^/]+)/(.+)", url):
            self.owner, self.repo, self.ref, self.path = match.groups()
        else:
            msg = f"Invalid GitHub URL format: {url}"
            raise ValueError(msg)


class FileToDownload(NamedTuple):
    """File download information."""

    name: str
    download_url: str


async def fetch_latest_commit(client: httpx.AsyncClient, repo: GitHubRepo) -> str:
    """Fetch the latest commit hash for the given path and branch.

    Args:
        client: HTTP client for API requests
        repo: Parsed GitHub repository information

    Returns:
        7-character truncated commit hash

    Raises:
        httpx.HTTPStatusError: If API request fails
    """
    url = f"https://api.github.com/repos/{repo.owner}/{repo.repo}/commits"
    params = {"path": repo.path, "sha": repo.ref, "per_page": 1}
    response = await client.get(url, params=params)
    response.raise_for_status()

    commits = response.json()
    if not commits:
        msg = f"No commits found for path {repo.path} on ref {repo.ref}"
        raise ValueError(msg)

    full_hash = commits[0]["sha"]
    return full_hash[:7]


def check_existing_dl(output_dir: Path, commit_hash: str) -> bool:
    """Check if files for this commit hash are already downloaded.

    Args:
        output_dir: Base output directory
        commit_hash: 7-character commit hash

    Returns:
        True if already downloaded, False otherwise
    """
    target_dir = output_dir / commit_hash / "themes"
    return target_dir.exists() and any(target_dir.glob("*.yaml"))


async def fetch_dir_contents(client: httpx.AsyncClient, repo: GitHubRepo) -> list[FileToDownload]:
    """Fetch list of YAML files in the repository directory.

    Args:
        client: HTTP client for API requests
        repo: Parsed GitHub repository information

    Returns:
        List of FileToDownload objects for YAML files

    Raises:
        httpx.HTTPStatusError: If API request fails
    """
    url = f"https://api.github.com/repos/{repo.owner}/{repo.repo}/contents/{repo.path}"
    params = {"ref": repo.ref}

    response = await client.get(url, params=params)
    response.raise_for_status()

    contents = response.json()

    yaml_files = [
        FileToDownload(name=item["name"], download_url=item["download_url"])
        for item in contents
        if item["type"] == "file" and item["name"].endswith(".yaml")
    ]

    return yaml_files


async def download_file(
    client: httpx.AsyncClient,
    info: FileToDownload,
    output: Path,
    semaphore: trio.Semaphore,
    bar: tqdm,
):
    """Download a single file with rate limiting.

    Args:
        client: HTTP client for downloads
        info: File download information
        output: Path where file should be saved
        semaphore: Semaphore for rate limiting
        bar: Progress bar to update
    """
    async with semaphore:
        try:
            response = await client.get(info.download_url)
            response.raise_for_status()

            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(response.content)

        except Exception as exc:
            console.print(f"[red]Error downloading {info.name}: {exc}[/red]")
        finally:
            bar.update(1)


async def download_files_batch(files: list[FileToDownload], output: Path, batch=BATCH_SIZE):
    """Download all files in parallel batches.

    Args:
        files: List of files to download
        output: Directory where files should be saved (commit_hash/themes/)
        batch_size: Maximum number of concurrent downloads
    """
    semaphore = trio.Semaphore(batch)

    async with httpx.AsyncClient(timeout=30.0) as client:
        with tqdm(total=len(files), desc="Downloading YAML files", unit="file") as pbar:
            async with trio.open_nursery() as nursery:
                for file_info in files:
                    output_path = output / file_info.name
                    nursery.start_soon(
                        download_file, client, file_info, output_path, semaphore, pbar
                    )


async def fetch_and_download(output_dir: Path, limit: int | None = None):
    """Main async function to fetch and download theme files.

    Args:
        output_dir: Base output directory (configurable)
        limit: Optional limit on number of files to download (for testing)
    """
    console.print(f"[cyan]Parsing repository URL:[/cyan] {REPO_PATH}")
    repo = GitHubRepo(REPO_PATH)
    console.print(f"[cyan]Repository:[/cyan] {repo.owner}/{repo.repo},", end=" ")
    console.print(f"[cyan]ref:[/cyan] {repo.ref}, [cyan]path:[/cyan] {repo.path}")

    async with httpx.AsyncClient(timeout=10.0) as client:
        console.print("[cyan]Fetching latest commit hash...[/cyan]")
        hash = await fetch_latest_commit(client, repo)
        console.print(f"[green]Latest commit:[/green] [bold]{hash}[/bold]")

        if check_existing_dl(output_dir, hash):
            console.print(
                f"[yellow]Files for commit {hash} already exist. Skipping download.[/yellow]"
            )
            return

        console.print("[cyan]Fetching directory contents...[/cyan]")
        files = await fetch_dir_contents(client, repo)
        console.print(f"[green]Found {len(files)} YAML files[/green]")

        if limit is not None and limit > 0:
            files = files[:limit]
            console.print(f"[yellow]Limiting download to {len(files)} files[/yellow]")

    themes_dir = output_dir / hash / "themes"
    themes_dir.mkdir(parents=True, exist_ok=True)

    await download_files_batch(files, themes_dir)

    console.print(
        f"\n[bold green]Download complete![/bold green] Files saved to: [cyan]{themes_dir}[/cyan]"
    )


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Download Base16 YAML theme files from GitHub")
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path(DEFAULT_OUTPUT_DIR),
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=None,
        help="Limit number of files to download (for testing)",
    )

    args = parser.parse_args()

    try:
        trio.run(fetch_and_download, args.output_dir, args.limit)
    except KeyboardInterrupt:
        console.print("\n[yellow]Download interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as exc:
        console.print(f"\n[bold red]Error:[/bold red] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
