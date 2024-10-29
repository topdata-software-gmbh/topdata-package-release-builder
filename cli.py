import click
from rich.console import Console

console = Console()

@click.group()
def main():
    """Shopware 6 Plugin Builder CLI"""
    pass

if __name__ == '__main__':
    main()
