
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


function entryAfterLevel(path, level){
    while(level > 0) {
        path = path.substring(path.indexOf('/') + 1)
        level = level - 1
    }
    return path
}

function updateContents(currentFolder, entries){
    let $cardContainer = $('#cardContainer');
    $cardContainer.empty();
    subfoldersInfo = {}
    reportParts = []
    for (let report in entries) {
        report_data = entries[report]
        report_path = report_data.report_name
        if(!report_path.startsWith(currentFolder)){
            continue;
        }
        remainingPath = report_path.substring(currentFolder.length)
        if(remainingPath.includes('/')) {
            // it is a folder
            subfolderPathName = remainingPath.substring(0, remainingPath.indexOf('/'))
            subfolderPath = currentFolder + subfolderPathName
            if (subfolderPath in subfoldersInfo) {
                info.reportCount = info.reportCount + 1
            } else{
                info = {}
                info.pathName = subfolderPathName
                info.path = subfolderPath
                info.reportCount = 1
                subfoldersInfo[subfolderPath] = info
            }
        }else{
            level = currentFolder.split('/').length - 1
            displayName = entryAfterLevel(report, level)
            let stats = entries[report];
            reportParts.push('<a class="ui card" href="/result_listing/' + stats.report_name + '">' +
                '  <div class="content">' +
                '    <h1>' + displayName + '</h1>\n' +
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
        
        
    }
    // first add all folders
    for (let subfolder in subfoldersInfo) {
        info = subfoldersInfo[subfolder]
        $cardContainer.append(
            '<a class="ui card folder" href="/folder/' + info.path + '">' +
            '  <div class="content">' +
            '    <h1><i class="fa-solid fa-folder fa-xs"></i> ' + info.pathName + '</h1>\n' +
            ' <span>Reports: ' + info.reportCount + '</span>' + 
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
        url: `/core/get_all_templates_with_results/folder/`.concat(getCurrentFolder()),
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
