from logging import getLogger

import click

from notebooker.utils.conversion import generate_py_from_ipynb

logger = getLogger(__name__)


@click.command()
@click.argument("ipynb_paths", nargs=-1)
@click.option("--output-dir", default=".")
def main(ipynb_paths, output_dir):
    for path in ipynb_paths:
        logger.info("Converting %s", path)
        generate_py_from_ipynb(path, output_dir=output_dir)


if __name__ == "__main__":
    main()
