import os
import glob
import secrets
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from datetime import datetime

app = FastAPI()
security = HTTPBasic()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AUDIO_DIR = r"V:\Sony-1"
EXTENSIONS = ["*.mp3", "*.wav", "*.m4a", "*.flac"]

# --- Security ---
def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "cnncn")
    correct_password = secrets.compare_digest(credentials.password, "cncncncn")
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# --- Helpers ---
def get_all_files():
    files = []
    for ext in EXTENSIONS:
        files.extend(glob.glob(os.path.join(AUDIO_DIR, ext)))
    # Sort by modification time, newest first
    files.sort(key=os.path.getmtime, reverse=True)
    return files

def get_latest_file():
    files = get_all_files()
    if not files:
        return None
    return files[0]

# --- Endpoints ---

@app.get("/stream", dependencies=[Depends(get_current_username)])
async def stream_latest_audio():
    latest_file = get_latest_file()
    if not latest_file:
        raise HTTPException(status_code=404, detail="No audio files found")
    return FileResponse(latest_file)

@app.get("/stream/{filename}", dependencies=[Depends(get_current_username)])
async def stream_specific_audio(filename: str):
    # Security check: prevent directory traversal
    if ".." in filename or "/" in filename or "\\" in filename:
         raise HTTPException(status_code=400, detail="Invalid filename")
    
    file_path = os.path.join(AUDIO_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path)

@app.get("/files", dependencies=[Depends(get_current_username)])
async def list_files():
    files = get_all_files()
    file_list = []
    for f in files:
        stats = os.stat(f)
        file_list.append({
            "filename": os.path.basename(f),
            "mtime": stats.st_mtime,
            "size": stats.st_size,
            "date": datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        })
    return file_list

@app.get("/metadata", dependencies=[Depends(get_current_username)])
async def get_metadata():
    latest_file = get_latest_file()
    if not latest_file:
        return {"filename": None}
    return {"filename": os.path.basename(latest_file), "mtime": os.path.getmtime(latest_file)}

@app.get("/", response_class=HTMLResponse, dependencies=[Depends(get_current_username)])
async def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sony-1 Audio Stream</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: system-ui, sans-serif; background: #1a1a1a; color: #fff; display: flex; flex-direction: column; align-items: center; height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }
            .container { width: 100%; max-width: 600px; display: flex; flex-direction: column; gap: 20px; height: 100%; }
            .player-card { background: #2d2d2d; padding: 1.5rem; border-radius: 1rem; box-shadow: 0 4px 6px rgba(0,0,0,0.3); text-align: center; flex-shrink: 0; }
            h1 { font-size: 1.2rem; margin: 0 0 1rem 0; color: #aaa; }
            #filename { font-size: 1rem; margin-bottom: 1rem; font-weight: bold; color: #4CAF50; word-break: break-all; }
            audio { width: 100%; margin-bottom: 1rem; }
            .status { font-size: 0.8rem; color: #666; }
            button { background: #4CAF50; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-size: 1rem; }
            button:hover { background: #45a049; }
            
            .file-list { background: #2d2d2d; border-radius: 1rem; overflow: hidden; display: flex; flex-direction: column; flex-grow: 1; min-height: 0; }
            .list-header { padding: 1rem; background: #333; font-weight: bold; border-bottom: 1px solid #444; }
            .list-content { overflow-y: auto; flex-grow: 1; }
            .file-item { padding: 1rem; border-bottom: 1px solid #444; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }
            .file-item:hover { background: #383838; }
            .file-item.active { background: #3d4c3d; border-left: 4px solid #4CAF50; }
            .file-info { display: flex; flex-direction: column; gap: 4px; text-align: left; }
            .file-name { font-weight: 500; word-break: break-all; }
            .file-date { font-size: 0.8rem; color: #888; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="player-card">
                <h1>Audio Player</h1>
                <div id="filename">Loading...</div>
                <audio id="audioPlayer" controls autoplay>
                    <source src="" type="audio/mpeg">
                    Your browser does not support the audio element.
                </audio>
                <div class="status" id="status">Ready</div>
                <br>
                <button onclick="playLatest()">Play Latest</button>
            </div>

            <div class="file-list">
                <div class="list-header">All Recordings</div>
                <div class="list-content" id="fileList">
                    <!-- Files will be populated here -->
                </div>
            </div>
        </div>

        <script>
            const audio = document.getElementById('audioPlayer');
            const filenameDisplay = document.getElementById('filename');
            const statusDisplay = document.getElementById('status');
            const fileListEl = document.getElementById('fileList');
            let currentFile = null;

            async function loadFileList() {
                try {
                    const response = await fetch('/files');
                    const files = await response.json();
                    renderList(files);
                    return files;
                } catch (e) {
                    console.error("Error loading files:", e);
                }
            }

            function renderList(files) {
                fileListEl.innerHTML = '';
                files.forEach(file => {
                    const div = document.createElement('div');
                    div.className = `file-item ${currentFile === file.filename ? 'active' : ''}`;
                    div.onclick = () => playFile(file.filename);
                    div.innerHTML = `
                        <div class="file-info">
                            <span class="file-name">${file.filename}</span>
                            <span class="file-date">${file.date}</span>
                        </div>
                        <span>▶</span>
                    `;
                    fileListEl.appendChild(div);
                });
            }

            async function playFile(filename) {
                currentFile = filename;
                filenameDisplay.textContent = filename;
                audio.src = "/stream/" + encodeURIComponent(filename);
                try {
                    await audio.play();
                    statusDisplay.textContent = "Playing: " + filename;
                } catch (e) {
                    console.log("Auto-play prevented or error", e);
                    statusDisplay.textContent = "Ready to play";
                }
                
                // Refresh list to update active state
                loadFileList();
            }

            async function playLatest() {
                const files = await loadFileList();
                if (files && files.length > 0) {
                    playFile(files[0].filename);
                } else {
                    filenameDisplay.textContent = "No files found";
                }
            }

            // Initial load
            playLatest();
            
            // Poll for updates every 30s
            setInterval(loadFileList, 30000);
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

