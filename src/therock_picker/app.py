"""Textual TUI for browsing local and remote TheRock builds."""

from __future__ import annotations

import http.client
import os
import platform as platform_module
import tarfile
from pathlib import Path
from typing import ClassVar, Optional

from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ProgressBar,
    Select,
    TabbedContent,
    TabPane,
)
from textual.widgets.data_table import RowKey

from therock_picker.config import load_therock_path, save_therock_path
from therock_picker.confirm_screen import ConfirmScreen
from therock_picker.gpu_detect import detect_local_gfx_targets, gfx_bucket_matches
from therock_picker.local import (
    LocalEntry,
    delete_entry,
    scan_local_directory,
    selected_link,
    update_symlink,
    versions_dir,
)
from therock_picker.models import TheRockBuild
from therock_picker.remote import (
    RemoteFetchResult,
    build_url,
    download_build,
    extract_build,
    fetch_remote_builds,
)
from therock_picker.update import current_version

_ALL_GFX = "__all__"
_ALL_PLATFORM = "__all__"
_SYSTEM_TO_PLATFORM = {"Linux": "linux", "Windows": "windows"}

_REMOTE_COLUMNS = ("Version", "GFX Target", "Variant", "Platform", "URL")
_LOCAL_COLUMNS = ("Version", "GFX Target", "Variant", "Platform", "Type", "Path")


class TheRockApp(App[None]):
    """Browse local TheRock builds and download remote nightly builds."""

    TITLE = "TheRock Picker"
    SUB_TITLE = f"v{current_version()}"

    CSS = """
    #dir_row { height: auto; }
    #dir_row Label { width: 14; content-align: left middle; }
    #dir_input { width: 40; }
    #selected_label { height: 1; }
    #status_label { margin: 1 0; height: 1; }
    #download_progress { margin: 1 0; }
    #remote_filters { height: auto; }
    #remote_filters Label { width: auto; content-align: left middle; margin: 0 1; }
    #gfx_filter, #platform_filter { width: 20; }
    #remote_actions, #local_actions { height: auto; margin-bottom: 1; }
    #remote_actions Button, #local_actions Button { min-width: 10; margin-right: 1; }
    #remote_tab_body, #local_tab_body { height: 1fr; }
    #remote_table, #local_table { height: 1fr; }
    TabbedContent { height: 1fr; }
    TabPane { height: 1fr; }
    """

    BINDINGS: ClassVar = [("q", "quit", "Quit")]

    def __init__(self) -> None:
        super().__init__()
        self._remote_builds: list[TheRockBuild] = []
        self._remote_row_builds: dict[RowKey, TheRockBuild] = {}
        self._selected_remote_build: Optional[TheRockBuild] = None
        self._local_row_entries: dict[RowKey, LocalEntry] = {}
        self._selected_local_entry: Optional[LocalEntry] = None
        self._detected_gfx_targets = detect_local_gfx_targets()
        self._detected_platform = _SYSTEM_TO_PLATFORM.get(
            platform_module.system()
        )

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="dir_row"):
            yield Label("TheRock path:")
            yield Input(
                value=load_therock_path(),
                placeholder="TheRock root directory...",
                id="dir_input",
                compact=True,
            )
        yield Label("", id="selected_label")
        with TabbedContent():
            with TabPane("Local", id="local_tab"), Vertical(id="local_tab_body"):
                with Horizontal(id="local_actions"):
                    yield Button("Scan directory", id="scan_button", compact=True)
                    yield Button("Select", id="select_button", compact=True)
                    yield Button("Delete", id="delete_button", compact=True)
                yield DataTable(id="local_table")
            with TabPane("Remote", id="remote_tab"), Vertical(id="remote_tab_body"):
                with Horizontal(id="remote_filters"):
                    yield Label("GPU:")
                    yield Select(
                        [("All GPU targets", _ALL_GFX)],
                        id="gfx_filter",
                        value=_ALL_GFX,
                        compact=True,
                    )
                    yield Label("Platform:")
                    yield Select(
                        [("All systems", _ALL_PLATFORM)],
                        id="platform_filter",
                        value=_ALL_PLATFORM,
                        compact=True,
                    )
                with Horizontal(id="remote_actions"):
                    yield Button("Refresh", id="refresh_button", compact=True)
                    yield Button("Download", id="download_button", compact=True)
                yield DataTable(id="remote_table")
                yield ProgressBar(id="download_progress")
                yield Label("", id="status_label")
        yield Footer()

    def on_mount(self) -> None:
        local_table = self.query_one("#local_table", DataTable)
        local_table.cursor_type = "row"
        local_table.add_columns(*_LOCAL_COLUMNS)

        remote_table = self.query_one("#remote_table", DataTable)
        remote_table.cursor_type = "row"
        remote_table.add_columns(*_REMOTE_COLUMNS)

        self._fetch_remote_builds()
        self._refresh_selected_label()

    def _therock_path(self) -> Path:
        raw_path = self.query_one("#dir_input", Input).value.strip() or load_therock_path()
        save_therock_path(raw_path)
        return Path(raw_path).expanduser()

    def _set_status(self, message: str) -> None:
        self.query_one("#status_label", Label).update(message)

    def _refresh_selected_label(self) -> None:
        link = selected_link(self._therock_path())
        if link.is_symlink():
            message = f"Selected: {os.readlink(link)}"
        else:
            message = "Selected: (none)"
        self.query_one("#selected_label", Label).update(message)

    @on(Input.Submitted, "#dir_input")
    def _handle_dir_input_submitted(self) -> None:
        self._refresh_selected_label()

    @on(Button.Pressed, "#scan_button")
    def _handle_scan(self) -> None:
        directory = versions_dir(self._therock_path())
        directory.mkdir(parents=True, exist_ok=True)

        entries = scan_local_directory(directory)
        table = self.query_one("#local_table", DataTable)
        table.clear()
        self._local_row_entries.clear()
        self._selected_local_entry = None
        for entry in entries:
            row_key = self._add_local_row(table, entry)
            self._local_row_entries[row_key] = entry
        self._set_status(f"Found {len(entries)} build(s) in {directory}")

    @staticmethod
    def _add_local_row(table: DataTable, entry: LocalEntry) -> RowKey:
        build = entry.build
        return table.add_row(
            build.version,
            build.gfx_target,
            build.variant or "-",
            build.platform,
            "extracted" if entry.extracted else "downloaded",
            str(entry.path),
        )

    @on(DataTable.RowHighlighted, "#local_table")
    def _handle_local_row_highlighted(
        self, event: DataTable.RowHighlighted
    ) -> None:
        if event.row_key is not None:
            self._selected_local_entry = self._local_row_entries.get(
                event.row_key
            )

    @on(Button.Pressed, "#select_button")
    def _handle_select(self) -> None:
        entry = self._selected_local_entry
        if entry is None:
            self._set_status("Select a local build first.")
            return
        if not entry.extracted:
            self._set_status(
                "That build is downloaded but not extracted yet; "
                "cannot select a tarball."
            )
            return
        link = update_symlink(entry.path, selected_link(self._therock_path()))
        self._set_status(f"Symlink updated: {link} -> {entry.path}")
        self._refresh_selected_label()

    @on(Button.Pressed, "#delete_button")
    def _handle_delete(self) -> None:
        entry = self._selected_local_entry
        if entry is None:
            self._set_status("Select a local build to delete first.")
            return
        self.push_screen(
            ConfirmScreen(f"Delete {entry.path.name}? This cannot be undone."),
            self._on_delete_confirmed,
        )

    def _on_delete_confirmed(self, confirmed: bool) -> None:
        if not confirmed:
            return
        self._delete_worker(self._selected_local_entry)

    @work(thread=True, exclusive=True)
    def _delete_worker(self, entry: LocalEntry) -> None:
        self.call_from_thread(self._set_status, f"Deleting {entry.path.name}...")
        try:
            delete_entry(entry)
        except OSError as exc:
            self.call_from_thread(self._set_status, f"Delete failed: {exc}")
            return
        self.call_from_thread(self._handle_scan)

    @on(Button.Pressed, "#refresh_button")
    def _handle_refresh(self) -> None:
        self._fetch_remote_builds()

    @work(thread=True)
    def _fetch_remote_builds(self) -> None:
        self.call_from_thread(self._set_status, "Fetching remote build list...")
        try:
            result = fetch_remote_builds()
        except (OSError, ValueError) as exc:
            self.call_from_thread(self._set_status, f"Fetch failed: {exc}")
            return
        self.call_from_thread(self._on_remote_builds_loaded, result)

    def _on_remote_builds_loaded(self, result: RemoteFetchResult) -> None:
        builds = result.builds
        self._remote_builds = builds

        gfx_targets = sorted({build.gfx_target for build in builds})
        gfx_options = [("All GPU targets", _ALL_GFX)]
        gfx_options += [(target, target) for target in gfx_targets]
        gfx_filter = self.query_one("#gfx_filter", Select)
        gfx_filter.set_options(gfx_options)

        default_target = None
        if len(self._detected_gfx_targets) == 1:
            detected = self._detected_gfx_targets[0]
            default_target = next(
                (t for t in gfx_targets if gfx_bucket_matches(t, detected)),
                None,
            )
        gfx_filter.value = default_target if default_target else _ALL_GFX

        platforms = sorted({build.platform for build in builds})
        platform_options = [("All systems", _ALL_PLATFORM)]
        platform_options += [(name, name) for name in platforms]
        platform_filter = self.query_one("#platform_filter", Select)
        platform_filter.set_options(platform_options)

        if self._detected_platform in platforms:
            platform_filter.value = self._detected_platform
        else:
            platform_filter.value = _ALL_PLATFORM

        self._refresh_remote_table()
        status = f"Loaded {len(builds)} remote build(s)"
        if result.warnings:
            status += "; " + "; ".join(result.warnings)
        self._set_status(status)

    @on(Select.Changed, "#gfx_filter")
    def _handle_gfx_filter_changed(self) -> None:
        self._refresh_remote_table()

    @on(Select.Changed, "#platform_filter")
    def _handle_platform_filter_changed(self) -> None:
        self._refresh_remote_table()

    def _refresh_remote_table(self) -> None:
        gfx_filter = self.query_one("#gfx_filter", Select).value
        platform_filter = self.query_one("#platform_filter", Select).value
        table = self.query_one("#remote_table", DataTable)
        table.clear()
        self._remote_row_builds.clear()
        self._selected_remote_build = None

        for build in self._remote_builds:
            if gfx_filter != _ALL_GFX and build.gfx_target != gfx_filter:
                continue
            if (
                platform_filter != _ALL_PLATFORM
                and build.platform != platform_filter
            ):
                continue
            url = build_url(build)
            row_key = table.add_row(
                build.version,
                build.gfx_target,
                build.variant or "-",
                build.platform,
                Text(url, style=f"link {url}"),
            )
            self._remote_row_builds[row_key] = build

    @on(DataTable.RowHighlighted, "#remote_table")
    def _handle_remote_row_highlighted(
        self, event: DataTable.RowHighlighted
    ) -> None:
        if event.row_key is not None:
            self._selected_remote_build = self._remote_row_builds.get(
                event.row_key
            )

    @on(Button.Pressed, "#download_button")
    def _handle_download(self) -> None:
        build = self._selected_remote_build
        if build is None:
            self._set_status("Select a remote build to download first.")
            return
        root = self._therock_path()
        self._download_worker(build, versions_dir(root), selected_link(root))

    @work(thread=True, exclusive=True)
    def _download_worker(
        self, build: TheRockBuild, dest_dir: Path, symlink: Path
    ) -> None:
        self.call_from_thread(
            self._set_status, f"Downloading {build.filename}..."
        )

        def on_progress(read: int, total: int) -> None:
            self.call_from_thread(self._update_progress, read, total)

        try:
            archive_path = download_build(build, dest_dir, on_progress=on_progress)
        except (OSError, http.client.IncompleteRead) as exc:
            self.call_from_thread(self._set_status, f"Download failed: {exc}")
            return

        self.call_from_thread(
            self._set_status, f"Extracting {archive_path.name}..."
        )
        try:
            extracted_path = extract_build(archive_path, dest_dir)
        except (OSError, tarfile.TarError) as exc:
            self.call_from_thread(self._set_status, f"Extraction failed: {exc}")
            return

        cleanup_warning = ""
        try:
            archive_path.unlink()
        except OSError as exc:
            cleanup_warning = f" (couldn't remove {archive_path.name}: {exc})"

        link = update_symlink(extracted_path, symlink)
        self.call_from_thread(
            self._set_status,
            f"Installed. Symlink updated: {link} -> {extracted_path}{cleanup_warning}",
        )
        self.call_from_thread(self._refresh_selected_label)

    def _update_progress(self, read: int, total: int) -> None:
        progress_bar = self.query_one("#download_progress", ProgressBar)
        if total:
            progress_bar.update(total=total, progress=read)
        else:
            progress_bar.update(progress=read)
