#!/usr/bin/env python3
"""CLI entry point for training dataset generator."""
import click

@click.command()
@click.option("--type", "infringement_type", required=True, help="Infringement type")
@click.option("--keyword", required=True, help="Search keyword for patent images")
@click.option("--registry", "registry_count", default=5, help="Number of registry images")
@click.option("--positive", "positive_count", default=20, help="Number of positive samples")
@click.option("--negative", "negative_count", default=20, help="Number of negative samples")
@click.option("--output", default="datasets", help="Output root directory")
def main(infringement_type, keyword, registry_count, positive_count, negative_count, output):
    """Generate training dataset for infringement detection."""
    from src.pipeline import Pipeline

    pipeline = Pipeline(output_root=output)
    pipeline.run(
        infringement_type=infringement_type,
        keyword=keyword,
        registry_count=registry_count,
        positive_count=positive_count,
        negative_count=negative_count,
    )

if __name__ == "__main__":
    main()
