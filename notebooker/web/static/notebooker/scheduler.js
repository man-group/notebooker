var parser = require('cron-parser');

load_data = () => {
    $.ajax({
        url: `/scheduler/jobs`,
        dataType: 'json',
        success: (result) => {
            const table = $('#schedulerTable').DataTable();
            table.clear();
            table.rows.add(result);
            table.draw();
            $('#schedulerTableContainer').fadeIn();
            add_delete_callback();
        },
        error: (jqXHR, textStatus, errorThrown) => {
            $('#failedLoad').fadeIn();
        },
    });
};

function loadTemplateParameters(templateName) {
    $.ajax({
        url: '/get_report_parameters/' + templateName,
        dataType: 'json',
        success: (result) => {
            $('#notebookParameters').text(result.result);
        }
    })
}

function setScheduleModalMode(mode) {
    // mode should be "adding" or "modifying"
    if (mode === "adding") {
        $('#jobNameField').removeClass("disabled");
        $('#nbTemplateNameField').removeClass("disabled");
    } else {
        $('#jobNameField').addClass("disabled");
        $('#nbTemplateNameField').addClass("disabled");
    }
}

load_all_templates = () => {
    $.ajax({
        url: '/core/all_possible_templates',
        dataType: 'json',
        success: (result) => {
            var templates = Array();
            for (var key in result) {
                templates = templates.concat({"name": key, "value": key})
            }
            $('.selection.dropdown').dropdown({
                values: templates,
                onChange: function(value, text, $selectedItem) {
                    loadTemplateParameters(value);
                }
            });
        },
        error: (jqXHR, textStatus, errorThrown) => {
            $('#failedLoad').fadeIn();
        },
    })
};


$(document).ready(() => {
    $('#showScheduler').click(() => {
        setScheduleModalMode("adding");
        $('#schedulerModal').modal('show');
    });
    $('#cronScheduleText').on('propertychange input', function(event) {
        var valueChanged = false;
        // debugger;
        if (event.type=='propertychange') {
            valueChanged = event.originalEvent.propertyName=='value';
        } else {
            valueChanged = true;
        }
        if (valueChanged && event.target.value.length > 3) {
            try {
                var interval = parser.parseExpression(event.target.value);
                let cpo = $('#crontabParserOutput');
                cpo.text("Next schedule: " + interval.next().toString());
                cpo.removeClass("hidden");
                $('#scheduleForm').removeClass("error");
            } catch (e) {
                $('#crontabParserOutput').addClass("hidden");
                $('#validationErrorsSpan').text("Crontab Parsing " + e)
                $('#scheduleForm').addClass("error")
            }

        }
    });
    $('#schedulerTable').DataTable({
        columns: [
            {
                title: 'Report ID',
                name: 'id',
                data: 'id',
            },
            {
                title: 'Status',
                name: 'status',
                data: 'status',
            },
            {
                title: 'Last Successful Run',
                name: 'run_date',
                data: 'run_date',
                render: (dt) => {
                    const d = new Date(dt);
                    return d.toISOString().replace('T', ' ').slice(0, 19);
                },
            },
        ],
        order: [[0, 'asc']],
    });
    load_data();
    load_all_templates();
});
