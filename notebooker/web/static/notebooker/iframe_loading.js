const iframeLoaded = function (iframe) {
    $('.iframeToLoad').show();
    setInterval(() => {
        iframe.style.height = `${iframe.contentWindow.document.body.scrollHeight}px`;
    }, 1);
    $('.iframeLoadingDimmer').removeClass('active').addClass('disabled');
};
