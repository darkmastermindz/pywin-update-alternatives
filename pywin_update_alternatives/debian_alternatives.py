from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree
from typing import Iterable, TextIO


_WINDOWS_ABSOLUTE_RE = re.compile(r"^[a-zA-Z]:[\\/]")
_SUPPORTED_COMMANDS = {
    "--install",
    "--set",
    "--remove",
    "--remove-all",
    "--all",
    "--auto",
    "--display",
    "--get-selections",
    "--set-selections",
    "--query",
    "--list",
    "--config",
    "--help",
    "--version",
}


class AlternativesError(RuntimeError):
    pass


@dataclass(frozen=True)
class SlaveLink:
    name: str
    link: str


@dataclass(frozen=True)
class SlaveAlternative:
    name: str
    path: str


@dataclass(frozen=True)
class Alternative:
    path: str
    priority: int
    slaves: tuple[SlaveAlternative, ...] = ()


@dataclass(frozen=True)
class LinkGroup:
    name: str
    link: str
    status: str
    selected: str | None
    slave_links: tuple[SlaveLink, ...]
    alternatives: tuple[Alternative, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "link": self.link,
            "status": self.status,
            "selected": self.selected,
            "slave_links": [
                {"name": slave.name, "link": slave.link} for slave in self.slave_links
            ],
            "alternatives": [
                {
                    "path": alt.path,
                    "priority": alt.priority,
                    "slaves": [{"name": slave.name, "path": slave.path} for slave in alt.slaves],
                }
                for alt in self.alternatives
            ],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "LinkGroup":
        return cls(
            name=str(payload["name"]),
            link=str(payload["link"]),
            status=str(payload.get("status", "auto")),
            selected=payload.get("selected") if payload.get("selected") is None else str(payload["selected"]),
            slave_links=tuple(
                SlaveLink(name=str(item["name"]), link=str(item["link"]))
                for item in payload.get("slave_links", [])
            ),
            alternatives=tuple(
                Alternative(
                    path=str(item["path"]),
                    priority=int(item["priority"]),
                    slaves=tuple(
                        SlaveAlternative(name=str(slave["name"]), path=str(slave["path"]))
                        for slave in item.get("slaves", [])
                    ),
                )
                for item in payload.get("alternatives", [])
            ),
        )


@dataclass(frozen=True)
class CommandContext:
    altdir: Path
    admindir: Path
    instdir: Path
    log_file: Path
    force: bool = False
    skip_auto: bool = False
    quiet: bool = False
    verbose: bool = False
    debug: bool = False

    def write_log(self, message: str) -> None:
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        with self.log_file.open("a", encoding="utf-8") as handle:
            handle.write(message.rstrip() + "\n")


def _package_version() -> str:
    try:
        from importlib.metadata import PackageNotFoundError, version

        try:
            return version("pywin_update_alternatives")
        except PackageNotFoundError:
            return "0.0.0"
    except ImportError:
        return "0.0.0"


def build_usage() -> str:
    return (
        "Usage: pywin-update-alternatives [<option> ...] <command>\n\n"
        "Commands:\n"
        "  --install <link> <name> <path> <priority>\n"
        "    [--slave <link> <name> <path>] ...\n"
        "                           add a group of alternatives to the system.\n"
        "  --remove <name> <path>   remove <path> from the <name> group alternative.\n"
        "  --remove-all <name>      remove <name> group from the alternatives system.\n"
        "  --auto <name>            switch the master link <name> to automatic mode.\n"
        "  --display <name>         display information about the <name> group.\n"
        "  --query <name>           machine parseable version of --display <name>.\n"
        "  --list <name>            display all targets of the <name> group.\n"
        "  --get-selections         list master alternative names and their status.\n"
        "  --set-selections         read alternative status from standard input.\n"
        "  --config <name>          show alternatives for the <name> group and ask the\n"
        "                           user to select which one to use.\n"
        "  --set <name> <path>      set <path> as alternative for <name>.\n"
        "  --all                    call --config on all alternatives.\n\n"
        "Options:\n"
        "  --altdir <directory>     change the alternatives directory.\n"
        "  --admindir <directory>   change the administrative directory.\n"
        "  --instdir <directory>    change the installation directory.\n"
        "  --root <directory>       change the filesystem root directory.\n"
        "  --log <file>             change the log file.\n"
        "  --force                  allow replacing files with alternative links.\n"
        "  --skip-auto              skip prompt for alternatives in automatic mode.\n"
        "  --quiet                  quiet operation, minimal output.\n"
        "  --verbose                verbose operation, more output.\n"
        "  --debug                  debug output, way more output.\n"
        "  --help                   show this help message.\n"
        "  --version                show the version.\n"
    )


def _is_absolute_like(path: str) -> bool:
    return path.startswith(("/", "\\")) or bool(_WINDOWS_ABSOLUTE_RE.match(path))


def _root_join(root: Path, path: str) -> Path:
    candidate = Path(path)
    if _is_absolute_like(path):
        stripped = path.lstrip("/\\")
        return root / Path(stripped)
    return root / candidate


def _path_exists(path: str) -> bool:
    return Path(path).exists()


def _group_file(ctx: CommandContext, name: str) -> Path:
    return ctx.admindir / f"{name}.json"


def _load_group(ctx: CommandContext, name: str) -> LinkGroup:
    path = _group_file(ctx, name)
    if not path.exists():
        raise AlternativesError(f"Alternative '{name}' is not registered.")
    return LinkGroup.from_dict(json.loads(path.read_text(encoding="utf-8")))


def _save_group(ctx: CommandContext, group: LinkGroup) -> None:
    ctx.admindir.mkdir(parents=True, exist_ok=True)
    _group_file(ctx, group.name).write_text(json.dumps(group.to_dict(), indent=2), encoding="utf-8")


def _remove_tree_or_link(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    rmtree(path)


def _replace_with_symlink(path: Path, target: Path, force: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        if path.is_symlink():
            path.unlink()
        elif force:
            _remove_tree_or_link(path)
        else:
            raise AlternativesError(f"Refusing to replace non-link path without --force: {path}")
    os.symlink(str(target), str(path))


def _cleanup_path(path: Path, force: bool) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink():
        path.unlink()
        return
    if force:
        _remove_tree_or_link(path)
        return
    raise AlternativesError(f"Refusing to remove non-link path without --force: {path}")


def _available_alternatives(group: LinkGroup) -> tuple[Alternative, ...]:
    return tuple(alt for alt in group.alternatives if _path_exists(alt.path))


def _best_alternative(group: LinkGroup) -> Alternative | None:
    candidates = _available_alternatives(group)
    if not candidates:
        return None
    return max(candidates, key=lambda alt: (alt.priority, alt.path))


def _selected_alternative(group: LinkGroup) -> Alternative | None:
    if group.status == "auto":
        return _best_alternative(group)
    if group.selected is None:
        return None
    for alt in group.alternatives:
        if alt.path == group.selected:
            return alt
    return None


def _group_links(group: LinkGroup) -> dict[str, SlaveLink]:
    return {slave.name: slave for slave in group.slave_links}


def _apply_group(ctx: CommandContext, group: LinkGroup) -> LinkGroup:
    selected = _selected_alternative(group)
    alt_link = ctx.altdir / group.name
    master_link = _root_join(ctx.instdir, group.link)

    if selected is None:
        _cleanup_path(master_link, ctx.force)
        _cleanup_path(alt_link, True)
        for slave in group.slave_links:
            _cleanup_path(_root_join(ctx.instdir, slave.link), ctx.force)
            _cleanup_path(ctx.altdir / slave.name, True)
        return LinkGroup(
            name=group.name,
            link=group.link,
            status=group.status,
            selected=None if group.status == "auto" else group.selected,
            slave_links=group.slave_links,
            alternatives=group.alternatives,
        )

    ctx.altdir.mkdir(parents=True, exist_ok=True)
    _replace_with_symlink(alt_link, Path(selected.path), True)
    _replace_with_symlink(master_link, alt_link, ctx.force)

    slave_links = _group_links(group)
    selected_slave_paths = {slave.name: slave.path for slave in selected.slaves if _path_exists(slave.path)}

    for name, slave in slave_links.items():
        alt_slave_link = ctx.altdir / name
        master_slave_link = _root_join(ctx.instdir, slave.link)
        slave_target = selected_slave_paths.get(name)
        if slave_target is None:
            _cleanup_path(master_slave_link, ctx.force)
            _cleanup_path(alt_slave_link, True)
            continue
        _replace_with_symlink(alt_slave_link, Path(slave_target), True)
        _replace_with_symlink(master_slave_link, alt_slave_link, ctx.force)

    return LinkGroup(
        name=group.name,
        link=group.link,
        status=group.status,
        selected=selected.path,
        slave_links=group.slave_links,
        alternatives=group.alternatives,
    )


def _write(stdout: TextIO, message: str) -> None:
    stdout.write(message)
    if not message.endswith("\n"):
        stdout.write("\n")


def _display_group(group: LinkGroup) -> str:
    selected = _selected_alternative(group)
    best = _best_alternative(group)
    lines = [f"{group.name} - {group.status} mode", f"  link best version is {best.path if best else 'none'}"]
    lines.append(f"  link currently points to {selected.path if selected else 'none'}")
    lines.append(f"  link {group.link}")
    for slave in group.slave_links:
        lines.append(f"  slave {slave.name} is {slave.link}")
    for alt in sorted(group.alternatives, key=lambda item: (item.priority, item.path)):
        lines.append(f"{alt.path} - priority {alt.priority}")
        for slave in alt.slaves:
            lines.append(f"  slave {slave.name}: {slave.path}")
    return "\n".join(lines)


def _query_group(group: LinkGroup) -> str:
    selected = _selected_alternative(group)
    best = _best_alternative(group)
    lines = [f"Name: {group.name}", f"Link: {group.link}"]
    if group.slave_links:
        lines.append("Slaves:")
        for slave in group.slave_links:
            lines.append(f" {slave.name} {slave.link}")
    lines.append(f"Status: {group.status}")
    if best is not None:
        lines.append(f"Best: {best.path}")
    lines.append(f"Value: {selected.path if selected else 'none'}")
    for alt in sorted(group.alternatives, key=lambda item: (item.priority, item.path)):
        lines.append("")
        lines.append(f"Alternative: {alt.path}")
        lines.append(f"Priority: {alt.priority}")
        if alt.slaves:
            lines.append("Slaves:")
            for slave in alt.slaves:
                lines.append(f" {slave.name} {slave.path}")
    return "\n".join(lines)


def _parse_install_arguments(args: list[str]) -> tuple[str, str, str, int, tuple[SlaveLink, ...], tuple[SlaveAlternative, ...]]:
    if len(args) < 4:
        raise AlternativesError("--install requires <link> <name> <path> <priority>")
    link, name, path, priority_raw = args[:4]
    try:
        priority = int(priority_raw)
    except ValueError as exc:
        raise AlternativesError(f"Invalid priority: {priority_raw}") from exc

    slave_links: list[SlaveLink] = []
    slave_alternatives: list[SlaveAlternative] = []
    index = 4
    while index < len(args):
        if args[index] != "--slave":
            raise AlternativesError(f"Unexpected argument after --install: {args[index]}")
        if index + 3 >= len(args):
            raise AlternativesError("--slave requires <link> <name> <path>")
        slave_link, slave_name, slave_path = args[index + 1 : index + 4]
        slave_links.append(SlaveLink(name=slave_name, link=slave_link))
        slave_alternatives.append(SlaveAlternative(name=slave_name, path=slave_path))
        index += 4
    return link, name, path, priority, tuple(slave_links), tuple(slave_alternatives)


def _merge_slave_links(existing: Iterable[SlaveLink], new: Iterable[SlaveLink]) -> tuple[SlaveLink, ...]:
    merged: dict[str, SlaveLink] = {slave.name: slave for slave in existing}
    merged.update({slave.name: slave for slave in new})
    return tuple(sorted(merged.values(), key=lambda slave: slave.name))


def install_alternative(
    ctx: CommandContext,
    link: str,
    name: str,
    path: str,
    priority: int,
    slave_links: tuple[SlaveLink, ...],
    slave_alternatives: tuple[SlaveAlternative, ...],
) -> LinkGroup:
    if not _path_exists(path):
        raise AlternativesError(f"Alternative path does not exist: {path}")
    group_path = _group_file(ctx, name)
    if group_path.exists():
        current = _load_group(ctx, name)
        if current.link != link:
            raise AlternativesError(f"Alternative '{name}' is already registered for link {current.link}")
        alternatives = [alt for alt in current.alternatives if alt.path != path]
        alternatives.append(Alternative(path=path, priority=priority, slaves=slave_alternatives))
        group = LinkGroup(
            name=name,
            link=link,
            status=current.status,
            selected=current.selected,
            slave_links=_merge_slave_links(current.slave_links, slave_links),
            alternatives=tuple(sorted(alternatives, key=lambda alt: alt.path)),
        )
    else:
        group = LinkGroup(
            name=name,
            link=link,
            status="auto",
            selected=None,
            slave_links=tuple(sorted(slave_links, key=lambda slave: slave.name)),
            alternatives=(Alternative(path=path, priority=priority, slaves=slave_alternatives),),
        )

    applied = _apply_group(ctx, group)
    _save_group(ctx, applied)
    ctx.write_log(f"install {name} {path} priority={priority}")
    return applied


def set_alternative(ctx: CommandContext, name: str, path: str) -> LinkGroup:
    group = _load_group(ctx, name)
    if not any(alt.path == path for alt in group.alternatives):
        raise AlternativesError(f"Alternative '{path}' is not registered for '{name}'.")
    updated = LinkGroup(
        name=group.name,
        link=group.link,
        status="manual",
        selected=path,
        slave_links=group.slave_links,
        alternatives=group.alternatives,
    )
    applied = _apply_group(ctx, updated)
    _save_group(ctx, applied)
    ctx.write_log(f"set {name} {path}")
    return applied


def auto_alternative(ctx: CommandContext, name: str) -> LinkGroup:
    group = _load_group(ctx, name)
    updated = LinkGroup(
        name=group.name,
        link=group.link,
        status="auto",
        selected=None,
        slave_links=group.slave_links,
        alternatives=group.alternatives,
    )
    applied = _apply_group(ctx, updated)
    _save_group(ctx, applied)
    ctx.write_log(f"auto {name}")
    return applied


def remove_alternative(ctx: CommandContext, name: str, path: str) -> LinkGroup | None:
    group = _load_group(ctx, name)
    remaining = tuple(alt for alt in group.alternatives if alt.path != path)
    if len(remaining) == len(group.alternatives):
        return group
    if not remaining:
        remove_all_alternatives(ctx, name)
        return None
    updated = LinkGroup(
        name=group.name,
        link=group.link,
        status="auto" if group.selected == path else group.status,
        selected=None if group.selected == path else group.selected,
        slave_links=group.slave_links,
        alternatives=remaining,
    )
    applied = _apply_group(ctx, updated)
    _save_group(ctx, applied)
    ctx.write_log(f"remove {name} {path}")
    return applied


def remove_all_alternatives(ctx: CommandContext, name: str) -> None:
    group = _load_group(ctx, name)
    cleared = LinkGroup(
        name=group.name,
        link=group.link,
        status="auto",
        selected=None,
        slave_links=group.slave_links,
        alternatives=(),
    )
    _apply_group(ctx, cleared)
    _group_file(ctx, name).unlink(missing_ok=True)
    ctx.write_log(f"remove-all {name}")


def list_groups(ctx: CommandContext) -> tuple[LinkGroup, ...]:
    if not ctx.admindir.exists():
        return ()
    groups: list[LinkGroup] = []
    for entry in sorted(ctx.admindir.glob("*.json")):
        groups.append(LinkGroup.from_dict(json.loads(entry.read_text(encoding="utf-8"))))
    return tuple(groups)


def _read_choice(stdin: TextIO, stdout: TextIO) -> str:
    stdout.write("Selection: ")
    stdout.flush()
    line = stdin.readline()
    return line.strip() if line else ""


def config_alternative(ctx: CommandContext, name: str, stdin: TextIO, stdout: TextIO) -> LinkGroup:
    group = _load_group(ctx, name)
    alternatives = tuple(sorted(group.alternatives, key=lambda alt: (-alt.priority, alt.path)))
    if not ctx.quiet:
        _write(stdout, f"There are {len(alternatives)} choices for {name}.")
        _write(stdout, "  0    auto mode")
        for index, alternative in enumerate(alternatives, start=1):
            marker = "*" if group.selected == alternative.path or (group.status == "auto" and _best_alternative(group) == alternative) else " "
            _write(stdout, f"{marker} {index}    {alternative.path}")
    choice = _read_choice(stdin, stdout)
    if choice == "":
        return group
    if choice == "0":
        return auto_alternative(ctx, name)
    try:
        selected = alternatives[int(choice) - 1]
    except (ValueError, IndexError) as exc:
        raise AlternativesError(f"Invalid selection: {choice}") from exc
    return set_alternative(ctx, name, selected.path)


def _build_context(parsed: dict[str, object]) -> CommandContext:
    root_value = str(parsed.get("root") or os.environ.get("DPKG_ROOT") or "/")
    root = Path(root_value)
    altdir = Path(str(parsed["altdir"])) if parsed.get("altdir") else root / "etc" / "alternatives"
    admindir = (
        Path(str(parsed["admindir"]))
        if parsed.get("admindir")
        else Path(os.environ.get("DPKG_ADMINDIR", str(root / "var" / "lib" / "dpkg" / "alternatives")))
    )
    instdir = Path(str(parsed["instdir"])) if parsed.get("instdir") else root
    log_file = Path(str(parsed["log"])) if parsed.get("log") else root / "var" / "log" / "alternatives.log"
    debug = bool(parsed.get("debug"))
    verbose = bool(parsed.get("verbose")) or debug
    quiet = bool(parsed.get("quiet"))
    return CommandContext(
        altdir=altdir,
        admindir=admindir,
        instdir=instdir,
        log_file=log_file,
        force=bool(parsed.get("force")),
        skip_auto=bool(parsed.get("skip_auto")),
        quiet=quiet,
        verbose=verbose and not quiet,
        debug=debug and not quiet,
    )


def _parse_cli(argv: list[str]) -> tuple[CommandContext, str, list[str]]:
    parsed: dict[str, object] = {}
    index = 0
    command: str | None = None
    while index < len(argv):
        token = argv[index]
        if token in _SUPPORTED_COMMANDS:
            command = token
            index += 1
            break
        if token in {"--altdir", "--admindir", "--instdir", "--root", "--log"}:
            if index + 1 >= len(argv):
                raise AlternativesError(f"{token} requires an argument")
            parsed[token[2:]] = argv[index + 1]
            index += 2
            continue
        if token in {"--force", "--skip-auto", "--quiet", "--verbose", "--debug"}:
            parsed[token[2:].replace("-", "_")] = True
            index += 1
            continue
        raise AlternativesError(f"Unknown option: {token}")
    if command is None:
        raise AlternativesError("No command specified")
    return _build_context(parsed), command, argv[index:]


def run_debian_cli(
    argv: list[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr

    try:
        ctx, command, args = _parse_cli(argv)
        if command == "--help":
            _write(stdout, build_usage())
            return 0
        if command == "--version":
            _write(stdout, f"pywin-update-alternatives {_package_version()}")
            return 0
        if command == "--install":
            link, name, path, priority, slave_links, slave_alternatives = _parse_install_arguments(args)
            install_alternative(ctx, link, name, path, priority, slave_links, slave_alternatives)
            return 0
        if command == "--set":
            if len(args) != 2:
                raise AlternativesError("--set requires <name> <path>")
            set_alternative(ctx, args[0], args[1])
            return 0
        if command == "--remove":
            if len(args) != 2:
                raise AlternativesError("--remove requires <name> <path>")
            remove_alternative(ctx, args[0], args[1])
            return 0
        if command == "--remove-all":
            if len(args) != 1:
                raise AlternativesError("--remove-all requires <name>")
            remove_all_alternatives(ctx, args[0])
            return 0
        if command == "--auto":
            if len(args) != 1:
                raise AlternativesError("--auto requires <name>")
            auto_alternative(ctx, args[0])
            return 0
        if command == "--display":
            if len(args) != 1:
                raise AlternativesError("--display requires <name>")
            _write(stdout, _display_group(_load_group(ctx, args[0])))
            return 0
        if command == "--query":
            if len(args) != 1:
                raise AlternativesError("--query requires <name>")
            _write(stdout, _query_group(_load_group(ctx, args[0])))
            return 0
        if command == "--list":
            if len(args) != 1:
                raise AlternativesError("--list requires <name>")
            group = _load_group(ctx, args[0])
            for alternative in sorted(group.alternatives, key=lambda alt: alt.path):
                _write(stdout, alternative.path)
            return 0
        if command == "--get-selections":
            if args:
                raise AlternativesError("--get-selections does not accept extra arguments")
            for group in list_groups(ctx):
                selected = _selected_alternative(group)
                _write(stdout, f"{group.name} {group.status} {selected.path if selected else 'none'}")
            return 0
        if command == "--set-selections":
            if args:
                raise AlternativesError("--set-selections does not accept extra arguments")
            for line in stdin:
                text = line.strip()
                if not text:
                    continue
                name, status, path = text.split(None, 2)
                if status == "auto":
                    auto_alternative(ctx, name)
                elif status == "manual":
                    set_alternative(ctx, name, path)
                else:
                    raise AlternativesError(f"Invalid status in selections input: {status}")
            return 0
        if command == "--config":
            if len(args) != 1:
                raise AlternativesError("--config requires <name>")
            config_alternative(ctx, args[0], stdin, stdout)
            return 0
        if command == "--all":
            if args:
                raise AlternativesError("--all does not accept extra arguments")
            for group in list_groups(ctx):
                if ctx.skip_auto and group.status == "auto":
                    continue
                config_alternative(ctx, group.name, stdin, stdout)
            return 0
    except AlternativesError as exc:
        _write(stderr, f"error: {exc}")
        return 2
    raise AlternativesError(f"Unsupported command: {command}")
