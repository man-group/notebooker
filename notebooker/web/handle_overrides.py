from __future__ import unicode_literals

import ast
import json
import os
import pickle
import subprocess
import sys
import tempfile
from logging import getLogger
from typing import Any, AnyStr, Dict, List, Tuple, Union

import click

logger = getLogger(__name__)


def _handle_overrides_safe(
    raw_python: AnyStr, output_path: AnyStr
) -> Dict[AnyStr, Union[Dict[AnyStr, Any], List[AnyStr]]]:
    """
    This function executes the given python (in "overrides") and returns the
    evaluated variables as a dictionary. Problems are returned as "issues" in a list.

    Warning
    -------
    You may want to disable this behaviour if you do not have an authorisation layer blocking untrusted webapp access.
    """
    issues = []
    result = {"overrides": {}, "issues": issues}
    logger.info("Parsing the following as raw python:\n%s", raw_python)
    try:
        # Parse the python input as a Abstract Syntax Tree (this is what python itself does)
        parsed_module = ast.parse(raw_python)
        # Figure out what each node of the tree is doing (i.e. assigning, expression, etc)
        nodes = ast.iter_child_nodes(parsed_module)
        # Execute the code blindly. We trust the users (just about...) and are doing this in a safe-ish environment.
        exec(compile(parsed_module, filename="<ast>", mode="exec"))

        # Now, iterate through the nodes, figure out what was assigned, and add it to the 'overrides' dict.
        for node in nodes:
            if isinstance(node, ast.Assign):
                targets = [_.id for _ in node.targets]
                logger.info("Found an assignment to: {}".format(", ".join(targets)))
                for target in targets:
                    value = locals()[target]
                    result["overrides"][target] = value
                    try:
                        json.dumps(result["overrides"])  # Test that we can JSON serialise this - required by papermill
                    except TypeError as te:
                        issues.append(
                            'Could not JSON serialise a parameter ("{}") - this must be serialisable so that '
                            "we can execute the notebook with it! (Error: {}, Value: {})".format(target, str(te), value)
                        )
            elif isinstance(node, ast.Expr):
                issues.append(
                    "Found an expression that did nothing! It has a value of type: {}".format(type(node.value))
                )
    except Exception as e:
        issues.append("An error was encountered: {}".format(str(e)))

    if not issues:
        try:
            with open(output_path, "wb") as f:
                logger.info("Dumping to %s: %s", output_path, result)
                pickle.dump(json.dumps(result), f)
            return result
        except TypeError as e:
            issues.append(
                "Could not pickle: {}. All input must be picklable (sorry!). " "Error: {}".format(str(result), str(e))
            )
    if issues:
        with open(output_path, "wb") as f:
            result = {"overrides": {}, "issues": issues}
            logger.info("Dumping to %s: %s", output_path, result)
            pickle.dump(json.dumps(result), f)
    return result


def handle_overrides(overrides_string: AnyStr, issues: List[AnyStr]) -> Tuple[Dict[AnyStr, Any]]:
    override_dict = {}
    if overrides_string.strip():
        tmp_file = tempfile.mktemp()
        try:
            subprocess.check_output(
                [sys.executable, "-m", __name__, "--overrides", overrides_string, "--output", tmp_file]
            )
            with open(tmp_file, "rb") as f:
                output_dict = json.loads(pickle.load(f))
            logger.info("Got %s from pickle", output_dict)
            override_dict, _issues = output_dict["overrides"], output_dict["issues"]
            issues.extend(_issues)
        except subprocess.CalledProcessError as cpe:
            issues.append(str(cpe.output))
        finally:
            os.remove(tmp_file)
    return override_dict


@click.command()
@click.option("--overrides")
@click.option("--output")
def main(overrides, output):
    return _handle_overrides_safe(overrides, output)


if __name__ == "__main__":
    main()
