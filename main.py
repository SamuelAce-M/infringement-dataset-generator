#!/usr/bin/env python3
"""CLI application for infringement training dataset generation."""
import click


@click.group()
def main():
    """Build and validate infringement training datasets."""


@main.command()
@click.option("--type", "infringement_type", required=True, help="Infringement type")
@click.option(
    "--registry",
    nargs=2,
    required=True,
    metavar="MODE VALUE",
    help="Registry source: file <manifest.csv> or search <keyword>",
)
@click.option("--negative-source", default=None, help="Negative sample manifest")
@click.option("--registry-count", default=5, help="Number of registry images")
@click.option("--positive", "positive_count", default=20, help="Number of positive samples")
@click.option("--negative", "negative_count", default=20, help="Number of negative samples")
@click.option("--output", default="datasets", help="Output root directory")
@click.option("--allow-placeholder", is_flag=True, help="Enable fixture placeholders for tests/demos")
def generate(
    infringement_type,
    registry,
    negative_source,
    registry_count,
    positive_count,
    negative_count,
    output,
    allow_placeholder,
):
    """Generate a training dataset."""
    from src.pipeline import Pipeline

    registry_mode, registry_value = registry
    pipeline = Pipeline(output_root=output)
    pipeline.run(
        infringement_type=infringement_type,
        registry_mode=registry_mode,
        registry_value=registry_value,
        negative_source=negative_source,
        registry_count=registry_count,
        positive_count=positive_count,
        negative_count=negative_count,
        allow_placeholder=allow_placeholder,
    )


@main.command("prepare-manifests")
@click.option("--registry-dir", required=True, help="Directory containing patent_*.png files")
@click.option("--negative-dir", required=True, help="Directory containing negative_*.png files")
@click.option("--registry-output", required=True, help="Output registry manifest CSV")
@click.option("--negative-output", required=True, help="Output negative manifest CSV")
@click.option(
    "--negative-similarity",
    default=0.20,
    type=float,
    help="Default similarity score for imported negative samples",
)
def prepare_manifests(
    registry_dir,
    negative_dir,
    registry_output,
    negative_output,
    negative_similarity,
):
    """Build local manifests from existing image directories."""
    from src.manifest import build_negative_manifest, build_registry_manifest

    registry_count = build_registry_manifest(registry_dir, registry_output)
    negative_count = build_negative_manifest(
        negative_dir,
        negative_output,
        default_similarity=negative_similarity,
    )
    click.echo(f"Registry rows: {registry_count} -> {registry_output}")
    click.echo(f"Negative rows: {negative_count} -> {negative_output}")


@main.command()
@click.option("--root", default="datasets", help="Dataset root directory")
def validate(root):
    """Validate a generated dataset."""
    from src.validation import validate_dataset

    report = validate_dataset(root)
    click.echo(f"Dataset: {report.dataset_root}")
    click.echo(f"Rows: {report.total_rows}")
    click.echo(f"Labels: {report.label_counts}")
    click.echo(f"Bands: {report.band_counts}")

    for warning in report.warnings:
        click.echo(f"WARNING: {warning}")
    for error in report.errors:
        click.echo(f"ERROR: {error}")

    raise click.exceptions.Exit(0 if report.ok else 1)


@main.command("source-spike")
@click.option("--output", default="reports/source_spike.json", help="JSON report path")
@click.option("--timeout", default=10.0, type=float, help="HTTP timeout in seconds")
def source_spike(output, timeout):
    """Probe candidate online patent/design sources."""
    from src.source_spike import run_source_spike, write_source_spike_report

    results = run_source_spike(timeout=timeout)
    write_source_spike_report(results, output)

    for result in results:
        status = "OK" if result.ok else "FAIL"
        detail = result.status_code if result.status_code is not None else result.error
        click.echo(f"{status}: {result.name} ({detail})")
    click.echo(f"Report: {output}")


@main.command("wipo-inspect")
@click.option("--output", default="reports/wipo_inspect.json", help="JSON report path")
@click.option("--timeout", default=10.0, type=float, help="HTTP timeout in seconds")
def wipo_inspect(output, timeout):
    """Inspect WIPO DesignDB frontend wiring for adapter development."""
    from src.wipo import inspect_wipo, write_wipo_inspect_report

    report = inspect_wipo(timeout=timeout)
    write_wipo_inspect_report(report, output)

    status = "OK" if report.ok else "FAIL"
    click.echo(f"{status}: WIPO DesignDB ({report.status_code or report.error})")
    click.echo(f"qk present: {report.qk_present}")
    click.echo(f"endpoints: {len(report.endpoints)}")
    click.echo(f"search fields: {len(report.search_fields)}")
    for warning in report.usage_warnings:
        click.echo(f"WARNING: {warning}")
    click.echo(f"Report: {output}")


@main.command("wipo-export")
@click.option("--keyword", required=True, help="Search keyword to export from WIPO")
@click.option("--output", required=True, help="Output registry manifest CSV")
@click.option("--report", default="reports/wipo_export.json", help="JSON export report path")
@click.option("--limit", default=5, help="Maximum records to export")
@click.option("--timeout", default=10.0, type=float, help="HTTP timeout in seconds")
@click.option(
    "--acknowledge-limits",
    is_flag=True,
    help="Acknowledge WIPO UI restrictions before attempting experimental export",
)
def wipo_export(keyword, output, report, limit, timeout, acknowledge_limits):
    """Experimental WIPO URL manifest export."""
    from src.wipo_export import export_wipo_manifest, write_wipo_export_report

    result = export_wipo_manifest(
        keyword=keyword,
        output_manifest=output,
        limit=limit,
        timeout=timeout,
        acknowledge_limits=acknowledge_limits,
    )
    write_wipo_export_report(result, report)

    if result.ok:
        click.echo(f"Exported {result.exported_count} records -> {output}")
        raise click.exceptions.Exit(0)

    click.echo("WIPO export blocked:")
    for blocker in result.blockers:
        click.echo(f"- {blocker}")
    click.echo(f"Manifest: {output}")
    click.echo(f"Report: {report}")
    raise click.exceptions.Exit(2)


if __name__ == "__main__":
    main()
