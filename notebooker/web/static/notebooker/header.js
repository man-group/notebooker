$(document).ready(() => {
    $.ajax({
        url: '/core/version',
        success: (result) => {
            $('#versionTitle').text("v" + result.version);
            $('#versionTitle').show();
        },
        error: () => {
            $('#versionTitle').hide();
        },
    });
    // Check auth is enabled on our host
    $.ajax({
        url: '/oauth/health',
        success: () => {
            // If enabled, then fetch our login status
            $.ajax({
                url: '/core/user_profile',
                dataType: 'json',
                success: (result) => {
                    console.log(result);
                    const user = result;
                    if (result.username) {
                        $('#usernameInfo').text(result.username);
                        $('.loggedIn').fadeIn();
                    } else {
                        $('.loggedOut').fadeIn();
                    }
                },
                error: (jqXHR, textStatus, errorThrown) => {
                    $('.loggedOut').fadeIn();
                },
            });
        },
        error: () => {
            $('#authArea').hide();
        },
    });
    $.ajax({
        url: '/scheduler/health',
        success: () => {
            // Show the status at some point
        },
        error: () => {
            $('#schedulerButton').hide();
        },
    });

    const sb = $('.ui.left.sidebar');
    sb.sidebar({
        transition: 'overlay',
    });
    sb.sidebar('attach events', '#runReport');
    $('.ui .dropdown').dropdown();

    $('.message .close')
        .on('click', function () {
            $(this)
                .closest('.message')
                .hide();
        });
});

function rerunReport(jobId, rerunUrl) {
    $.ajax({
        type: 'POST',
        url: rerunUrl,
        dataType: 'json',
        success(data, status, request) {
            window.location.href = data.results_url;
        },
        error(xhr, textStatus, errorThrown) {
            $('#errorMsg').text(`${xhr.status} ${textStatus} ${errorThrown}`);
            $('#errorPopup').show();
        },
    });
}

function cloneReport(cloneUrl) {
    window.location.href = cloneUrl;
}

function viewStdout(stdoutUrl) {
    stdoutContent = document.getElementById('stdoutContent')

    if (!stdoutContent.textContent) {
        $.ajax({
            type: 'GET',
            url: stdoutUrl,
            dataType: 'json',
            success(data, status, request) {
                stdoutContent.textContent = data.join("")
            },
            error(xhr, textStatus, errorThrown) {
                $('#errorMsg').text(`${xhr.status} ${textStatus} ${errorThrown}`);
                $('#errorPopup').show();
            },
        });
    }

    $('#stdoutModal').modal({
        onDeny() {
            return true;
        },
        onApprove() {
            copy(stdoutContent.textContent)
            return false;
        },
    }).modal('show');
}

function copy(text) {
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text);
    } else {
        // workaround for Chrome without https - create a hidden text area and copy from that
        textArea = document.createElement("textarea");
        textArea.value = text;

        textArea.style.position = "absolute";
        textArea.style.opacity = 0
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();

        new Promise((res, rej) => {
            document.execCommand('copy') ? res() : rej();
            textArea.remove();
        });
    }
}

function viewFullscreen(fullscreenUrl) {
    window.location.href = fullscreenUrl;
}