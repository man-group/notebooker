
deleteReport = (delete_url) => {
    $('#deleteModal').modal({
        closable: true,
        onDeny() {
            return true;
        },
        onApprove() {
            $.ajax({
                type: 'POST',
                url: delete_url, // We get this from loading.html, which comes from flask
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
};

create_datatable = (result, readonly_mode) => {

    let columns = [
        {
            title: 'Title',
            name: 'title',
            data: 'report_title',
        }]

    let override_keys = new Set();
    for (let i=0; i<result.length; i++) {
        for (let key in result[i].overrides) {
            override_keys.add(key)
        }
    }
    for (let key of override_keys) {
        columns = columns.concat([{
            title: "Param: "+key,
            data: "overrides."+key,
            defaultContent: "",
            render: (data) => {
                if (typeof(data) === "object") {
                    return JSON.stringify(data, null, 2)
                }
                return data;
            },
        }])
    }

    columns = columns.concat([
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
        }])
    var usingScheduler = undefined;
    $.ajax({
        async: false,
        url: '/scheduler/health',
        success: () => {
            usingScheduler = true;
        },
        error: () => {
            usingScheduler = false;
        },
    });
    if (usingScheduler === true) {
        columns = columns.concat([
            {
                title: 'Scheduler Job',
                name: 'scheduler_job_id',
                data: 'scheduler_job_id',
                render: (url, type, row) => {
                    if (row.scheduler_job_id) {
                        return `<button onclick="location.href='/scheduler?id=${row.scheduler_job_id}'" class="ui button blue">Scheduler</button>`;
                    } else {
                        return '';
                    }
                }
            }
        ])
    }
    if (readonly_mode === "False") {
        columns = columns.concat([
            {
                title: 'Rerun',
                name: 'rerun_url',
                data: 'rerun_url',
                render: (url, type, row) => `<button onclick="rerunReport('${row.job_id}', '${url}')" `
                    + 'type="button" class="ui yellow centred button rerunButton">'
                    + '<i class="redo alternate icon"></i></button>',
            },
            {
                title: 'Delete',
                name: 'delete_url',
                data: 'delete_url',
                render: (url, type, row) => `<button onclick="deleteReport('${url}')" `
                    + 'type="button" class="ui button red deletebutton">'
                    + `<i class="trash icon"></i></button>`,
            }
        ])
    }
    let startTimeColumnIndex = 1 + override_keys.size + 1;
    const $resultsTable = $('#resultsTable');
    table = $resultsTable.DataTable({
        columns: columns,
        order: [[startTimeColumnIndex, 'desc']],
        "initComplete": function (settings, json) {
            $("#resultsTable_wrapper").wrap("<div class='scrolledTable'></div>");
        },
    });
    table.clear()
    table.rows.add(result);
    table.draw();
    $('#indexTableContainer').fadeIn();
}

load_data = (limit, report_name, readonly_mode) => {
    $.ajax({
        url: `/core/get_all_available_results?limit=${limit}&report_name=${report_name}`,
        dataType: 'json',
        success: (result) => {
            create_datatable(result, readonly_mode);
        },
        error: (jqXHR, textStatus, errorThrown) => {
            $('#failedLoad').fadeIn();
        },
    });
};


$(document).ready(() => {
    load_data(LIMIT, REPORT_NAME, READONLY_MODE);
});
