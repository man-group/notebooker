import json
import urllib

import mock
from flask import jsonify
from mock.mock import ANY


def test_run_report_json_parameters(flask_app, setup_workspace):
    with flask_app.test_client() as client:
        report_name = "fake/report"
        overrides = {"a": 1}
        report_title = "title"
        mailto = "abc@email.asdkj"
        error_mailto = "def@email.asdkj"
        mailfrom = "test@example.com"
        generate_pdf = True
        hide_code = True
        is_slideshow = True
        scheduler_job_id = "abc/123"
        email_subject = "Subject"
        payload = {
            "overrides": json.dumps(overrides),
            "report_title": report_title,
            "mailto": mailto,
            "error_mailto": error_mailto,
            "generate_pdf": generate_pdf,
            "hide_code": hide_code,
            "scheduler_job_id": scheduler_job_id,
            "is_slideshow": is_slideshow,
            "mailfrom": mailfrom,
            "email_subject": email_subject,
        }
        with mock.patch("notebooker.web.routes.report_execution.run_report_in_subprocess") as rr:
            rr.return_value = "fake_job_id"
            rv = client.post(f"/run_report_json/{report_name}?{urllib.parse.urlencode(payload)}")
            assert rv.data == jsonify({"id": "fake_job_id"}).data
            assert rv.status_code == 202, rv.data

            rr.assert_called_with(
                base_config=ANY,
                report_name=report_name,
                report_title=report_title,
                mailto=mailto,
                error_mailto=error_mailto,
                overrides=overrides,
                generate_pdf_output=generate_pdf,
                hide_code=hide_code,
                scheduler_job_id=scheduler_job_id,
                mailfrom=mailfrom,
                is_slideshow=is_slideshow,
                email_subject=email_subject,
            )


def test_run_report_doesnt_work_in_readonly_mode(flask_app_readonly, setup_workspace):
    with flask_app_readonly.test_client() as client:
        with mock.patch("notebooker.web.routes.report_execution.run_report_in_subprocess") as rr:
            rr.return_value = "fake_job_id"
            rv = client.post(f"/run_report_json/fake/report")
            assert rv.status_code == 404, rv.data
