# Abd Editor V1.0

A high-performance automated video processing and editing application powered by PyQt5 and FFmpeg filter graphs. Designed for content creators, social media video editors, and batch video compilation workflows.

---

## Key Features (Version 1.0)

- **Batch Folder Video Compilations**:
  - Automatically groups scanned folder videos into a single merged compilation job (`Compilation_<FolderName>.mp4`).
  - Seamlessly concatenates multiple clips sequentially.
  - Smooth real-time progress tracking from 0% to 100%.

- **Multi-Song Audio Playlist & Seamless Looping**:
  - Automatically scans your music directory, shuffles all tracks into a randomized sequence playlist, and concatenates them sequentially.
  - Applies `aloop` to ensure audio continuously fills long video compilations without dropping into silence.

- **Dual-Layer Border Frames**:
  - Customizable solid color borders with an optional **Inner White/Custom Outline Line** adjacent to the video stream.
  - Supports Left & Right Side Borders (pillarbox) and All-Sides framing.
  - Expanded palette of 16 vibrant solid colors: *Violet, Magenta, Teal, Fuchsia, Deep Purple, Bright Cyan, Coral, Mustard Yellow, Tangerine, Mint Green, Electric Blue, Lavender, Navy Blue, Forest Green, Solid Black, Solid White*.

- **Video Crop-Zoom**:
  - Scalable crop-zoom (105% to 200%) supporting **Cut Top & Bottom (Zoom Wider)** to trim off unwanted outer edges, side bars, or original video watermarks.

- **Image & Logo Overlays**:
  - Select picture/logo assets (`.png`, `.jpg`, `.jpeg`, `.bmp`, `.webp`) from your computer.
  - Proportional non-stretching scaling (`scale=target_w:-1:force_original_aspect_ratio=decrease,setsar=1`).
  - Position presets (Center, Left, Right, Top, Bottom) plus **0%–100% Custom X & Y Percentage Positioning**.

- **Text Overlay & Semi-Transparent Watermarks**:
  - Custom font family, font size, text colors, outlines, and shadows.
  - Opacity slider (0% to 100%) for semi-transparent text watermarks.

- **Script Editor Modal**:
  - Graphical script editor with drag-and-drop operation reordering and stackable filter configuration.

- **Persistent Queue & Audit History**:
  - Clean Dashboard queue view with selected row deletion (`Delete` key shortcut & right-click context menu).
  - Isolated database connection architecture preventing test pollution.

---

## Tech Stack

- **Core**: Python 3.10+, PyQt5
- **Engine**: FFmpeg (Filter complex pipeline, `zoompan`, `crop`, `pad`, `drawtext`, `overlay`, `concat`, `aloop`)
- **Database**: SQLite 3 (WAL journal mode)
- **Image Processing**: Pillow (PIL) for emoji & rich graphic rendering

---

## Installation & Running Locally

1. **Clone the repository**:
   ```bash
   git clone https://github.com/abdultechs/Abd-Editor.git
   cd Abd-Editor
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Ensure FFmpeg is installed** and accessible on your system PATH.

4. **Launch the application**:
   ```bash
   python main.py
   ```

---

## Building Standalone Executable (.exe)

You can package the application into a standalone Windows `.exe` file that runs without needing Python pre-installed:

### Option A: Automatic Build (Recommended)
Double-click `build_exe.bat` or run:
```cmd
build_exe.bat
```

### Option B: Manual Command
1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```
2. Build the `.exe`:
   ```bash
   py -3 -m PyInstaller --noconsole --onefile --name="Abd Editor V1.0" --add-data "resources;resources" --add-data "music;music" --hidden-import=PIL --hidden-import=PyQt5.QtCore --hidden-import=PyQt5.QtWidgets --hidden-import=PyQt5.QtGui main.py
   ```
3. Your executable will be ready in the `dist/` directory:
   `dist/Abd Editor V1.0.exe`

---

## License

Version 1.0 Release. Developed for Abd Editor.
