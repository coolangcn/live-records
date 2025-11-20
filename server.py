import os
import glob
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AUDIO_DIR = r"V:\Sony-1"
EXTENSIONS = ["*.mp3", "*.wav", "*.m4a", "*.flac"]

def get_latest_file():
    files = []
    for ext in EXTENSIONS:
        files.extend(glob.glob(os.path.join(AUDIO_DIR, ext)))
    
    if not files:
        return None
        
    # Sort by modification time, newest first
    return max(files, key=os.path.getmtime)

@app.get("/stream")
async def stream_audio():
    latest_file = get_latest_file()
    if not latest_file:
        raise HTTPException(status_code=404, detail="No audio files found")
    
    return FileResponse(latest_file)

@app.get("/metadata")
async def get_metadata():
    latest_file = get_latest_file()
    if not latest_file:
        return {"filename": None}
    return {"filename": os.path.basename(latest_file), "mtime": os.path.getmtime(latest_file)}

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sony-1 Audio Stream</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: system-ui, sans-serif; background: #1a1a1a; color: #fff; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; }
            .player { background: #2d2d2d; padding: 2rem; border-radius: 1rem; box-shadow: 0 4px 6px rgba(0,0,0,0.3); text-align: center; width: 90%; max-width: 400px; }
            h1 { font-size: 1.2rem; margin-bottom: 1rem; color: #aaa; }
            #filename { font-size: 1rem; margin-bottom: 1.5rem; font-weight: bold; color: #4CAF50; word-break: break-all; }
            audio { width: 100%; margin-bottom: 1rem; }
            .status { font-size: 0.8rem; color: #666; }
            button { background: #4CAF50; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-size: 1rem; }
            button:hover { background: #45a049; }
        </style>
    </head>
    <body>
        <div class="player">
            <h1>Latest Recording</h1>
            <div id="filename">Loading...</div>
            <audio id="audioPlayer" controls autoplay>
                <source src="/stream" type="audio/mpeg">
                Your browser does not support the audio element.
            </audio>
            <div class="status" id="status">Checking for updates...</div>
            <br>
            <button onclick="reloadAudio()">Refresh / Play Latest</button>
        </div>

        <script>
            const audio = document.getElementById('audioPlayer');
            const filenameDisplay = document.getElementById('filename');
            const statusDisplay = document.getElementById('status');
            let currentFile = null;

            async function checkUpdates() {
                try {
                    const response = await fetch('/metadata');
                    const data = await response.json();
                    
                    if (data.filename) {
                        if (currentFile && currentFile !== data.filename) {
                            statusDisplay.textContent = "New file detected!";
                            // Optional: Auto-reload if desired, but might interrupt playback if just checking
                        }
                        if (!currentFile) {
                            currentFile = data.filename;
                            filenameDisplay.textContent = data.filename;
                        } else if (currentFile !== data.filename) {
                             filenameDisplay.textContent = data.filename + " (New)";
                        }
                    } else {
                        filenameDisplay.textContent = "No files found";
                    }
                } catch (e) {
                    console.error(e);
                }
            }

            function reloadAudio() {
                audio.src = "/stream?t=" + new Date().getTime();
                audio.play().catch(e => console.log("Auto-play prevented"));
                checkUpdates();
                // Update current file name after reload
                fetch('/metadata').then(r => r.json()).then(d => {
                    if(d.filename) {
                        currentFile = d.filename;
                        filenameDisplay.textContent = d.filename;
                        statusDisplay.textContent = "Playing latest";
                    }
                });
            }

            // Initial load
            checkUpdates();
            
            // Check every 10 seconds
            setInterval(checkUpdates, 10000);

            // When audio ends, check if there is a newer file and play it? 
            // For now, just let user manually refresh or loop. 
            // Simple "monitor" mode:
            audio.onended = () => {
                statusDisplay.textContent = "Finished. Checking for new...";
                setTimeout(() => {
                    reloadAudio();
                }, 2000);
            };
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    # Listen on all interfaces
    uvicorn.run(app, host="0.0.0.0", port=8000)
