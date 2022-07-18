const iframeLoaded = function (iframe) {
    $('#resultsIframe').contents().find('.container').css('width', '97%')
    setInterval(() => {
        iframe.style.height = `${iframe.contentWindow.document.body.scrollHeight}px`;
    }, 1000);
    $('.iframeToLoad').show();
    $('.iframeLoadingDimmer').removeClass('active').addClass('disabled');

};
