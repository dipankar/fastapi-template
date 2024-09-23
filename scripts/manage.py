import click
import subprocess
import os

@click.group()
def cli():
    pass

@cli.command()
def run():
    """Run the FastAPI server"""
    subprocess.run(["uvicorn", "app.main:app", "--reload"])

@cli.command()
def test():
    """Run tests"""
    subprocess.run(["pytest"])

@cli.command()
@click.argument('message')
def make_migration(message):
    """Create a new migration"""
    subprocess.run(["alembic", "revision", "--autogenerate", "-m", message])

@cli.command()
def migrate():
    """Apply migrations"""
    subprocess.run(["alembic", "upgrade", "head"])

@cli.command()
def docker_up():
    """Start Docker containers"""
    subprocess.run(["docker-compose", "up", "-d"])

@cli.command()
def docker_down():
    """Stop Docker containers"""
    subprocess.run(["docker-compose", "down"])

if __name__ == "__main__":
    cli()