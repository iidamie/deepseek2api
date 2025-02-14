document.addEventListener('DOMContentLoaded', function () {
    const fetchDataButton = document.getElementById('fetchDataButton');
    const dataContainer = document.getElementById('dataContainer');

    fetchDataButton.addEventListener('click', function () {
        chrome.runtime.sendMessage({ action: 'fetchData', url: 'https://api.deepseek.com/data', token: 'your-token-here' }, function (response) {
            if (response.success) {
                dataContainer.textContent = 'Data fetched: ' + JSON.stringify(response.data);
            } else {
                dataContainer.textContent = 'Error: ' + response.error;
            }
        });
    });
});
