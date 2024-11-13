#!/usr/bin/env python3
import os
import subprocess
import time
from pathlib import Path
from typing import List, Tuple

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.markdown import Markdown

console = Console()


def print_summary(results: dict) -> None:
    """Print a summary table of the conversion results."""
    table = Table(title="Conversion Summary")
    table.add_column("Language", style="cyan")
    table.add_column("Files Found", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Output File", style="blue")

    for lang, data in results.items():
        table.add_row(
            lang,
            str(len(data['files'])),
            "✓ Success" if data['success'] else "✗ Failed",
            str(data['output']) if data['output'] else "N/A"
        )

    console.print("\n", table, "\n")


def get_markdown_files(directory: Path, language: str) -> List[Path]:
    """Get all markdown files for a specific language, sorted by filename."""
    files = sorted(directory.glob(f'*.{language}.md'))
    if files:
        console.print(f"\n[cyan]Found files for {language}:[/cyan]")
        for f in files:
            console.print(f"  - {f.name}")
    return files


def display_markdown_content(file_path: Path) -> None:
    """Display markdown content with syntax highlighting."""
    content = file_path.read_text(encoding='utf-8')
    console.print(Panel(
        Syntax(content, "markdown", theme="monokai", line_numbers=True),
        title=f"[yellow]Content of {file_path.name}[/yellow]",
        border_style="blue"
    ))


def create_temp_combined_file(files: List[Path], output_file: Path, preview: bool = False) -> None:
    """Combine markdown files with proper spacing and headers."""
    console.print(f"\n[yellow]Combining {len(files)} files into temporary file: {output_file}[/yellow]")

    combined_content = []
    with output_file.open('w', encoding='utf-8') as outfile:
        for i, file in enumerate(files):
            console.print(f"  Processing: {file.name}")
            if i > 0:
                outfile.write('\n\\newpage\n\n')
                combined_content.append('\n\\newpage\n\n')

            content = file.read_text(encoding='utf-8')
            outfile.write(content)
            outfile.write('\n\n')
            combined_content.append(content)
            combined_content.append('\n\n')

    console.print(f"[green]✓[/green] Combined file created: {output_file}")

    if preview:
        display_markdown_content(output_file)


def run_pandoc_verbose(cmd: List[str]) -> Tuple[bool, str]:
    """Run pandoc with detailed error capturing."""
    verbose_cmd = cmd.copy()
    verbose_cmd.insert(1, '--verbose')

    try:
        result = subprocess.run(
            verbose_cmd,
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode == 0:
            return True, result.stderr

        error_msg = f"Exit code: {result.returncode}\n"
        error_msg += "STDOUT:\n" + result.stdout + "\n"
        error_msg += "STDERR:\n" + result.stderr
        return False, error_msg

    except Exception as e:
        return False, str(e)


def convert_to_pdf(input_file: Path, output_file: Path, language: str) -> None:
    """Convert the combined markdown file to PDF using pandoc with enhanced error handling."""
    console.print(f"\n[yellow]Converting to PDF: {output_file}[/yellow]")

    if not input_file.exists():
        raise click.ClickException(f"Input file not found: {input_file}")

    if input_file.stat().st_size == 0:
        raise click.ClickException(f"Input file is empty: {input_file}")

    cmd = [
        'pandoc',
        str(input_file),
        '-o', str(output_file),
        '--pdf-engine=xelatex',
        '--pdf-engine-opt=-shell-escape',
        '--toc',
        '--toc-depth=3',
        '--variable', 'papersize=a4',
        '--variable', 'fontsize=11pt',
        '--variable', 'geometry:margin=2.5cm',
        '--variable', 'links-as-notes=true',
        '--variable', 'mainfont=DejaVu Sans',
        '--variable', 'monofont=DejaVu Sans Mono',
        '-f', 'markdown+raw_tex',
    ]

    lang_settings = {
        'de': ['--variable', 'lang=de',
               '--variable', 'babel-lang=german'],
        'en': ['--variable', 'lang=en',
               '--variable', 'babel-lang=english']
    }

    if language in lang_settings:
        cmd.extend(lang_settings[language])
        console.print(f"  Using language settings for: {language}")

    console.print("  Running pandoc with options:", " ".join(cmd))

    start_time = time.time()
    success, output = run_pandoc_verbose(cmd)
    duration = time.time() - start_time

    if success:
        console.print(f"[green]✓[/green] PDF created successfully in {duration:.1f} seconds")
        if output:
            console.print("[yellow]Pandoc messages:[/yellow]")
            console.print(output)
    else:
        console.print("[red]Error creating PDF[/red]")
        console.print(Panel(output, title="Pandoc Error Details", border_style="red"))

        console.print("\n[yellow]Troubleshooting suggestions:[/yellow]")
        console.print("1. Check if all required LaTeX packages are installed:")
        console.print("   sudo apt-get install texlive-xetex texlive-fonts-recommended texlive-lang-german")
        console.print("2. Verify markdown syntax in the input files")
        console.print("3. Check for special characters or encoding issues")
        console.print("4. Ensure all referenced images or files exist")

        raise click.ClickException("PDF conversion failed")



class PathPath(click.Path):
    """Custom path type that returns a Path object."""

    def convert(self, value, param, ctx):
        return Path(super().convert(value, param, ctx))


@click.command()
@click.argument('manual_dir',
                type=PathPath(exists=True, file_okay=False, dir_okay=True, resolve_path=True))
@click.option('--languages', '-l',
              default='en,de',
              help='Comma-separated list of languages')
@click.option('--output', '-o',
              type=PathPath(file_okay=False, dir_okay=True),
              help='Output directory for PDF files (defaults to manual directory)')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--preview', '-p', is_flag=True, help='Preview combined markdown content')
@click.option('--keep-temp', '-k', is_flag=True, help='Keep temporary combined markdown files')
def create_manual(
        manual_dir: Path,
        languages: str,
        output: Path | None,
        verbose: bool,
        preview: bool,
        keep_temp: bool
):
    """
    Create PDF manuals from markdown files for specified languages.
    Files should be named like: 00-index.en.md, 00-index.de.md, etc.
    """
    console.print(Panel(
        "[bold blue]PDF Manual Generator[/bold blue]\n"
        f"Source directory: [cyan]{manual_dir}[/cyan]\n"
        f"Languages: [cyan]{languages}[/cyan]\n"
        f"Preview: [cyan]{'Yes' if preview else 'No'}[/cyan]\n"
        f"Keep temp files: [cyan]{'Yes' if keep_temp else 'No'}[/cyan]"
    ))

    output_dir = output or manual_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"\nOutput directory: [cyan]{output_dir}[/cyan]")

    results = {}
    lang_list = languages.split(',')

    with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
    ) as progress:
        for lang in lang_list:
            task_id = progress.add_task(f"Processing {lang} manual...", total=None)

            files = get_markdown_files(manual_dir, lang)
            if not files:
                progress.update(task_id, description=f"[yellow]No markdown files found for language: {lang}")
                results[lang] = {'files': [], 'success': False, 'output': None}
                continue

            temp_md = manual_dir / f'combined_{lang}.md'
            output_pdf = output_dir / f'manual_{lang}.pdf'

            try:
                create_temp_combined_file(files, temp_md, preview)
                convert_to_pdf(temp_md, output_pdf, lang)
                progress.update(task_id, description=f"[green]Successfully created {output_pdf}")
                results[lang] = {'files': files, 'success': True, 'output': output_pdf}
            except Exception as e:
                console.print(f"[red]Error:[/red] {str(e)}")
                progress.update(task_id, description=f"[red]Failed to create {lang} manual")
                results[lang] = {'files': files, 'success': False, 'output': None}
            finally:
                if temp_md.exists() and not keep_temp:
                    if verbose:
                        console.print(f"Cleaning up temporary file: {temp_md}")
                    temp_md.unlink()

    print_summary(results)
    console.print("[bold green]✓[/bold green] Manual creation completed!")


if __name__ == "__main__":
    create_manual()