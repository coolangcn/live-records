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
    # Only keep the latest 2 files
    files = files[:2]
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
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg-color: #0f0f13;
                --card-bg: rgba(255, 255, 255, 0.05);
                --primary: #00ff9d;
                --secondary: #bd00ff;
                --text: #ffffff;
                --text-dim: #8b8b9e;
            }
            
            body { 
                font-family: 'Outfit', sans-serif; 
                background: var(--bg-color); 
                color: var(--text); 
                display: flex; 
                flex-direction: column; 
                align-items: center; 
                height: 100vh; 
                margin: 0; 
                padding: 20px; 
                box-sizing: border-box; 
                overflow: hidden;
            }

            /* Background Animation */
            body::before {
                content: '';
                position: absolute;
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                background: radial-gradient(circle, rgba(189,0,255,0.1) 0%, rgba(0,0,0,0) 70%);
                animation: pulse 15s infinite;
                z-index: -1;
            }

            @keyframes pulse {
                0% { transform: scale(1); opacity: 0.5; }
                50% { transform: scale(1.2); opacity: 0.8; }
                100% { transform: scale(1); opacity: 0.5; }
            }

            .container { 
                width: 100%; 
                max-width: 800px; 
                display: flex; 
                flex-direction: column; 
                gap: 20px; 
                height: 100%; 
                position: relative;
            }

            /* Glassmorphism Card */
            .player-card { 
                background: var(--card-bg); 
                backdrop-filter: blur(10px); 
                -webkit-backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                padding: 2rem; 
                border-radius: 1.5rem; 
                box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
                text-align: center; 
                flex-shrink: 0; 
                position: relative;
                overflow: hidden;
            }

            h1 { 
                font-size: 1.5rem; 
                margin: 0 0 0.5rem 0; 
                background: linear-gradient(90deg, var(--primary), var(--secondary));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-weight: 700;
                letter-spacing: 1px;
            }

            #filename { 
                font-size: 1.1rem; 
                margin-bottom: 1.5rem; 
                font-weight: 500; 
                color: var(--text); 
                word-break: break-all; 
                text-shadow: 0 0 10px rgba(0, 255, 157, 0.3);
            }

            /* CSS Visualizer */
            .visualizer-container {
                display: flex;
                justify-content: center;
                align-items: flex-end;
                height: 60px;
                gap: 4px;
                margin-bottom: 1.5rem;
            }
            
            .bar {
                width: 6px;
                background: linear-gradient(to top, var(--secondary), var(--primary));
                border-radius: 3px;
                animation: bounce 1s infinite ease-in-out;
            }
            
            .bar:nth-child(odd) { animation-duration: 0.8s; }
            .bar:nth-child(2n) { animation-duration: 1.1s; }
            .bar:nth-child(3n) { animation-duration: 1.3s; }
            .bar:nth-child(4n) { animation-duration: 0.9s; }
            
            /* Pause animation when not playing */
            .paused .bar {
                animation-play-state: paused;
                height: 5px !important;
                transition: height 0.3s;
            }

            @keyframes bounce {
                0%, 100% { height: 10px; }
                50% { height: 50px; }
            }

            audio { 
                width: 100%; 
                margin-bottom: 1rem; 
                filter: invert(1) hue-rotate(180deg); /* Dark mode audio player hack */
                border-radius: 30px;
            }

            .status { font-size: 0.9rem; color: var(--text-dim); margin-bottom: 1rem; }

            /* Controls */
            .controls { 
                display: flex; 
                align-items: center; 
                justify-content: center; 
                gap: 15px; 
            }

            button { 
                background: linear-gradient(135deg, var(--primary), #00cc7d); 
                color: #000; 
                border: none; 
                padding: 12px 24px; 
                border-radius: 50px; 
                cursor: pointer; 
                font-size: 1rem; 
                font-weight: 700;
                transition: transform 0.2s, box-shadow 0.2s;
                box-shadow: 0 0 15px rgba(0, 255, 157, 0.4);
            }

            button:hover { 
                transform: translateY(-2px); 
                box-shadow: 0 0 25px rgba(0, 255, 157, 0.6);
            }

            button:active { transform: translateY(0); }

            .checkbox-wrapper { 
                display: flex; 
                align-items: center; 
                gap: 8px; 
                font-size: 0.9rem; 
                cursor: pointer; 
                color: var(--text-dim);
                user-select: none;
            }

            input[type="checkbox"] { 
                accent-color: var(--primary); 
                width: 18px; 
                height: 18px; 
            }

            /* File List */
            .file-list { 
                background: var(--card-bg); 
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 1.5rem; 
                overflow: hidden; 
                display: flex; 
                flex-direction: column; 
                flex-grow: 1; 
                min-height: 0; 
                box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
            }

            .list-header { 
                padding: 1.2rem; 
                background: rgba(255, 255, 255, 0.03); 
                font-weight: 700; 
                border-bottom: 1px solid rgba(255, 255, 255, 0.05); 
                color: var(--primary);
                text-transform: uppercase;
                letter-spacing: 1px;
                font-size: 0.9rem;
            }

            .list-content { 
                overflow-y: auto; 
                flex-grow: 1; 
                padding: 0.5rem;
            }

            /* Scrollbar */
            .list-content::-webkit-scrollbar { width: 6px; }
            .list-content::-webkit-scrollbar-track { background: transparent; }
            .list-content::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.2); border-radius: 3px; }

            .file-item { 
                padding: 1rem; 
                margin-bottom: 5px;
                border-radius: 10px;
                cursor: pointer; 
                display: flex; 
                justify-content: space-between; 
                align-items: center; 
                transition: background 0.2s, transform 0.2s;
                border: 1px solid transparent;
                animation: slideIn 0.3s ease-out forwards;
                opacity: 0;
            }

            @keyframes slideIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }

            .file-item:hover { 
                background: rgba(255, 255, 255, 0.05); 
                transform: translateX(5px);
            }

            .file-item.active { 
                background: rgba(0, 255, 157, 0.1); 
                border: 1px solid rgba(0, 255, 157, 0.3);
                box-shadow: 0 0 15px rgba(0, 255, 157, 0.1);
            }

            .file-info { display: flex; flex-direction: column; gap: 4px; text-align: left; }
            .file-name { font-weight: 500; word-break: break-all; color: var(--text); }
            .file-date { font-size: 0.8rem; color: var(--text-dim); }
            
            .play-icon { color: var(--primary); font-size: 1.2rem; opacity: 0; transition: opacity 0.2s; }
            .file-item:hover .play-icon, .file-item.active .play-icon { opacity: 1; }

        </style>
    </head>
    <body>
        <div class="container">
            <div class="player-card">
                <h1>SONY-1 STREAM</h1>
                <div id="filename">Loading...</div>
                
                <div class="visualizer-container paused" id="visualizer">
                    <!-- Generated bars -->
                </div>
                
                <audio id="audioPlayer" controls>
                    <source src="" type="audio/mpeg">
                </audio>
                
                <div class="status" id="status">Ready</div>
                
                <div class="controls">
                    <button onclick="playLatest()">PLAY LATEST</button>
                    <label class="checkbox-wrapper">
                        <input type="checkbox" id="autoPlay" checked>
                        AUTO-PLAY
                    </label>
                </div>
            </div>

            <div class="file-list">
                <div class="list-header">Recordings Library</div>
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
            const autoPlayCheckbox = document.getElementById('autoPlay');
            const visualizerContainer = document.getElementById('visualizer');
            
            let currentFile = null;
            let latestServerFile = null;

            // --- Visualizer Setup ---
            function initVisualizer() {
                visualizerContainer.innerHTML = '';
                for(let i=0; i<20; i++) {
                    const bar = document.createElement('div');
                    bar.className = 'bar';
                    // Randomize heights slightly for variety
                    bar.style.height = Math.floor(Math.random() * 30 + 10) + 'px';
                    visualizerContainer.appendChild(bar);
                }
            }
            initVisualizer();

            audio.addEventListener('play', () => {
                visualizerContainer.classList.remove('paused');
            });
            audio.addEventListener('pause', () => {
                visualizerContainer.classList.add('paused');
            });
            audio.addEventListener('ended', () => {
                visualizerContainer.classList.add('paused');
            });

            // --- App Logic ---

            async function loadFileList() {
                try {
                    const response = await fetch('/files');
                    const files = await response.json();
                    renderList(files);
                    
                    if (files.length > 0) {
                        latestServerFile = files[0].filename;
                        checkAutoPlay();
                    }
                    
                    return files;
                } catch (e) {
                    console.error("Error loading files:", e);
                }
            }

            function checkAutoPlay() {
                if (autoPlayCheckbox.checked && latestServerFile && latestServerFile !== currentFile) {
                    console.log("Auto-playing new file:", latestServerFile);
                    playFile(latestServerFile);
                }
            }

            function renderList(files) {
                const currentScroll = fileListEl.scrollTop;
                fileListEl.innerHTML = '';
                
                files.forEach((file, index) => {
                    const div = document.createElement('div');
                    div.className = `file-item ${currentFile === file.filename ? 'active' : ''}`;
                    div.style.animationDelay = `${index * 0.05}s`; 
                    div.onclick = () => playFile(file.filename);
                    div.innerHTML = `
                        <div class="file-info">
                            <span class="file-name">${file.filename}</span>
                            <span class="file-date">${file.date}</span>
                        </div>
                        <span class="play-icon">▶</span>
                    `;
                    fileListEl.appendChild(div);
                });
                
                fileListEl.scrollTop = currentScroll;
            }

            async function playFile(filename) {
                currentFile = filename;
                filenameDisplay.textContent = filename;
                audio.src = "/stream/" + encodeURIComponent(filename);
                
                try {
                    await audio.play();
                    statusDisplay.textContent = "PLAYING NOW";
                } catch (e) {
                    console.log("Auto-play prevented or error", e);
                    statusDisplay.textContent = "READY";
                }
                
                document.querySelectorAll('.file-item').forEach(el => {
                    el.classList.remove('active');
                    if(el.querySelector('.file-name').textContent === filename) {
                        el.classList.add('active');
                    }
                });
            }

            async function playLatest() {
                const files = await loadFileList();
                if (files && files.length > 0) {
                    playFile(files[0].filename);
                } else {
                    filenameDisplay.textContent = "NO FILES FOUND";
                }
            }

            // Initial load
            playLatest();
            
            // Poll for updates every 10s
            setInterval(loadFileList, 10000);
            
            audio.onended = () => {
                statusDisplay.textContent = "FINISHED";
                if (autoPlayCheckbox.checked) {
                    loadFileList();
                }
            };
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
