from pathlib import Path
from click.testing import CliRunner

from notebooker.utils.template_testing import sanity_check


def test_sanity_checking():
    from notebooker import notebook_templates_example

    f = Path(notebook_templates_example.__file__).parent / "sample"
    runner = CliRunner()
    result = runner.invoke(sanity_check, ["--template-dir", f])
    assert not result.exception, result.output
    assert result.exit_code == 0
