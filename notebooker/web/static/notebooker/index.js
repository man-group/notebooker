const getCurrentFolder = () => {
    let currentFolder = "";
    if (window.location.pathname.startsWith("/folder/")) {
        currentFolder = window.location.pathname.substring("/folder/".length) + "/";
    }
    return decodeURI(currentFolder);
};

const updateNavigationPanel = (currentFolder) => {
    const folderNavigationPanel = $("#folderNavigationPanel");
    folderNavigationPanel.empty();

    if (currentFolder !== "") {
        folderNavigationPanel.append('<a href="/">Start</a>');
        const parts = currentFolder.split("/");
        let folderSoFar = "";
        parts.forEach((part, idx) => {
            if (part.length > 0) {
                folderSoFar = `${folderSoFar}/${part}`;
                if (idx === parts.length - 2) {
                    folderNavigationPanel.append(`&nbsp;&gt;&nbsp;<span>${part}</span>`);
                } else {
                    folderNavigationPanel.append(`&nbsp;&gt;&nbsp;<a href="/folder${folderSoFar}">${part} </a>`);
                }
            }
        });
    }
};

const entryAfterLevel = (path, level) => {
    while (level > 0) {
        path = path.substring(path.indexOf("/") + 1);
        level = level - 1;
    }
    return path;
};

const updateContents = (currentFolder, entries) => {
    const $cardContainer = $("#cardContainer");
    $cardContainer.empty();
    const subfoldersInfo = {};
    const reportParts = [];
    for (const report in entries) {
        const report_data = entries[report];
        const report_path = report_data.report_name;
        if (!report_path.startsWith(currentFolder)) {
            continue;
        }
        const remainingPath = report_path.substring(currentFolder.length);
        if (remainingPath.includes("/")) {
            // it is a folder
            const subfolderPathName = remainingPath.substring(0, remainingPath.indexOf("/"));
            const subfolderPath = currentFolder + subfolderPathName;
            let info = subfoldersInfo[subfolderPath];
            if (subfolderPath in subfoldersInfo) {
                info.reportCount = info.reportCount + 1;
            } else {
                let info = {};
                info.pathName = subfolderPathName;
                info.path = subfolderPath;
                info.reportCount = 1;
                subfoldersInfo[subfolderPath] = info;
            }
        } else {
            const level = currentFolder.split("/").length - 1;
            const displayName = entryAfterLevel(report, level);
            const stats = entries[report];
            reportParts.push(
                `<a class="ui card" href="/result_listing/${stats.report_name}">` +
                    '  <div class="content">' +
                    `    <h1>${displayName}</h1>\n` +
                    '    <div class="meta">\n' +
                    `      <span class="date">Last ran ${stats.time_diff} ago</span>\n` +
                    "    </div>" +
                    "    <span>\n" +
                    `${stats.count} Runs\n` +
                    "    </span>" +
                    "<br/>" +
                    "    <span>\n" +
                    `${stats.scheduler_runs} Scheduler Runs\n` +
                    "    </span>" +
                    "  </div>" +
                    '  <div class="extra content">' +
                    `      <span>Original report name: ${stats.report_name}</span>\n` +
                    "  </div>" +
                    "</a>"
            );
        }
    }
    // first add all folders
    for (let subfolder in subfoldersInfo) {
        let info = subfoldersInfo[subfolder];
        $cardContainer.append(
            `<a class="ui card folder" href="/folder/${info.path}">` +
                '  <div class="content">' +
                `    <h1><i class="fa-solid fa-folder fa-xs"></i>${info.pathName}</h1>\n` +
                `    <span>Reports: ${info.reportCount}</span>` +
                "  </div>" +
                "</a>"
        );
    }
    // only then add individual items
    for (let idx in reportParts) {
        $cardContainer.append(reportParts[idx]);
    }
};

const load_data = async () => {
    const currentFolder = getCurrentFolder();
    try {
        const response = await fetch(`/core/get_all_templates_with_results/folder/`.concat(currentFolder));
        const result = await response.json();
        updateNavigationPanel(currentFolder);
        updateContents(currentFolder, result);
    } catch (error) {
        $("#failedLoad").fadeIn();
    }
};

$(document).ready(async () => {
    await load_data();
});

try {
    module.exports = {
        getCurrentFolder,
        updateNavigationPanel,
        updateContents,
        load_data,
    };
} catch (e) {
    // do nothing
}
