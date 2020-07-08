$(document).ready(() => {
    $('#run-check-form').submit(function () {
        const form = $(this);
        $('#runReportButton').removeClass('active').addClass('disabled');
        $('.message').hide();
        $('#parametersDimmer').show();
        const reportName = $('input[name="report_name"]').val();
        $.ajax({
            type: 'POST',
            url: `/run_report/${reportName}`,
            data: form.serialize(),
            success(data, status, request) {
                if (data.status === 'Failed') {
                    $('#errorMsg').text(data.content);
                    $('#errorPopup').show();
                    $('#runReportButton').removeClass('disabled').addClass('active');
                    $('#parametersDimmer').hide();
                } else {
                    window.location.href = `/results/${reportName}/${data.id}`;
                }
            },
            error(jqXHR, textStatus, errorThrown) {
                $('#errorMsg').text(`${jqXHR.status} ${textStatus} ${errorThrown}`);
                $('#errorPopup').show();
                $('#runReportButton').removeClass('disabled').addClass('active');
                $('#parametersDimmer').hide();
            },
        });
        return false;
    });
});
