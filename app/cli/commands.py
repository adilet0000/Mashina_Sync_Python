import logging
from typing import Annotated

import typer

from app.config import get_settings
from app.config.providers import get_provider_config, list_provider_configs
from app.db.health import check_catalog_database
from app.db.reflection import inspect_catalog_tables
from app.dto import SyncResult
from app.repositories.catalog_listings import CatalogWritesDisabledError
from app.services import SyncService, SyncTargetError
from app.utils import configure_logging

app = typer.Typer(
    help="Mashina.kg provider-to-catalog sync CLI.",
    no_args_is_help=True,
)

logger = logging.getLogger(__name__)


def _bootstrap() -> None:
    settings = get_settings()
    configure_logging(settings)
    logger.debug("app_env=%s sync_target=%s", settings.app_env, settings.sync_target)


def _exit_if_sync_error(exc: Exception) -> None:
    typer.echo(f"ERROR: {exc}")
    raise typer.Exit(code=1) from exc


def _print_sync_result(result: SyncResult) -> None:
    for line in result.to_lines():
        typer.echo(line)


@app.command()
def healthcheck() -> None:
    """Check catalog DB connectivity with a read-only SELECT 1."""

    _bootstrap()
    settings = get_settings()
    result = check_catalog_database(settings)
    status = "OK" if result.ok else "SKIPPED" if not result.configured else "FAILED"
    typer.echo(f"catalog: {status} - {result.message}")
    if not result.ok:
        raise typer.Exit(code=1)


@app.command()
def inspect_db() -> None:
    """Inspect required catalog tables without writing to DB."""

    _bootstrap()
    settings = get_settings()
    result = inspect_catalog_tables(settings)
    typer.echo(f"catalog inspection: {'OK' if result.ok else 'FAILED'} - {result.message}")
    for table_status in result.tables:
        marker = "OK" if table_status.exists else "MISSING"
        typer.echo(f"{table_status.table_name}: {marker}")
    if not result.ok:
        raise typer.Exit(code=1)


@app.command()
def list_providers() -> None:
    """List known providers and provider-specific env configuration status."""

    _bootstrap()
    settings = get_settings()
    for provider_config in list_provider_configs():
        user_id = settings.catalog_user_id_for_provider(provider_config.key)
        phone_count = len(settings.phones_for_provider(provider_config.key))
        legacy = provider_config.legacy_service or "-"
        typer.echo(
            f"{provider_config.key}: name={provider_config.display_name} "
            f"legacy={legacy} user_id={'set' if user_id is not None else 'missing'} "
            f"phones={phone_count}"
        )


@app.command()
def sync(
    provider: Annotated[
        str,
        typer.Option("--provider", "-p", help="Provider key, for example autohub or autoland."),
    ],
    dry_run: Annotated[
        bool | None,
        typer.Option(
            "--dry-run/--no-dry-run",
            help="Preview actions without writing. Defaults to SYNC_DRY_RUN=1.",
        ),
    ] = None,
    limit: Annotated[
        int | None,
        typer.Option("--limit", min=1, help="Limit provider records for a test run."),
    ] = None,
    verify: Annotated[
        bool,
        typer.Option("--verify", help="Verify affected rows after a real write run."),
    ] = False,
    debug_record: Annotated[
        str | None,
        typer.Option("--debug-record", help="Show planned changes for one provider external_id."),
    ] = None,
) -> None:
    """Run one provider sync against the catalog DB target."""

    _bootstrap()
    try:
        get_provider_config(provider)
        result = SyncService(get_settings()).sync_provider(
            provider,
            dry_run=dry_run,
            limit=limit,
            verify=verify,
            debug_record=debug_record,
        )
    except (CatalogWritesDisabledError, SyncTargetError, ValueError) as exc:
        _exit_if_sync_error(exc)
    _print_sync_result(result)
    if not result.ok:
        raise typer.Exit(code=1)


@app.command()
def sync_all(
    dry_run: Annotated[
        bool | None,
        typer.Option(
            "--dry-run/--no-dry-run",
            help="Preview actions without writing. Defaults to SYNC_DRY_RUN=1.",
        ),
    ] = None,
    limit: Annotated[
        int | None,
        typer.Option("--limit", min=1, help="Limit records per provider for a test run."),
    ] = None,
    verify: Annotated[
        bool,
        typer.Option("--verify", help="Verify affected rows after a real write run."),
    ] = False,
) -> None:
    """Run all implemented provider syncs against the catalog DB target."""

    _bootstrap()
    try:
        results = SyncService(get_settings()).sync_all(dry_run=dry_run, limit=limit, verify=verify)
    except (CatalogWritesDisabledError, SyncTargetError, ValueError) as exc:
        _exit_if_sync_error(exc)

    failed = False
    for index, result in enumerate(results):
        if index:
            typer.echo("")
        _print_sync_result(result)
        failed = failed or not result.ok
    if failed:
        raise typer.Exit(code=1)
