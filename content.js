console.log('DeepSeek Chrome Extension content script loaded.');

function injectUI() {
  const container = document.createElement('div');
  container.id = 'deepseek-container';
  container.style.position = 'fixed';
  container.style.bottom = '10px';
  container.style.right = '10px';
  container.style.zIndex = '1000';
  container.style.backgroundColor = 'white';
  container.style.border = '1px solid #ccc';
  container.style.padding = '10px';
  container.style.boxShadow = '0 0 10px rgba(0, 0, 0, 0.1)';

  const button = document.createElement('button');
  button.textContent = 'Fetch Data';
  button.onclick = () => {
    chrome.runtime.sendMessage({ action: 'fetchData', url: 'https://api.deepseek.com/data', token: 'your-token-here' }, (response) => {
      if (response.success) {
        alert('Data fetched: ' + JSON.stringify(response.data));
      } else {
        alert('Error: ' + response.error);
      }
    });
  };

  container.appendChild(button);
  document.body.appendChild(container);
}

injectUI();
