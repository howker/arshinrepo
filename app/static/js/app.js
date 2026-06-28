console.log("Arshin Checker loaded");
function pollJobStatus(jobId) {
    fetch('/api/jobs/' + jobId)
        .then(r => r.json())
        .then(data => {
            document.getElementById('status').innerText = data.status;
            if (data.status === 'completed' || data.status === 'completed_with_issues') {
                document.getElementById('result-link').style.display = 'block';
            } else {
                setTimeout(() => pollJobStatus(jobId), 3000);
            }
        });
}
