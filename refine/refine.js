fetch('data.txt')
  .then(response => response.text())
  .then(text => {
    const refine_data = parseMarkdownKeyValue(text);

    document.getElementById("nameBox").innerText = refine_data["Name"];
  });

function parseMarkdownKeyValue(text) {
  const lines = text.trim().split('\n');
  const result = {};

  for (const line of lines) {
    const match = line.match(/\*\*(.+?):\*\*\s*(.+)/);
    if (match) {
      const key = match[1].trim();
      const value = match[2].trim();
      result[key] = value;
    }
  }

  return result;
}
