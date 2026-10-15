"""
Command-line interface entry point for Hamsa OSINT Framework.
"""

import argparse
import asyncio
import os
import sys
from typing import List, Tuple
from hamsa import __version__
from hamsa.core.models import TargetType
from hamsa.core.orchestrator import Orchestrator
from hamsa.utils.formatters import (
    BOLD,
    CYAN,
    GREEN,
    HAMSA_BANNER,
    RESET,
    YELLOW,
    colorize,
    log_error,
    log_info,
    log_success,
    log_warn,
)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hamsa",
        description="Hamsa: Modular, fast, and lightweight open-source intelligence framework.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--no-banner", action="store_true", help="Suppress the startup ASCII banner.")

    # Target inputs
    targets = parser.add_argument_group("Target Options")
    targets.add_argument("-u", "--username", help="Target username to hunt across web platforms.")
    targets.add_argument("-e", "--email", help="Target email address to check for breach exposures.")
    targets.add_argument("-p", "--phone", help="Target phone number (e.g. +628123456789 or 08123456789).")
    targets.add_argument("-i", "--image", help="Target photo/image file to extract EXIF and GPS coordinates.")

    # Plugin Management
    plugins = parser.add_argument_group("Plugin Options")
    plugins.add_argument("--list-plugins", action="store_true", help="List all loaded plugins and exit.")

    # Investigation & Recursion Options
    investigation = parser.add_argument_group("Investigation Options")
    investigation.add_argument("--depth", type=int, default=2, help="Maximum recursion depth for multi-round profiling (default: 2).")
    investigation.add_argument("--no-recursive", action="store_true", help="Disable automatic second-round scanning of discovered identities.")
    investigation.add_argument("--all-sites", action="store_true", help="Scan across all 690+ sites for usernames (default scans top 50 to prevent rate-limiting).")
    investigation.add_argument("--getcontact-token", metavar="TOKEN", help="Session token for direct GetContact tag retrieval (BYOT).")
    investigation.add_argument("--truecaller-token", metavar="TOKEN", help="Bearer token for direct Truecaller tag retrieval (BYOT).")

    # Output Options
    outputs = parser.add_argument_group("Export Options")
    outputs.add_argument("--json", metavar="FILE", help="Save the resulting intelligence graph as JSON.")
    outputs.add_argument("--csv", metavar="FILE", help="Save the resulting intelligence graph as CSV spreadsheet.")
    outputs.add_argument("--html", metavar="FILE", default="hamsa_graph.html", help="Save interactive HTML network graph (default: hamsa_graph.html).")
    outputs.add_argument("--report", metavar="FILE", help="Save executive summary and chronological timeline dossier (HTML or Markdown).")
    outputs.add_argument("--proxy", metavar="PROXY_URL", help="Optional HTTP/SOCKS proxy (e.g. http://127.0.0.1:8888).")
    outputs.add_argument("--tor", action="store_true", help="Route reconnaissance traffic through Tor SOCKS5 proxy (socks5://127.0.0.1:9050).")
    outputs.add_argument("--wayback", action="store_true", help="Passively verify targets against Wayback Machine before active checks.")
    outputs.add_argument("--neo4j", action="store_true", help="Persist knowledge graph in Neo4j cluster (requires NEO4J_URI/USER/PASSWORD).")

    # Continuous Surveillance & Alerting Options
    monitor = parser.add_argument_group("Continuous Surveillance & Alerting Options")
    monitor.add_argument("--watchlist-add", metavar="TARGET", help="Add a target identity to continuous surveillance watchlist.")
    monitor.add_argument("--watchlist-type", default="username", choices=["username", "email", "phone"], help="Target type for watchlist addition (default: username).")
    monitor.add_argument("--watchlist-list", action="store_true", help="List all targets registered in continuous surveillance watchlist.")
    monitor.add_argument("--watchlist-remove", metavar="TARGET", help="Remove a target from continuous surveillance watchlist.")
    monitor.add_argument("--check-watchlist", action="store_true", help="Execute an automated monitoring pass across all watchlist targets.")
    monitor.add_argument("--webhook", metavar="URL", help="Webhook endpoint (Discord, Slack, or Telegram) to alert on perimeter drift.")

    # Web Dashboard & Source Options
    web_opts = parser.add_argument_group("Web Dashboard & Source Options")
    web_opts.add_argument("--serve", action="store_true", help="Launch the embedded Hamsa Web App & REST API Server.")
    web_opts.add_argument("--port", type=int, default=8888, help="Port for the embedded web server (default: 8888, auto-switches if busy).")
    web_opts.add_argument("--host", default="0.0.0.0", help="Host address for the web server (default: 0.0.0.0).")
    web_opts.add_argument("--update-sources", action="store_true", help="Synchronize the latest 690+ website definitions from WhatsMyName.")

    return parser


async def main_async() -> int:
    parser = create_parser()
    args = parser.parse_args()

    if not args.no_banner:
        print(HAMSA_BANNER)

    orchestrator = Orchestrator()

    if args.list_plugins:
        print(f"{BOLD}Registered Hamsa Plugins:{RESET}\n")
        for p in orchestrator.list_plugins():
            print(f"  • {colorize(p['name'], CYAN)} (v{p['version']}) by {p['author']}")
            print(f"    Description: {p['description']}")
            print(f"    Handles: {', '.join(p['target_types'])}\n")
        return 0

    if args.update_sources:
        from hamsa.core.sources import SourceManager
        sm = SourceManager()
        count = sm.update_sources()
        if count > 0:
            log_success(f"Dynamic community database updated ({count} sites).")
        return 0

    if args.watchlist_add:
        from hamsa.core.monitor import WatchlistManager
        wm = WatchlistManager()
        entry = wm.add(args.watchlist_add, target_type=args.watchlist_type)
        log_success(f"Added target to continuous surveillance: {entry.value} [{entry.target_type.upper()}]")
        return 0

    if args.watchlist_list:
        from hamsa.core.monitor import WatchlistManager
        wm = WatchlistManager()
        items = wm.list_all()
        print(f"{BOLD}Continuous Surveillance Watchlist ({len(items)} subjects):{RESET}\n")
        if not items:
            print("  (No subjects registered. Add with --watchlist-add <target>)")
        for item in items:
            scanned_str = f" | Last Scanned: {item.last_scanned}" if item.last_scanned else ""
            print(f"  • {colorize(item.value, CYAN)} [{item.target_type.upper()}] (Added: {item.added_at}{scanned_str})")
        print()
        return 0

    if args.watchlist_remove:
        from hamsa.core.monitor import WatchlistManager
        wm = WatchlistManager()
        if wm.remove(args.watchlist_remove, target_type=args.watchlist_type):
            log_success(f"Removed '{args.watchlist_remove}' from continuous monitoring watchlist.")
        else:
            log_warn(f"Subject '{args.watchlist_remove}' was not found in watchlist.")
        return 0

    if args.check_watchlist:
        from hamsa.core.monitor import ScanDiffEngine, WatchlistManager, WebhookDispatcher
        import json

        wm = WatchlistManager()
        items = wm.list_all()
        if not items:
            log_warn("Surveillance watchlist is empty. Add subjects using --watchlist-add <TARGET>.")
            return 0

        log_info(f"Running automated surveillance cycle across {len(items)} watchlist subjects...")
        snapshot_dir = os.path.expanduser("~/.hamsa/snapshots")
        os.makedirs(snapshot_dir, exist_ok=True)

        for item in items:
            log_info(f"Checking subject: {item.value} ({item.target_type})...")
            t_type = TargetType.USERNAME
            if item.target_type == "email":
                t_type = TargetType.EMAIL
            elif item.target_type == "phone":
                t_type = TargetType.PHONE

            # Run targeted scan
            target_graph = await orchestrator.scan([(item.value, t_type)], max_depth=2, recursive=True)
            new_snapshot = target_graph.to_dict()

            snapshot_file = os.path.join(snapshot_dir, f"{item.target_type}_{item.value.replace('/', '_')}.json")
            old_snapshot = {}
            if os.path.exists(snapshot_file):
                try:
                    with open(snapshot_file, "r", encoding="utf-8") as f:
                        old_snapshot = json.load(f)
                except Exception:
                    old_snapshot = {}

            diff = ScanDiffEngine.compute_diff(old_snapshot, new_snapshot)
            wm.update_scanned(item.value, item.target_type)

            with open(snapshot_file, "w", encoding="utf-8") as f:
                json.dump(new_snapshot, f, indent=2, ensure_ascii=False)

            if diff["has_drift"]:
                log_warn(f"Perimeter drift detected for {item.value}! Drift Score: {diff['drift_score']}/100 (+{diff['total_added_nodes']} entities)")
                alert_text = ScanDiffEngine.format_alert_markdown(f"{item.value} ({item.target_type})", diff)
                print("\n" + alert_text + "\n")

                webhook_url = args.webhook or os.getenv("HAMSA_WEBHOOK")
                if webhook_url:
                    log_info(f"Dispatching threat alert to webhook...")
                    WebhookDispatcher.send(webhook_url, f"HAMSA Alert: {item.value}", alert_text, diff_score=diff["drift_score"])
            else:
                log_info(f"✓ {item.value}: No new perimeter drift observed.")

        log_success("Surveillance cycle completed successfully.")
        return 0

    if args.serve:
        from hamsa.web.server import run_server
        run_server(host=args.host, port=args.port)
        return 0

    # Configure backend and proxy
    if args.neo4j:
        os.environ["HAMSA_GRAPH_BACKEND"] = "neo4j"
        log_info("Engaging Neo4j Graph Persistence backend.")

    # Collect input targets
    targets_to_scan: List[Tuple[str, TargetType]] = []
    if args.username:
        targets_to_scan.append((args.username, TargetType.USERNAME))
    if args.email:
        targets_to_scan.append((args.email, TargetType.EMAIL))
    if args.phone:
        targets_to_scan.append((args.phone, TargetType.PHONE))
    if args.image:
        if not os.path.exists(args.image):
            log_error(f"Specified image file does not exist: {args.image}")
            return 1
        targets_to_scan.append((args.image, TargetType.IMAGE))

    if not targets_to_scan:
        log_warn("No target specified. Please provide at least one target (-u, -e, -p, -i).")
        parser.print_help()
        return 1

    log_info(f"Initiating OSINT correlation engine for {len(targets_to_scan)} target(s)...")

    context = {}
    if args.tor:
        context["proxy"] = "socks5://127.0.0.1:9050"
        log_info("Tor SOCKS5 circuit routing engaged (socks5://127.0.0.1:9050).")
    elif args.proxy:
        context["proxy"] = args.proxy
        log_info(f"Using proxy routing: {args.proxy}")

    if args.wayback:
        context["wayback"] = True
        log_info("Passive Wayback Machine archival verification enabled.")

    if args.all_sites:
        context["all_sites"] = True
        log_info("Username hunting: Unlocked full 690+ community platform database.")
    if args.getcontact_token:
        context["getcontact_token"] = args.getcontact_token
    if args.truecaller_token:
        context["truecaller_token"] = args.truecaller_token

    graph = await orchestrator.scan(
        targets_to_scan,
        context=context,
        max_depth=args.depth,
        recursive=(not args.no_recursive),
    )

    # Summary
    summary = graph.to_dict()["summary"]
    print()
    log_success(f"Investigation complete!")
    print(f"  {BOLD}Total Entity Nodes Discovered:{RESET} {colorize(str(summary['total_entities']), GREEN)}")
    print(f"  {BOLD}Total Relationship Edges:{RESET} {colorize(str(summary['total_relations']), CYAN)}")

    # Exporters
    if args.json:
        graph.export_json(args.json)
        log_success(f"Intelligence graph exported to JSON: {args.json}")

    if args.csv:
        graph.export_csv(args.csv)
        log_success(f"Intelligence graph exported to CSV: {args.csv}")

    if args.html:
        graph.export_html(args.html, title=f"Hamsa Investigation: {', '.join([t[0] for t in targets_to_scan])}")
        log_success(f"Interactive visual graph exported to HTML: {args.html}")

    if args.report:
        from hamsa.core.reporting import ReportGenerator
        reporter = ReportGenerator(graph)
        out_path = reporter.export(args.report, targets_to_scan)
        log_success(f"Forensic executive report exported: {out_path}")

    return 0


def main() -> None:
    try:
        sys.exit(asyncio.run(main_async()))
    except KeyboardInterrupt:
        print("\n[!] Operation cancelled by user.")
        sys.exit(130)


if __name__ == "__main__":
    main()
