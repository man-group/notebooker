from pathlib import Path
from click.testing import CliRunner

from notebooker.utils.template_testing import regression_test


def test_regression_testing():
    from notebooker import notebook_templates_example
    f = Path(notebook_templates_example.__file__).parent / "sample"
    runner = CliRunner()
    result = runner.invoke(regression_test, ["--template-dir", f])
    assert not result.exception, result.output
    assert result.exit_code == 0

