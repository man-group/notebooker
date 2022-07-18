const iframeLoaded = function (iframe) {
    let iframeContents = $('#resultsIframe').contents();
    iframeContents.find('.container').css('width', '97%');
    iframeContents.find('.code_cell').css('padding', '0px');
    setInterval(() => {
        iframe.style.height = `${iframe.contentWindow.document.body.scrollHeight}px`;
    }, 1000);
    $('.iframeToLoad').show();
    $('.iframeLoadingDimmer').removeClass('active').addClass('disabled');

};
