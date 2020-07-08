$(document).ready(() => {
    let results_url = '';
    let last_data;
    const load_status = function () {
        if (typeof last_data !== 'undefined' && typeof last_data.results_url !== 'undefined') {
            clearInterval(intervalId);
            top.window.location.href = last_data.results_url;
        }
        $.ajax({
            url: loc, // We get this from loading.html, which comes from flask
            dataType: 'json',
            success(data, status, request) {
                console.log(data);
                results_url = data.results_url;
                $('#loadingStatus').text(data.status);
                $('#run_output').text(data.run_output);
                last_data = data;
                const i = $('#resultsIframe', window.parent.document);
                // Add 40 pixels to make sure we actually get the whole iframe contents...
                i.css('height', `${i[0].contentWindow.document.body.scrollHeight + 40}px`);
            },
            error(xhr, error) {
                $('h2').text(xhr.responseJSON.status);
                $('.loader').hide();
                clearInterval(intervalId);
            },
        });
    };
    load_status();
    let intervalId = window.setInterval(() => {
        load_status();
    }, 1500);
});
