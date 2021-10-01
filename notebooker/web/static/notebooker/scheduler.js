var parser = require('cron-parser');
var schedulerModalState = "Add";

addCallbacks = () => {
    $('#schedulerTable').on('click', 'tbody tr', handleRowClick);
    $('.deleteScheduleButton').click((clicked) => {
        const deleteHref = clicked.target.closest('button').dataset.href;
        $('#deleteModal').modal({
            closable: true,
            onDeny() {
                return true;
            },
            onApprove() {
                $.ajax({
                    type: 'DELETE',
                    url: deleteHref,
                    dataType: 'json',
                    success(data, status, request) {
                        if (data.status === 'error') {
                            $('#errorMsg').text(data.content);
                            $('#errorPopup').show();
                        } else {
                            location.reload();
                        }
                    },
                    error(xhr, error) {
                    },
                });
            },
        }).modal('show');
    });

}

load_data = (callback) => {
    $.ajax({
        url: `/scheduler/jobs`,
        dataType: 'json',
        success: (result) => {
            const table = $('#schedulerTable').DataTable();
            table.clear();
            table.rows.add(result);
            table.draw();
            $('#schedulerTableContainer').fadeIn();
            addCallbacks();
            callback();
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
    // mode should be "Add" or "Modify"
    $('#scheduleAction').text(mode);
    schedulerModalState = mode;
    if (mode === "Add") {
        $('#jobTitleField').removeClass("disabled");
        $('#nbTemplateNameField').removeClass("disabled");
    } else {
        $('#jobTitleField').addClass("disabled");
        $('#nbTemplateNameField').addClass("disabled");
    }
}

load_all_templates = (callback) => {
    $.ajax({
        url: '/core/all_possible_templates_flattened',
        dataType: 'json',
        success: (result) => {
            let templates = Array();
            for (let i = 0; i < result.result.length; i++) {
                let value = result.result[i]
                templates = templates.concat({"name": value, "value": value})
            }
            $('.selection.dropdown').dropdown({
                values: templates,
                onChange: function(value, text, $selectedItem) {
                    loadTemplateParameters(value);
                }
            });
            callback();
        },
        error: (jqXHR, textStatus, errorThrown) => {
            $('#failedLoad').fadeIn();
        },
    })
};

function showSelection() {
    let params = new URL(window.location.href).searchParams;
    if (params.get('id')) {
        let table = $('#schedulerTable').DataTable();
        for (let row of table.rows().data().toArray()) {
            if (row.id == params.get('id')) {
                modifySchedulerModal(row);
                break;
            }
        }
    }
}

function removeSchedulerIdFromURL() {
    let url = new URL(window.location.href);
    url.searchParams.delete('id');
    history.replaceState({}, null, url.toString());
}

function showSchedulerModal() {
    $('#schedulerModal').modal({
        closable: true,
        onHidden() {
            removeSchedulerIdFromURL()
        }
    }).modal('show');
}

function modifySchedulerModal(row) {
    let url = new URL(window.location.href);
    url.searchParams.set('id', row.id);
    history.replaceState({}, null, url.toString());
    $('#scheduleForm').form('set values',
        {
            jobTitle: row.params.report_title,
            templateToExecute: row.params.report_name,
            overrides: row.params.overrides,
            hide_code: row.params.hide_code,
            generate_pdf: row.params.generate_pdf,
            mailto: row.params.mailto,
            cronSchedule: row.cron_schedule,
        }
    );
    setScheduleModalMode("Modify");
    showSchedulerModal();
}

function handleRowClick(e) {
    if ($(e.target).closest('button').length) {
        return;
    }
    let table = $('#schedulerTable').DataTable();
    let row = table.row($(this)).data();
    modifySchedulerModal(row);
}

function handleAddButtonClick() {
    $('#scheduleForm').form('set values',
        {
            jobTitle: "",
            templateToExecute: "",
            overrides: "",
            hide_code: "",
            generate_pdf: "",
            mailto: "",
            cronSchedule: "",
        }
    );
    setScheduleModalMode("Add");
    showSchedulerModal();
}


function handleFormError(errorMsg) {
    let ul = $('#formErrorMessage ul');
    ul.empty();
    ul.append(`<li>${errorMsg}</li>`);
    $('#scheduleForm').addClass('error');
}

function handleCrontabError(errorMsg) {
    let cpo = $('#crontabParserOutput');
    cpo.addClass("red");
    cpo.text("Parsing " + errorMsg)
    cpo.removeClass(["yellow", "hidden"]);
    $('#schedulerSubmitButton').addClass("disabled");
}

$(document).ready(() => {
    $('.ui.checkbox').checkbox();
    $('#showSchedulerButton').click(handleAddButtonClick);
    $('#cronScheduleText').on('propertychange input', function(event) {
        var valueChanged = false;
        // debugger;
        if (event.type=='propertychange') {
            valueChanged = event.originalEvent.propertyName=='value';
        } else {
            valueChanged = true;
        }
        if (valueChanged && event.target.value.length > 3) {
            if (event.target.value.trim().split(' ').length !== 5) {
                handleCrontabError('Error: crontab must have 5 parts: minute/hour/day/month/day of week');
                return
            }
            try {
                var interval = parser.parseExpression(event.target.value);
                let cpo = $('#crontabParserOutput');
                cpo.text("Next schedule: " + interval.next().toString());
                cpo.addClass("yellow");
                cpo.removeClass(["red", "hidden"]);
                $('#scheduleForm').removeClass("error");
                $('#schedulerSubmitButton').removeClass("disabled");
            } catch (e) {
                handleCrontabError(e)
            }

        }
    });
    var the_form = $('#scheduleForm');
    the_form.form({
        fields: {
            jobTitle: {
                identifier: 'jobTitle',
                rules: [
                    {
                        type: 'empty',
                        prompt: 'Please enter a unique name for your scheduled job.'
                    }
                ]
            },
            templateToExecute: {
                identifier: 'templateToExecute',
                rules: [
                    {
                        type: 'empty',
                        prompt: 'Please select a template to be executed.'
                    }
                ]
            },
            cronSchedule: {
                identifier: 'cronSchedule',
                rules: [
                    {
                        type: 'empty',
                        prompt: 'Please add a valid cron schedule.'
                    }
                ]
            },
        },
        onSuccess: function(event) {
            const form = $(this);
            const formObj = form.serializeArray().reduce(function(obj, item) {
                obj[item.name] = item.value;
                return obj;
            }, {});
            let urlAction = schedulerModalState === "Add" ? "create" : "update";
            $.ajax({
                type: 'POST',
                url: `/scheduler/${urlAction}/${formObj.templateToExecute}`,
                data: {
                    report_title: formObj.jobTitle,
                    report_name: formObj.templateToExecute,
                    overrides: formObj.overrides,
                    cron_schedule: formObj.cronSchedule,
                    mailto: formObj.mailto,
                    generate_pdf: formObj.generate_pdf,
                    hide_code: formObj.hide_code,
                },
                success(data, status, request) {
                    if (data.status === 'Failed') {
                        handleFormError(data.content);
                    } else {
                        removeSchedulerIdFromURL();
                        location.reload();
                    }
                },
                error(jqXHR, textStatus, errorThrown) {
                    handleFormError(`${jqXHR.status} ${textStatus} ${errorThrown}`)
                },
            });
            return false;
        }
    });
    the_form.submit(function() {
        return false;
    });
    $('#schedulerTable').DataTable({
        columns: [
            {
                title: 'Report Unique ID',
                name: 'id',
                data: 'id',
            },
            {
                title: 'Report Title',
                name: 'report_title',
                data: 'params.report_title',
            },
            {
                title: 'Report Name',
                name: 'report_name',
                data: 'params.report_name',
            },
            {
                title: 'Cron Schedule',
                name: 'cron_schedule',
                data: 'cron_schedule',
            },
            {
                title: 'Next Run Time',
                name: 'next_run_time',
                data: 'next_run_time',
                render: (dt) => {
                    const d = new Date(dt);
                    return d.toLocaleString();
                },
            },
            {
                title: 'Delete',
                name: 'delete_url',
                data: 'delete_url',
                render: (url, type, row) => '<button type="button" class="ui button red deleteScheduleButton" '
                        + `id="delete_${row.id}" data-href="${url}"> <i class="trash icon"></i>`,
            },
        ],
        order: [[0, 'asc']],
    });
    // We can only call the showSelection function after both load_data and load_all_templates are loaded. Even though
    // the two requests can be initiated simultaneously, we are serializing them in order to simplify the flow.
    load_data(() => load_all_templates(showSelection));
});
