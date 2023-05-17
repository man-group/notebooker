
function getCurrentFolder(){
    if (window.location.pathname.startsWith("/folder/")){
        currentFolder = window.location.pathname.substring("/folder/".length) + "/"
    } else {
        currentFolder = ""
    }
    return currentFolder
}

function updateNavigationPanel(currentFolder){
    let $folderNavigationPanel = $('#folderNavigationPanel');
    $folderNavigationPanel.empty()
    
    if (currentFolder != "") {
        $folderNavigationPanel.append('<a href="/">Start</a>')
        parts = currentFolder.split("/")
        folderSoFar = ""
        for(let idx in parts){
            part = parts[idx]
            if(part.length > 0){
                folderSoFar = folderSoFar + "/" + part
                if(idx == parts.length - 2){
                    $folderNavigationPanel.append('&nbsp;&gt;&nbsp;<span>' + part + "</span>")
                }else{
                    $folderNavigationPanel.append('&nbsp;&gt;&nbsp;<a href="/folder' + folderSoFar + '">' + part + " </a>")
                }
                
            }
        }
    }
}


function updateContents(currentFolder, entries){
    let $cardContainer = $('#cardContainer');
    $cardContainer.empty();
    subfolderPaths = {}
    reportParts = []
    for (let report in entries) {
        if(!report.startsWith(currentFolder)){
            continue;
        }
        
        shortReportName = report.substring(currentFolder.length)
        if(shortReportName.includes('/')) {
            subfolderName = shortReportName.substring(0, shortReportName.indexOf('/'))
            subfolderPaths[subfolderName] = currentFolder + subfolderName
            // it is a folder
            continue
        }
        
        let stats = entries[report];
        reportParts.push('<a class="ui card" href="/result_listing/' + stats.report_name + '">' +
            '  <div class="content">' +
            '    <h1>' + shortReportName + '</h1>\n' +
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
    // first add all folders
    for (let subfolder in subfolderPaths) {
        $cardContainer.append(
            '<a class="ui card folder" href="/folder/' + subfolderPaths[subfolder] + '">' +
            '  <div class="content">' +
            '    <h1><img src="/static/notebooker/folder.svg" class="folderImg">' + subfolder + '</h1>\n' +
            '  </div>' +
            '</a>');
    }
    // only then add individual items
    for (let idx in reportParts) {
        $cardContainer.append(reportParts[idx])
    }
}


load_data = () => {
    $.ajax({
        url: `/core/get_all_templates_with_results`,
        dataType: 'json',
        success: (result) => {
            currentFolder = getCurrentFolder()
            updateNavigationPanel(currentFolder)
            updateContents(currentFolder, result)
        },
        error: (jqXHR, textStatus, errorThrown) => {
            $('#failedLoad').fadeIn();
        },
    });
};


$(document).ready(() => {
    load_data();
});
