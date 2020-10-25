import json
import os
from typing import AnyStr, List, Optional

from notebooker.constants import EMAIL_SPACE_ERR_MSG, FORBIDDEN_CHAR_ERR_MSG, FORBIDDEN_INPUT_CHARS


def _check_bad_chars(s, issues):
    # Checks from a set of forbidden characters
    if any(forbidden in s for forbidden in FORBIDDEN_INPUT_CHARS):
        issues.append(FORBIDDEN_CHAR_ERR_MSG.format(s, FORBIDDEN_INPUT_CHARS))


def convert_report_name_url_to_path(report_name: AnyStr) -> AnyStr:
    # We expect the /run_report/path/to/file URL to resolve to a template under /templates/path/to/file.
    return report_name.replace("/", os.sep) if isinstance(report_name, str) else report_name


def convert_report_name_path_to_url(report_name: AnyStr) -> AnyStr:
    # We expect the /run_report/path/to/file URL to resolve to a template under /templates/path/to/file.
    return report_name.replace(os.sep, "/") if isinstance(report_name, str) else report_name


def json_to_python(json_candidate: AnyStr) -> Optional[AnyStr]:
    if not json_candidate:
        return None
    val_dict = json.loads(json_candidate)
    out_s = []
    for var_name in sorted(val_dict.keys()):
        value = val_dict[var_name]
        if isinstance(value, (str, bytes)):
            out_s.append("{} = '{}'".format(var_name, value))
        else:
            out_s.append("{} = {}".format(var_name, value))
    return "\n".join(out_s)


def validate_mailto(mailto: AnyStr, issues: List[AnyStr]) -> AnyStr:
    if not mailto:
        return ""
    mailto = mailto.strip()
    if any(c.isspace() for c in mailto):
        issues.append(EMAIL_SPACE_ERR_MSG)
    _check_bad_chars(mailto, issues)
    return mailto


def validate_title(title: AnyStr, issues: List[AnyStr]) -> AnyStr:
    out_s = title.strip()
    _check_bad_chars(out_s, issues)
    return out_s


def validate_generate_pdf_output(generate_pdf_output: AnyStr, issues: List[AnyStr]) -> bool:
    return bool(generate_pdf_output)
