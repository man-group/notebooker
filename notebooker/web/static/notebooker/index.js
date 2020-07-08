add_delete_callback = () => {
    $('.deletebutton').click((clicked) => {
        const to_delete = clicked.target.closest('button').id.split('_')[1];
        $('#deleteModal').modal({
            closable: true,
            onDeny() {
                return true;
            },
            onApprove() {
                $.ajax({
                    type: 'POST',
                    url: `/delete_report/${to_delete}`, // We get this from loading.html, which comes from flask
                    dataType: 'json',
                    success(data, status, request) {
                        if (data.status === 'error') {
                            $('#errorMsg').text(data.content);
                            $('#errorPopup').show();
                        } else {
                            window.location.reload();
                        }
                    },
                    error(xhr, error) {
                    },
                });
            },
        }).modal('show');
    });
};

load_data = (limit) => {
    $.ajax({
        url: `/core/get_all_available_results?limit=${limit}`,
        dataType: 'json',
        success: (result) => {
            const table = $('#resultsTable').DataTable();
            table.clear();
            table.rows.add(result);
            table.draw();
            $('#indexTableContainer').fadeIn();
            add_delete_callback();
        },
        error: (jqXHR, textStatus, errorThrown) => {
            $('#failedLoad').fadeIn();
        },
    });
};


$(document).ready(() => {
    $('#resultsTable').DataTable({
        columns: [
            {
                title: 'Title',
                name: 'title',
                data: 'report_title',
            },
            {
                title: 'Report Template Name',
                name: 'report_name',
                data: 'report_name',
            },
            {
                title: 'Status',
                name: 'status',
                data: 'status',
            },
            {
                title: 'Start Time',
                name: 'job_start_time',
                data: 'job_start_time',
                render: (dt) => {
                    const d = new Date(dt);
                    return d.toISOString().replace('T', ' ').slice(0, 19);
                },
            },
            {
                title: 'Completion Time',
                name: 'job_finish_time',
                data: 'job_finish_time',
                render: (dt) => {
                    if (dt) {
                        const d = new Date(dt);
                        return d.toISOString().replace('T', ' ').slice(0, 19);
                    }
                    return '';
                },
            },
            {
                title: 'Results',
                name: 'result_url',
                data: 'result_url',
                render: (url) => `<button onclick="location.href='${url}'" type="button" `
                        + 'class="ui button blue">Result</button>',
            },
            {
                title: 'PDF',
                name: 'pdf_url',
                data: 'pdf_url',
                render: (url, type, row) => {
                    if (row.generate_pdf_output) {
                        return `<button onclick="location.href='${url}'" type="button" `
                            + 'class="ui button green"><i class="download icon"></i></button>';
                    }
                    return '';
                },
            },
            {
                title: 'Rerun',
                name: 'rerun_url',
                data: 'rerun_url',
                render: (url, type, row) => `<button onclick="rerunReport('${row.job_id}', '${url}')" `
                           + 'type="button" class="ui yellow button rerunButton">'
                        + '<i class="redo alternate icon"></i>Rerun</button>',
            },
            {
                title: 'Delete',
                name: 'result_url',
                data: 'result_url',
                render: (url, type, row) => `${'<button type="button" class="ui button red deletebutton" '
                        + 'id="delete_'}${row.job_id}"> <i class="trash icon"></i>`,
            },
        ],
        order: [[3, 'desc']],
    });
    load_data(50);
});
