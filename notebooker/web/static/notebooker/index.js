load_data = () => {
    $.ajax({
        url: `/core/get_all_templates_with_results`,
        dataType: 'json',
        success: (result) => {
            let $cardContainer = $('#cardContainer');
            $cardContainer.empty();
            for (let report in result) {
                let stats = result[report];
                $cardContainer.append(
                    '<a class="ui card" href="/result_listing/' + stats.report_name + '">' +
                    '  <div class="content">' +
                    '    <h1>' + report + '</h1>\n' +
                    '    <div class="meta">\n' +
                    '      <span class="date">Last ran ' + stats.time_diff + ' ago</span>\n' +
                    '    </div>' +
                    '    <span>\n' +
                    stats.count +
                    '        Runs\n' +
                    '    </span>' +
                    '<br/>' +
                    '    <span>\n' +
                    stats.scheduler_runs +
                    '        Scheduler Runs\n' +
                    '    </span>' +
                    '  </div>' +
                    '  <div class="extra content">' +
                    '      <span>Original report name: ' + stats.report_name + '</span>\n' +
                    '  </div>' +
                    '</a>');
            }
        },
        error: (jqXHR, textStatus, errorThrown) => {
            $('#failedLoad').fadeIn();
        },
    });
};


$(document).ready(() => {
    load_data();
});
