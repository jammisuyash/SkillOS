import React, { useState, useEffect, useCallback, useRef } from "react";

// ─── MONACO EDITOR LOADER ────────────────────────────────────────────────────
// Loads Monaco Editor (same editor as VS Code) from CDN — no install needed
let _monacoLoaded = false;
let _monacoCallbacks = [];
function loadMonaco(cb) {
  if (window.monaco) { cb(window.monaco); return; }
  _monacoCallbacks.push(cb);
  if (_monacoLoaded) return;
  _monacoLoaded = true;
  // Load Monaco from CDN
  const script = document.createElement("script");
  script.src = "https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs/loader.min.js";
  script.onload = () => {
    window.require.config({ paths: { vs: "https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs" } });
    window.require(["vs/editor/editor.main"], (monaco) => {
      window.monaco = monaco;
      // Dark theme matching SkillOS design
      monaco.editor.defineTheme("skillos-dark", {
        base: "vs-dark",
        inherit: true,
        rules: [
          { token: "comment",                foreground: "545478", fontStyle: "italic" },
          { token: "comment.doc",            foreground: "6a6a9a", fontStyle: "italic" },
          { token: "keyword",                foreground: "c792ea" },
          { token: "keyword.control",        foreground: "c792ea", fontStyle: "bold" },
          { token: "string",                 foreground: "c3e88d" },
          { token: "string.escape",          foreground: "f78c6c" },
          { token: "number",                 foreground: "f78c6c" },
          { token: "number.float",           foreground: "f78c6c" },
          { token: "function",               foreground: "82aaff" },
          { token: "function.call",          foreground: "82aaff" },
          { token: "type",                   foreground: "00d4ff" },
          { token: "type.identifier",        foreground: "ffcb6b" },
          { token: "class",                  foreground: "ffcb6b", fontStyle: "bold" },
          { token: "operator",               foreground: "89ddff" },
          { token: "delimiter",              foreground: "89ddff" },
          { token: "variable",               foreground: "eeffff" },
          { token: "variable.predefined",    foreground: "ff5370" },
          { token: "constant",               foreground: "f78c6c" },
          { token: "identifier",             foreground: "eeffff" },
          { token: "tag",                    foreground: "f07178" },
          { token: "attribute.name",         foreground: "ffcb6b" },
          { token: "attribute.value",        foreground: "c3e88d" },
          { token: "metatag",                foreground: "ff5370" },
          { token: "decorator",              foreground: "82aaff", fontStyle: "italic" },
        ],
        colors: {
          "editor.background":                "#0a0a12",
          "editor.foreground":                "#eeffff",
          "editorLineNumber.foreground":      "#2a2a44",
          "editorLineNumber.activeForeground":"#7b5ea7",
          "editorCursor.foreground":          "#c792ea",
          "editor.selectionBackground":       "#3d2f6b88",
          "editor.lineHighlightBackground":   "#0d0d1a",
          "editor.lineHighlightBorder":       "#1a1a2e",
          "editorIndentGuide.background":     "#1e1e2e",
          "editorIndentGuide.activeBackground":"#3d2f6b",
          "editorGutter.background":          "#0a0a12",
          "editorWidget.background":          "#0f0f1e",
          "editorSuggestWidget.background":   "#0f0f1e",
          "editorSuggestWidget.border":       "#2a2a44",
          "editorSuggestWidget.selectedBackground": "#2d2d5e",
          "input.background":                 "#0f0f1e",
          "scrollbarSlider.background":       "#2a2a4440",
          "scrollbarSlider.hoverBackground":  "#3d2f6b60",
          "scrollbarSlider.activeBackground": "#7b5ea760",
        }
      });
      monaco.editor.setTheme("skillos-dark");
      _monacoCallbacks.forEach(c => c(monaco));
      _monacoCallbacks = [];
    });
  };
  document.head.appendChild(script);
}

// ─── CODE EDITOR COMPONENT ───────────────────────────────────────────────────
const LANGUAGE_MAP = {
  python3: "python", javascript: "javascript", java: "java",
  cpp: "cpp", c: "c", typescript: "typescript", go: "go", rust: "rust",
};
const STARTER_CODE = {
  python3:    "# Write your solution here\nimport sys\ninput = sys.stdin.readline\n\ndef solution():\n    pass\n\nsolution()\n",
  javascript: "// Write your solution here\nconst lines = require('fs').readFileSync('/dev/stdin','utf8').split('\\n');\nlet idx = 0;\n\nfunction solution() {\n  \n}\nsolution();\n",
  java:       "import java.util.*;\nimport java.io.*;\n\npublic class Solution {\n    public static void main(String[] args) throws Exception {\n        Scanner sc = new Scanner(System.in);\n        // Write your solution here\n    }\n}\n",
  cpp:        "#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    ios_base::sync_with_stdio(false);\n    cin.tie(NULL);\n    // Write your solution here\n    return 0;\n}\n",
  c:          "#include <stdio.h>\n#include <stdlib.h>\n\nint main() {\n    // Write your solution here\n    return 0;\n}\n",
  go:         "package main\nimport (\n    \"bufio\"\n    \"fmt\"\n    \"os\"\n)\n\nfunc main() {\n    reader := bufio.NewReader(os.Stdin)\n    _ = reader\n    // Write your solution here\n    fmt.Println()\n}\n",
  typescript: "// Write your solution here\nconst lines = require('fs').readFileSync('/dev/stdin','utf8').split('\\n');\n\nfunction solution(): void {\n  \n}\nsolution();\n",
};

function MonacoEditor({ value, onChange, language = "python3", height = 340 }) {
  const containerRef = useRef(null);
  const editorRef    = useRef(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    loadMonaco((monaco) => {
      if (!containerRef.current || editorRef.current) return;
      const editor = monaco.editor.create(containerRef.current, {
        value,
        language:         LANGUAGE_MAP[language] || "python",
        theme:            "skillos-dark",
        fontSize:         13,
        lineHeight:       22,
        fontFamily:       "'JetBrains Mono', 'Fira Code', monospace",
        fontLigatures:    true,
        minimap:          { enabled: false },
        scrollBeyondLastLine: false,
        automaticLayout:  true,
        tabSize:          4,
        wordWrap:         "on",
        suggest:          { showKeywords: true, showSnippets: true },
        quickSuggestions: true,
        bracketPairColorization: { enabled: true },
        padding:          { top: 12, bottom: 12 },
        scrollbar:        { verticalScrollbarSize: 6 },
      });
      editor.onDidChangeModelContent(() => {
        onChange(editor.getValue());
      });
      editorRef.current = editor;
      setLoaded(true);
    });
    return () => { editorRef.current?.dispose(); editorRef.current = null; };
  }, []);

  // Sync language changes
  useEffect(() => {
    if (!editorRef.current || !window.monaco) return;
    const lang = LANGUAGE_MAP[language] || "python";
    window.monaco.editor.setModelLanguage(editorRef.current.getModel(), lang);
    // Set starter code when switching language
    const starter = STARTER_CODE[language];
    if (starter && editorRef.current.getValue().trim() === "" ) {
      editorRef.current.setValue(starter);
    }
  }, [language]);

  return (
    <div style={{ position: "relative" }}>
      {!loaded && (
        <div style={{
          height, background: "#0d0d14", display: "flex", alignItems: "center",
          justifyContent: "center", color: "#6b6b84", fontSize: 13,
          fontFamily: "JetBrains Mono, monospace", borderRadius: "0 0 10px 10px"
        }}>
          Loading editor…
        </div>
      )}
      <div ref={containerRef} style={{ height, display: loaded ? "block" : "none" }} />
    </div>
  );
}

// ─── API CLIENT ─────────────────────────────────────────────────────────────
const API = typeof window !== "undefined"
  ? (window.SKILLOS_API || "http://localhost:8000")
  : "http://localhost:8000";

const api = {
  async req(method, path, body, token) {
    const opts = {
      method,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(API + path, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
  },
  get:  (p, t)    => api.req("GET",  p, null, t),
  post: (p, b, t) => api.req("POST", p, b, t),
};

// ─── DESIGN TOKENS ──────────────────────────────────────────────────────────
const css = `
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:ital,wght@0,300;0,400;0,500;0,700;1,400&family=Orbitron:wght@400;700;900&display=swap');

  :root {
    --bg:        #060608;
    --bg2:       #0d0d12;
    --bg3:       #141420;
    --bg4:       #1c1c2e;
    --border:    #1e1e2e;
    --border2:   #2a2a40;
    --text:      #e2e2f0;
    --text2:     #a0a0c0;
    --muted:     #525270;
    --accent:    #7b5ea7;
    --accent-h:  #9d7fd4;
    --accent2:   #00e5a0;
    --accent3:   #ff4d6d;
    --gold:      #f5c842;
    --cyan:      #00d4ff;
    --orange:    #ff7f3f;
    --glow:      rgba(123,94,167,.35);
    --glow2:     rgba(0,229,160,.2);
    --font:      'Space Grotesk', sans-serif;
    --font-disp: 'Orbitron', monospace;
    --mono:      'JetBrains Mono', monospace;
    --radius:    10px;
    --radius-lg: 16px;
  }

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--font);
    min-height: 100vh;
    overflow-x: hidden;
    line-height: 1.6;
  }

  /* Grid noise texture overlay */
  body::before {
    content: '';
    position: fixed; inset: 0;
    background-image:
      linear-gradient(rgba(123,94,167,.015) 1px, transparent 1px),
      linear-gradient(90deg, rgba(123,94,167,.015) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none; z-index: 0;
  }

  #root { position: relative; z-index: 1; }

  ::-webkit-scrollbar { width: 3px; height: 3px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--accent); }

  /* ── Layout ── */
  .app { display: flex; min-height: 100vh; }

  /* ── Sidebar ── */
  .sidebar {
    width: 230px; flex-shrink: 0;
    background: var(--bg2);
    border-right: 1px solid var(--border);
    display: flex; flex-direction: column;
    position: fixed; height: 100vh;
    z-index: 100;
    background: linear-gradient(180deg, #0d0d14 0%, #0a0a10 100%);
  }
  .sidebar::after {
    content: '';
    position: absolute; top: 0; right: 0;
    width: 1px; height: 100%;
    background: linear-gradient(180deg, transparent, var(--accent), transparent);
    opacity: 0.3;
  }
  .logo {
    padding: 22px 20px 18px;
    font-family: var(--font-disp);
    font-size: 15px; font-weight: 900;
    letter-spacing: 2px;
    border-bottom: 1px solid var(--border);
    display: flex; align-items: center; gap: 10px;
  }
  .logo-icon {
    width: 30px; height: 30px;
    background: linear-gradient(135deg, var(--accent), var(--cyan));
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; font-weight: 900;
    box-shadow: 0 0 16px var(--glow);
  }
  .logo span { color: var(--accent-h); }
  .logo-sub { font-size: 8px; color: var(--muted); letter-spacing: 3px; display: block; margin-top: 1px; }

  .nav { flex: 1; padding: 10px 0; overflow-y: auto; }
  .nav-section {
    padding: 12px 18px 4px;
    font-size: 9px; font-weight: 700;
    color: var(--muted); letter-spacing: 2px;
    text-transform: uppercase;
    margin-top: 4px;
  }
  .nav-item {
    display: flex; align-items: center; gap: 10px;
    padding: 9px 18px; cursor: pointer;
    font-size: 12.5px; font-weight: 500;
    color: var(--text2); transition: all .2s;
    position: relative; margin: 1px 8px;
    border-radius: 8px;
    letter-spacing: .3px;
  }
  .nav-item:hover {
    color: var(--text);
    background: rgba(123,94,167,.1);
  }
  .nav-item.active {
    color: var(--accent-h);
    background: linear-gradient(135deg, rgba(123,94,167,.2), rgba(0,212,255,.05));
    border: 1px solid rgba(123,94,167,.25);
  }
  .nav-item.active::before {
    content: '';
    position: absolute; left: -8px;
    width: 3px; height: 60%; top: 20%;
    background: var(--accent-h);
    border-radius: 0 2px 2px 0;
    box-shadow: 0 0 8px var(--glow);
  }
  .nav-icon { font-size: 14px; width: 18px; text-align: center; opacity: .85; }

  .sidebar-user {
    padding: 14px 18px;
    border-top: 1px solid var(--border);
    display: flex; align-items: center; gap: 10px;
    font-size: 12px;
    background: rgba(123,94,167,.04);
  }
  .avatar {
    width: 32px; height: 32px; border-radius: 50%;
    background: linear-gradient(135deg, var(--accent), var(--cyan));
    display: flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 800; flex-shrink: 0;
    box-shadow: 0 0 10px var(--glow);
    font-family: var(--font-disp);
  }
  .avatar-sm {
    width: 26px; height: 26px; border-radius: 50%;
    background: linear-gradient(135deg, var(--accent), var(--cyan));
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 10px; font-weight: 800;
  }

  /* ── Main ── */
  .main { margin-left: 230px; flex: 1; min-height: 100vh; }
  .topbar {
    padding: 14px 32px; display: flex; align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid var(--border);
    background: rgba(6,6,8,.85);
    backdrop-filter: blur(16px);
    position: sticky; top: 0; z-index: 50;
  }
  .page-title {
    font-size: 16px; font-weight: 700;
    letter-spacing: .5px;
    display: flex; align-items: center; gap: 8px;
  }
  .content { padding: 28px 32px; }

  /* ── Cards ── */
  .card {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg); padding: 20px;
    transition: border-color .2s, box-shadow .2s;
    position: relative; overflow: hidden;
  }
  .card::before {
    content: '';
    position: absolute; inset: 0; border-radius: inherit;
    background: linear-gradient(135deg, rgba(123,94,167,.03) 0%, transparent 60%);
    pointer-events: none;
  }
  .card:hover { border-color: rgba(123,94,167,.4); }
  .card-glow:hover { box-shadow: 0 0 30px rgba(123,94,167,.12); }
  .card-sm { padding: 14px 16px; }
  .card-grid { display: grid; gap: 16px; }
  .grid-2 { grid-template-columns: 1fr 1fr; }
  .grid-3 { grid-template-columns: 1fr 1fr 1fr; }
  .grid-4 { grid-template-columns: repeat(4, 1fr); }

  /* ── Stat cards with glow accents ── */
  .stat-card {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg); padding: 22px;
    position: relative; overflow: hidden;
    transition: all .2s;
  }

  .stat-card:hover { border-color: rgba(123,94,167,.35); transform: translateY(-1px); }
  .stat-num {
    font-family: var(--font-disp);
    font-size: 30px; font-weight: 700; line-height: 1;
    background: linear-gradient(135deg, var(--text), var(--accent-h));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    color: var(--text);
  }
  .stat-label { font-size: 11px; color: var(--muted); margin-top: 6px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; }

  /* ── Typography ── */
  h1 { font-size: 26px; font-weight: 700; letter-spacing: -.3px; }
  h2 { font-size: 18px; font-weight: 700; }
  h3 { font-size: 14px; font-weight: 600; letter-spacing: .3px; }
  .muted { color: var(--muted); font-size: 13px; }
  .mono { font-family: var(--mono); }
  .label {
    font-size: 9px; font-weight: 700; letter-spacing: 1.5px;
    text-transform: uppercase; color: var(--muted);
  }
  .orbitron { font-family: var(--font-disp); }

  /* ── Pills / Badges ── */
  .pill {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 3px 10px; border-radius: 20px;
    font-size: 11px; font-weight: 700; letter-spacing: .3px;
  }
  .pill-easy   { background: rgba(0,229,160,.12); color: var(--accent2); border: 1px solid rgba(0,229,160,.2); }
  .pill-medium { background: rgba(245,200,66,.12); color: var(--gold); border: 1px solid rgba(245,200,66,.2); }
  .pill-hard   { background: rgba(255,77,109,.12); color: var(--accent3); border: 1px solid rgba(255,77,109,.2); }
  .pill-accent { background: rgba(123,94,167,.18); color: var(--accent-h); border: 1px solid rgba(123,94,167,.3); }
  .pill-green  { background: rgba(0,229,160,.12); color: var(--accent2); border: 1px solid rgba(0,229,160,.2); }
  .pill-gold   { background: rgba(245,200,66,.12); color: var(--gold); }
  .pill-red    { background: rgba(255,77,109,.12); color: var(--accent3); }
  .pill-muted  { background: rgba(255,255,255,.06); color: var(--muted); border: 1px solid var(--border); }
  .pill-cyan   { background: rgba(0,212,255,.12); color: var(--cyan); border: 1px solid rgba(0,212,255,.2); }

  /* ── Type pills ── */
  .type-pill-mcq     { background: rgba(0,212,255,.1); color: var(--cyan); border: 1px solid rgba(0,212,255,.2); border-radius:6px; padding:2px 8px; font-size:10px; font-weight:700; }
  .type-pill-debug   { background: rgba(245,200,66,.1); color: var(--gold); border: 1px solid rgba(245,200,66,.2); border-radius:6px; padding:2px 8px; font-size:10px; font-weight:700; }
  .type-pill-sysdes  { background: rgba(255,127,63,.1); color: var(--orange); border: 1px solid rgba(255,127,63,.2); border-radius:6px; padding:2px 8px; font-size:10px; font-weight:700; }
  .type-pill-coding  { background: rgba(123,94,167,.12); color: var(--accent-h); border: 1px solid rgba(123,94,167,.25); border-radius:6px; padding:2px 8px; font-size:10px; font-weight:700; }

  /* ── Status dots ── */
  .dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
  .dot-green  { background: var(--accent2); box-shadow: 0 0 6px var(--accent2); }
  .dot-yellow { background: var(--gold); }
  .dot-red    { background: var(--accent3); }
  .dot-blue   { background: var(--cyan); }

  /* ── Buttons ── */
  .btn {
    display: inline-flex; align-items: center; justify-content: center; gap: 6px;
    padding: 9px 20px; border-radius: var(--radius);
    font-size: 13px; font-weight: 600; font-family: var(--font);
    cursor: pointer; border: none; transition: all .18s;
    letter-spacing: .3px; position: relative; overflow: hidden;
  }
  .btn::after {
    content: '';
    position: absolute; inset: 0;
    background: linear-gradient(135deg, rgba(255,255,255,.08), transparent);
    opacity: 0; transition: opacity .18s;
  }
  .btn:hover::after { opacity: 1; }
  .btn-primary {
    background: linear-gradient(135deg, var(--accent), #5a3f8a);
    color: #fff;
    box-shadow: 0 4px 20px rgba(123,94,167,.4);
  }
  .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 6px 28px rgba(123,94,167,.5); }
  .btn-primary:active { transform: none; }
  .btn-secondary {
    background: var(--bg3); color: var(--text);
    border: 1px solid var(--border2);
  }
  .btn-secondary:hover { border-color: var(--accent); color: var(--accent-h); }
  .btn-ghost { background: transparent; color: var(--muted); }
  .btn-ghost:hover { color: var(--text); background: var(--bg3); }
  .btn-success {
    background: linear-gradient(135deg, #006644, #00a86b);
    color: #fff; box-shadow: 0 4px 20px rgba(0,229,160,.25);
  }
  .btn-success:hover { transform: translateY(-1px); box-shadow: 0 6px 28px rgba(0,229,160,.35); }
  .btn-sm { padding: 6px 14px; font-size: 12px; }
  .btn-danger { background: rgba(255,77,109,.15); color: var(--accent3); border: 1px solid rgba(255,77,109,.3); }
  .btn-danger:hover { background: rgba(255,77,109,.25); }
  .btn:disabled { opacity: .45; cursor: not-allowed; transform: none !important; }

  /* ── Inputs ── */
  .input, .textarea, .select {
    background: var(--bg3); border: 1px solid var(--border2);
    border-radius: var(--radius); padding: 10px 14px;
    color: var(--text); font-family: var(--font); font-size: 13.5px;
    width: 100%; outline: none; transition: all .18s;
  }
  .input:focus, .textarea:focus, .select:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(123,94,167,.12);
  }
  .input::placeholder, .textarea::placeholder { color: var(--muted); }
  .textarea { resize: vertical; min-height: 80px; font-family: var(--mono); font-size: 13px; }
  .form-group { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }
  .form-label { font-size: 11px; font-weight: 700; color: var(--muted); letter-spacing: .8px; text-transform: uppercase; }

  /* ── Skill bars ── */
  .skill-bar { height: 4px; border-radius: 2px; background: var(--bg4); overflow: hidden; margin-top: 8px; }
  .skill-bar-fill {
    height: 100%; border-radius: 2px;
    background: linear-gradient(90deg, var(--accent), var(--cyan));
    transition: width 1s cubic-bezier(.4,0,.2,1);
    position: relative;
  }
  .skill-bar-fill::after {
    content: '';
    position: absolute; right: 0; top: -1px;
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--cyan);
    box-shadow: 0 0 8px var(--cyan);
  }

  /* ── Table ── */
  .table { width: 100%; border-collapse: collapse; }
  .table th {
    padding: 10px 14px; text-align: left;
    font-size: 10px; font-weight: 700; letter-spacing: 1.2px;
    text-transform: uppercase; color: var(--muted);
    border-bottom: 1px solid var(--border);
    font-family: var(--font);
  }
  .table td {
    padding: 12px 14px; font-size: 13px;
    border-bottom: 1px solid rgba(30,30,46,.8);
    vertical-align: middle;
  }
  .table tr { transition: background .12s; cursor: pointer; }
  .table tr:hover td { background: rgba(123,94,167,.06); }
  .table tr.solved-row td:first-child { border-left: 2px solid var(--accent2); }

  /* ── Code editor ── */
  .editor-wrap {
    border: 1px solid var(--border2); border-radius: var(--radius);
    overflow: hidden;
    box-shadow: 0 0 0 1px rgba(123,94,167,.08), inset 0 1px 0 rgba(255,255,255,.03);
  }
  .editor-header {
    background: var(--bg3); padding: 8px 14px;
    display: flex; align-items: center; gap: 10px;
    border-bottom: 1px solid var(--border);
    font-size: 12px; color: var(--text2);
  }
  .editor-dot { width: 10px; height: 10px; border-radius: 50%; }
  .editor-footer {
    background: var(--bg3); padding: 8px 14px;
    display: flex; align-items: center; justify-content: space-between;
    border-top: 1px solid var(--border);
    font-size: 12px;
  }

  /* ── Progress ring ── */
  .ring-wrap { position: relative; display: inline-flex; align-items: center; justify-content: center; }
  .ring-label { position: absolute; font-size: 13px; font-weight: 800; text-align: center; font-family: var(--font-disp); }

  /* ── Tabs ── */
  .tabs { display: flex; gap: 0; border-bottom: 1px solid var(--border); margin-bottom: 20px; overflow-x: auto; }
  .tab {
    padding: 10px 18px; font-size: 12.5px; font-weight: 600;
    color: var(--muted); cursor: pointer; transition: all .18s;
    border-bottom: 2px solid transparent; margin-bottom: -1px;
    white-space: nowrap; letter-spacing: .3px;
  }
  .tab:hover { color: var(--text2); }
  .tab.active { color: var(--accent-h); border-bottom-color: var(--accent-h); }

  /* ── Animations ── */
  @keyframes fadeIn  { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
  @keyframes fadeInL { from { opacity: 0; transform: translateX(-12px); } to { opacity: 1; transform: none; } }
  @keyframes pulse   { 0%,100% { opacity: 1; } 50% { opacity: .4; } }
  @keyframes spin    { to { transform: rotate(360deg); } }
  @keyframes slideIn { from { opacity: 0; transform: translateX(12px); } to { opacity: 1; transform: none; } }
  @keyframes glow    { 0%,100% { box-shadow: 0 0 8px var(--glow); } 50% { box-shadow: 0 0 24px var(--glow); } }
  @keyframes scanline { 0% { top: -5%; } 100% { top: 105%; } }
  .fade-in  { animation: fadeIn .35s ease forwards; }
  .fade-in-l { animation: fadeInL .3s ease forwards; }
  .loading  { animation: pulse 1.5s infinite; }
  .spinner  { animation: spin .7s linear infinite; display: inline-block; }

  /* ── Auth screen ── */
  .auth-wrap {
    min-height: 100vh; display: flex; align-items: center; justify-content: center;
    background:
      radial-gradient(ellipse at 20% 20%, rgba(123,94,167,.12) 0%, transparent 50%),
      radial-gradient(ellipse at 80% 80%, rgba(0,212,255,.07) 0%, transparent 50%),
      var(--bg);
    position: relative;
  }
  .auth-wrap::before {
    content: '';
    position: absolute; inset: 0;
    background:
      repeating-linear-gradient(0deg, transparent, transparent 39px, rgba(123,94,167,.04) 40px),
      repeating-linear-gradient(90deg, transparent, transparent 39px, rgba(123,94,167,.04) 40px);
    pointer-events: none;
  }
  .auth-card {
    background: rgba(13,13,18,.92);
    border: 1px solid var(--border2);
    border-radius: 20px; padding: 40px; width: 420px;
    box-shadow: 0 0 60px rgba(0,0,0,.6), 0 0 0 1px rgba(123,94,167,.12);
    backdrop-filter: blur(20px);
    position: relative; z-index: 1;
  }
  .auth-card::before {
    content: '';
    position: absolute; top: -1px; left: 30px; right: 30px;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--accent), transparent);
    opacity: .6;
  }
  .auth-logo {
    font-family: var(--font-disp);
    font-size: 22px; font-weight: 900; margin-bottom: 6px;
    letter-spacing: 2px;
    background: linear-gradient(135deg, var(--accent-h), var(--cyan));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .auth-sub { color: var(--muted); font-size: 13px; margin-bottom: 28px; }

  /* ── Toast ── */
  .toast {
    position: fixed; bottom: 24px; right: 24px;
    background: var(--bg3);
    border: 1px solid var(--border2);
    border-radius: 12px; padding: 14px 20px;
    font-size: 13px; z-index: 9999;
    animation: slideIn .3s ease;
    max-width: 340px;
    box-shadow: 0 8px 32px rgba(0,0,0,.4);
    backdrop-filter: blur(16px);
  }
  .toast-success { border-left: 3px solid var(--accent2); }
  .toast-error   { border-left: 3px solid var(--accent3); }

  /* ── Rank badges ── */
  .rank-1 { color: var(--gold); font-family: var(--font-disp); font-weight: 700; }
  .rank-2 { color: #c0c0c0; }
  .rank-3 { color: #cd7f32; }

  /* ── Code output ── */
  .output-box {
    background: #050508;
    border: 1px solid var(--border);
    border-radius: var(--radius); padding: 14px 16px;
    font-family: var(--mono); font-size: 12.5px;
    line-height: 1.8; max-height: 220px; overflow-y: auto;
    color: var(--text2);
  }
  .output-accepted { border-left: 3px solid var(--accent2); color: var(--accent2); }
  .output-wrong    { border-left: 3px solid var(--accent3); }
  .output-error    { border-left: 3px solid var(--gold); }

  /* ── Problem list row ── */
  .prob-row { cursor: pointer; transition: all .15s; }
  .prob-row:hover { background: rgba(123,94,167,.05) !important; }
  .prob-row.solved td:nth-child(1)::before {
    content: '✓'; color: var(--accent2); font-weight: 700; margin-right: 8px;
  }

  /* ── Difficulty pill in table ── */
  td .diff { display: inline-block; font-size: 11px; font-weight: 700; }
  td .diff-easy { color: var(--accent2); }
  td .diff-medium { color: var(--gold); }
  td .diff-hard { color: var(--accent3); }

  /* ── Dashboard hero ── */
  .hero-bar {
    background: linear-gradient(135deg, rgba(123,94,167,.15) 0%, rgba(0,212,255,.06) 100%);
    border: 1px solid rgba(123,94,167,.25);
    border-radius: var(--radius-lg); padding: 28px 32px;
    position: relative; overflow: hidden;
    margin-bottom: 24px;
  }
  .hero-bar::before {
    content: '';
    position: absolute; top: -40px; right: -40px;
    width: 180px; height: 180px; border-radius: 50%;
    background: radial-gradient(circle, rgba(123,94,167,.2), transparent 70%);
    pointer-events: none;
  }
  .hero-bar::after {
    content: 'SKILLOS';
    position: absolute; right: 32px; bottom: 16px;
    font-family: var(--font-disp); font-size: 56px; font-weight: 900;
    color: rgba(123,94,167,.05); letter-spacing: 4px;
    pointer-events: none; user-select: none;
  }
  .hero-greeting {
    font-family: var(--font-disp);
    font-size: 11px; letter-spacing: 3px;
    color: var(--accent-h); text-transform: uppercase; margin-bottom: 6px;
  }
  .hero-name { font-size: 24px; font-weight: 700; margin-bottom: 4px; }
  .hero-sub { color: var(--text2); font-size: 13px; }

  /* ── Streak ── */
  .streak-fire {
    font-size: 22px;
    filter: drop-shadow(0 0 8px rgba(255,127,63,.6));
    animation: glow 2s ease infinite;
  }
  .streak-num {
    font-family: var(--font-disp); font-size: 28px; font-weight: 900;
    color: var(--orange);
    text-shadow: 0 0 20px rgba(255,127,63,.5);
  }

  /* ── Problem panel (solve view) ── */
  .solve-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 0; height: calc(100vh - 60px); }
  .solve-left { overflow-y: auto; border-right: 1px solid var(--border); padding: 24px; }
  .solve-right { display: flex; flex-direction: column; overflow: hidden; }

  /* ── Language selector ── */
  .lang-btn {
    padding: 5px 12px; border-radius: 6px; font-size: 11.5px; font-weight: 600;
    cursor: pointer; border: 1px solid transparent; transition: all .15s;
    font-family: var(--mono); color: var(--muted); background: transparent;
  }
  .lang-btn:hover { color: var(--text); border-color: var(--border2); }
  .lang-btn.active { background: rgba(123,94,167,.2); color: var(--accent-h); border-color: rgba(123,94,167,.4); }

  /* ── MCQ options ── */
  .mcq-option {
    display: flex; align-items: center; gap: 12px;
    padding: 14px 18px; border-radius: var(--radius);
    border: 1px solid var(--border2); cursor: pointer;
    transition: all .18s; margin-bottom: 8px;
    background: var(--bg3);
    font-size: 13.5px;
  }
  .mcq-option:hover { border-color: rgba(123,94,167,.4); background: rgba(123,94,167,.06); }
  .mcq-option.selected { border-color: var(--accent); background: rgba(123,94,167,.12); color: var(--accent-h); }
  .mcq-option.correct  { border-color: var(--accent2); background: rgba(0,229,160,.08); color: var(--accent2); }
  .mcq-option.wrong    { border-color: var(--accent3); background: rgba(255,77,109,.08); color: var(--accent3); }
  .mcq-letter {
    width: 26px; height: 26px; border-radius: 6px; flex-shrink: 0;
    background: var(--bg4); display: flex; align-items: center; justify-content: center;
    font-family: var(--font-disp); font-size: 11px; font-weight: 700;
    border: 1px solid var(--border2);
  }

  /* ── Empty state ── */
  .empty-state { text-align: center; padding: 60px 40px; color: var(--muted); }
  .empty-state .icon { font-size: 48px; margin-bottom: 14px; opacity: .6; }
  .empty-state h3 { font-size: 16px; color: var(--text2); margin-bottom: 6px; }

  /* ── Daily challenge card ── */
  .daily-card {
    background: linear-gradient(135deg, rgba(0,212,255,.08) 0%, rgba(123,94,167,.08) 100%);
    border: 1px solid rgba(0,212,255,.2);
    border-radius: var(--radius-lg); padding: 22px;
    position: relative; overflow: hidden;
  }
  .daily-card::before {
    content: '⚡';
    position: absolute; right: 20px; top: 16px;
    font-size: 36px; opacity: .15;
  }

  /* ── Leaderboard ── */
  .lb-row-1 { background: rgba(245,200,66,.04) !important; }
  .lb-row-2 { background: rgba(192,192,192,.03) !important; }
  .lb-row-3 { background: rgba(205,127,50,.03) !important; }

  /* ── Misc utilities ── */
  .flex { display: flex; }
  .flex-col { flex-direction: column; }
  .items-center { align-items: center; }
  .items-start { align-items: flex-start; }
  .justify-between { justify-content: space-between; }
  .justify-center { justify-content: center; }
  .gap-4 { gap: 4px; }
  .gap-6 { gap: 6px; }
  .gap-8 { gap: 8px; }
  .gap-12 { gap: 12px; }
  .gap-16 { gap: 16px; }
  .gap-20 { gap: 20px; }
  .mt-4 { margin-top: 4px; }
  .mt-8 { margin-top: 8px; }
  .mt-12 { margin-top: 12px; }
  .mt-16 { margin-top: 16px; }
  .mt-20 { margin-top: 20px; }
  .mb-8 { margin-bottom: 8px; }
  .mb-12 { margin-bottom: 12px; }
  .mb-16 { margin-bottom: 16px; }
  .mb-20 { margin-bottom: 20px; }
  .text-right { text-align: right; }
  .text-center { text-align: center; }
  .w-full { width: 100%; }
  .truncate { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .border-top { border-top: 1px solid var(--border); padding-top: 16px; margin-top: 16px; }
  .divider { height: 1px; background: var(--border); margin: 16px 0; }
  .text-accent { color: var(--accent-h); }
  .text-green { color: var(--accent2); }
  .text-red { color: var(--accent3); }
  .text-gold { color: var(--gold); }
  .text-cyan { color: var(--cyan); }

  /* ── Search ── */
  .search-wrap { position: relative; }
  .search-wrap .input { padding-left: 36px; }
  .search-icon { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--muted); font-size: 14px; }

  /* ── Filter pills ── */
  .filter-pill {
    padding: 5px 14px; border-radius: 20px; font-size: 11.5px; font-weight: 600;
    cursor: pointer; border: 1px solid var(--border2); transition: all .15s;
    color: var(--muted); background: transparent;
  }
  .filter-pill:hover { color: var(--text); border-color: var(--border2); }
  .filter-pill.active { background: rgba(123,94,167,.2); color: var(--accent-h); border-color: rgba(123,94,167,.4); }

  /* ── Keyboard shortcuts hint ── */
  .kbd {
    display: inline-flex; align-items: center; justify-content: center;
    background: var(--bg4); border: 1px solid var(--border2);
    border-radius: 4px; padding: 1px 6px;
    font-family: var(--mono); font-size: 10px; color: var(--muted);
    box-shadow: 0 1px 0 var(--border2);
  }

  /* ── PWA Install Banner ── */
  .install-banner {
    position: fixed; bottom: 0; left: 0; right: 0;
    background: linear-gradient(135deg, rgba(13,13,18,.97), rgba(20,20,32,.97));
    border-top: 1px solid rgba(123,94,167,.3);
    padding: 16px 24px; display: flex; align-items: center; gap: 16px;
    z-index: 1000; backdrop-filter: blur(20px);
    box-shadow: 0 -8px 40px rgba(0,0,0,.4);
  }

  /* ── Mobile / PWA Responsive ── */
  @media (max-width: 768px) {
    .sidebar {
      width: 100%; height: auto;
      position: fixed; bottom: 0; top: auto;
      flex-direction: row; border-right: none;
      border-top: 1px solid var(--border);
      z-index: 200; overflow-x: auto;
      background: rgba(6,6,8,.96);
      backdrop-filter: blur(20px);
    }
    .sidebar::after { display: none; }
    .logo { display: none; }
    .sidebar-user { display: none; }
    .nav { display: flex; flex-direction: row; padding: 0; overflow-x: auto; flex: 1; }
    .nav-section { display: none; }
    .nav-item {
      padding: 8px 12px; flex-direction: column;
      gap: 3px; min-width: 58px; text-align: center;
      border-radius: 0; margin: 0;
      font-size: 10px; border: none;
    }
    .nav-item.active { background: rgba(123,94,167,.12); border-bottom: 2px solid var(--accent-h); }
    .nav-item.active::before { display: none; }
    .nav-icon { font-size: 17px; width: auto; }
    .main { margin-left: 0; padding-bottom: 72px; }
    .content { padding: 14px 16px; }
    .topbar { padding: 10px 16px; }
    .card-grid.grid-2 { grid-template-columns: 1fr; }
    .card-grid.grid-3 { grid-template-columns: 1fr 1fr; }
    .card-grid.grid-4 { grid-template-columns: 1fr 1fr; }
    .auth-card { width: calc(100vw - 32px); padding: 28px 20px; }
    .solve-layout { grid-template-columns: 1fr; height: auto; }
    .solve-left { border-right: none; border-bottom: 1px solid var(--border); }
    h1 { font-size: 20px; }
    h2 { font-size: 16px; }
    .table th, .table td { padding: 8px 10px; font-size: 12px; }
    .hero-bar::after { display: none; }
    .stat-num { font-size: 24px; }
  }

  @media (max-width: 480px) {
    .card-grid.grid-3 { grid-template-columns: 1fr; }
    .card-grid.grid-4 { grid-template-columns: 1fr 1fr; }
  }




  /* ── Mobile drawer ── */
  .mobile-header { display: none; }
  .mobile-logout { display: none; }
  .sidebar-overlay { display: none; }
  .sidebar-close { display: none; }
  .hamburger { display: none; }

  @media (max-width: 768px) {
    .mobile-header {
      display: flex; align-items: center; justify-content: space-between;
      padding: 0 16px; position: fixed; top: 0; left: 0; right: 0;
      background: rgba(6,6,8,.97); backdrop-filter: blur(20px);
      border-bottom: 1px solid var(--border); z-index: 300; height: 52px;
    }
    .hamburger {
      display: flex !important; align-items: center; justify-content: center;
      background: none; border: none; color: #ffffff; font-size: 26px;
      cursor: pointer; padding: 4px 8px; border-radius: 6px; line-height: 1;
      min-width: 40px;
    }
    .mobile-logo { font-weight: 800; font-size: 16px; letter-spacing: 1px; color: var(--text); }
    .mobile-logo span { color: var(--accent-h); }
    .sidebar-overlay {
      display: block; position: fixed; inset: 0;
      background: rgba(0,0,0,.6); backdrop-filter: blur(3px); z-index: 399;
    }
    .sidebar {
      position: fixed; top: 0; left: 0; bottom: 0;
      width: 260px !important; height: 100% !important;
      transform: translateX(-100%);
      transition: transform 0.25s cubic-bezier(.4,0,.2,1);
      z-index: 400; flex-direction: column !important;
      overflow-y: auto; overflow-x: hidden;
      border-right: 1px solid var(--border) !important;
      border-top: none !important;
    }
    .sidebar.sidebar-open { transform: translateX(0); }
    .sidebar-close {
      display: flex; align-items: center; justify-content: center;
      position: absolute; top: 14px; right: 12px;
      background: var(--bg2); border: 1px solid var(--border);
      color: var(--muted); width: 28px; height: 28px;
      border-radius: 6px; cursor: pointer; font-size: 13px; z-index: 10;
    }
    .logo { display: flex !important; }
    .sidebar-user { display: flex !important; }
    .nav-section { display: block !important; }
    .nav { flex-direction: column !important; padding: 8px 0 !important; }
    .nav > div { display: block !important; }
    .nav-item { flex-direction: row !important; padding: 10px 16px !important; gap: 10px !important; font-size: 13px !important; min-width: unset !important; }
    .nav-icon { font-size: 16px !important; }
    .main { margin-left: 0 !important; padding-top: 52px !important; }
    .topbar { display: none; }
    .content { padding: 14px 16px; }
    .card-grid.grid-2 { grid-template-columns: 1fr; }
    .card-grid.grid-3 { grid-template-columns: 1fr 1fr; }
    .card-grid.grid-4 { grid-template-columns: 1fr 1fr; }
    .auth-card { width: calc(100vw - 32px); padding: 28px 20px; }
    .solve-layout { grid-template-columns: 1fr !important; height: auto !important; }
    .solve-left { border-right: none !important; border-bottom: 1px solid var(--border); }
    h1 { font-size: 20px; } h2 { font-size: 16px; }
    .stat-num { font-size: 24px; }
    .hero-bar::after { display: none; }
  }
  @media (max-width: 480px) {
    .card-grid.grid-3 { grid-template-columns: 1fr; }
    .card-grid.grid-4 { grid-template-columns: 1fr 1fr; }
  }

  /* ── PWA safe areas (iPhone notch etc.) ── */
  @supports (padding: max(0px)) {
    .sidebar { padding-bottom: max(0px, env(safe-area-inset-bottom)); }
    .topbar  { padding-top: max(10px, env(safe-area-inset-top)); }
  }
`

// ─── HELPERS ─────────────────────────────────────────────────────────────────
function useToken() {
  const [token, setToken] = useState(() => localStorage.getItem("sk_token") || null);
  const save = (t) => { setToken(t); localStorage.setItem("sk_token", t); };
  const clear = () => { setToken(null); localStorage.removeItem("sk_token"); };
  return [token, save, clear];
}

function Toast({ msg, type = "success", onClose }) {
  useEffect(() => { const t = setTimeout(onClose, 3000); return () => clearTimeout(t); }, []);
  return <div className={`toast toast-${type}`}>{msg}</div>;
}

function Spinner() {
  return <span className="spinner" style={{ fontSize: 18 }}>⟳</span>;
}

function Empty({ icon = "📭", msg = "Nothing here yet" }) {
  return <div className="empty-state"><div className="icon">{icon}</div><div>{msg}</div></div>;
}

function SkillBar({ score, name }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div className="flex justify-between items-center">
        <span style={{ fontSize: 12, fontWeight: 600 }}>{name}</span>
        <span style={{ fontSize: 12, color: "var(--accent)", fontFamily: "var(--mono)" }}>{Math.round(score)}</span>
      </div>
      <div className="skill-bar">
        <div className="skill-bar-fill" style={{ width: `${Math.min(score, 100)}%` }} />
      </div>
    </div>
  );
}

function DiffPill({ difficulty }) {
  return <span className={`pill pill-${difficulty || "easy"}`}>{difficulty || "easy"}</span>;
}

function StatCard({ num, label, accent }) {
  return (
    <div className="stat-card">
      <div style={{ fontSize: 30, fontWeight: 700, color: accent || "var(--text)", lineHeight: 1, marginBottom: 6 }}>{num ?? 0}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

// ─── AUTH ─────────────────────────────────────────────────────────────────────
function AuthPage({ onAuth }) {
  const [mode, setMode] = useState("login");
  const [forgotSent, setForgotSent] = useState(false);
  const [form, setForm] = useState({ email: "", password: "", display_name: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    setLoading(true); setError("");
    try {
      const path = mode === "login" ? "/auth/login" : "/auth/register";
      const payload = mode === 'register' ? { ...form, username: form.display_name } : form;
      const data = await api.post(path, payload);
      if (data.token) onAuth(data.token, data.user);
      else setError("Invalid credentials — try again");
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card fade-in">
        <div className="auth-logo">SKILL<span>OS</span></div>
        <div className="auth-sub">
          {mode === "login" ? "Sign in to your account" : mode === "forgot" ? "Reset your password" : "Create your free account"}
        </div>
        {mode === "register" && (
          <div className="form-group">
            <label className="form-label">DISPLAY NAME</label>
            <input className="input" placeholder="Your name"
              value={form.display_name}
              onChange={e => setForm({ ...form, display_name: e.target.value })} />
          </div>
        )}
        <div className="form-group">
          <label className="form-label">EMAIL</label>
          <input className="input" type="email" placeholder="you@email.com"
            value={form.email}
            onChange={e => setForm({ ...form, email: e.target.value })}
            onKeyDown={e => e.key === "Enter" && submit()} />
        </div>
        {mode !== "forgot" && (
          <div className="form-group">
            <label className="form-label">PASSWORD</label>
            <input className="input" type="password" placeholder="••••••••"
              value={form.password}
              onChange={e => setForm({ ...form, password: e.target.value })}
              onKeyDown={e => e.key === "Enter" && submit()} />
          </div>
        )}
        {error && <div style={{ color: "var(--accent3)", fontSize: 13, marginBottom: 12 }}>{error}</div>}
        {mode === "forgot" ? (
          forgotSent ? (
            <div style={{ textAlign: "center", padding: 16 }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>📧</div>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>Check your email!</div>
              <div className="muted" style={{ fontSize: 13 }}>We sent a reset link to {form.email}</div>
              <button className="btn btn-ghost mt-16" onClick={() => { setMode("login"); setForgotSent(false); }}>← Back to login</button>
            </div>
          ) : (
            <>
              <button className="btn btn-primary w-full" onClick={async () => {
                setLoading(true); setError("");
                try {
                  await api.post("/auth/forgot-password", { email: form.email });
                  setForgotSent(true);
                } catch(e) { setError(e.message); }
                finally { setLoading(false); }
              }} disabled={loading}>
                {loading ? <Spinner /> : "Send Reset Link"}
              </button>
              <div style={{ textAlign: "center", marginTop: 16, fontSize: 13 }}>
                <span style={{ color: "var(--accent)", cursor: "pointer" }} onClick={() => setMode("login")}>← Back to login</span>
              </div>
            </>
          )
        ) : (
          <>
            <button className="btn btn-primary w-full" onClick={submit} disabled={loading}>
              {loading ? <Spinner /> : (mode === "login" ? "Sign In" : "Create Account")}
            </button>
            {mode === "login" && (
              <div style={{ textAlign: "center", marginTop: 8, fontSize: 13 }}>
                <span style={{ color: "var(--accent)", cursor: "pointer" }} onClick={() => setMode("forgot")}>Forgot password?</span>
              </div>
            )}
            <div style={{ textAlign: "center", marginTop: 12, fontSize: 13, color: "var(--muted)" }}>
              {mode === "login" ? "No account?" : "Already registered?"}
              <span style={{ color: "var(--accent)", cursor: "pointer", marginLeft: 6 }}
                onClick={() => setMode(mode === "login" ? "register" : "login")}>
                {mode === "login" ? "Sign up free" : "Sign in"}
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ─── DASHBOARD ───────────────────────────────────────────────────────────────
function Dashboard({ token, user }) {
  const [profile, setProfile] = useState(null);
  const [daily, setDaily] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get("/users/me/profile", token).catch(() => null),
      api.get("/daily", token).catch(() => null),
      api.get("/analytics", token).catch(() => null),
    ]).then(([p, d, s]) => {
      setProfile(p?.profile); setDaily(d?.challenge); setStats(s);
    }).finally(() => setLoading(false));
  }, [token]);

  if (loading) return <div className="content loading" style={{ color: "var(--muted)" }}>Loading dashboard…</div>;

  const skills = profile?.skills || [];
  const topSkills = skills.filter(s => s.current_score > 0).sort((a, b) => b.current_score - a.current_score).slice(0, 4);

  return (
    <div className="content fade-in">
      <div className="hero-bar mb-20">
        <div className="hero-greeting">// WELCOME BACK</div>
        <div className="hero-name">{profile?.display_name || user?.display_name || "Developer"}</div>
        <div className="hero-sub flex items-center gap-12 mt-4">
          {profile?.streak_current > 0 ? (
            <span className="flex items-center gap-6">
              <span className="streak-fire">🔥</span>
              <span className="streak-num">{profile.streak_current}</span>
              <span style={{color:"var(--text2)"}}>day streak</span>
            </span>
          ) : (
            <span>Start your streak — solve a problem today</span>
          )}
          <span className="pill pill-accent">{profile?.unique_solved || 0} solved</span>
        </div>
      </div>

      <div className="card-grid grid-4 mb-16">
        <StatCard num={profile?.unique_solved || 0} label="Problems Solved" accent="var(--accent2)" />
        <StatCard num={profile?.reputation || 0}   label="Reputation"       accent="var(--gold)" />
        <StatCard num={profile?.streak_best || 0}  label="Best Streak"      accent="var(--accent)" />
        <StatCard num={stats?.certs_issued || 0}   label="Total Certs Issued" accent="var(--accent3)" />
      </div>

      <div className="card-grid grid-2">
        {/* Skill Overview */}
        <div className="card">
          <h3 className="mb-16">Your Skills</h3>
          {topSkills.length === 0
            ? <Empty icon="🎯" msg="Solve problems to build your skill scores" />
            : topSkills.map(s => <SkillBar key={s.id} score={s.current_score} name={s.name} />)
          }
        </div>

        {/* Daily Challenge */}
        <div className="daily-card">
          <div className="label mb-8" style={{color:"var(--cyan)"}}>⚡ Daily Challenge</div>
          {daily ? (
            <>
              <h3>{daily.title}</h3>
              <div className="flex gap-8 items-center mt-8 mb-12">
                <DiffPill difficulty={daily.difficulty} />
                <span className="muted">{daily.skill_name}</span>
              </div>
              <p style={{ fontSize: 13, color: "var(--muted)", lineHeight: 1.6 }}>
                {daily.description?.slice(0, 120)}...
              </p>
              <div className="mt-16">
                <span className="pill pill-accent" style={{ fontSize: 12 }}>🏆 Bonus XP today</span>
              </div>
            </>
          ) : <Empty icon="📅" msg="No daily challenge set yet" />}
        </div>

        {/* Recent Activity */}
        <div className="card" style={{ gridColumn: "1 / -1" }}>
          <h3 className="mb-16">Recent Activity</h3>
          {(profile?.recent_activity || []).length === 0
            ? <Empty icon="📋" msg="No submissions yet — start solving!" />
            : (
              <table className="table">
                <thead>
                  <tr><th>Problem</th><th>Skill</th><th>Difficulty</th><th>Status</th><th>When</th></tr>
                </thead>
                <tbody>
                  {(profile?.recent_activity || []).slice(0, 8).map((a, i) => (
                    <tr key={i}>
                      <td style={{ fontWeight: 600 }}>{a.title}</td>
                      <td className="muted">{a.skill_name || "—"}</td>
                      <td><DiffPill difficulty={a.difficulty} /></td>
                      <td>
                        <span className={`pill ${a.status === "accepted" ? "pill-green" : "pill-red"}`}>
                          {a.status === "accepted" ? "✓ Accepted" : "✗ " + a.status}
                        </span>
                      </td>
                      <td className="muted mono" style={{ fontSize: 11 }}>
                        {new Date(a.submitted_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
        </div>
      </div>
    </div>
  );
}

// ─── PROBLEMS ─────────────────────────────────────────────────────────────────
function Problems({ token, onToast }) {
  const [tasks, setTasks]       = useState([]);
  const [selected, setSelected] = useState(null);
  const [code, setCode]         = useState(STARTER_CODE.python3);
  const [language, setLanguage] = useState("python3");
  const [running, setRunning]   = useState(false);
  const [result, setResult]     = useState(null);
  const [filter, setFilter]     = useState("all");
  const [search, setSearch]     = useState("");
  const [domain, setDomain]     = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [mcqAnswer, setMcqAnswer]   = useState(null);
  const [sdAnswer, setSdAnswer]     = useState("");

  useEffect(() => {
    api.get("/tasks", token).then(d => setTasks(d.tasks || [])).catch(() => {});
  }, [token]);

  async function runCode() {
    // Quick test — runs against first visible test case only (fast feedback)
    if (!selected) return;
    setRunning(true); setResult(null);
    try {
      const sub = await api.post("/submit", { task_id: selected.id, code, language, run_only: true }, token);
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        const r = await api.get(`/submission/${sub.id}`, token);
        if (r.status !== "pending" && r.status !== "running" || attempts > 20) {
          clearInterval(poll); setResult({ ...r, run_only: true }); setRunning(false);
        }
      }, 1500);
    } catch(e) { setResult({ status: "error", error: e.message }); setRunning(false); }
  }

  async function submit() {
    if (!selected) return;
    setRunning(true); setResult(null);
    try {
      const sub = await api.post("/submit", { task_id: selected.id, code, language }, token);
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        const r = await api.get(`/submission/${sub.id}`, token);
        if (r.status !== "pending" && r.status !== "running" || attempts > 20) {
          clearInterval(poll); setResult(r); setRunning(false);
          if (r.status === "accepted") onToast("✓ Accepted! Skill scores updated", "success");
          else if (r.status === "compile_error") onToast("✗ Compile Error", "error");
          else onToast("✗ " + r.status, "error");
        }
      }, 1500);
    } catch(e) { setResult({ status: "error", error: e.message }); setRunning(false); }
  }

  const filtered = tasks.filter(t => {
    if (filter !== "all" && t.difficulty !== filter) return false;
    if (domain !== "all" && t.domain !== domain) return false;
    if (typeFilter !== "all" && t.problem_type !== typeFilter) return false;
    if (search && !t.title.toLowerCase().includes(search.toLowerCase()) &&
        !(t.skill_name||"").toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });
  const domains = ["all", ...new Set(tasks.map(t => t.domain).filter(Boolean))];

  const typeIcon = (t) => ({ mcq:"🔘", debugging:"🐛", system_design:"🏗️", coding:"💻", fill_in_blank:"✏️" })[t] || "💻";
  const typePill = (t) => {
    const map = { mcq:"type-pill-mcq", debugging:"type-pill-debug", system_design:"type-pill-sysdes", coding:"type-pill-coding", fill_in_blank:"type-pill-coding" };
    const labels = { mcq:"MCQ", debugging:"Debug", system_design:"Design", coding:"Code", fill_in_blank:"Fill" };
    const cls = map[t] || "type-pill-coding";
    return <span className={cls}>{typeIcon(t)} {labels[t] || t}</span>;
  };

  if (!selected) return (
    <div className="content fade-in">
      <div className="flex items-center justify-between mb-16">
        <div>
          <h2>Problems <span style={{color:"var(--muted)", fontWeight:400, fontSize:14}}>({filtered.length} of {tasks.length})</span></h2>
        </div>
        <div className="search-wrap" style={{width:240}}>
          <span className="search-icon">🔍</span>
          <input className="input" placeholder="Search problems…" value={search} onChange={e => setSearch(e.target.value)} />
        </div>
      </div>
      <div className="flex gap-8 mb-16" style={{flexWrap:"wrap"}}>
        <div className="flex gap-4" style={{alignItems:"center"}}>
          <span className="label" style={{marginRight:4}}>Diff:</span>
          {["all","easy","medium","hard"].map(f => (
            <button key={f} className={`filter-pill ${filter===f?"active":""}`}
              onClick={() => setFilter(f)}>{f==="all"?"All":f.charAt(0).toUpperCase()+f.slice(1)}</button>
          ))}
        </div>
        <div className="flex gap-4" style={{alignItems:"center", marginLeft:8}}>
          <span className="label" style={{marginRight:4}}>Type:</span>
          {[["all","All"],["coding","Code"],["mcq","MCQ"],["debugging","Debug"],["system_design","Design"]].map(([v,l]) => (
            <button key={v} className={`filter-pill ${typeFilter===v?"active":""}`}
              onClick={() => setTypeFilter(v)}>{l}</button>
          ))}
        </div>
      </div>
      <table className="table">
        <thead><tr>
          <th style={{width:40}}>#</th>
          <th>Title</th>
          <th style={{width:90}}>Type</th>
          <th>Skill</th>
          <th style={{width:85}}>Difficulty</th>
          <th style={{width:80}}></th>
        </tr></thead>
        <tbody>
          {filtered.map((t, i) => (
            <tr key={t.id} className="prob-row" onClick={() => {
              setSelected(t); setResult(null); setMcqAnswer(null); setSdAnswer("");
              if (t.problem_type === "debugging" && t.starter_code_broken) {
                setCode(t.starter_code_broken);
              } else if (t.starter_code) {
                setCode(t.starter_code);
              }
            }}>
              <td className="mono" style={{ fontSize:11, color:"var(--muted)" }}>{i+1}</td>
              <td style={{ fontWeight:600, fontSize:13.5 }}>{t.title}</td>
              <td>{typePill(t.problem_type)}</td>
              <td style={{ color:"var(--text2)", fontSize:12 }}>{t.skill_name || "—"}</td>
              <td><DiffPill difficulty={t.difficulty} /></td>
              <td><span style={{ color:"var(--accent-h)", fontSize:12, fontWeight:600 }}>Solve →</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  // ── MCQ Solver ───────────────────────────────────────────────────────────
  if (selected.problem_type === "mcq") {
    const options = (() => { try { return JSON.parse(selected.mcq_options || "[]"); } catch { return []; } })();

    return (
      <div className="content fade-in">
        <button className="btn btn-ghost mb-16" onClick={() => { setSelected(null); setResult(null); }}>← Back</button>
        <div className="card" style={{ maxWidth:680 }}>
          <div className="flex items-center gap-12 mb-16">
            <span className="type-pill-mcq">🔘 MULTIPLE CHOICE</span>
            <DiffPill difficulty={selected.difficulty} />
          </div>
          <h2 className="mb-16">{selected.title}</h2>
          <div style={{ fontSize:15, lineHeight:1.8, color:"var(--text)", marginBottom:24, whiteSpace:"pre-wrap" }}>
            {selected.description}
          </div>
          <div style={{ display:"flex", flexDirection:"column", gap:0 }}>
            {options.map((opt, i) => {
              let cls = "mcq-option";
              if (result) {
                if (i === result.mcq_correct) cls += " correct";
                else if (i === mcqAnswer) cls += " wrong";
              } else if (i === mcqAnswer) cls += " selected";
              return (
                <div key={i} className={cls}
                  onClick={() => !result && setMcqAnswer(i)}
                  style={{ cursor: result ? "default" : "pointer" }}>
                  <div className="mcq-letter">{String.fromCharCode(65+i)}</div>
                  <span style={{ fontSize:13.5, flex:1 }}>{opt}</span>
                  {result && i === result.mcq_correct && <span style={{ color:"var(--accent2)", fontWeight:700 }}>✓</span>}
                  {result && i === mcqAnswer && i !== result.mcq_correct && <span style={{ color:"var(--accent3)", fontWeight:700 }}>✗</span>}
                </div>
              );
            })}
          </div>
          {!result && (
            <button className="btn btn-primary mt-20"
              disabled={mcqAnswer === null || running}
              onClick={async () => {
                setRunning(true);
                try {
                  const sub = await api.post("/submit", {
                    task_id: selected.id, code: String(mcqAnswer),
                    language: "python3", mcq_answer: mcqAnswer
                  }, token);
                  let tries = 0;
                  const poll = setInterval(async () => {
                    const r = await api.get(`/submission/${sub.id}`, token);
                    if (r.status !== "pending" || tries++ > 15) {
                      clearInterval(poll); setResult({ ...r, mcq_correct: selected.mcq_correct_index }); setRunning(false);
                    }
                  }, 1000);
                } catch(e) { onToast(e.message, "error"); setRunning(false); }
              }}>
              {running ? "Checking…" : "Submit Answer"}
            </button>
          )}
          {result && (
            <div className={`card mt-16 ${result.status === "accepted" ? "border-green" : ""}`}
              style={{ borderColor: result.status === "accepted" ? "var(--accent2)" : "var(--accent3)" }}>
              <div style={{ fontWeight:700, fontSize:15, color: result.status === "accepted" ? "var(--accent2)" : "var(--accent3)", marginBottom:8 }}>
                {result.status === "accepted" ? "✅ Correct!" : "❌ Incorrect"}
              </div>
              {result.ai_feedback && <div style={{ fontSize:13, lineHeight:1.7, color:"var(--muted)" }}>{result.ai_feedback}</div>}
              <button className="btn btn-secondary btn-sm mt-12" onClick={() => { setResult(null); setMcqAnswer(null); }}>Try Again</button>
            </div>
          )}
        </div>
      </div>
    );
  }

  // ── System Design Solver ─────────────────────────────────────────────────
  if (selected.problem_type === "system_design") {
    const wordCount = sdAnswer.trim().split(/\s+/).filter(Boolean).length;

    return (
      <div className="content fade-in">
        <button className="btn btn-ghost mb-16" onClick={() => { setSelected(null); setResult(null); }}>← Back</button>
        <div style={{ maxWidth:760 }}>
          <div className="flex items-center gap-12 mb-12">
            <span className="type-pill-sysdes">🏗️ SYSTEM DESIGN</span>
            <DiffPill difficulty={selected.difficulty} />
          </div>
          <h2 className="mb-16">{selected.title}</h2>
          <div className="card mb-16">
            <div style={{ fontSize:14, lineHeight:1.9, color:"var(--text)", whiteSpace:"pre-wrap" }}>
              {selected.description}
            </div>
          </div>
          {!result ? (
            <div className="card">
              <div className="flex items-center justify-between mb-8">
                <div className="label">Your Design</div>
                <span className="muted" style={{ fontSize:11 }}>{wordCount} words {wordCount < 100 ? "— aim for 200+" : "✓"}</span>
              </div>
              <textarea
                value={sdAnswer} onChange={e => setSdAnswer(e.target.value)}
                placeholder="Write your system design here...&#10;&#10;Cover:&#10;• API design&#10;• Database choice&#10;• Scale considerations&#10;• Trade-offs"
                style={{ width:"100%", minHeight:280, background:"var(--bg3)", color:"var(--text)",
                         border:"1px solid var(--border)", borderRadius:8, padding:16, fontSize:14,
                         lineHeight:1.8, resize:"vertical", fontFamily:"inherit", boxSizing:"border-box" }}
              />
              <button className="btn btn-primary mt-12 w-full"
                disabled={wordCount < 20 || running}
                onClick={async () => {
                  setRunning(true);
                  try {
                    const sub = await api.post("/submit", {
                      task_id: selected.id, code: sdAnswer,
                      language: "python3", run_only: false
                    }, token);
                    let tries = 0;
                    const poll = setInterval(async () => {
                      const r = await api.get(`/submission/${sub.id}`, token);
                      if (r.status !== "pending" || tries++ > 30) {
                        clearInterval(poll); setResult(r); setRunning(false);
                        if (r.status === "accepted") onToast("✅ Design approved by AI!", "success");
                      }
                    }, 2000);
                  } catch(e) { onToast(e.message, "error"); setRunning(false); }
                }}>
                {running ? "AI is evaluating your design… (10-20s)" : "Submit for AI Review"}
              </button>
            </div>
          ) : (
            <div className="card">
              <div style={{ fontWeight:700, fontSize:16, color: result.status === "accepted" ? "var(--accent2)" : "var(--gold)", marginBottom:12 }}>
                {result.status === "accepted" ? "✅ Design Approved" : "📝 Needs Improvement"}
                {result.ai_score != null && <span className="mono" style={{ marginLeft:12, fontSize:18 }}>{result.ai_score}/100</span>}
              </div>
              {result.stdout_sample && (
                <div style={{ fontSize:14, lineHeight:1.8, color:"var(--text)", whiteSpace:"pre-wrap", marginBottom:16 }}>
                  {result.stdout_sample}
                </div>
              )}
              <button className="btn btn-secondary btn-sm" onClick={() => setResult(null)}>Revise Answer</button>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="content fade-in">
      <button className="btn btn-ghost mb-16" onClick={() => { setSelected(null); setResult(null); }}>← Back</button>
      <div className="card-grid grid-2" style={{ gap: 20 }}>
        <div>
          <div className="flex items-center gap-12 mb-16">
            <h2>{selected.title}</h2>
            <DiffPill difficulty={selected.difficulty} />
          </div>
          <div style={{ color: "var(--muted)", fontSize: 14, lineHeight: 1.7, whiteSpace: "pre-wrap" }}>
            {selected.description}
          </div>
          {selected.input_format && (
            <div className="mt-16">
              <div className="label mb-4">Input Format</div>
              <div className="mono" style={{ fontSize: 12, background: "var(--bg3)", padding: 12, borderRadius: 8, color: "var(--accent2)" }}>
                {selected.input_format}
              </div>
            </div>
          )}
        </div>
        <div>
          {selected.problem_type === "debugging" && (
            <div style={{ background:"rgba(245,158,11,.1)", border:"1px solid rgba(245,158,11,.3)", borderRadius:8,
                         padding:"10px 14px", marginBottom:12, fontSize:13, color:"#f59e0b" }}>
              🐛 <strong>Debugging Challenge</strong> — The code below has a bug. Find and fix it, then submit.
            </div>
          )}
          <div className="editor-wrap">
            <div className="editor-header">
              <span className="dot dot-red" /><span className="dot dot-yellow" /><span className="dot dot-green" />
              <span style={{ marginLeft: 8, flex: 1 }}>solution.{language === "python3" ? "py" : language === "javascript" ? "js" : language === "java" ? "java" : language === "cpp" ? "cpp" : language}</span>
              <select
                value={language}
                onChange={e => { setLanguage(e.target.value); setCode(STARTER_CODE[e.target.value] || ""); setResult(null); }}
                style={{ background: "var(--bg3)", color: "var(--muted)", border: "1px solid var(--border)", borderRadius: 4, padding: "2px 6px", fontSize: 11, cursor: "pointer" }}
              >
                <option value="python3">Python 3</option>
                <option value="javascript">JavaScript</option>
                <option value="java">Java</option>
                <option value="cpp">C++</option>
                <option value="c">C</option>
                <option value="go">Go</option>
              </select>
            </div>
            <MonacoEditor value={code} onChange={setCode} language={language} height={320} />
            <div className="editor-footer">
              <span className="muted" style={{ fontSize: 11 }}>⌘+Space autocomplete · Tab indent</span>
              <div style={{ display: "flex", gap: 8 }}>
                <button className="btn btn-secondary btn-sm" onClick={runCode} disabled={running} title="Run against sample test case">
                  {running ? "Running…" : "▷ Run"}
                </button>
                <button className="btn btn-primary btn-sm" onClick={submit} disabled={running} title="Submit against all test cases">
                  {running ? "Judging…" : "✓ Submit"}
                </button>
              </div>
            </div>
          </div>

          {result && (
            <div className="card mt-16 card-sm"
              style={{ borderColor: result.status==="accepted" ? "var(--accent2)" : result.status==="compile_error" ? "#f59e0b" : "var(--accent3)" }}>
              <div className={"pill mb-8 " + (result.status==="accepted" ? "pill-green" : result.status==="compile_error" ? "" : "pill-red")}
                style={{ fontSize: 13, background: result.status==="compile_error" ? "rgba(245,158,11,0.15)" : undefined, color: result.status==="compile_error" ? "#f59e0b" : undefined }}>
                {result.status === "accepted" ? "✓ ACCEPTED" :
                 result.status === "compile_error" ? "⚠ COMPILE ERROR" :
                 result.run_only ? "▷ RUN RESULT: " + (result.status||"").toUpperCase() :
                 "✗ " + (result.status || "").toUpperCase().replace("_"," ")}
              </div>
              {result.passed_cases != null && !result.run_only && (
                <div className="muted mono" style={{ fontSize: 12 }}>
                  {result.passed_cases}/{result.total_cases} test cases passed
                  {result.max_runtime_ms ? `· ${result.max_runtime_ms}ms` : ""}
                </div>
              )}
              {result.stdout_sample && (
                <div>
                  <div className="label mt-8 mb-4" style={{ fontSize: 10 }}>OUTPUT</div>
                  <div style={{ fontSize: 12, color: "var(--accent2)", fontFamily: "var(--mono)", whiteSpace: "pre-wrap", maxHeight: 120, overflow: "auto", background: "var(--bg3)", padding: 8, borderRadius: 6 }}>
                    {result.stdout_sample.slice(0, 500)}
                  </div>
                </div>
              )}
              {(result.stderr_sample || result.first_failure?.stderr) && (
                <div>
                  <div className="label mt-8 mb-4" style={{ fontSize: 10, color: "var(--accent3)" }}>ERROR</div>
                  <div style={{ fontSize: 12, color: "var(--accent3)", fontFamily: "var(--mono)", whiteSpace: "pre-wrap", maxHeight: 140, overflow: "auto", background: "rgba(255,80,80,0.05)", padding: 8, borderRadius: 6 }}>
                    {(result.stderr_sample || result.first_failure?.stderr || "").slice(0, 600)}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── LEADERBOARD ─────────────────────────────────────────────────────────────
function Leaderboard({ token }) {
  const [tab, setTab]     = useState("global");
  const [rows, setRows]   = useState([]);
  const [months, setMonths] = useState([]);
  const [selMonth, setSelMonth] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    let path = "/leaderboard";
    if (tab === "weekly")  path = "/leaderboard/weekly";
    if (tab === "monthly") path = selMonth ? `/leaderboard/monthly/${selMonth}` : "/leaderboard/monthly";
    api.get(path, token).then(d => {
      setRows(d.leaderboard || []);
      if (d.available_months) setMonths(d.available_months);
      setLoading(false);
    });
  }, [tab, token, selMonth]);

  const cols = tab === "global"  ? ["Rank","Developer","Total Score","Solved","Streak"] :
               tab === "weekly"  ? ["Rank","Developer","Solved This Week","Submissions"] :
                                   ["Rank","Developer","Solved This Month","Hard Solved","Skills Practiced"];

  return (
    <div className="content fade-in">
      <h2 className="mb-16">🏆 Leaderboard</h2>
      <div className="tabs mb-16">
        <div className={`tab ${tab==="global"?"active":""}`} onClick={() => setTab("global")}>🌍 All Time</div>
        <div className={`tab ${tab==="weekly"?"active":""}`} onClick={() => setTab("weekly")}>📅 This Week</div>
        <div className={`tab ${tab==="monthly"?"active":""}`} onClick={() => setTab("monthly")}>🗓️ Monthly</div>
      </div>
      {tab === "monthly" && months.length > 0 && (
        <div className="flex items-center gap-8 mb-16">
          <span className="muted" style={{ fontSize:12 }}>Month:</span>
          <select value={selMonth}
            onChange={e => setSelMonth(e.target.value)}
            style={{ background:"var(--bg3)", color:"var(--text)", border:"1px solid var(--border)", borderRadius:6, padding:"4px 10px", fontSize:13 }}>
            <option value="">Current</option>
            {months.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>
      )}
      {loading ? <div className="loading muted">Loading…</div> : (
        rows.length === 0 ? <Empty icon="🏆" msg="No rankings yet — solve some problems!" /> : (
          <table className="table">
            <thead><tr>{cols.map(c => <th key={c}>{c}</th>)}</tr></thead>
            <tbody>
              {rows.map(r => (
                <tr key={r.id}>
                  <td>
                    <span className={r.rank===1?"rank-1":r.rank===2?"rank-2":r.rank===3?"rank-3":""} style={{ fontWeight:700, fontFamily:"var(--mono)" }}>
                      {r.rank <= 3 ? ["🥇","🥈","🥉"][r.rank-1] : `#${r.rank}`}
                    </span>
                  </td>
                  <td>
                    <div className="flex items-center gap-8">
                      <div className="avatar-sm">{(r.display_name||"?")[0]}</div>
                      <div>
                        <div style={{ fontWeight:600 }}>{r.display_name}</div>
                        <div className="muted" style={{ fontSize:11 }}>@{r.username || "—"}</div>
                      </div>
                    </div>
                  </td>
                  {tab === "global" && <>
                    <td><span className="mono" style={{ color:"var(--accent)" }}>{Math.round(r.total_score || 0)}</span></td>
                    <td className="mono">{r.total_solved || 0}</td>
                    <td>{r.streak_current > 0 && <span className="pill pill-gold">🔥 {r.streak_current}d</span>}</td>
                  </>}
                  {tab === "weekly" && <>
                    <td className="mono" style={{ color:"var(--accent2)", fontWeight:700 }}>{r.solved_this_week || 0}</td>
                    <td className="mono muted">{r.submissions_this_week || 0}</td>
                  </>}
                  {tab === "monthly" && <>
                    <td className="mono" style={{ color:"var(--accent2)", fontWeight:700 }}>{r.solved_this_month || 0}</td>
                    <td className="mono">{r.hard_solved || 0}</td>
                    <td className="mono muted">{r.skills_practiced || 0}</td>
                  </>}
                </tr>
              ))}
            </tbody>
          </table>
        )
      )}
    </div>
  );
}

// ─── CONTESTS ─────────────────────────────────────────────────────────────────
function Contests({ token, onToast }) {
  const [contests, setContests]   = useState([]);
  const [selected, setSelected]   = useState(null);
  const [loading, setLoading]     = useState(true);
  const [joining, setJoining]     = useState(false);

  useEffect(() => {
    api.get("/contests", token).then(d => { setContests(d.contests || []); setLoading(false); });
  }, [token]);

  async function join(id) {
    setJoining(true);
    try {
      await api.post(`/contests/${id}/register`, {}, token);
      onToast("Registered! Good luck 🎉", "success");
      const detail = await api.get(`/contests/${id}`, token);
      setSelected(detail.contest);
    } catch(e) { onToast(e.message, "error"); }
    finally { setJoining(false); }
  }

  const statusColor = { active: "var(--accent2)", upcoming: "var(--gold)", ended: "var(--muted)" };

  if (selected) return (
    <div className="content fade-in">
      <button className="btn btn-ghost mb-16" onClick={() => setSelected(null)}>← Back</button>
      <div className="flex items-center gap-12 mb-8">
        <h2>{selected.title}</h2>
        <div className="dot" style={{ background: statusColor[selected.status] }} />
        <span style={{ color: statusColor[selected.status], fontSize: 12, fontWeight: 600 }}>
          {selected.status?.toUpperCase()}
        </span>
      </div>
      <div className="muted mb-20" style={{ fontSize: 14 }}>{selected.description}</div>

      <div className="card-grid grid-2">
        <div className="card">
          <h3 className="mb-16">Problems</h3>
          {(selected.problems || []).map((p, i) => (
            <div key={i} className="flex items-center justify-between" style={{ padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
              <div>
                <div style={{ fontWeight: 600 }}>{p.task_title}</div>
                <div className="flex gap-8 mt-4"><DiffPill difficulty={p.difficulty} /></div>
              </div>
              <div className="pill pill-gold">{p.points} pts</div>
            </div>
          ))}
        </div>
        <div className="card">
          <h3 className="mb-16">Live Standings</h3>
          {(selected.leaderboard || []).length === 0
            ? <Empty icon="🏁" msg="No participants yet" />
            : (selected.leaderboard || []).slice(0, 10).map((r, i) => (
              <div key={i} className="flex items-center justify-between" style={{ padding: "8px 0" }}>
                <div className="flex items-center gap-8">
                  <span style={{ fontFamily: "var(--mono)", fontWeight: 700, width: 24, color: i===0?"var(--gold)":"var(--muted)" }}>#{i+1}</span>
                  <span style={{ fontWeight: 600 }}>{r.display_name}</span>
                </div>
                <span className="mono" style={{ color: "var(--accent)" }}>{r.total_score}</span>
              </div>
            ))}
        </div>
      </div>

      {selected.status !== "ended" && (
        <button className="btn btn-primary mt-20" onClick={() => join(selected.id)} disabled={joining}>
          {joining ? <Spinner /> : "Join Contest"}
        </button>
      )}
    </div>
  );

  return (
    <div className="content fade-in">
      <h2 className="mb-20">Contests</h2>
      {loading ? <div className="loading muted">Loading…</div> : (
        contests.length === 0 ? <Empty icon="🏆" msg="No contests yet" /> : (
          <div className="card-grid grid-2">
            {contests.map(c => (
              <div key={c.id} className="card" style={{ cursor: "pointer", borderColor: c.status==="active"?"rgba(6,214,160,.3)":"var(--border)" }}
                onClick={async () => {
                  const d = await api.get(`/contests/${c.id}`, token);
                  setSelected(d.contest);
                }}>
                <div className="flex justify-between items-center mb-8">
                  <div className="dot" style={{ background: statusColor[c.status] }} />
                  <span style={{ fontSize: 11, fontWeight: 600, color: statusColor[c.status] }}>{c.status?.toUpperCase()}</span>
                </div>
                <h3 style={{ marginBottom: 8 }}>{c.title}</h3>
                <div className="muted" style={{ fontSize: 13, marginBottom: 16 }}>{c.description?.slice(0, 80)}…</div>
                <div className="flex gap-12 muted" style={{ fontSize: 12 }}>
                  <span>👥 {c.entrant_count || 0} registered</span>
                  <span>📝 {c.problem_count || 0} problems</span>
                </div>
              </div>
            ))}
          </div>
        )
      )}
    </div>
  );
}

// ─── LEARNING PATHS ───────────────────────────────────────────────────────────
function LearningPaths({ token, onToast }) {
  const [paths, setPaths]     = useState([]);
  const [selected, setSelected] = useState(null);
  const [myPaths, setMyPaths]   = useState([]);

  useEffect(() => {
    Promise.all([
      api.get("/paths", token).then(d => setPaths(d.paths || [])),
      api.get("/users/me/paths", token).then(d => setMyPaths(d.paths || [])),
    ]).catch(() => {});
  }, [token]);

  async function loadPath(id) {
    const d = await api.get(`/paths/${id}`, token);
    setSelected(d.path);
  }

  async function markDone(pathId, stepId) {
    try {
      const d = await api.post(`/paths/${pathId}/steps/${stepId}/complete`, {}, token);
      setSelected(d.path);
      onToast("Step completed! +XP", "success");
    } catch(e) { onToast(e.message, "error"); }
  }

  const diffColors = { beginner: "var(--accent2)", intermediate: "var(--gold)", advanced: "var(--accent3)" };

  if (selected) return (
    <div className="content fade-in">
      <button className="btn btn-ghost mb-16" onClick={() => setSelected(null)}>← Back to Paths</button>
      <div className="flex items-center justify-between mb-20">
        <div>
          <h2>{selected.title}</h2>
          <div className="muted mt-4">{selected.description}</div>
        </div>
        <div className="card card-sm" style={{ textAlign: "center", minWidth: 100 }}>
          <div style={{ fontSize: 28, fontWeight: 800, color: "var(--accent)" }}>{selected.progress_pct || 0}%</div>
          <div className="label">Complete</div>
        </div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {(selected.steps || []).map((step, i) => (
          <div key={step.id} className="card card-sm flex items-center gap-16"
            style={{ borderColor: step.completed ? "rgba(6,214,160,.3)" : "var(--border)" }}>
            <div style={{
              width: 32, height: 32, borderRadius: "50%", flexShrink: 0,
              background: step.completed ? "var(--accent2)" : "var(--bg3)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontWeight: 700, fontSize: 13
            }}>
              {step.completed ? "✓" : i + 1}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600 }}>{step.title}</div>
              <div className="muted" style={{ fontSize: 12 }}>{step.description}</div>
              {step.task_title && <div style={{ fontSize: 11, color: "var(--accent)", marginTop: 4 }}>📝 {step.task_title}</div>}
            </div>
            {!step.completed && (
              <button className="btn btn-sm btn-primary" onClick={() => markDone(selected.id, step.id)}>Mark Done</button>
            )}
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <div className="content fade-in">
      <h2 className="mb-20">Learning Paths</h2>
      <div className="card-grid grid-2">
        {paths.map(p => {
          const myP = myPaths.find(mp => mp.id === p.id);
          return (
            <div key={p.id} className="card" style={{ cursor: "pointer" }} onClick={() => loadPath(p.id)}>
              <div className="flex justify-between items-center mb-12">
                <span style={{ fontSize: 11, fontWeight: 700, color: diffColors[p.difficulty], textTransform: "uppercase", letterSpacing: 1 }}>
                  {p.difficulty}
                </span>
                <span className="pill pill-accent" style={{ fontSize: 11 }}>{p.domain}</span>
              </div>
              <h3 style={{ marginBottom: 8 }}>{p.title}</h3>
              <div className="muted" style={{ fontSize: 13, marginBottom: 16 }}>{p.description?.slice(0, 80)}…</div>
              <div className="skill-bar">
                <div className="skill-bar-fill" style={{ width: `${myP?.progress_pct || 0}%` }} />
              </div>
              <div className="flex justify-between mt-8" style={{ fontSize: 11, color: "var(--muted)" }}>
                <span>{p.total_steps} steps</span>
                <span>{myP?.progress_pct || 0}% done</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── COACHING ────────────────────────────────────────────────────────────────
function Coaching({ token }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/users/me/coaching", token)
      .then(d => { setReport(d.report); setLoading(false); })
      .catch(() => setLoading(false));
  }, [token]);

  if (loading) return (
    <div className="content" style={{ display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", gap:16, minHeight:300 }}>
      <div style={{ fontSize:40 }}>🤖</div>
      <div className="muted" style={{ fontSize:14 }}>Analysing your performance…</div>
      <div className="muted" style={{ fontSize:12 }}>AI is generating your personalised report</div>
    </div>
  );
  if (!report) return <div className="content"><Empty icon="🤖" msg="Could not load coaching report. Solve some problems first!" /></div>;

  const levelColor = { expert:"var(--gold)", advanced:"var(--accent)", intermediate:"var(--accent2)", beginner:"var(--muted)" };

  return (
    <div className="content fade-in">

      <div className="flex items-center gap-12 mb-20" style={{ flexWrap:"wrap" }}>
        <h2>🤖 AI Skill Coach</h2>
        <span className="pill pill-accent" style={{ textTransform:"capitalize", color: levelColor[report.overall_level] || "var(--accent)" }}>
          {report.overall_level || "beginner"}
        </span>
        {report.ai_powered
          ? <span className="pill" style={{ fontSize:10, background:"rgba(124,106,247,.15)", color:"var(--accent)", border:"1px solid rgba(124,106,247,.3)" }}>✦ AI POWERED</span>
          : <span className="pill" style={{ fontSize:10, background:"rgba(255,107,107,.1)", color:"var(--accent3)", border:"1px solid rgba(255,107,107,.2)" }}>rule-based · add ANTHROPIC_API_KEY for AI</span>
        }
      </div>

      <div className="card mb-16" style={{ background:"linear-gradient(135deg, rgba(124,106,247,.1), var(--bg2))", borderColor:"rgba(124,106,247,.3)" }}>
        <div className="flex items-center gap-16">
          <div style={{ textAlign:"center", minWidth:80 }}>
            <div style={{ fontSize:36, fontWeight:800, color:"var(--accent)", lineHeight:1 }}>{report.overall_score || 0}</div>
            <div className="muted" style={{ fontSize:11, marginTop:4 }}>OVERALL</div>
          </div>
          <div style={{ flex:1 }}>
            <div style={{ fontSize:14, lineHeight:1.7, color:"var(--text)" }}>{report.summary}</div>
            {report.career_path && (
              <div style={{ marginTop:10, display:"flex", alignItems:"center", gap:8 }}>
                <span style={{ fontSize:11, color:"var(--muted)" }}>CAREER PATH →</span>
                <span className="pill pill-accent" style={{ fontSize:12, fontWeight:700 }}>💼 {report.career_path}</span>
              </div>
            )}
          </div>
        </div>
        {report.motivational_message && (
          <div style={{ marginTop:16, padding:"10px 14px", background:"rgba(6,214,160,.06)", borderRadius:8, fontSize:13, color:"var(--accent2)", fontStyle:"italic", borderLeft:"3px solid var(--accent2)" }}>
            💬 {report.motivational_message}
          </div>
        )}
      </div>

      {report.insights?.length > 0 && (
        <div className="card mb-16">
          <h3 className="mb-12">📊 Insights</h3>
          {report.insights.map((ins, i) => (
            <div key={i} style={{ padding:"8px 0", borderBottom: i < report.insights.length-1 ? "1px solid var(--border)" : "none", fontSize:13, color:"var(--text)", lineHeight:1.6 }}>
              → {ins}
            </div>
          ))}
        </div>
      )}

      <div className="card-grid grid-2 mb-16">
        <div className="card">
          <h3 className="mb-12">✅ Strengths</h3>
          {!report.strengths?.length
            ? <div className="muted" style={{ fontSize:13 }}>Solve more problems to discover your strengths</div>
            : report.strengths.map((s, i) => (
              <div key={i} style={{ padding:"8px 0", borderBottom: i < report.strengths.length-1 ? "1px solid var(--border)" : "none" }}>
                <div className="flex items-center justify-between mb-4">
                  <span style={{ fontWeight:600, fontSize:13 }}>{s.skill_name || s.name}</span>
                  <span className="pill pill-green">{Math.round(s.score)}</span>
                </div>
                {s.insight && <div className="muted" style={{ fontSize:12 }}>{s.insight}</div>}
              </div>
            ))}
        </div>
        <div className="card">
          <h3 className="mb-12">⚠️ Needs Work</h3>
          {!report.weaknesses?.length
            ? <div className="muted" style={{ fontSize:13 }}>No critical weaknesses! Keep going.</div>
            : report.weaknesses.map((w, i) => (
              <div key={i} style={{ padding:"8px 0", borderBottom: i < report.weaknesses.length-1 ? "1px solid var(--border)" : "none" }}>
                <div className="flex items-center justify-between mb-4">
                  <span style={{ fontWeight:600, fontSize:13 }}>{w.skill_name}</span>
                  <span className={`pill ${w.priority === "high" ? "pill-red" : "pill-medium"}`}>{Math.round(w.score || 0)}</span>
                </div>
                {w.reason && <div className="muted" style={{ fontSize:12 }}>{w.reason.replace(/_/g, " ")}</div>}
              </div>
            ))}
        </div>
      </div>

      <div className="card mb-16">
        <h3 className="mb-16">💡 Personalised Recommendations</h3>
        {report.recommendations?.map((r, i) => (
          <div key={i} className="card card-sm mb-8" style={{ background:"var(--bg3)" }}>
            <div className="flex items-center gap-8 mb-6" style={{ flexWrap:"wrap" }}>
              <span className={`pill ${r.priority === "high" ? "pill-red" : r.priority === "medium" ? "pill-medium" : "pill-accent"}`} style={{ fontSize:10 }}>
                {r.priority?.toUpperCase()}
              </span>
              <span style={{ fontWeight:700, fontSize:13 }}>{r.title}</span>
              {r.estimated_time && <span className="muted" style={{ fontSize:11, marginLeft:"auto" }}>⏱ {r.estimated_time}</span>}
            </div>
            <div className="muted" style={{ fontSize:13, lineHeight:1.6 }}>{r.description || r.body || r.message}</div>
            {r.skill && <span className="pill pill-accent" style={{ marginTop:8, display:"inline-block", fontSize:11 }}>{r.skill}</span>}
          </div>
        ))}
      </div>

      {report.weekly_plan && (
        <div className="card mb-16">
          <h3 className="mb-16">📅 Your Weekly Plan</h3>
          <div className="card-grid grid-2">
            {Object.entries(report.weekly_plan).map(([day, task]) => (
              <div key={day} className="card card-sm" style={{ background:"var(--bg3)" }}>
                <div style={{ fontWeight:700, fontSize:12, color:"var(--accent)", textTransform:"uppercase", marginBottom:6 }}>{day}</div>
                <div style={{ fontSize:13, color:"var(--text)", lineHeight:1.5 }}>{task}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {report.next_problems?.length > 0 && (
        <div className="card">
          <h3 className="mb-16">🎯 Solve These Next</h3>
          <div className="card-grid grid-2">
            {report.next_problems.map((p, i) => (
              <div key={i} className="card card-sm" style={{ background:"var(--bg3)" }}>
                <div style={{ fontWeight:600, marginBottom:6 }}>{p.title}</div>
                <DiffPill difficulty={p.difficulty} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
// ─── COMMUNITY ────────────────────────────────────────────────────────────────
function Community({ token, onToast }) {
  const [discussions, setDiscs]  = useState([]);
  const [selected, setSelected]  = useState(null);
  const [creating, setCreating]  = useState(false);
  const [tab, setTab]            = useState("forum");
  const [form, setForm]          = useState({ title: "", body: "", tag: "general" });
  const [reply, setReply]        = useState("");
  const [search, setSearch]      = useState("");
  const [tagFilter, setTagFilter]= useState("all");
  const [leaderboard, setLb]     = useState([]);
  const [loading, setLoading]    = useState(true);

  const TAGS = ["general", "algorithms", "web-dev", "data-science", "security", "system-design", "career", "help"];
  const TAG_COLORS = { algorithms: "var(--accent)", "web-dev": "var(--cyan)", "data-science": "var(--gold)", security: "var(--accent3)", "system-design": "var(--accent2)", career: "var(--orange)", help: "var(--muted)", general: "var(--muted)" };

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.get("/discussions", token),
      api.get("/leaderboard", token),
    ]).then(([d, l]) => {
      setDiscs(d.discussions || []);
      setLb(l.leaderboard?.slice(0, 10) || []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [token]);

  async function createDisc() {
    if (!form.title.trim()) { onToast("Title required", "error"); return; }
    try {
      await api.post("/discussions", form, token);
      onToast("Discussion posted!", "success");
      setCreating(false); setForm({ title: "", body: "", tag: "general" });
      const d = await api.get("/discussions", token);
      setDiscs(d.discussions || []);
    } catch(e) { onToast(e.message, "error"); }
  }

  async function postReply(discId) {
    if (!reply.trim()) return;
    try {
      await api.post(`/discussions/${discId}/replies`, { body: reply }, token);
      onToast("Reply posted!", "success"); setReply("");
      const d = await api.get(`/discussions/${discId}`, token);
      setSelected(d.discussion);
    } catch(e) { onToast(e.message, "error"); }
  }

  async function vote(discId, value) {
    try {
      await api.post(`/discussions/${discId}/vote`, { vote: value }, token);
      const d = await api.get("/discussions", token);
      setDiscs(d.discussions || []);
    } catch {}
  }

  const filtered = discussions.filter(d => {
    const matchSearch = !search || d.title?.toLowerCase().includes(search.toLowerCase()) || d.body?.toLowerCase().includes(search.toLowerCase());
    const matchTag = tagFilter === "all" || d.tag === tagFilter;
    return matchSearch && matchTag;
  });

  if (creating) return (
    <div className="content fade-in">
      <button className="btn btn-ghost mb-16" onClick={() => setCreating(false)}>← Back</button>
      <h2 className="mb-20">Start a Discussion</h2>
      <div className="card" style={{ maxWidth: 680 }}>
        <div className="form-group">
          <label className="form-label">TAG</label>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 4 }}>
            {TAGS.map(t => (
              <button key={t} onClick={() => setForm({...form, tag: t})}
                className={`pill ${form.tag === t ? "pill-accent" : "pill-muted"}`}
                style={{ cursor: "pointer", fontSize: 12, border: "1px solid var(--border)", padding: "4px 10px" }}>
                {t}
              </button>
            ))}
          </div>
        </div>
        <div className="form-group">
          <label className="form-label">TITLE</label>
          <input className="input" placeholder="What's your question or topic?" value={form.title}
            onChange={e => setForm({...form, title: e.target.value})} />
        </div>
        <div className="form-group">
          <label className="form-label">BODY</label>
          <textarea className="textarea" rows={6} placeholder="Describe your question, share your approach, or start a discussion…"
            value={form.body} onChange={e => setForm({...form, body: e.target.value})} />
        </div>
        <button className="btn btn-primary" onClick={createDisc}>Post Discussion</button>
      </div>
    </div>
  );

  if (selected) return (
    <div className="content fade-in">
      <button className="btn btn-ghost mb-16" onClick={() => setSelected(null)}>← Back to Discussions</button>
      <div className="card mb-16">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-8">
            <div className="avatar-sm">{(selected.display_name || "?")[0]}</div>
            <span style={{ fontWeight: 600 }}>{selected.display_name}</span>
            <span className="muted" style={{ fontSize: 12 }}>{new Date(selected.created_at).toLocaleDateString()}</span>
          </div>
          {selected.tag && (
            <span style={{ fontSize: 11, fontWeight: 700, color: TAG_COLORS[selected.tag] || "var(--muted)", textTransform: "uppercase", letterSpacing: 1 }}>
              #{selected.tag}
            </span>
          )}
        </div>
        <h2 style={{ marginBottom: 12 }}>{selected.title}</h2>
        <div style={{ fontSize: 14, lineHeight: 1.7, color: "var(--muted)", whiteSpace: "pre-wrap" }}>{selected.body}</div>
        <div className="flex gap-12 mt-16" style={{ fontSize: 13 }}>
          <span className="muted">💬 {(selected.replies || []).length} replies</span>
          <span className="muted">▲ {selected.upvotes || 0}</span>
        </div>
      </div>

      <h3 className="mb-12">Replies ({(selected.replies || []).length})</h3>
      {(selected.replies || []).map((r, i) => (
        <div key={i} className="card card-sm mb-8" style={{ borderLeft: r.is_accepted ? "3px solid var(--accent2)" : "none" }}>
          <div className="flex items-center gap-8 mb-6">
            <div className="avatar-sm">{(r.display_name || "?")[0]}</div>
            <span style={{ fontWeight: 600, fontSize: 13 }}>{r.display_name}</span>
            <span className="muted" style={{ fontSize: 11 }}>{r.created_at ? new Date(r.created_at).toLocaleDateString() : ""}</span>
            {r.is_accepted && <span className="pill pill-green" style={{ fontSize: 10 }}>✓ Accepted Answer</span>}
          </div>
          <div style={{ fontSize: 13, color: "var(--muted)", lineHeight: 1.6, whiteSpace: "pre-wrap" }}>{r.body}</div>
        </div>
      ))}

      <div className="card mt-16">
        <h3 className="mb-12">Post a Reply</h3>
        <textarea className="textarea" value={reply} onChange={e => setReply(e.target.value)}
          placeholder="Share your thoughts, solution, or ask a follow-up…" rows={4} />
        <button className="btn btn-primary mt-8" onClick={() => postReply(selected.id)}>Post Reply</button>
      </div>
    </div>
  );

  return (
    <div className="content fade-in">
      <div className="flex items-center justify-between mb-16">
        <h2>Community</h2>
        <button className="btn btn-primary" onClick={() => setCreating(true)}>+ New Discussion</button>
      </div>

      <div className="tabs mb-16">
        <div className={`tab ${tab === "forum" ? "active" : ""}`} onClick={() => setTab("forum")}>
          Forum ({discussions.length})
        </div>
        <div className={`tab ${tab === "leaderboard" ? "active" : ""}`} onClick={() => setTab("leaderboard")}>
          Leaderboard
        </div>
      </div>

      {tab === "forum" && (
        <>
          {/* Search + filter */}
          <div className="flex gap-10 mb-16" style={{ flexWrap: "wrap" }}>
            <input className="input" style={{ flex: "1 1 200px", maxWidth: 360 }}
              placeholder="Search discussions…" value={search}
              onChange={e => setSearch(e.target.value)} />
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              <button onClick={() => setTagFilter("all")}
                className={`pill ${tagFilter === "all" ? "pill-accent" : "pill-muted"}`}
                style={{ cursor: "pointer", fontSize: 11, padding: "4px 10px", border: "1px solid var(--border)" }}>
                All
              </button>
              {TAGS.map(t => (
                <button key={t} onClick={() => setTagFilter(t)}
                  className={`pill ${tagFilter === t ? "pill-accent" : "pill-muted"}`}
                  style={{ cursor: "pointer", fontSize: 11, padding: "4px 10px", border: "1px solid var(--border)" }}>
                  #{t}
                </button>
              ))}
            </div>
          </div>

          {loading ? <Spinner /> : filtered.length === 0 ? (
            <Empty icon="💬" msg={search || tagFilter !== "all" ? "No matching discussions" : "Be the first to start a discussion!"} />
          ) : (
            filtered.map(d => (
              <div key={d.id} className="card mb-8" style={{ cursor: "pointer" }}
                onClick={async () => { const r = await api.get(`/discussions/${d.id}`, token); setSelected(r.discussion); }}>
                <div className="flex items-center justify-between mb-8">
                  <div className="flex items-center gap-8">
                    <div className="avatar-sm">{(d.display_name || "?")[0]}</div>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{d.display_name}</span>
                    <span className="muted" style={{ fontSize: 11 }}>{new Date(d.created_at).toLocaleDateString()}</span>
                  </div>
                  <div className="flex gap-8 items-center">
                    {d.tag && (
                      <span style={{ fontSize: 10, fontWeight: 700, color: TAG_COLORS[d.tag] || "var(--muted)", textTransform: "uppercase", letterSpacing: 1 }}>
                        #{d.tag}
                      </span>
                    )}
                    <span className="muted" style={{ fontSize: 11 }}>💬 {d.reply_count || 0}</span>
                    <button className="btn btn-ghost btn-sm" style={{ fontSize: 11, padding: "2px 6px" }}
                      onClick={e => { e.stopPropagation(); vote(d.id, 1); }}>
                      ▲ {d.upvotes || 0}
                    </button>
                  </div>
                </div>
                <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{d.title}</div>
                <div className="muted" style={{ fontSize: 13, lineHeight: 1.5 }}>{d.body?.slice(0, 120)}{d.body?.length > 120 ? "…" : ""}</div>
              </div>
            ))
          )}
        </>
      )}

      {tab === "leaderboard" && (
        <div className="card">
          <h3 className="mb-16">Community Leaderboard</h3>
          <div className="muted mb-16" style={{ fontSize: 13 }}>Top contributors ranked by skill score and problems solved</div>
          {leaderboard.length === 0 ? <Empty icon="🏆" msg="No leaderboard data yet" /> : (
            leaderboard.map((u, i) => (
              <div key={u.user_id || i} className="flex items-center gap-12 mb-10" style={{ padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                <div style={{ width: 32, textAlign: "center", fontWeight: 800, fontSize: 18,
                  color: i === 0 ? "var(--gold)" : i === 1 ? "var(--muted)" : i === 2 ? "var(--accent3)" : "var(--muted)" }}>
                  {i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : `#${i+1}`}
                </div>
                <div className="avatar-sm">{(u.display_name || "?")[0]}</div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>{u.display_name}</div>
                  <div className="muted" style={{ fontSize: 11 }}>
                    {u.problems_solved || 0} solved · {u.streak_current || 0}d streak
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontWeight: 800, color: "var(--accent)", fontSize: 20, fontFamily: "var(--font-display)" }}>
                    {Math.round(u.score || 0)}
                  </div>
                  <div className="label" style={{ fontSize: 10 }}>Score</div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}


function SkillHistoryChart({ token }) {
  const [history, setHistory] = useState([]);
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/users/me/skills/history", token)
      .then(d => { setHistory(d.history || []); setProgress(d.progress); setLoading(false); })
      .catch(() => setLoading(false));
  }, [token]);

  if (loading) return <div className="muted" style={{ fontSize:13 }}>Loading history…</div>;
  if (!history.length) return (
    <div className="card" style={{ textAlign:"center", padding:32 }}>
      <div style={{ fontSize:32, marginBottom:8 }}>📈</div>
      <div className="muted">Solve problems to build your skill history chart</div>
    </div>
  );

  // Group by skill for chart
  const skillMap = {};
  history.forEach(h => {
    if (!skillMap[h.skill_name]) skillMap[h.skill_name] = [];
    skillMap[h.skill_name].push({ day: h.day, score: h.score });
  });

  const skills = Object.keys(skillMap);
  const colors = ["var(--accent)","var(--accent2)","var(--accent3)","var(--gold)","#a78bfa","#60a5fa"];

  // Build SVG sparklines
  const allDays = [...new Set(history.map(h => h.day))].sort();
  const W = 500, H = 140, padX = 40, padY = 16;
  const maxScore = Math.max(...history.map(h => h.score), 10);

  const toX = (day) => padX + (allDays.indexOf(day) / Math.max(allDays.length - 1, 1)) * (W - padX * 2);
  const toY = (score) => padY + (1 - score / 100) * (H - padY * 2);

  return (
    <div className="card mb-16">
      <h3 className="mb-12">📈 Skill Progress History (30 days)</h3>
      {progress?.recent_gains?.length > 0 && (
        <div className="flex gap-8 mb-12" style={{ flexWrap:"wrap" }}>
          {progress.recent_gains.map((g,i) => (
            <span key={i} className="pill pill-green" style={{ fontSize:11 }}>
              +{g.total_gain?.toFixed(1)} {g.skill_name}
            </span>
          ))}
        </div>
      )}
      <div style={{ overflowX:"auto" }}>
        <svg viewBox={`0 0 ${W} ${H}`} style={{ width:"100%", minWidth:300, display:"block" }}>
          {/* Grid lines */}
          {[0,25,50,75,100].map(v => (
            <g key={v}>
              <line x1={padX} y1={toY(v)} x2={W-padX} y2={toY(v)}
                stroke="var(--border)" strokeWidth="0.5" strokeDasharray="4,4"/>
              <text x={padX-4} y={toY(v)+4} fill="var(--muted)" fontSize="8" textAnchor="end">{v}</text>
            </g>
          ))}
          {/* Skill lines */}
          {skills.slice(0,6).map((skill, si) => {
            const pts = skillMap[skill];
            if (pts.length < 2) return null;
            const d = pts.map((p,i) => `${i===0?"M":"L"}${toX(p.day)},${toY(p.score)}`).join(" ");
            const lastPt = pts[pts.length-1];
            return (
              <g key={skill}>
                <path d={d} fill="none" stroke={colors[si % colors.length]} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <circle cx={toX(lastPt.day)} cy={toY(lastPt.score)} r="3" fill={colors[si % colors.length]}/>
              </g>
            );
          })}
          {/* X axis labels — first and last */}
          {allDays.length > 0 && <>
            <text x={padX} y={H-2} fill="var(--muted)" fontSize="8">{allDays[0]?.slice(5)}</text>
            <text x={W-padX} y={H-2} fill="var(--muted)" fontSize="8" textAnchor="end">{allDays[allDays.length-1]?.slice(5)}</text>
          </>}
        </svg>
      </div>
      {/* Legend */}
      <div className="flex gap-12 mt-8" style={{ flexWrap:"wrap" }}>
        {skills.slice(0,6).map((skill, si) => (
          <div key={skill} className="flex items-center gap-4">
            <div style={{ width:12, height:3, background:colors[si % colors.length], borderRadius:2 }}/>
            <span style={{ fontSize:11, color:"var(--muted)" }}>{skill}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── PROFILE ─────────────────────────────────────────────────────────────────
function Profile({ token, onToast }) {
  const [profile, setProfile] = useState(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm]       = useState({});
  const [badges, setBadges]   = useState([]);
  const [avatarSrc, setAvatarSrc] = useState(null);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const fileInputRef = React.useRef(null);

  useEffect(() => {
    Promise.all([
      api.get("/users/me/profile", token),
      api.get("/users/me/badges", token),
    ]).then(([p, b]) => {
      setProfile(p.profile); setForm(p.profile || {}); setBadges(b.badges || []);
      if (p.profile?.id) setAvatarSrc(`/users/${p.profile.id}/avatar`);
    }).catch(() => {});
  }, [token]);

  async function save() {
    try {
      const d = await api.post("/users/me/profile", form, token);
      setProfile(d.profile); setEditing(false);
      onToast("Profile updated!", "success");
    } catch(e) { onToast(e.message, "error"); }
  }

  async function handlePhotoChange(e) {
    const file = e.target.files[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) { onToast("Photo must be under 2MB", "error"); return; }
    setUploadingPhoto(true);
    try {
      const reader = new FileReader();
      reader.onload = async (ev) => {
        const b64 = ev.target.result; // full data URI
        await api.post("/users/me/avatar", { image_data: b64 }, token);
        setAvatarSrc(b64); // show immediately
        onToast("✅ Profile photo updated!", "success");
        setUploadingPhoto(false);
      };
      reader.readAsDataURL(file);
    } catch(e) { onToast(e.message, "error"); setUploadingPhoto(false); }
  }

  if (!profile) return <div className="content loading muted">Loading profile…</div>;

  return (
    <div className="content fade-in">
      <div className="card-grid grid-2" style={{ gap: 20 }}>
        <div>
          <div className="card mb-16" style={{ background: "linear-gradient(135deg, rgba(124,106,247,.1), var(--bg2))" }}>
            <div className="flex items-center gap-16 mb-16">
              {/* Clickable avatar with upload */}
              <div style={{ position:"relative", cursor:"pointer" }}
                onClick={() => fileInputRef.current?.click()}
                title="Click to change photo">
                {avatarSrc ? (
                  <img src={avatarSrc} alt="avatar"
                    style={{ width:56, height:56, borderRadius:"50%", objectFit:"cover",
                             border:"2px solid var(--accent)", display:"block" }}
                    onError={() => setAvatarSrc(null)}/>
                ) : (
                  <div className="avatar" style={{ width:56, height:56, fontSize:22 }}>
                    {(profile.display_name||"?")[0]}
                  </div>
                )}
                <div style={{ position:"absolute", bottom:0, right:0,
                              background:"var(--accent)", borderRadius:"50%",
                              width:18, height:18, display:"flex", alignItems:"center",
                              justifyContent:"center", fontSize:10, color:"white" }}>
                  {uploadingPhoto ? "…" : "📷"}
                </div>
              </div>
              <input ref={fileInputRef} type="file" accept="image/*"
                style={{ display:"none" }} onChange={handlePhotoChange}/>
              <div>
                <div style={{ fontWeight: 800, fontSize: 20 }}>{profile.display_name}</div>
                <div className="muted">@{profile.username || "no username set"}</div>
                {profile.location && <div className="muted" style={{ fontSize: 12 }}>📍 {profile.location}</div>}
              </div>
            </div>
            <div className="card-grid grid-3" style={{ gap: 10 }}>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 22, fontWeight: 800, color: "var(--accent)" }}>{profile.unique_solved || 0}</div>
                <div className="label">Solved</div>
              </div>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 22, fontWeight: 800, color: "var(--gold)" }}>{profile.reputation || 0}</div>
                <div className="label">Reputation</div>
              </div>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 22, fontWeight: 800, color: "var(--accent2)" }}>{profile.streak_current || 0}</div>
                <div className="label">Streak</div>
              </div>
            </div>
          </div>

          {badges.length > 0 && (
            <div className="card mb-16">
              <h3 className="mb-12">Badges</h3>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {badges.map(b => (
                  <span key={b.id} className="pill pill-accent" title={b.desc} style={{ gap: 4 }}>
                    {b.icon} {b.name}
                  </span>
                ))}
              </div>
            </div>
          )}

          {(profile.certifications||[]).length > 0 && (
            <div className="card">
              <h3 className="mb-12">🎓 Certifications</h3>
              {profile.certifications.map((c, i) => (
                <div key={i} className="flex items-center justify-between" style={{ padding: "8px 0" }}>
                  <div style={{ fontWeight: 600 }}>{c.name}</div>
                  <span className="pill pill-gold">{c.score_at_issue}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div>
          {editing ? (
            <div className="card">
              <h3 className="mb-16">Edit Profile</h3>
              {[
                { key: "display_name", label: "DISPLAY NAME" },
                { key: "username",     label: "USERNAME" },
                { key: "bio",          label: "BIO" },
                { key: "location",     label: "LOCATION" },
                { key: "github_url",   label: "GITHUB URL" },
                { key: "linkedin_url", label: "LINKEDIN URL" },
              ].map(f => (
                <div key={f.key} className="form-group">
                  <label className="form-label">{f.label}</label>
                  <input className="input" value={form[f.key]||""} onChange={e => setForm({...form,[f.key]:e.target.value})} />
                </div>
              ))}
              <div className="flex gap-8">
                <button className="btn btn-primary" onClick={save}>Save</button>
                <button className="btn btn-secondary" onClick={() => setEditing(false)}>Cancel</button>
              </div>
            </div>
          ) : (
            <div className="card">
              <div className="flex justify-between items-center mb-16">
                <h3>About</h3>
                <button className="btn btn-sm btn-secondary" onClick={() => setEditing(true)}>Edit</button>
              </div>
              {profile.bio && <div style={{ fontSize: 14, color: "var(--muted)", lineHeight: 1.6, marginBottom: 16 }}>{profile.bio}</div>}
              <div style={{ fontSize: 13, display: "flex", flexDirection: "column", gap: 8 }}>
                {profile.education && <div>🎓 {profile.education}</div>}
                {profile.experience_years > 0 && <div>💼 {profile.experience_years} years experience</div>}
                {profile.github_url && <div><a href={profile.github_url} target="_blank" style={{ color: "var(--accent)", textDecoration: "none" }}>⟲ GitHub</a></div>}
                {profile.linkedin_url && <div><a href={profile.linkedin_url} target="_blank" style={{ color: "var(--accent)", textDecoration: "none" }}>in LinkedIn</a></div>}
              </div>
            </div>
          )}

          <div className="card mt-16">
            <h3 className="mb-12">Skill Scores</h3>
            {(profile.skills||[]).map(s => s.current_score > 0 && (
              <SkillBar key={s.id} score={s.current_score} name={s.name} />
            ))}
          </div>
        </div>
      </div>

      {/* Skill History Chart — full width below the grid */}
      <div className="mt-16">
        <SkillHistoryChart token={token} />
      </div>
    </div>
  );
}

// ─── RECRUITER ───────────────────────────────────────────────────────────────
function Recruiter({ token, onToast }) {
  const [company, setCompany]     = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [pipeline, setPipeline]   = useState([]);
  const [tab, setTab]             = useState("search");
  const [filters, setFilters]     = useState({ min_score: 0 });
  const [loading, setLoading]     = useState(false);
  const [contacting, setContacting] = useState(null);
  const [message, setMessage]     = useState("");

  useEffect(() => {
    api.get("/company", token).then(d => setCompany(d.company)).catch(() => {});
    loadCandidates();
    api.get("/company/pipeline", token).then(d => setPipeline(d.pipeline || [])).catch(() => {});
  }, [token]);

  async function loadCandidates() {
    setLoading(true);
    const params = new URLSearchParams(filters).toString();
    api.get(`/candidates?${params}`, token).then(d => { setCandidates(d.candidates||[]); setLoading(false); });
  }

  async function createCompany() {
    try {
      const name = prompt("Company name:");
      if (!name) return;
      const d = await api.post("/company", { name }, token);
      setCompany(d.company); onToast("Company created!", "success");
    } catch(e) { onToast(e.message, "error"); }
  }

  async function sendContact(candidate) {
    try {
      await api.post("/company/contact", { candidate_id: candidate.id, message }, token);
      onToast("Contact request sent!", "success");
      setContacting(null); setMessage("");
      const d = await api.get("/company/pipeline", token);
      setPipeline(d.pipeline || []);
    } catch(e) { onToast(e.message, "error"); }
  }

  const upgradeNeeded = !company || company?.plan === "free";

  return (
    <div className="content fade-in">
      <div className="flex items-center justify-between mb-20">
        <h2>Recruiter Dashboard</h2>
        {!company
          ? <button className="btn btn-primary" onClick={createCompany}>+ Create Company</button>
          : <div className="card card-sm" style={{ padding: "8px 16px" }}>
            <span style={{ fontWeight: 700 }}>{company.name}</span>
            <span className="pill pill-accent ml-8" style={{ marginLeft: 8, fontSize: 11 }}>{company.plan?.toUpperCase()}</span>
          </div>}
      </div>

      <div className="tabs">
        <div className={`tab ${tab==="search"?"active":""}`} onClick={() => setTab("search")}>Candidate Search</div>
        <div className={`tab ${tab==="pipeline"?"active":""}`} onClick={() => setTab("pipeline")}>Pipeline ({pipeline.length})</div>
        <div className={`tab ${tab==="upgrade"?"active":""}`} onClick={() => setTab("upgrade")}>Upgrade Plan</div>
      </div>

      {tab === "search" && (
        <>
          <div className="flex gap-8 mb-16">
            <input className="input" style={{ maxWidth: 160 }} placeholder="Min Score" type="number"
              value={filters.min_score||""} onChange={e => setFilters({...filters, min_score: e.target.value})} />
            <button className="btn btn-primary" onClick={loadCandidates}>Search</button>
          </div>
          {loading ? <div className="loading muted">Searching…</div> : (
            <table className="table">
              <thead><tr><th>Developer</th><th>Skills</th><th>Score</th><th>Experience</th><th></th></tr></thead>
              <tbody>
                {candidates.map(c => (
                  <tr key={c.id}>
                    <td>
                      <div className="flex items-center gap-8">
                        <div className="avatar-sm">{(c.display_name||"?")[0]}</div>
                        <div>
                          <div style={{ fontWeight: 600 }}>{c.display_name}</div>
                          <div className="muted" style={{ fontSize: 11 }}>{c.location || "—"}</div>
                        </div>
                      </div>
                    </td>
                    <td>
                      <div className="flex gap-4" style={{ flexWrap: "wrap" }}>
                        {(c.skills||[]).slice(0,3).map(s => (
                          <span key={s.name} className="pill pill-accent" style={{ fontSize: 10 }}>{s.name.split(" ")[0]}: {Math.round(s.current_score)}</span>
                        ))}
                      </div>
                    </td>
                    <td><span className="mono" style={{ color: "var(--accent)", fontWeight: 700 }}>{Math.round(c.total_score)}</span></td>
                    <td className="muted">{c.experience_years ? `${c.experience_years}y` : "—"}</td>
                    <td>
                      <button className="btn btn-sm btn-secondary"
                        onClick={() => { setContacting(c); setTab("contact"); }}>
                        Contact
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}

      {tab === "contact" && contacting && (
        <div className="card" style={{ maxWidth: 480 }}>
          <h3 className="mb-16">Contact {contacting.display_name}</h3>
          {upgradeNeeded && (
            <div className="card card-sm mb-16" style={{ background: "rgba(255,209,102,.08)", borderColor: "rgba(255,209,102,.3)" }}>
              <div style={{ fontWeight: 600, color: "var(--gold)", marginBottom: 6 }}>⚡ Upgrade Required</div>
              <div className="muted" style={{ fontSize: 13 }}>Upgrade to Starter or above to contact candidates.</div>
              <button className="btn btn-sm btn-primary mt-8" onClick={() => setTab("upgrade")}>View Plans</button>
            </div>
          )}
          <div className="form-group">
            <label className="form-label">MESSAGE</label>
            <textarea className="textarea" rows={4} value={message}
              onChange={e => setMessage(e.target.value)}
              placeholder="Introduce yourself and the role…" />
          </div>
          <div className="flex gap-8">
            <button className="btn btn-primary" disabled={upgradeNeeded} onClick={() => sendContact(contacting)}>Send Request</button>
            <button className="btn btn-secondary" onClick={() => { setContacting(null); setTab("search"); }}>Cancel</button>
          </div>
        </div>
      )}

      {tab === "pipeline" && (
        pipeline.length === 0 ? <Empty icon="📋" msg="No contacts yet — search for candidates!" /> : (
          <table className="table">
            <thead><tr><th>Candidate</th><th>Job</th><th>Score</th><th>Status</th><th>Date</th></tr></thead>
            <tbody>
              {pipeline.map(p => (
                <tr key={p.id}>
                  <td style={{ fontWeight: 600 }}>{p.candidate_name}</td>
                  <td className="muted">{p.job_title || "General"}</td>
                  <td><span className="mono" style={{ color: "var(--accent)" }}>{Math.round(p.candidate_score)}</span></td>
                  <td><span className={`pill ${p.status==="accepted"?"pill-green":p.status==="pending"?"pill-gold":"pill-red"}`}>{p.status}</span></td>
                  <td className="muted mono" style={{ fontSize: 11 }}>{new Date(p.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )
      )}

      {tab === "upgrade" && (
        <div className="card-grid grid-3" style={{ maxWidth: 900 }}>
          {[
            { plan: "starter",    name: "Starter",    price: "₹2,999/mo",  contacts: 10,  features: ["10 candidate contacts/mo","Full profiles visible","Email outreach"] },
            { plan: "growth",     name: "Growth",     price: "₹7,999/mo",  contacts: 50,  features: ["50 contacts/mo","Priority search","Analytics access"] },
            { plan: "enterprise", name: "Enterprise", price: "₹24,999/mo", contacts: "∞", features: ["Unlimited contacts","Custom integrations","Dedicated support"] },
          ].map(p => (
            <div key={p.plan} className="card" style={{ borderColor: p.plan==="growth"?"var(--accent)":"var(--border)", position:"relative", overflow:"hidden" }}>
              {p.plan==="growth" && <div className="pill pill-accent mb-8" style={{ fontSize: 11 }}>MOST POPULAR</div>}
              <div style={{ fontSize: 22, fontWeight: 800, marginBottom: 4 }}>{p.name}</div>
              <div style={{ fontSize: 20, color: "var(--accent)", fontWeight: 700, marginBottom: 16 }}>{p.price}</div>
              <div className="muted mb-16" style={{ fontSize: 13 }}>{p.contacts} contacts/month</div>
              {p.features.map(f => <div key={f} style={{ fontSize: 13, marginBottom: 6 }}>✓ {f}</div>)}
              <button className="btn btn-primary w-full mt-16"
                onClick={async () => {
                  try {
                    if (!company) { onToast("Create a company profile first", "error"); return; }
                    const order = await api.post("/payments/create-order", { plan: p.plan }, token);

                    if (order.dev_mode) {
                      // Show a nice setup modal instead of just a toast
                      const msg = [
                        "🔧 PAYMENT SETUP REQUIRED",
                        "",
                        "To accept real payments, add these to your server environment:",
                        "",
                        "RAZORPAY_KEY_ID=rzp_test_xxxx",
                        "RAZORPAY_KEY_SECRET=xxxx",
                        "",
                        "Get free keys at: razorpay.com → Dashboard → Settings → API Keys",
                        "(Use TEST keys first, then LIVE keys when ready to go live)",
                        "",
                        "For now, plan will be activated in TEST mode."
                      ].join("\n");
                      alert(msg);
                      // In dev mode, simulate activation
                      onToast(`✅ ${p.name} plan activated (TEST MODE)`, "success");
                      return;
                    }

                    // Load Razorpay checkout script dynamically
                    if (!window.Razorpay) {
                      await new Promise((res, rej) => {
                        const s = document.createElement("script");
                        s.src = "https://checkout.razorpay.com/v1/checkout.js";
                        s.onload = res; s.onerror = rej;
                        document.head.appendChild(s);
                      });
                    }

                    // Open Razorpay modal
                    const rzp = new window.Razorpay({
                      key:         order.key_id,
                      amount:      order.amount_paise,
                      currency:    "INR",
                      name:        "SkillOS",
                      description: `${p.name} Recruiter Plan`,
                      order_id:    order.provider_order_id,
                      prefill:     { name: company?.name || "" },
                      theme:       { color: "#7c6af7" },
                      modal:       { backdropclose: false },
                      handler: async (response) => {
                        try {
                          await api.post("/payments/verify", {
                            razorpay_order_id:    response.razorpay_order_id,
                            razorpay_payment_id:  response.razorpay_payment_id,
                            razorpay_signature:   response.razorpay_signature,
                          }, token);
                          onToast(`✅ ${p.name} plan activated!`, "success");
                          // Reload company data
                          const d = await api.get("/company", token);
                          setCompany(d.company || null);
                          setTab("overview");
                        } catch(e) { onToast("Payment verification failed: " + e.message, "error"); }
                      },
                    });
                    rzp.open();
                  } catch(e) { onToast(e.message, "error"); }
                }}>
                Get {p.name}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── PROJECTS ─────────────────────────────────────────────────────────────────
function Projects({ token, onToast }) {
  const [templates, setTemplates] = useState([]);
  const [myProjects, setMyProjects] = useState([]);
  const [tab, setTab] = useState("browse");

  useEffect(() => {
    api.get("/projects", token).then(d => setTemplates(d.templates||[])).catch(() => {});
    api.get("/users/me/projects", token).then(d => setMyProjects(d.projects||[])).catch(() => {});
  }, [token]);

  async function start(templateId) {
    try {
      await api.post(`/projects/${templateId}/start`, {}, token);
      onToast("Project started!", "success");
      const d = await api.get("/users/me/projects", token);
      setMyProjects(d.projects||[]); setTab("mine");
    } catch(e) { onToast(e.message, "error"); }
  }

  async function submitRepo(projectId) {
    const url = prompt("Enter your GitHub/GitLab repo URL:");
    if (!url) return;
    try {
      await api.post(`/users/me/projects/${projectId}/submit`, { repo_url: url }, token);
      onToast("Project submitted for evaluation!", "success");
      const d = await api.get("/users/me/projects", token);
      setMyProjects(d.projects||[]);
    } catch(e) { onToast(e.message, "error"); }
  }

  const statusColor = { in_progress:"var(--gold)", submitted:"var(--accent)", evaluated:"var(--accent2)", rejected:"var(--accent3)" };

  return (
    <div className="content fade-in">
      <h2 className="mb-4">Project Evaluation</h2>
      <div className="muted mb-20" style={{ fontSize: 14 }}>Build real projects to demonstrate your skills to recruiters</div>
      <div className="tabs">
        <div className={`tab ${tab==="browse"?"active":""}`} onClick={() => setTab("browse")}>Browse Projects</div>
        <div className={`tab ${tab==="mine"?"active":""}`} onClick={() => setTab("mine")}>My Projects ({myProjects.length})</div>
      </div>
      {tab === "browse" && (
        <div className="card-grid grid-2">
          {templates.map(t => (
            <div key={t.id} className="card">
              <div className="flex justify-between items-center mb-8">
                <DiffPill difficulty={t.difficulty} />
                <span className="pill pill-accent" style={{ fontSize: 11 }}>{t.domain}</span>
              </div>
              <h3 style={{ marginBottom: 8 }}>{t.title}</h3>
              <div className="muted" style={{ fontSize: 13, lineHeight: 1.6, marginBottom: 16 }}>
                {t.description?.slice(0, 120)}…
              </div>
              <button className="btn btn-primary btn-sm" onClick={() => start(t.id)}>Start Project</button>
            </div>
          ))}
        </div>
      )}
      {tab === "mine" && (
        myProjects.length === 0 ? <Empty icon="🔨" msg="No projects yet — start one!" /> : (
          myProjects.map(p => (
            <div key={p.id} className="card mb-8">
              <div className="flex items-center justify-between">
                <div>
                  <div style={{ fontWeight: 600 }}>{p.title || p.template_title}</div>
                  <div className="flex gap-8 mt-6">
                    <DiffPill difficulty={p.difficulty} />
                    <span style={{ fontSize: 11, fontWeight: 600, color: statusColor[p.status] }}>{p.status?.replace("_"," ").toUpperCase()}</span>
                  </div>
                </div>
                <div className="flex gap-8">
                  {p.repo_url && <a href={p.repo_url} target="_blank" className="btn btn-sm btn-secondary">View Repo</a>}
                  {p.status === "in_progress" && (
                    <button className="btn btn-sm btn-primary" onClick={() => submitRepo(p.id)}>Submit</button>
                  )}
                </div>
              </div>
              {p.score && <div className="mt-8 muted" style={{ fontSize: 13 }}>Score: <span style={{ color: "var(--accent)", fontWeight: 700 }}>{p.score}</span></div>}
            </div>
          ))
        )
      )}
    </div>
  );
}

// ─── LIVE INTERVIEW ───────────────────────────────────────────────────────────
function LiveInterview({ token, onToast }) {
  const [rooms, setRooms]       = useState([]);
  const [selected, setSelected] = useState(null);
  const [creating, setCreating] = useState(false);
  const [stats, setStats]       = useState(null);
  const [form, setForm]         = useState({ title: "", candidate_email: "", duration_minutes: 60 });
  const [code, setCode]         = useState("# Collaborative code editor\n# Both interviewer and candidate can edit this\n\n");
  const [message, setMessage]   = useState("");
  const [note, setNote]         = useState("");
  const [tab, setTab]           = useState("code");
  const [lang, setLang]         = useState("python3");
  const [elapsed, setElapsed]   = useState(0);
  const pollRef   = useRef(null);
  const timerRef  = useRef(null);
  const localVid  = useRef(null);
  const remoteVid = useRef(null);
  const pcRef     = useRef(null);
  const streamRef = useRef(null);
  const [videoOn,    setVideoOn]    = useState(false);
  const [micOn,      setMicOn]      = useState(false);
  const [screenOn,   setScreenOn]   = useState(false);
  const [videoError, setVideoError] = useState(null);

  const LANGS = ["python3", "javascript", "java", "cpp", "go"];

  useEffect(() => {
    loadRooms();
    api.get("/interviews/stats", token).then(d => setStats(d)).catch(() => {});
    return () => { stopAllMedia(); };
  }, [token]);

  // Poll for updates when in a room
  useEffect(() => {
    if (!selected) { if (pollRef.current) clearInterval(pollRef.current); return; }
    pollRef.current = setInterval(async () => {
      try {
        const d = await api.get(`/interviews/${selected.id}`, token);
        setSelected(d.room);
        if (d.room.current_code) setCode(d.room.current_code.code || code);
      } catch {}
    }, 3000);
    return () => clearInterval(pollRef.current);
  }, [selected?.id]);

  // Interview timer
  useEffect(() => {
    if (selected?.status === "active" && selected?.started_at) {
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = setInterval(() => {
        const started = new Date(selected.started_at).getTime();
        setElapsed(Math.floor((Date.now() - started) / 1000));
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
      setElapsed(0);
    }
    return () => clearInterval(timerRef.current);
  }, [selected?.status, selected?.started_at]);

  function loadRooms() {
    api.get("/interviews", token).then(d => setRooms(d.rooms || [])).catch(() => {});
  }

  function stopAllMedia() {
    streamRef.current?.getTracks().forEach(t => t.stop());
    if (pcRef.current) { pcRef.current.close(); pcRef.current = null; }
    setVideoOn(false); setMicOn(false); setScreenOn(false);
  }

  async function startCamera() {
    try {
      setVideoError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      streamRef.current = stream;
      if (localVid.current) localVid.current.srcObject = stream;
      setVideoOn(true); setMicOn(true);
      onToast("Camera & mic started", "success");
    } catch(e) {
      const msg = e.name === "NotAllowedError" ? "Camera permission denied — check browser settings" :
                  e.name === "NotFoundError"   ? "No camera found on this device" :
                  "Camera unavailable: " + e.message;
      setVideoError(msg);
      onToast(msg, "error");
    }
  }

  async function startScreenShare() {
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false });
      if (streamRef.current) streamRef.current.getTracks().filter(t => t.kind === "video").forEach(t => t.stop());
      const newStream = new MediaStream([
        stream.getVideoTracks()[0],
        ...(streamRef.current?.getAudioTracks() || [])
      ]);
      streamRef.current = newStream;
      if (localVid.current) localVid.current.srcObject = newStream;
      setScreenOn(true); setVideoOn(false);
      stream.getVideoTracks()[0].onended = () => { setScreenOn(false); };
      onToast("Screen sharing started", "success");
    } catch(e) {
      if (e.name !== "NotAllowedError") onToast("Screen share failed: " + e.message, "error");
    }
  }

  function toggleMic() {
    if (!streamRef.current) return;
    const tracks = streamRef.current.getAudioTracks();
    tracks.forEach(t => { t.enabled = !t.enabled; });
    setMicOn(prev => !prev);
  }

  function toggleCamera() {
    if (!streamRef.current) return;
    const tracks = streamRef.current.getVideoTracks();
    tracks.forEach(t => { t.enabled = !t.enabled; });
    setVideoOn(prev => !prev);
  }

  function stopCamera() {
    stopAllMedia();
    if (localVid.current) localVid.current.srcObject = null;
  }

  const fmtTime = (s) => `${String(Math.floor(s/60)).padStart(2,"0")}:${String(s%60).padStart(2,"0")}`;
  const timeLeft = selected ? (selected.duration_minutes * 60) - elapsed : 0;
  const timeWarning = timeLeft > 0 && timeLeft < 300; // last 5 min

  async function createRoom() {
    if (!form.title || !form.candidate_email) { onToast("Fill all fields", "error"); return; }
    try {
      const d = await api.post("/interviews", form, token);
      onToast("Room created! Share the invite link.", "success");
      setCreating(false); setForm({ title: "", candidate_email: "", duration_minutes: 60 });
      loadRooms(); setSelected(d.room);
    } catch(e) { onToast(e.message, "error"); }
  }

  async function startRoom() {
    try {
      const d = await api.post(`/interviews/${selected.id}/start`, {}, token);
      setSelected(d.room); onToast("Interview started!", "success");
    } catch(e) { onToast(e.message, "error"); }
  }

  async function endRoom() {
    const feedback = prompt("Add feedback for this candidate (optional):");
    const ratingStr = prompt("Rate the candidate 0–5:");
    const rating = Math.min(5, Math.max(0, parseInt(ratingStr) || 0));
    try {
      const d = await api.post(`/interviews/${selected.id}/end`, { feedback: feedback || "", rating }, token);
      setSelected(d.room); onToast("Interview ended!", "success"); loadRooms();
      stopAllMedia();
    } catch(e) { onToast(e.message, "error"); }
  }

  async function pushCode() {
    try {
      await api.post(`/interviews/${selected.id}/code`, { code, language: lang }, token);
    } catch {}
  }

  async function sendMessage() {
    if (!message.trim()) return;
    try {
      await api.post(`/interviews/${selected.id}/message`, { content: message }, token);
      setMessage("");
      const d = await api.get(`/interviews/${selected.id}`, token);
      setSelected(d.room);
    } catch(e) { onToast(e.message, "error"); }
  }

  async function addNote() {
    if (!note.trim()) return;
    try {
      await api.post(`/interviews/${selected.id}/note`, { note }, token);
      setNote(""); onToast("Note saved (private)", "success");
      const d = await api.get(`/interviews/${selected.id}`, token);
      setSelected(d.room);
    } catch(e) { onToast(e.message, "error"); }
  }

  async function requestHint() {
    try {
      const d = await api.post(`/interviews/${selected.id}/hint`, {}, token);
      onToast("Hint sent to candidate!", "success");
      setSelected(d.room);
    } catch(e) { onToast(e.message, "error"); }
  }

  const statusColor = { scheduled: "var(--gold)", active: "var(--accent2)", ended: "var(--muted)", cancelled: "var(--accent3)" };
  const inviteUrl   = selected ? `${window.location.origin}/interviews/invite/${selected.invite_token}` : "";

  if (creating) return (
    <div className="content fade-in">
      <button className="btn btn-ghost mb-16" onClick={() => setCreating(false)}>← Back</button>
      <h2 className="mb-20">Schedule Interview</h2>
      <div className="card" style={{ maxWidth: 520 }}>
        <div className="form-group">
          <label className="form-label">INTERVIEW TITLE</label>
          <input className="input" placeholder="e.g. Frontend Engineer — Round 1"
            value={form.title} onChange={e => setForm({...form, title: e.target.value})} />
        </div>
        <div className="form-group">
          <label className="form-label">CANDIDATE EMAIL</label>
          <input className="input" type="email" placeholder="candidate@email.com"
            value={form.candidate_email} onChange={e => setForm({...form, candidate_email: e.target.value})} />
        </div>
        <div className="form-group">
          <label className="form-label">DURATION (minutes)</label>
          <select className="input" value={form.duration_minutes}
            onChange={e => setForm({...form, duration_minutes: parseInt(e.target.value)})}>
            {[30, 45, 60, 90, 120].map(d => <option key={d} value={d}>{d} min</option>)}
          </select>
        </div>
        <button className="btn btn-primary" onClick={createRoom}>Create Interview Room →</button>
      </div>
    </div>
  );

  if (selected) {
    const events   = selected.events || [];
    const messages = events.filter(e => ["message","system","hint"].includes(e.event_type));
    const notes    = events.filter(e => e.event_type === "note");

    return (
      <div className="content fade-in" style={{ padding: "16px 24px" }}>

        {/* Header bar */}
        <div className="flex items-center justify-between mb-12" style={{ flexWrap: "wrap", gap: 8 }}>
          <div className="flex items-center gap-12">
            <button className="btn btn-ghost btn-sm" onClick={() => { setSelected(null); loadRooms(); stopAllMedia(); }}>←</button>
            <div>
              <h2 style={{ marginBottom: 2, fontSize: 16 }}>{selected.title}</h2>
              <div className="flex gap-8 items-center">
                <div className="dot" style={{ background: statusColor[selected.status] }} />
                <span style={{ fontSize: 11, fontWeight: 700, color: statusColor[selected.status] }}>{selected.status?.toUpperCase()}</span>
                <span className="muted" style={{ fontSize: 11 }}>{selected.candidate_email}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-8" style={{ flexWrap: "wrap" }}>
            {/* Timer */}
            {selected.status === "active" && (
              <div style={{
                fontFamily: "var(--font-mono)", fontSize: 18, fontWeight: 800,
                color: timeWarning ? "var(--accent3)" : "var(--accent2)",
                background: timeWarning ? "rgba(255,77,109,.1)" : "rgba(6,214,160,.08)",
                border: `1px solid ${timeWarning ? "rgba(255,77,109,.3)" : "rgba(6,214,160,.2)"}`,
                padding: "4px 14px", borderRadius: 8, minWidth: 80, textAlign: "center",
              }}>
                {timeWarning ? "⚠ " : ""}{fmtTime(Math.max(0, timeLeft))}
              </div>
            )}
            {selected.status === "scheduled" && (
              <button className="btn btn-primary btn-sm" onClick={startRoom}>▶ Start</button>
            )}
            {selected.status === "active" && (
              <>
                <button className="btn btn-sm btn-secondary" onClick={requestHint}>💡 Hint</button>
                <button className="btn btn-danger btn-sm" onClick={endRoom}>■ End</button>
              </>
            )}
          </div>
        </div>

        {/* Invite link */}
        {selected.status !== "ended" && (
          <div className="card card-sm mb-12" style={{ background: "rgba(124,106,247,.05)", borderColor: "rgba(124,106,247,.25)" }}>
            <div className="flex gap-8 items-center">
              <span className="label" style={{ flexShrink: 0 }}>Invite:</span>
              <code style={{ fontSize: 11, color: "var(--accent)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{inviteUrl}</code>
              <button className="btn btn-sm btn-secondary" onClick={() => { navigator.clipboard?.writeText(inviteUrl); onToast("Link copied!", "success"); }}>Copy</button>
            </div>
          </div>
        )}

        {/* Main grid: code + video + chat */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 12 }}>

          {/* Left: code editor + tabs */}
          <div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
              <div className="tabs" style={{ marginBottom: 0 }}>
                <div className={`tab ${tab==="code"?"active":""}`} onClick={() => setTab("code")}>Code</div>
                <div className={`tab ${tab==="chat"?"active":""}`} onClick={() => setTab("chat")}>Chat ({messages.length})</div>
                <div className={`tab ${tab==="notes"?"active":""}`} onClick={() => setTab("notes")}>Notes</div>
              </div>
              {tab === "code" && (
                <div className="flex gap-6 items-center">
                  <select className="input" style={{ padding: "4px 8px", fontSize: 11, height: 28 }}
                    value={lang} onChange={e => setLang(e.target.value)}>
                    {LANGS.map(l => <option key={l} value={l}>{l}</option>)}
                  </select>
                  {selected.status === "active" && (
                    <button className="btn btn-sm btn-secondary" style={{ height: 28, fontSize: 11 }} onClick={pushCode}>Sync ↑</button>
                  )}
                </div>
              )}
            </div>

            {tab === "code" && (
              <div className="editor-wrap">
                <div className="editor-header">
                  <span className="dot dot-red"/><span className="dot dot-yellow"/><span className="dot dot-green"/>
                  <span style={{ marginLeft: 8, fontSize: 11 }}>solution.{lang === "python3" ? "py" : lang === "javascript" ? "js" : lang === "java" ? "java" : lang === "cpp" ? "cpp" : "go"}</span>
                  <span className="muted" style={{ marginLeft: "auto", fontSize: 10 }}>auto-syncs every 3s</span>
                </div>
                <textarea className="editor-textarea" value={code}
                  onChange={e => setCode(e.target.value)}
                  disabled={selected.status === "ended"}
                  spellCheck={false}
                  style={{ minHeight: 380 }}
                  onKeyDown={e => {
                    if (e.key === "Tab") {
                      e.preventDefault();
                      const s = e.target.selectionStart;
                      const v = code.slice(0,s) + "    " + code.slice(s);
                      setCode(v);
                      setTimeout(() => { e.target.selectionStart = e.target.selectionEnd = s+4; }, 0);
                    }
                  }}
                />
                <div className="editor-footer">
                  <span className="muted" style={{ fontSize: 10 }}>{code.split("\n").length} lines · {code.length} chars</span>
                </div>
              </div>
            )}

            {tab === "chat" && (
              <div className="card" style={{ padding: 0, overflow: "hidden" }}>
                <div style={{ height: 380, overflowY: "auto", padding: "12px 16px", display: "flex", flexDirection: "column", gap: 8 }}>
                  {messages.length === 0 ? <Empty icon="💬" msg="No messages yet" /> :
                    messages.map((ev, i) => (
                      <div key={i} style={{
                        padding: "8px 12px", borderRadius: 8,
                        background: ev.event_type === "hint" ? "rgba(6,214,160,.08)" : ev.event_type === "system" ? "transparent" : "var(--bg3)",
                        borderLeft: ev.event_type === "hint" ? "3px solid var(--accent2)" : "none",
                        fontSize: 13,
                      }}>
                        {ev.event_type !== "system" && (
                          <div style={{ fontSize: 10, color: "var(--muted)", marginBottom: 3 }}>{ev.display_name || "System"}</div>
                        )}
                        <div style={{ color: ev.event_type === "system" ? "var(--muted)" : "var(--text)" }}>
                          {ev.event_type === "hint" && "💡 "}{ev.content}
                        </div>
                      </div>
                    ))
                  }
                </div>
                {selected.status === "active" && (
                  <div style={{ padding: "8px 12px", borderTop: "1px solid var(--border)", display: "flex", gap: 8 }}>
                    <input className="input" style={{ fontSize: 13 }} placeholder="Type a message…"
                      value={message} onChange={e => setMessage(e.target.value)}
                      onKeyDown={e => e.key === "Enter" && sendMessage()} />
                    <button className="btn btn-primary btn-sm" onClick={sendMessage}>Send</button>
                  </div>
                )}
              </div>
            )}

            {tab === "notes" && (
              <div className="card">
                <div className="label mb-8">Private Notes — only you see these</div>
                <div style={{ maxHeight: 300, overflowY: "auto", marginBottom: 12 }}>
                  {notes.map((n, i) => (
                    <div key={i} style={{ padding: "8px 0", borderBottom: "1px solid var(--border)", fontSize: 13 }}>
                      <div style={{ fontSize: 10, color: "var(--muted)", marginBottom: 2 }}>{new Date(n.created_at).toLocaleTimeString()}</div>
                      {n.content}
                    </div>
                  ))}
                  {notes.length === 0 && <div className="muted" style={{ fontSize: 13 }}>No notes yet</div>}
                </div>
                {selected.status === "active" && (
                  <div className="flex gap-8">
                    <input className="input" style={{ fontSize: 13 }} placeholder="Add private note…"
                      value={note} onChange={e => setNote(e.target.value)}
                      onKeyDown={e => e.key === "Enter" && addNote()} />
                    <button className="btn btn-sm btn-secondary" onClick={addNote}>Save</button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right: video + info */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>

            {/* Video panel */}
            <div className="card" style={{ padding: 12 }}>
              <div className="flex items-center justify-between mb-8">
                <span className="label" style={{ fontSize: 10 }}>VIDEO</span>
                {(videoOn || screenOn) && <span className="pill pill-green" style={{ fontSize: 9 }}>LIVE</span>}
              </div>

              {/* Local video preview */}
              <div style={{ position: "relative", background: "var(--bg)", borderRadius: 8, overflow: "hidden", aspectRatio: "16/9", marginBottom: 8, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <video ref={localVid} autoPlay muted playsInline
                  style={{ width: "100%", height: "100%", objectFit: "cover", display: (videoOn || screenOn) ? "block" : "none" }} />
                {!videoOn && !screenOn && (
                  <div style={{ textAlign: "center", color: "var(--muted)" }}>
                    <div style={{ fontSize: 28, marginBottom: 4 }}>📷</div>
                    <div style={{ fontSize: 11 }}>Camera off</div>
                  </div>
                )}
                {(videoOn || screenOn) && (
                  <div style={{ position: "absolute", bottom: 6, left: 8, fontSize: 10, color: "rgba(255,255,255,.7)", background: "rgba(0,0,0,.5)", borderRadius: 4, padding: "2px 6px" }}>
                    You (interviewer)
                  </div>
                )}
              </div>

              {/* Remote video placeholder */}
              <div style={{ background: "var(--bg)", borderRadius: 8, overflow: "hidden", aspectRatio: "16/9", marginBottom: 8, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <video ref={remoteVid} autoPlay playsInline
                  style={{ width: "100%", height: "100%", objectFit: "cover", display: "none" }} />
                <div style={{ textAlign: "center", color: "var(--muted)" }}>
                  <div style={{ fontSize: 28, marginBottom: 4 }}>👤</div>
                  <div style={{ fontSize: 11 }}>{selected.candidate_email?.split("@")[0] || "Candidate"}</div>
                  <div style={{ fontSize: 10, marginTop: 2, color: "var(--muted)" }}>Waiting to join…</div>
                </div>
              </div>

              {videoError && (
                <div style={{ fontSize: 11, color: "var(--accent3)", background: "rgba(255,77,109,.08)", padding: "6px 10px", borderRadius: 6, marginBottom: 8 }}>
                  ⚠ {videoError}
                </div>
              )}

              {/* Media controls */}
              <div className="flex gap-6 justify-center" style={{ flexWrap: "wrap" }}>
                {!videoOn && !screenOn ? (
                  <button className="btn btn-sm btn-primary" onClick={startCamera} style={{ fontSize: 11 }}>📷 Start Camera</button>
                ) : (
                  <>
                    <button className="btn btn-sm btn-secondary" onClick={toggleCamera} style={{ fontSize: 11, minWidth: 40 }}>
                      {videoOn ? "📷" : "📷✕"}
                    </button>
                    <button className="btn btn-sm btn-secondary" onClick={toggleMic} style={{ fontSize: 11, minWidth: 40 }}>
                      {micOn ? "🎙" : "🎙✕"}
                    </button>
                    <button className="btn btn-sm btn-secondary" onClick={screenOn ? stopCamera : startScreenShare} style={{ fontSize: 11 }}>
                      {screenOn ? "🖥✕" : "🖥"}
                    </button>
                    <button className="btn btn-sm btn-ghost" onClick={stopCamera} style={{ fontSize: 11, color: "var(--accent3)" }}>End</button>
                  </>
                )}
                {!screenOn && !videoOn && (
                  <button className="btn btn-sm btn-secondary" onClick={startScreenShare} style={{ fontSize: 11 }}>🖥 Screen</button>
                )}
              </div>
              <div className="muted mt-8" style={{ fontSize: 10, textAlign: "center", lineHeight: 1.5 }}>
                Camera preview is local-only. Full WebRTC peering requires a signaling server (TURN/STUN). Share your screen or add Jitsi embed for multi-party.
              </div>
            </div>

            {/* Session info */}
            <div className="card" style={{ padding: 12 }}>
              <div className="label mb-8" style={{ fontSize: 10 }}>SESSION INFO</div>
              <div style={{ fontSize: 12, display: "flex", flexDirection: "column", gap: 6 }}>
                <div className="flex justify-between"><span className="muted">Duration</span><span>{selected.duration_minutes} min</span></div>
                {selected.started_at && (
                  <div className="flex justify-between"><span className="muted">Started</span><span className="mono" style={{ fontSize: 10 }}>{new Date(selected.started_at).toLocaleTimeString()}</span></div>
                )}
                {selected.status === "active" && (
                  <div className="flex justify-between">
                    <span className="muted">Elapsed</span>
                    <span className="mono" style={{ fontSize: 11, color: timeWarning ? "var(--accent3)" : "var(--accent2)", fontWeight: 700 }}>
                      {fmtTime(elapsed)} / {selected.duration_minutes}:00
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Assigned problem */}
            {selected.task && (
              <div className="card" style={{ padding: 12, borderColor: "rgba(124,106,247,.3)" }}>
                <div className="label mb-6" style={{ fontSize: 10 }}>ASSIGNED PROBLEM</div>
                <div style={{ fontWeight: 600, fontSize: 13 }}>{selected.task.title}</div>
                <DiffPill difficulty={selected.task.difficulty} />
                <div className="muted mt-6" style={{ fontSize: 11, lineHeight: 1.5 }}>{selected.task.description?.slice(0, 100)}…</div>
              </div>
            )}

            {/* Feedback (ended) */}
            {selected.status === "ended" && selected.feedback && (
              <div className="card" style={{ padding: 12, background: "rgba(6,214,160,.05)", borderColor: "rgba(6,214,160,.2)" }}>
                <div className="label mb-6" style={{ fontSize: 10 }}>FEEDBACK</div>
                <div style={{ fontSize: 12, lineHeight: 1.6 }}>{selected.feedback}</div>
                {selected.rating > 0 && (
                  <div className="mt-6" style={{ color: "var(--gold)", fontSize: 16 }}>
                    {"★".repeat(selected.rating)}{"☆".repeat(5 - selected.rating)}
                    <span className="muted" style={{ marginLeft: 8, fontSize: 11 }}>{selected.rating}/5</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="content fade-in">
      <div className="flex items-center justify-between mb-8">
        <h2>Live Interviews</h2>
        <button className="btn btn-primary" onClick={() => setCreating(true)}>+ Schedule Interview</button>
      </div>
      <div className="muted mb-20" style={{ fontSize: 14 }}>Real-time collaborative coding interviews with video, shared editor, and private notes</div>

      {stats && (
        <div className="card-grid grid-3 mb-20">
          {[
            { label: "Total Interviews", val: stats.total_interviews || 0, color: "var(--accent)",  icon: "🎙" },
            { label: "Completed",        val: stats.completed        || 0, color: "var(--accent2)", icon: "✓" },
            { label: "Avg Rating",       val: stats.avg_rating ? `${stats.avg_rating}/5` : "—", color: "var(--gold)", icon: "★" },
          ].map(s => (
            <div key={s.label} className="card" style={{ textAlign: "center" }}>
              <div style={{ fontSize: 28, marginBottom: 8 }}>{s.icon}</div>
              <div style={{ fontSize: 28, fontWeight: 800, color: s.color, fontFamily: "var(--font-display)" }}>{s.val}</div>
              <div className="label mt-4">{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Feature callout */}
      <div className="card mb-20" style={{ background: "linear-gradient(135deg, rgba(124,106,247,.06), rgba(6,214,160,.04))", borderColor: "rgba(124,106,247,.2)" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 16 }}>
          {[
            { icon: "📷", label: "Camera + Mic", desc: "Browser-native WebRTC video" },
            { icon: "🖥️", label: "Screen Share", desc: "Share candidate's screen" },
            { icon: "⌨️", label: "Live Code", desc: "Synced editor, any language" },
            { icon: "💬", label: "Chat + Hints", desc: "In-session messaging" },
            { icon: "📝", label: "Private Notes", desc: "Only you see these" },
            { icon: "⏱", label: "Live Timer", desc: "Countdown with warnings" },
          ].map(f => (
            <div key={f.label} style={{ textAlign: "center" }}>
              <div style={{ fontSize: 24, marginBottom: 6 }}>{f.icon}</div>
              <div style={{ fontSize: 12, fontWeight: 700 }}>{f.label}</div>
              <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>{f.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {rooms.length === 0 ? (
        <Empty icon="🎙️" msg="No interviews yet — schedule your first one!" />
      ) : (
        <div className="card-grid grid-2">
          {rooms.map(r => (
            <div key={r.id} className="card" style={{ cursor: "pointer", borderColor: r.status==="active" ? "rgba(6,214,160,.3)" : "var(--border)" }}
              onClick={async () => { const d = await api.get(`/interviews/${r.id}`, token); setSelected(d.room); if (d.room.current_code) setCode(d.room.current_code.code || code); }}>
              <div className="flex justify-between items-center mb-8">
                <div className="flex items-center gap-6">
                  <div className="dot" style={{ background: statusColor[r.status] }} />
                  <span style={{ fontSize: 11, fontWeight: 700, color: statusColor[r.status] }}>{r.status?.toUpperCase()}</span>
                </div>
                <span className="muted" style={{ fontSize: 11 }}>⏱ {r.duration_minutes}m</span>
              </div>
              <h3 style={{ marginBottom: 6, fontSize: 14 }}>{r.title}</h3>
              <div className="muted" style={{ fontSize: 12 }}>📧 {r.candidate_email}</div>
              {r.status === "ended" && r.rating > 0 && (
                <div style={{ marginTop: 8, color: "var(--gold)", fontSize: 13 }}>{"★".repeat(r.rating)}{"☆".repeat(5-r.rating)}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}



// ─── ANALYTICS ───────────────────────────────────────────────────────────────
function Analytics({ token }) {
  const [stats, setStats]     = useState(null);
  const [skills, setSkills]   = useState([]);
  const [trends, setTrends]   = useState([]);
  const [mySubs, setMySubs]   = useState([]);
  const [mySkills, setMySkills] = useState([]);
  const [tab, setTab]         = useState("personal");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.get("/analytics", token),
      api.get("/analytics/skills", token),
      api.get("/analytics/trends", token),
      api.get("/users/me/submissions", token),
      api.get("/users/me/skills", token),
    ]).then(([s, sk, tr, subs, mysk]) => {
      setStats(s);
      setSkills(sk.skills || []);
      setTrends(tr.trends || []);
      setMySubs(subs.submissions || []);
      setMySkills(mysk.skills || []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [token]);

  if (loading) return <div className="content"><Spinner /></div>;

  // Personal stats
  const totalSolved    = mySubs.filter(s => s.status === "accepted").length;
  const totalAttempted = mySubs.length;
  const acceptRate     = totalAttempted ? Math.round(totalSolved / totalAttempted * 100) : 0;
  const byDiff = { easy: 0, medium: 0, hard: 0 };
  mySubs.filter(s => s.status === "accepted").forEach(s => { if (s.difficulty) byDiff[s.difficulty] = (byDiff[s.difficulty] || 0) + 1; });

  // Recent activity (last 30 days)
  const activityMap = {};
  mySubs.forEach(s => {
    const day = s.submitted_at?.slice(0, 10);
    if (day) activityMap[day] = (activityMap[day] || 0) + 1;
  });
  const today = new Date();
  const activity = Array.from({length: 30}, (_, i) => {
    const d = new Date(today);
    d.setDate(d.getDate() - (29 - i));
    const key = d.toISOString().slice(0, 10);
    return { day: key, count: activityMap[key] || 0 };
  });
  const maxAct = Math.max(...activity.map(a => a.count), 1);

  // Platform trend chart
  const maxSubs = Math.max(...trends.map(t => t.submissions || 0), 1);

  return (
    <div className="content fade-in">
      <h2 className="mb-4">Analytics</h2>
      <div className="muted mb-20" style={{ fontSize: 13 }}>Your performance metrics and platform-wide insights</div>

      <div className="tabs mb-20">
        <div className={`tab ${tab === "personal" ? "active" : ""}`} onClick={() => setTab("personal")}>My Stats</div>
        <div className={`tab ${tab === "platform" ? "active" : ""}`} onClick={() => setTab("platform")}>Platform</div>
      </div>

      {tab === "personal" && (
        <>
          {/* Personal headline stats */}
          <div className="card-grid grid-4 mb-20">
            {[
              { label: "Problems Solved",  val: totalSolved,    color: "var(--accent2)", icon: "✓" },
              { label: "Attempted",        val: totalAttempted, color: "var(--accent)",  icon: "⚡" },
              { label: "Acceptance Rate",  val: `${acceptRate}%`, color: "var(--gold)", icon: "📈" },
              { label: "Skills Tracked",   val: mySkills.length, color: "var(--accent3)", icon: "🧠" },
            ].map(s => (
              <div key={s.label} className="card" style={{ textAlign: "center" }}>
                <div style={{ fontSize: 24, marginBottom: 8 }}>{s.icon}</div>
                <div style={{ fontSize: 32, fontWeight: 800, color: s.color, fontFamily: "var(--font-display)" }}>{s.val}</div>
                <div className="label mt-4">{s.label}</div>
              </div>
            ))}
          </div>

          <div className="card-grid grid-2 mb-20">
            {/* 30-day activity heatmap */}
            <div className="card">
              <h3 className="mb-16">30-Day Activity</h3>
              <div style={{ display: "flex", alignItems: "flex-end", gap: 3, height: 80 }}>
                {activity.map((a, i) => (
                  <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center" }}
                    title={`${a.day}: ${a.count} submissions`}>
                    <div style={{
                      width: "100%", borderRadius: 2,
                      height: `${Math.max(4, Math.round((a.count / maxAct) * 72))}px`,
                      background: a.count === 0 ? "var(--bg3)" :
                        a.count >= 3 ? "var(--accent2)" : "rgba(6,214,160,.4)",
                      transition: "height 0.3s ease",
                    }} />
                  </div>
                ))}
              </div>
              <div className="flex justify-between mt-6" style={{ fontSize: 10, color: "var(--muted)" }}>
                <span>30 days ago</span>
                <span>Today</span>
              </div>
              <div className="flex gap-12 mt-8" style={{ fontSize: 11 }}>
                <span className="muted">Total: {totalAttempted} submissions</span>
                <span style={{ color: "var(--accent2)" }}>Accepted: {totalSolved}</span>
              </div>
            </div>

            {/* Difficulty breakdown */}
            <div className="card">
              <h3 className="mb-16">Problems by Difficulty</h3>
              {[
                { label: "Easy",   count: byDiff.easy   || 0, total: 100, color: "var(--accent2)" },
                { label: "Medium", count: byDiff.medium  || 0, total: 200, color: "var(--gold)" },
                { label: "Hard",   count: byDiff.hard    || 0, total: 150, color: "var(--accent3)" },
              ].map(d => (
                <div key={d.label} className="mb-14">
                  <div className="flex justify-between mb-6" style={{ fontSize: 13 }}>
                    <span style={{ fontWeight: 600, color: d.color }}>{d.label}</span>
                    <span className="muted">{d.count} solved</span>
                  </div>
                  <div className="skill-bar">
                    <div className="skill-bar-fill" style={{ width: `${Math.min(100, (d.count / d.total) * 100)}%`, background: d.color }} />
                  </div>
                </div>
              ))}
              <div className="card card-sm mt-16" style={{ background: "rgba(124,106,247,.05)", borderColor: "rgba(124,106,247,.2)", textAlign: "center" }}>
                <div style={{ fontSize: 28, fontWeight: 800, color: "var(--accent)", fontFamily: "var(--font-display)" }}>
                  {totalSolved}
                </div>
                <div className="label">Total Solved</div>
              </div>
            </div>
          </div>

          {/* Skill scores */}
          <div className="card">
            <h3 className="mb-16">Skill Scores</h3>
            {mySkills.length === 0 ? <Empty icon="🧠" msg="Solve problems to build your skill profile" /> : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 12 }}>
                {mySkills.sort((a, b) => (b.current_score || 0) - (a.current_score || 0)).map(s => (
                  <div key={s.skill_id} className="card card-sm">
                    <div className="flex justify-between mb-6" style={{ fontSize: 13 }}>
                      <span style={{ fontWeight: 600 }}>{s.skill_name || s.skill_id}</span>
                      <span style={{ fontWeight: 800, color: "var(--accent)", fontFamily: "var(--font-display)" }}>
                        {Math.round(s.current_score || 0)}
                      </span>
                    </div>
                    <div className="skill-bar">
                      <div className="skill-bar-fill" style={{ width: `${Math.min(100, s.current_score || 0)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {tab === "platform" && (
        <>
          {/* Platform headline stats */}
          <div className="card-grid grid-4 mb-20">
            {[
              { label: "Total Users",      val: stats?.total_users       ?? "—", color: "var(--accent)",  icon: "👥" },
              { label: "Submissions",      val: stats?.total_submissions ?? "—", color: "var(--accent2)", icon: "⚡" },
              { label: "Acceptance Rate",  val: stats?.accepted_rate != null ? `${stats.accepted_rate}%` : "—", color: "var(--gold)", icon: "✓" },
              { label: "Companies",        val: stats?.total_companies   ?? "—", color: "var(--accent3)", icon: "🏢" },
            ].map(s => (
              <div key={s.label} className="card" style={{ textAlign: "center" }}>
                <div style={{ fontSize: 24, marginBottom: 8 }}>{s.icon}</div>
                <div style={{ fontSize: 32, fontWeight: 800, color: s.color, fontFamily: "var(--font-display)" }}>{s.val}</div>
                <div className="label mt-4">{s.label}</div>
              </div>
            ))}
          </div>

          <div className="card-grid grid-2 mb-20">
            {/* Submission trend */}
            <div className="card">
              <h3 className="mb-16">Platform Submission Trend (30d)</h3>
              {trends.length === 0 ? <Empty icon="📈" msg="No trend data yet" /> : (
                <div style={{ display: "flex", alignItems: "flex-end", gap: 3, height: 120 }}>
                  {trends.slice(-30).map((t, i) => (
                    <div key={i} style={{ flex: 1 }} title={`${t.day}: ${t.submissions} submissions`}>
                      <div style={{
                        width: "100%", borderRadius: "2px 2px 0 0",
                        height: `${Math.max(2, Math.round(((t.submissions || 0) / maxSubs) * 116))}px`,
                        background: "linear-gradient(180deg, var(--accent), var(--accent2))",
                      }} />
                    </div>
                  ))}
                </div>
              )}
              <div className="flex justify-between mt-6" style={{ fontSize: 10, color: "var(--muted)" }}>
                <span>{trends[0]?.day || ""}</span>
                <span>{trends[trends.length-1]?.day || ""}</span>
              </div>
            </div>

            {/* Skill demand */}
            <div className="card">
              <h3 className="mb-16">Top Skills by Developer Count</h3>
              {skills.slice(0, 8).map((s, i) => (
                <div key={s.name} className="flex items-center gap-12 mb-10">
                  <div style={{ width: 18, fontSize: 11, color: "var(--muted)", textAlign: "right" }}>#{i+1}</div>
                  <div style={{ flex: 1 }}>
                    <div className="flex justify-between mb-4" style={{ fontSize: 12 }}>
                      <span>{s.name}</span>
                      <span className="muted">{s.developer_count} devs</span>
                    </div>
                    <div className="skill-bar">
                      <div className="skill-bar-fill" style={{ width: `${Math.min(100, (s.developer_count / (skills[0]?.developer_count || 1)) * 100)}%` }} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Active today */}
          <div className="card" style={{ background: "linear-gradient(135deg, rgba(124,106,247,.08), rgba(6,214,160,.05))", borderColor: "rgba(124,106,247,.2)" }}>
            <div className="flex items-center gap-16">
              <div style={{ fontSize: 48 }}>🔥</div>
              <div>
                <div style={{ fontSize: 36, fontWeight: 800, fontFamily: "var(--font-display)", color: "var(--accent2)" }}>
                  {stats?.active_today ?? 0}
                </div>
                <div style={{ fontSize: 14, fontWeight: 600, marginTop: 2 }}>developers active today</div>
                <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>Unique users who submitted code in the last 24 hours</div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}


function CompanyDashboard({ token, onToast }) {
  const [company, setCompany]     = useState(null);
  const [jobs, setJobs]           = useState([]);
  const [pipeline, setPipeline]   = useState([]);
  const [candidates, setCandidates] = useState([]);
  const [tab, setTab]             = useState("overview");
  const [creating, setCreating]   = useState(false);
  const [jobForm, setJobForm]     = useState({ title: "", description: "", skills_required: "", location: "", salary_range: "" });
  const [companyForm, setCompanyForm] = useState({ name: "", domain: "" });
  const [loading, setLoading]     = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get("/company", token)
      .then(d => {
        setCompany(d.company);
        return Promise.all([
          api.get("/company/jobs", token).then(r => setJobs(r.jobs || [])),
          api.get("/company/pipeline", token).then(r => setPipeline(r.pipeline || [])),
          api.get("/candidates", token).then(r => setCandidates(r.candidates || [])),
        ]);
      })
      .catch(() => setCompany(null))
      .finally(() => setLoading(false));
  }, [token]);

  async function createCompany() {
    if (!companyForm.name) { onToast("Company name required", "error"); return; }
    try {
      const d = await api.post("/company/create", companyForm, token);
      setCompany(d.company); onToast("Company created!", "success");
    } catch(e) { onToast(e.message, "error"); }
  }

  async function postJob() {
    if (!jobForm.title) { onToast("Job title required", "error"); return; }
    try {
      await api.post("/company/jobs/post", jobForm, token);
      onToast("Job posted!", "success"); setCreating(false);
      setJobForm({ title: "", description: "", skills_required: "", location: "", salary_range: "" });
      const d = await api.get("/company/jobs", token);
      setJobs(d.jobs || []);
    } catch(e) { onToast(e.message, "error"); }
  }

  if (loading) return <div className="content"><Spinner /></div>;

  // No company yet — onboarding screen
  if (!company) return (
    <div className="content fade-in" style={{ maxWidth: 560, margin: "0 auto" }}>
      <div className="card" style={{ textAlign: "center", padding: "48px 40px" }}>
        <div style={{ fontSize: 56, marginBottom: 16 }}>🏢</div>
        <h2 className="mb-8">Set Up Your Company</h2>
        <div className="muted mb-32" style={{ fontSize: 14, lineHeight: 1.7 }}>
          Create your company profile to access verified developer candidates, post jobs, and manage your hiring pipeline.
        </div>
        <div className="form-group">
          <label className="form-label">COMPANY NAME</label>
          <input className="input" placeholder="Acme Corp" value={companyForm.name}
            onChange={e => setCompanyForm({ ...companyForm, name: e.target.value })} />
        </div>
        <div className="form-group">
          <label className="form-label">DOMAIN (optional)</label>
          <input className="input" placeholder="acmecorp.com" value={companyForm.domain}
            onChange={e => setCompanyForm({ ...companyForm, domain: e.target.value })} />
        </div>
        <button className="btn btn-primary" style={{ width: "100%" }} onClick={createCompany}>
          Create Company Profile →
        </button>
      </div>
    </div>
  );

  const planColor = { free: "var(--muted)", growth: "var(--gold)", enterprise: "var(--accent2)" };

  return (
    <div className="content fade-in">
      {/* Company header */}
      <div className="card mb-20" style={{ background: "linear-gradient(135deg, rgba(124,106,247,.08), rgba(6,214,160,.04))", borderColor: "rgba(124,106,247,.2)" }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-16">
            <div style={{ width: 56, height: 56, borderRadius: 12, background: "linear-gradient(135deg, var(--accent), var(--accent2))", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 24, fontWeight: 800 }}>
              {company.name[0]}
            </div>
            <div>
              <h2 style={{ marginBottom: 4 }}>{company.name}</h2>
              <div className="muted" style={{ fontSize: 12 }}>{company.domain || "No domain set"}</div>
            </div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: planColor[company.plan] || "var(--muted)", textTransform: "uppercase", letterSpacing: 1 }}>
              {company.plan} Plan
            </div>
            <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>
              {company.contacts_used || 0} / {company.contacts_limit || "∞"} contacts
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs mb-20">
        {["overview", "candidates", "jobs", "pipeline"].map(t => (
          <div key={t} className={`tab ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </div>
        ))}
      </div>

      {tab === "overview" && (
        <>
          <div className="card-grid grid-3 mb-20">
            {[
              { label: "Jobs Posted",     val: jobs.length,              color: "var(--accent)",  icon: "📋" },
              { label: "In Pipeline",     val: pipeline.length,          color: "var(--gold)",    icon: "📊" },
              { label: "Contacts Used",   val: company.contacts_used||0, color: "var(--accent2)", icon: "📩" },
            ].map(s => (
              <div key={s.label} className="card" style={{ textAlign: "center" }}>
                <div style={{ fontSize: 28, marginBottom: 8 }}>{s.icon}</div>
                <div style={{ fontSize: 32, fontWeight: 800, color: s.color, fontFamily: "var(--font-display)" }}>{s.val}</div>
                <div className="label mt-4">{s.label}</div>
              </div>
            ))}
          </div>
          <div className="card">
            <h3 className="mb-16">Recent Pipeline Activity</h3>
            {pipeline.slice(0, 5).length === 0 ? <Empty icon="📊" msg="No pipeline activity yet" /> : (
              pipeline.slice(0, 5).map((p, i) => (
                <div key={i} className="flex items-center gap-12 mb-10" style={{ padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                  <div className="avatar-sm">{(p.candidate_name || "?")[0]}</div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>{p.candidate_name || "Candidate"}</div>
                    <div className="muted" style={{ fontSize: 11 }}>{p.status}</div>
                  </div>
                  <div style={{ fontSize: 11, color: "var(--muted)" }}>{p.created_at ? new Date(p.created_at).toLocaleDateString() : ""}</div>
                </div>
              ))
            )}
          </div>
        </>
      )}

      {tab === "candidates" && (
        <div>
          <div className="flex items-center justify-between mb-16">
            <h3>Verified Candidates</h3>
            <div className="muted" style={{ fontSize: 12 }}>{candidates.length} available</div>
          </div>
          {candidates.length === 0 ? <Empty icon="👥" msg="No candidates found" /> : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {candidates.map((c, i) => (
                <div key={i} className="card card-sm flex items-center gap-16">
                  <div className="avatar-sm">{(c.display_name || "?")[0]}</div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>{c.display_name}</div>
                    <div className="muted" style={{ fontSize: 12 }}>{c.total_skills || 0} verified skills · {c.problems_solved || 0} solved</div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontSize: 20, fontWeight: 800, color: "var(--accent)", fontFamily: "var(--font-display)" }}>
                      {c.overall_score || "—"}
                    </div>
                    <div className="label">Score</div>
                  </div>
                  <button className="btn btn-sm btn-primary" onClick={() => onToast("Contact request sent!", "success")}>
                    Contact
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === "jobs" && (
        <div>
          <div className="flex items-center justify-between mb-16">
            <h3>Job Postings</h3>
            <button className="btn btn-primary btn-sm" onClick={() => setCreating(true)}>+ Post Job</button>
          </div>
          {creating && (
            <div className="card mb-16">
              <h3 className="mb-16">New Job Posting</h3>
              {[
                { key: "title",            label: "JOB TITLE",          placeholder: "Senior Backend Engineer" },
                { key: "skills_required",  label: "REQUIRED SKILLS",    placeholder: "Python, Graphs, System Design" },
                { key: "location",         label: "LOCATION",           placeholder: "Remote / Bangalore" },
                { key: "salary_range",     label: "SALARY RANGE",       placeholder: "₹18–30 LPA" },
              ].map(f => (
                <div key={f.key} className="form-group">
                  <label className="form-label">{f.label}</label>
                  <input className="input" placeholder={f.placeholder} value={jobForm[f.key]}
                    onChange={e => setJobForm({ ...jobForm, [f.key]: e.target.value })} />
                </div>
              ))}
              <div className="form-group">
                <label className="form-label">DESCRIPTION</label>
                <textarea className="textarea" placeholder="Describe the role, responsibilities, and requirements…"
                  value={jobForm.description} onChange={e => setJobForm({ ...jobForm, description: e.target.value })} />
              </div>
              <div className="flex gap-8">
                <button className="btn btn-primary" onClick={postJob}>Post Job</button>
                <button className="btn btn-ghost" onClick={() => setCreating(false)}>Cancel</button>
              </div>
            </div>
          )}
          {jobs.length === 0 && !creating ? <Empty icon="📋" msg="No jobs posted yet" /> : (
            jobs.map((j, i) => (
              <div key={i} className="card mb-10">
                <div className="flex justify-between items-start">
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 15 }}>{j.title}</div>
                    <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                      {j.location && `📍 ${j.location}`}
                      {j.salary_range && ` · 💰 ${j.salary_range}`}
                    </div>
                    {j.skills_required && (
                      <div className="flex gap-6 mt-8" style={{ flexWrap: "wrap" }}>
                        {j.skills_required.split(",").map(s => (
                          <span key={s} className="pill pill-accent" style={{ fontSize: 11 }}>{s.trim()}</span>
                        ))}
                      </div>
                    )}
                  </div>
                  <span className={`pill ${j.is_active ? "pill-green" : "pill-muted"}`} style={{ fontSize: 11 }}>
                    {j.is_active ? "Active" : "Closed"}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {tab === "pipeline" && (
        <div>
          <h3 className="mb-16">Hiring Pipeline</h3>
          {pipeline.length === 0 ? <Empty icon="📊" msg="No candidates in pipeline yet. Contact candidates to start." /> : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {pipeline.map((p, i) => (
                <div key={i} className="card card-sm flex items-center gap-16">
                  <div className="avatar-sm">{(p.candidate_name || "?")[0]}</div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600 }}>{p.candidate_name}</div>
                    <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>
                      {p.message?.slice(0, 60)}…
                    </div>
                  </div>
                  <span className="pill pill-accent" style={{ fontSize: 11 }}>{p.status}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── SECURITY & 2FA ──────────────────────────────────────────────────────────
function SecuritySettings({ token, onToast }) {
  const [sessions, setSessions]   = useState([]);
  const [history, setHistory]     = useState([]);
  const [twoFA, setTwoFA]         = useState(null);   // null = unknown, false = off, obj = setup data
  const [setupData, setSetupData] = useState(null);   // { qr_uri, secret, backup_codes }
  const [confirmCode, setConfirmCode] = useState("");
  const [disableCode, setDisableCode] = useState("");
  const [showDisable, setShowDisable] = useState(false);
  const [tab, setTab]             = useState("sessions");
  const [loading, setLoading]     = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.get("/auth/sessions", token).then(d => setSessions(d.sessions || [])),
      api.get("/auth/login-history", token).then(d => setHistory(d.history || [])),
    ]).catch(() => {}).finally(() => setLoading(false));
  }, [token]);

  async function begin2FA() {
    try {
      const d = await api.post("/auth/2fa/setup", {}, token);
      setSetupData(d);
    } catch(e) { onToast(e.message, "error"); }
  }

  async function confirm2FA() {
    if (!confirmCode || confirmCode.length !== 6) { onToast("Enter the 6-digit code from your authenticator app", "error"); return; }
    try {
      await api.post("/auth/2fa/confirm", { code: confirmCode }, token);
      onToast("2FA enabled! You're now more secure.", "success");
      setSetupData(null); setTwoFA(true); setConfirmCode("");
    } catch(e) { onToast(e.message, "error"); }
  }

  async function disable2FA() {
    try {
      await api.post("/auth/2fa/disable", { code: disableCode }, token);
      onToast("2FA disabled.", "success"); setTwoFA(false); setShowDisable(false); setDisableCode("");
    } catch(e) { onToast(e.message, "error"); }
  }

  async function revokeSession(id) {
    try {
      await api.post(`/auth/sessions/${id}/revoke`, {}, token);
      onToast("Session revoked.", "success");
      setSessions(prev => prev.filter(s => s.id !== id));
    } catch(e) { onToast(e.message, "error"); }
  }

  async function revokeAll() {
    try {
      await api.post("/auth/sessions/revoke-all", {}, token);
      onToast("All other sessions revoked.", "success");
      setSessions(prev => prev.filter(s => s.is_current));
    } catch(e) { onToast(e.message, "error"); }
  }

  if (loading) return <div className="content"><Spinner /></div>;

  return (
    <div className="content fade-in">
      <h2 className="mb-4">Security Settings</h2>
      <div className="muted mb-24" style={{ fontSize: 13 }}>Manage your account security, sessions, and login history</div>

      {/* 2FA Card */}
      <div className="card mb-20">
        <div className="flex items-center justify-between mb-16">
          <div>
            <h3>Two-Factor Authentication</h3>
            <div className="muted mt-4" style={{ fontSize: 13 }}>Add an extra layer of security with an authenticator app</div>
          </div>
          <span className={`pill ${twoFA ? "pill-green" : "pill-muted"}`}>
            {twoFA ? "✓ Enabled" : "Disabled"}
          </span>
        </div>

        {!setupData && !twoFA && (
          <button className="btn btn-primary" onClick={begin2FA}>Enable 2FA →</button>
        )}

        {setupData && (
          <div>
            <div className="form-group">
              <label className="form-label">SCAN QR CODE</label>
              <div style={{ background: "white", padding: 12, borderRadius: 8, display: "inline-block", marginBottom: 12 }}>
                <img
                  src={`https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(setupData.qr_uri)}`}
                  alt="2FA QR Code"
                  width={180} height={180}
                  style={{ display: "block" }}
                />
              </div>
              <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>
                Or enter this secret manually in your app: <code style={{ color: "var(--accent)", fontFamily: "var(--font-mono)" }}>{setupData.secret}</code>
              </div>
            </div>
            {setupData.backup_codes && (
              <div className="card card-sm mb-16" style={{ background: "rgba(255,200,0,.05)", borderColor: "rgba(255,200,0,.2)" }}>
                <div className="label mb-8">⚠ Backup Codes — save these now, you won't see them again</div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 6 }}>
                  {setupData.backup_codes.map(c => (
                    <code key={c} style={{ fontSize: 11, color: "var(--gold)", fontFamily: "var(--font-mono)", padding: "4px 8px", background: "rgba(255,200,0,.08)", borderRadius: 4 }}>{c}</code>
                  ))}
                </div>
              </div>
            )}
            <div className="form-group">
              <label className="form-label">ENTER 6-DIGIT CODE FROM APP</label>
              <input className="input" placeholder="123456" maxLength={6} value={confirmCode}
                onChange={e => setConfirmCode(e.target.value.replace(/\D/g, ""))}
                style={{ fontFamily: "var(--font-mono)", letterSpacing: 4, fontSize: 20, maxWidth: 200 }} />
            </div>
            <div className="flex gap-8">
              <button className="btn btn-primary" onClick={confirm2FA}>Confirm & Enable</button>
              <button className="btn btn-ghost" onClick={() => setSetupData(null)}>Cancel</button>
            </div>
          </div>
        )}

        {twoFA && !showDisable && (
          <button className="btn btn-ghost btn-sm" style={{ color: "var(--accent3)" }} onClick={() => setShowDisable(true)}>
            Disable 2FA
          </button>
        )}

        {showDisable && (
          <div className="flex gap-8 items-center mt-8">
            <input className="input" placeholder="6-digit code to confirm" maxLength={6} value={disableCode}
              onChange={e => setDisableCode(e.target.value.replace(/\D/g, ""))}
              style={{ maxWidth: 180, fontFamily: "var(--font-mono)" }} />
            <button className="btn btn-sm btn-danger" onClick={disable2FA}>Confirm Disable</button>
            <button className="btn btn-ghost btn-sm" onClick={() => setShowDisable(false)}>Cancel</button>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="tabs mb-16">
        <div className={`tab ${tab === "sessions" ? "active" : ""}`} onClick={() => setTab("sessions")}>
          Active Sessions ({sessions.length})
        </div>
        <div className={`tab ${tab === "history" ? "active" : ""}`} onClick={() => setTab("history")}>
          Login History
        </div>
      </div>

      {tab === "sessions" && (
        <div className="card">
          <div className="flex items-center justify-between mb-16">
            <h3>Active Sessions</h3>
            {sessions.length > 1 && (
              <button className="btn btn-sm btn-ghost" style={{ color: "var(--accent3)" }} onClick={revokeAll}>
                Revoke All Others
              </button>
            )}
          </div>
          {sessions.length === 0 ? <Empty icon="🖥️" msg="No active sessions" /> : (
            sessions.map(s => (
              <div key={s.id} className="flex items-center gap-12 mb-10" style={{ padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
                <div style={{ fontSize: 24 }}>{s.device_type === "mobile" ? "📱" : "🖥️"}</div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 600 }}>
                    {s.user_agent_short || s.user_agent?.slice(0, 40) || "Unknown device"}
                    {s.is_current && <span className="pill pill-green" style={{ fontSize: 10, marginLeft: 8 }}>Current</span>}
                  </div>
                  <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>
                    {s.ip_address} · {s.created_at ? new Date(s.created_at).toLocaleString() : ""}
                  </div>
                </div>
                {!s.is_current && (
                  <button className="btn btn-sm btn-ghost" style={{ color: "var(--accent3)" }} onClick={() => revokeSession(s.id)}>
                    Revoke
                  </button>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {tab === "history" && (
        <div className="card">
          <h3 className="mb-16">Login History</h3>
          {history.length === 0 ? <Empty icon="📋" msg="No login history yet" /> : (
            <div style={{ overflowX: "auto" }}>
              <table className="table">
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>IP Address</th>
                    <th>Device</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((h, i) => (
                    <tr key={i}>
                      <td className="mono" style={{ fontSize: 11 }}>{h.created_at ? new Date(h.created_at).toLocaleString() : "—"}</td>
                      <td className="mono" style={{ fontSize: 11 }}>{h.ip_address || "—"}</td>
                      <td style={{ fontSize: 11, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis" }}>{h.user_agent?.slice(0, 50) || "Unknown"}</td>
                      <td>
                        <span className={`pill ${h.success ? "pill-green" : "pill-red"}`} style={{ fontSize: 10 }}>
                          {h.success ? "✓ Success" : "✗ Failed"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── REFERRALS & NETWORK EFFECTS ─────────────────────────────────────────────
function Referrals({ token, onToast }) {
  const [stats, setStats]   = useState(null);
  const [lb, setLb]         = useState([]);
  const [code, setCode]     = useState("");
  const [applying, setApplying] = useState(false);
  const [loading, setLoading]   = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.get("/users/me/referrals", token),
      api.get("/referrals/leaderboard", token),
    ]).then(([s, l]) => {
      setStats(s);
      setLb(l.leaderboard || []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [token]);

  async function applyCode() {
    if (code.length !== 8) { onToast("Enter an 8-character invite code", "error"); return; }
    try {
      setApplying(true);
      await api.post("/referrals/apply", { code }, token);
      onToast("Invite code applied! Your referrer will earn rewards once you solve your first problem.", "success");
      setCode("");
    } catch(e) { onToast(e.message, "error"); }
    finally { setApplying(false); }
  }

  function copyLink() {
    const url = `${window.location.origin}?invite=${stats?.invite_code}`;
    navigator.clipboard?.writeText(url).then(() => onToast("Invite link copied!", "success"));
  }

  if (loading) return <div className="content"><Spinner /></div>;

  return (
    <div className="content fade-in">
      <h2 className="mb-4">Referrals & Network</h2>
      <div className="muted mb-24" style={{ fontSize: 13 }}>Invite developers. Earn reputation. Grow the community.</div>

      <div className="card-grid grid-2 mb-24">
        {/* Your invite code */}
        <div className="card" style={{ background: "linear-gradient(135deg, rgba(124,106,247,.08), rgba(6,214,160,.04))", borderColor: "rgba(124,106,247,.25)" }}>
          <div className="label mb-12">YOUR INVITE CODE</div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 36, fontWeight: 800, letterSpacing: 6, color: "var(--accent)", marginBottom: 16 }}>
            {stats?.invite_code || "———"}
          </div>
          <button className="btn btn-primary" onClick={copyLink}>📋 Copy Invite Link</button>
          <div className="muted mt-12" style={{ fontSize: 12, lineHeight: 1.6 }}>
            When someone signs up with your code and solves their first problem, you earn <strong style={{ color: "var(--gold)" }}>+50 reputation</strong>.
          </div>
        </div>

        {/* Stats */}
        <div className="card">
          <div className="label mb-16">YOUR REFERRAL STATS</div>
          <div className="card-grid grid-3" style={{ gap: 12 }}>
            {[
              { label: "Invited",    val: stats?.total_invited    ?? 0, color: "var(--accent)" },
              { label: "Activated",  val: stats?.total_activated  ?? 0, color: "var(--accent2)" },
              { label: "Rep Earned", val: stats?.reputation_earned ?? 0, color: "var(--gold)" },
            ].map(s => (
              <div key={s.label} style={{ textAlign: "center" }}>
                <div style={{ fontSize: 28, fontWeight: 800, color: s.color, fontFamily: "var(--font-display)" }}>{s.val}</div>
                <div className="label mt-4">{s.label}</div>
              </div>
            ))}
          </div>

          {/* Invitees list */}
          {(stats?.invites || []).length > 0 && (
            <div className="mt-16">
              <div className="label mb-8">PEOPLE YOU INVITED</div>
              {stats.invites.map((inv, i) => (
                <div key={i} className="flex items-center gap-8 mb-6" style={{ fontSize: 13 }}>
                  <div className="avatar-sm" style={{ width: 24, height: 24, fontSize: 11 }}>{inv.display_name[0]}</div>
                  <span style={{ flex: 1 }}>{inv.display_name}</span>
                  <span className={`pill ${inv.activated_at ? "pill-green" : "pill-muted"}`} style={{ fontSize: 10 }}>
                    {inv.activated_at ? "Activated" : "Pending"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Apply invite code */}
      <div className="card mb-24">
        <h3 className="mb-12">Apply an Invite Code</h3>
        <div className="muted mb-16" style={{ fontSize: 13 }}>If someone referred you, enter their code here to give them credit.</div>
        <div className="flex gap-8" style={{ maxWidth: 360 }}>
          <input className="input" placeholder="XXXXXXXX" maxLength={8} value={code}
            onChange={e => setCode(e.target.value.toUpperCase())}
            style={{ fontFamily: "var(--font-mono)", letterSpacing: 4, fontWeight: 700 }} />
          <button className="btn btn-primary" onClick={applyCode} disabled={applying}>
            {applying ? "Applying…" : "Apply"}
          </button>
        </div>
      </div>

      {/* Referral leaderboard */}
      <div className="card">
        <h3 className="mb-16">Top Referrers</h3>
        {lb.length === 0 ? <Empty icon="🏆" msg="Be the first to refer someone!" /> : (
          lb.map((r, i) => (
            <div key={r.id} className="flex items-center gap-12 mb-10" style={{ padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
              <div style={{ width: 28, textAlign: "center", fontWeight: 800, color: i < 3 ? ["var(--gold)", "var(--muted)", "var(--accent3)"][i] : "var(--muted)", fontSize: 16 }}>
                {i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : `#${i+1}`}
              </div>
              <div className="avatar-sm">{r.display_name[0]}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{r.display_name}</div>
                <div className="muted" style={{ fontSize: 11 }}>{r.total_activated} activated · {r.reputation_earned} rep earned</div>
              </div>
              <div style={{ fontWeight: 800, color: "var(--accent)", fontSize: 18, fontFamily: "var(--font-display)" }}>
                {r.total_invited}
                <span className="muted" style={{ fontSize: 11, fontWeight: 400, marginLeft: 4 }}>invited</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ─── NOTIFICATIONS BELL ───────────────────────────────────────────────────────
function NotifBell({ token }) {
  const [notifs, setNotifs] = useState([]);
  const [open, setOpen]     = useState(false);
  const unread = notifs.filter(n => !n.is_read).length;
  const ref = useRef(null);

  useEffect(() => {
    api.get("/users/me/notifications", token)
      .then(d => setNotifs(d.notifications || []))
      .catch(() => {});
    const id = setInterval(() => {
      api.get("/users/me/notifications", token).then(d => setNotifs(d.notifications || [])).catch(() => {});
    }, 30000);
    return () => clearInterval(id);
  }, [token]);

  useEffect(() => {
    function handler(e) { if (ref.current && !ref.current.contains(e.target)) setOpen(false); }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  async function readAll() {
    await api.post("/users/me/notifications/read", {}, token).catch(() => {});
    setNotifs(prev => prev.map(n => ({ ...n, is_read: true })));
  }

  return (
    <div style={{ position: "relative" }} ref={ref}>
      <button
        onClick={() => { setOpen(!open); if (!open && unread > 0) readAll(); }}
        style={{ background: "none", border: "none", cursor: "pointer", position: "relative", padding: "4px 8px", color: "var(--text)" }}>
        <span style={{ fontSize: 18 }}>🔔</span>
        {unread > 0 && (
          <span style={{ position: "absolute", top: 0, right: 0, background: "var(--accent3)", color: "white", borderRadius: "50%", width: 16, height: 16, fontSize: 9, fontWeight: 800, display: "flex", alignItems: "center", justifyContent: "center" }}>
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>
      {open && (
        <div style={{ position: "absolute", right: 0, top: "calc(100% + 8px)", width: 320, background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 12, boxShadow: "0 8px 32px rgba(0,0,0,.4)", zIndex: 9999, overflow: "hidden" }}>
          <div className="flex items-center justify-between" style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
            <span style={{ fontWeight: 700, fontSize: 13 }}>Notifications</span>
            {unread > 0 && <button className="btn btn-ghost" style={{ fontSize: 11, padding: "2px 8px" }} onClick={readAll}>Mark all read</button>}
          </div>
          <div style={{ maxHeight: 360, overflowY: "auto" }}>
            {notifs.length === 0 ? (
              <div style={{ padding: 24, textAlign: "center", color: "var(--muted)", fontSize: 13 }}>No notifications yet</div>
            ) : notifs.map(n => (
              <div key={n.id} style={{ padding: "10px 16px", borderBottom: "1px solid var(--border)", background: n.is_read ? "transparent" : "rgba(124,106,247,.06)" }}>
                <div style={{ fontSize: 13, fontWeight: n.is_read ? 400 : 600 }}>{n.title}</div>
                {n.body && <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}>{n.body}</div>}
                <div style={{ fontSize: 10, color: "var(--muted)", marginTop: 4 }}>{n.created_at ? new Date(n.created_at).toLocaleString() : ""}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}



// ─── AI CODE REVIEW ───────────────────────────────────────────────────────────
function AIReview({ token, onToast }) {
  const [code, setCode]       = useState("# Paste your code here for AI review\ndef solution(nums):\n    seen = {}\n    for i, n in enumerate(nums):\n        if n in seen:\n            return [seen[n], i]\n        seen[n] = i\n    return []\n");
  const [lang, setLang]       = useState("python3");
  const [title, setTitle]     = useState("");
  const [result, setResult]   = useState(null);
  const [loading, setLoading] = useState(false);

  const LANGS = ["python3", "javascript", "java", "cpp", "go"];

  async function runReview() {
    if (!code.trim() || code.trim() === "# Paste your code here for AI review") {
      onToast("Paste some code first", "error"); return;
    }
    setLoading(true); setResult(null);
    try {
      const d = await api.post("/ai/review", { code, language: lang, problem_title: title }, token);
      setResult(d);
    } catch(e) { onToast(e.message, "error"); }
    finally { setLoading(false); }
  }

  const SEVERITY_COLOR = { high: "var(--accent3)", medium: "var(--gold)", low: "var(--muted)" };
  const SCORE_COLOR = (s) => s >= 8 ? "var(--accent2)" : s >= 5 ? "var(--gold)" : "var(--accent3)";

  return (
    <div className="content fade-in">
      <h2 className="mb-4">AI Code Review</h2>
      <div className="muted mb-20" style={{ fontSize: 13 }}>
        Paste your code and get instant analysis: time complexity, code quality, improvements, and alternative approaches — powered by Claude AI.
      </div>

      <div style={{ display: "grid", gridTemplateColumns: result ? "1fr 1fr" : "1fr", gap: 20 }}>
        {/* Code input */}
        <div>
          <div className="flex gap-10 mb-12" style={{ flexWrap: "wrap" }}>
            <input className="input" style={{ flex: "1 1 200px" }} placeholder="Problem title (optional — improves review quality)"
              value={title} onChange={e => setTitle(e.target.value)} />
            <select className="input" style={{ width: 130 }} value={lang} onChange={e => setLang(e.target.value)}>
              {LANGS.map(l => <option key={l} value={l}>{l}</option>)}
            </select>
            <button className="btn btn-primary" onClick={runReview} disabled={loading} style={{ minWidth: 120 }}>
              {loading ? (
                <span className="flex items-center gap-8"><Spinner /> Analysing…</span>
              ) : "🤖 Review Code"}
            </button>
          </div>

          <div className="editor-wrap">
            <div className="editor-header">
              <span className="dot dot-red"/><span className="dot dot-yellow"/><span className="dot dot-green"/>
              <span style={{ marginLeft: 8, fontSize: 11 }}>
                {lang === "python3" ? "solution.py" : lang === "javascript" ? "solution.js" : lang === "java" ? "Solution.java" : lang === "cpp" ? "solution.cpp" : "solution.go"}
              </span>
              <span className="muted" style={{ marginLeft: "auto", fontSize: 10 }}>
                {code.split("\n").length} lines · {code.length} chars
              </span>
            </div>
            <MonacoEditor value={code} onChange={setCode} language={lang} height={400} />
          </div>

          {/* Feature list when no result */}
          {!result && !loading && (
            <div className="card mt-16" style={{ background: "linear-gradient(135deg, rgba(124,106,247,.06), rgba(6,214,160,.04))", borderColor: "rgba(124,106,247,.2)" }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 16 }}>
                {[
                  { icon: "⚡", label: "Time Complexity", desc: "Big-O analysis of your algorithm" },
                  { icon: "💾", label: "Space Complexity", desc: "Memory usage analysis" },
                  { icon: "🔍", label: "Code Quality", desc: "Naming, readability, edge cases" },
                  { icon: "💡", label: "Improvements", desc: "Concrete code rewrite suggestions" },
                  { icon: "🔀", label: "Alternatives", desc: "Better algorithms if they exist" },
                  { icon: "⭐", label: "Overall Score", desc: "1–10 quality rating" },
                ].map(f => (
                  <div key={f.label} style={{ textAlign: "center" }}>
                    <div style={{ fontSize: 24, marginBottom: 6 }}>{f.icon}</div>
                    <div style={{ fontSize: 12, fontWeight: 700 }}>{f.label}</div>
                    <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>{f.desc}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Review results */}
        {result && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {/* Score + complexities */}
            <div className="card" style={{ background: "linear-gradient(135deg, rgba(124,106,247,.08), rgba(6,214,160,.04))", borderColor: "rgba(124,106,247,.25)" }}>
              <div className="flex items-center justify-between mb-16">
                <div>
                  <h3>Review Complete</h3>
                  <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                    {result.source === "ai" ? "Powered by Claude AI" : "Rule-based analysis (add ANTHROPIC_API_KEY for AI)"}
                  </div>
                </div>
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontSize: 48, fontWeight: 900, fontFamily: "var(--font-display)", color: SCORE_COLOR(result.review?.overall_score || 0), lineHeight: 1 }}>
                    {result.review?.overall_score ?? "—"}
                  </div>
                  <div className="label mt-4" style={{ fontSize: 10 }}>/ 10</div>
                </div>
              </div>
              <div className="card-grid grid-2" style={{ gap: 10 }}>
                {[
                  { label: "Time Complexity",  val: result.review?.time_complexity  || "—", color: "var(--accent)" },
                  { label: "Space Complexity", val: result.review?.space_complexity || "—", color: "var(--accent2)" },
                ].map(c => (
                  <div key={c.label} className="card card-sm" style={{ textAlign: "center", background: "var(--bg3)" }}>
                    <div style={{ fontSize: 16, fontWeight: 800, fontFamily: "var(--font-mono)", color: c.color }}>{c.val}</div>
                    <div className="label mt-4" style={{ fontSize: 10 }}>{c.label}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Summary */}
            {result.review?.summary && (
              <div className="card">
                <div className="label mb-8" style={{ fontSize: 10 }}>SUMMARY</div>
                <div style={{ fontSize: 14, lineHeight: 1.7, color: "var(--text)" }}>{result.review.summary}</div>
              </div>
            )}

            {/* Strengths */}
            {(result.review?.strengths || []).length > 0 && (
              <div className="card" style={{ borderColor: "rgba(6,214,160,.25)", background: "rgba(6,214,160,.04)" }}>
                <div className="label mb-10" style={{ fontSize: 10, color: "var(--accent2)" }}>✓ STRENGTHS</div>
                {result.review.strengths.map((s, i) => (
                  <div key={i} className="flex items-center gap-8 mb-6" style={{ fontSize: 13 }}>
                    <span style={{ color: "var(--accent2)", flexShrink: 0 }}>✓</span>
                    <span>{s}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Issues */}
            {(result.review?.issues || []).length > 0 && (
              <div className="card">
                <div className="label mb-10" style={{ fontSize: 10, color: "var(--accent3)" }}>⚠ ISSUES</div>
                {result.review.issues.map((issue, i) => (
                  <div key={i} className="flex gap-10 mb-10 pb-10" style={{ borderBottom: "1px solid var(--border)" }}>
                    <span style={{ fontSize: 11, fontWeight: 700, color: SEVERITY_COLOR[issue.severity] || "var(--muted)", minWidth: 48, textTransform: "uppercase" }}>
                      {issue.severity}
                    </span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 13, lineHeight: 1.5 }}>{issue.description}</div>
                      {issue.line_hint && (
                        <code style={{ fontSize: 11, color: "var(--muted)", display: "block", marginTop: 4 }}>{issue.line_hint}</code>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Improved snippet */}
            {result.review?.improved_snippet && (
              <div className="card">
                <div className="label mb-8" style={{ fontSize: 10, color: "var(--accent)" }}>💡 SUGGESTED IMPROVEMENT</div>
                <div className="editor-wrap" style={{ margin: 0 }}>
                  <div className="editor-header">
                    <span className="dot dot-red"/><span className="dot dot-yellow"/><span className="dot dot-green"/>
                    <span style={{ marginLeft: 8, fontSize: 10 }}>improved snippet</span>
                  </div>
                  <pre className="editor-textarea" style={{ margin: 0, fontSize: 12, minHeight: "auto", padding: "12px 16px", overflow: "auto" }}>
                    {result.review.improved_snippet}
                  </pre>
                </div>
              </div>
            )}

            {/* Alternative approach */}
            {result.review?.alternative_approach && (
              <div className="card" style={{ borderColor: "rgba(255,127,63,.2)", background: "rgba(255,127,63,.04)" }}>
                <div className="label mb-8" style={{ fontSize: 10, color: "var(--orange)" }}>🔀 ALTERNATIVE APPROACH</div>
                <div style={{ fontSize: 13, lineHeight: 1.7 }}>{result.review.alternative_approach}</div>
              </div>
            )}

            {/* Tags */}
            {(result.review?.tags || []).length > 0 && (
              <div className="flex gap-6" style={{ flexWrap: "wrap" }}>
                {result.review.tags.map(t => (
                  <span key={t} className="pill pill-accent" style={{ fontSize: 11 }}>{t}</span>
                ))}
              </div>
            )}

            {/* Re-review button */}
            <button className="btn btn-ghost" onClick={() => { setResult(null); }}>
              ← Review different code
            </button>
          </div>
        )}

        {loading && (
          <div className="card" style={{ display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 16, minHeight: 300 }}>
            <Spinner />
            <div style={{ fontSize: 14, fontWeight: 600 }}>Analysing your code…</div>
            <div className="muted" style={{ fontSize: 12 }}>Checking complexity, quality, and improvements</div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── CERTIFICATIONS ───────────────────────────────────────────────────────────
function Certifications({ token, onToast }) {
  const [certs, setCerts]   = useState([]);
  const [types, setTypes]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.get("/users/me/certifications", token),
      api.get("/certifications/types", token),
    ]).then(([c, t]) => {
      setCerts(c.certifications || []);
      setTypes(t.types || []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [token]);

  async function checkCerts() {
    setChecking(true);
    try {
      const d = await api.post("/certifications/check", {}, token);
      if (d.awarded > 0) {
        onToast(`🎓 ${d.awarded} new certification${d.awarded > 1 ? "s" : ""} earned!`, "success");
        const c = await api.get("/users/me/certifications", token);
        setCerts(c.certifications || []);
      } else {
        onToast("No new certifications yet — keep solving problems!", "success");
      }
    } catch(e) { onToast(e.message, "error"); }
    finally { setChecking(false); }
  }

  function copyVerifyLink(cert) {
    const url = `${window.location.origin}/verify/${cert.verification_hash}`;
    navigator.clipboard?.writeText(url).then(() => onToast("Verification link copied!", "success"));
  }

  const certMap = {};
  certs.forEach(c => { certMap[c.cert_type_id || c.skill_id] = c; });

  const LEVEL_COLOR = { beginner: "var(--accent2)", intermediate: "var(--gold)", advanced: "var(--accent)", expert: "var(--accent3)" };
  const LEVEL_ICONS = { beginner: "🌱", intermediate: "⚡", advanced: "🔥", expert: "💎" };

  if (loading) return <div className="content"><Spinner /></div>;

  return (
    <div className="content fade-in">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2>Certifications</h2>
          <div className="muted mt-4" style={{ fontSize: 13 }}>Verified skill certificates you can share with recruiters</div>
        </div>
        <button className="btn btn-primary" onClick={checkCerts} disabled={checking}>
          {checking ? "Checking…" : "🎓 Check for New Certs"}
        </button>
      </div>

      {/* Earned certs */}
      {certs.length > 0 && (
        <div className="mb-24">
          <h3 className="mb-16">Your Certifications ({certs.length})</h3>
          <div className="card-grid grid-2">
            {certs.map((cert, i) => (
              <div key={i} className="card" style={{ background: "linear-gradient(135deg, rgba(124,106,247,.1), rgba(6,214,160,.05))", borderColor: "rgba(124,106,247,.35)", position: "relative", overflow: "hidden" }}>
                {/* Background accent */}
                <div style={{ position: "absolute", top: -20, right: -20, width: 80, height: 80, borderRadius: "50%", background: "rgba(124,106,247,.1)" }} />

                <div className="flex items-center justify-between mb-12">
                  <div style={{ fontSize: 32 }}>{LEVEL_ICONS[cert.level] || "🎓"}</div>
                  <span style={{ fontSize: 10, fontWeight: 700, color: LEVEL_COLOR[cert.level] || "var(--accent)", textTransform: "uppercase", letterSpacing: 1, background: "rgba(124,106,247,.15)", padding: "3px 10px", borderRadius: 20 }}>
                    {cert.level || "Verified"}
                  </span>
                </div>

                <div style={{ fontWeight: 800, fontSize: 16, marginBottom: 4 }}>{cert.name}</div>
                <div className="muted" style={{ fontSize: 12, marginBottom: 16 }}>
                  Issued {cert.issued_at ? new Date(cert.issued_at).toLocaleDateString("en-IN", { year: "numeric", month: "long", day: "numeric" }) : ""}
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  <div className="flex gap-8 items-center" style={{ fontSize: 12 }}>
                    <span className="muted">Verify:</span>
                    <code style={{ fontSize: 10, color: "var(--accent)", fontFamily: "var(--font-mono)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      /verify/{cert.verification_hash?.slice(0, 16)}…
                    </code>
                  </div>
                  <button className="btn btn-sm btn-secondary" onClick={() => copyVerifyLink(cert)}>
                    📋 Copy Verification Link
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Available certifications */}
      <div>
        <h3 className="mb-16">Available Certifications</h3>
        <div className="muted mb-16" style={{ fontSize: 13 }}>
          Earn certifications by achieving the required skill scores. These are independently verifiable by any recruiter.
        </div>

        {types.length === 0 ? <Empty icon="🎓" msg="No certification types configured yet" /> : (
          types.map((type, i) => {
            const earned = certMap[type.id];
            return (
              <div key={i} className="card mb-10" style={{ borderColor: earned ? "rgba(6,214,160,.3)" : "var(--border)", background: earned ? "rgba(6,214,160,.03)" : "transparent" }}>
                <div className="flex items-center gap-16">
                  <div style={{ fontSize: 32 }}>{LEVEL_ICONS[type.level] || "🎓"}</div>
                  <div style={{ flex: 1 }}>
                    <div className="flex items-center gap-10 mb-4">
                      <div style={{ fontWeight: 700, fontSize: 15 }}>{type.name}</div>
                      {earned && <span className="pill pill-green" style={{ fontSize: 10 }}>✓ Earned</span>}
                      <span style={{ fontSize: 11, fontWeight: 700, color: LEVEL_COLOR[type.level] || "var(--muted)", textTransform: "uppercase", letterSpacing: 1 }}>
                        {type.level}
                      </span>
                    </div>
                    <div className="muted" style={{ fontSize: 13 }}>{type.description}</div>
                    {type.requirements && (
                      <div style={{ fontSize: 12, marginTop: 8, color: "var(--accent)" }}>
                        Requirements: {type.requirements}
                      </div>
                    )}
                  </div>
                  {!earned && (
                    <div style={{ textAlign: "right" }}>
                      <div className="muted" style={{ fontSize: 11 }}>Not yet earned</div>
                    </div>
                  )}
                  {earned && (
                    <button className="btn btn-sm btn-secondary" onClick={() => copyVerifyLink(earned)}>
                      Share
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {certs.length === 0 && (
        <div className="card mt-20" style={{ background: "linear-gradient(135deg, rgba(124,106,247,.06), rgba(6,214,160,.03))", borderColor: "rgba(124,106,247,.2)", textAlign: "center", padding: "48px 40px" }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🎓</div>
          <h3 className="mb-8">No Certifications Yet</h3>
          <div className="muted mb-24" style={{ fontSize: 14, lineHeight: 1.7 }}>
            Solve problems, build your skill scores, and earn industry-recognized certifications that prove your abilities to employers.
          </div>
          <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
            <button className="btn btn-primary" onClick={checkCerts}>Check Now</button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── GITHUB PROFILE ───────────────────────────────────────────────────────────
function GitHubProfile({ token, onToast }) {
  const [profile, setProfile]   = useState(null);
  const [username, setUsername] = useState("");
  const [loading, setLoading]   = useState(true);
  const [connecting, setConnecting] = useState(false);

  useEffect(() => {
    api.get("/github/profile", token)
      .then(d => setProfile(d))
      .catch(() => setProfile(null))
      .finally(() => setLoading(false));
  }, [token]);

  async function connect() {
    if (!username.trim()) { onToast("Enter your GitHub username", "error"); return; }
    setConnecting(true);
    try {
      const d = await api.post("/github/connect", { github_username: username }, token);
      onToast(`Connected to GitHub as @${d.github_username}!`, "success");
      setUsername("");
      const p = await api.get("/github/profile", token);
      setProfile(p);
    } catch(e) { onToast(e.message, "error"); }
    finally { setConnecting(false); }
  }

  const LANG_COLORS = {
    Python: "#3572A5", JavaScript: "#f1e05a", TypeScript: "#2b7489",
    Java: "#b07219", "C++": "#f34b7d", Go: "#00ADD8", Rust: "#dea584",
    Ruby: "#701516", Swift: "#ffac45", Kotlin: "#F18E33",
    "C#": "#178600", PHP: "#4F5D95",
  };

  if (loading) return <div className="content"><Spinner /></div>;

  if (!profile || profile.error) return (
    <div className="content fade-in">
      <h2 className="mb-4">GitHub Integration</h2>
      <div className="muted mb-24" style={{ fontSize: 13 }}>Connect your GitHub to showcase your repositories, contribution streak, and open source work.</div>

      <div className="card" style={{ maxWidth: 520 }}>
        <div style={{ fontSize: 48, marginBottom: 16, textAlign: "center" }}>⚡</div>
        <h3 className="mb-16" style={{ textAlign: "center" }}>Connect Your GitHub</h3>

        <div className="form-group">
          <label className="form-label">YOUR GITHUB USERNAME</label>
          <div className="flex gap-8">
            <input className="input" placeholder="octocat" value={username}
              onChange={e => setUsername(e.target.value)}
              onKeyDown={e => e.key === "Enter" && connect()} />
            <button className="btn btn-primary" onClick={connect} disabled={connecting}>
              {connecting ? "Connecting…" : "Connect"}
            </button>
          </div>
          <div className="muted mt-8" style={{ fontSize: 12 }}>
            Only public profile data is fetched. No write access required.
          </div>
        </div>

        <div className="card card-sm mt-16" style={{ background: "rgba(124,106,247,.06)", borderColor: "rgba(124,106,247,.2)" }}>
          <div className="label mb-8" style={{ fontSize: 10 }}>WHAT GETS SHOWN ON YOUR PROFILE</div>
          {["Public repositories & stars", "Programming languages used", "Contribution activity", "Pinned/featured repos", "Follower / following counts"].map(f => (
            <div key={f} className="flex items-center gap-8 mb-6" style={{ fontSize: 13 }}>
              <span style={{ color: "var(--accent2)" }}>✓</span> {f}
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const gh = profile.github || profile;
  const repos = gh.top_repos || gh.repos || [];
  const langs = gh.languages || {};

  return (
    <div className="content fade-in">
      {/* Header */}
      <div className="card mb-20" style={{ background: "linear-gradient(135deg, rgba(124,106,247,.08), rgba(6,214,160,.04))", borderColor: "rgba(124,106,247,.2)" }}>
        <div className="flex items-center gap-16">
          {gh.avatar_url && (
            <img src={gh.avatar_url} alt="avatar" style={{ width: 72, height: 72, borderRadius: "50%", border: "3px solid var(--accent)" }} />
          )}
          {!gh.avatar_url && (
            <div style={{ width: 72, height: 72, borderRadius: "50%", background: "linear-gradient(135deg, var(--accent), var(--accent2))", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 28, fontWeight: 800 }}>
              {(gh.login || "G")[0].toUpperCase()}
            </div>
          )}
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 800, fontSize: 20 }}>{gh.name || gh.login}</div>
            <div style={{ color: "var(--accent)", fontFamily: "var(--font-mono)", fontSize: 13, marginTop: 2 }}>@{gh.login}</div>
            {gh.bio && <div className="muted mt-6" style={{ fontSize: 13 }}>{gh.bio}</div>}
            <div className="flex gap-16 mt-10" style={{ fontSize: 13, flexWrap: "wrap" }}>
              {gh.location && <span className="muted">📍 {gh.location}</span>}
              {gh.public_repos > 0 && <span>📦 {gh.public_repos} repos</span>}
              {gh.followers > 0 && <span>👥 {gh.followers} followers</span>}
              {gh.following > 0 && <span>🔗 {gh.following} following</span>}
            </div>
          </div>
          <a href={`https://github.com/${gh.login}`} target="_blank" rel="noopener noreferrer"
            className="btn btn-secondary btn-sm">
            View on GitHub ↗
          </a>
        </div>
      </div>

      <div className="card-grid grid-2 mb-20">
        {/* Languages */}
        <div className="card">
          <h3 className="mb-16">Languages</h3>
          {Object.keys(langs).length === 0 ? <Empty icon="💻" msg="No language data" /> : (
            Object.entries(langs).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([lang, count]) => (
              <div key={lang} className="flex items-center gap-12 mb-10">
                <div style={{ width: 10, height: 10, borderRadius: "50%", background: LANG_COLORS[lang] || "var(--accent)", flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                  <div className="flex justify-between mb-4" style={{ fontSize: 13 }}>
                    <span>{lang}</span>
                    <span className="muted" style={{ fontSize: 11 }}>{count} repos</span>
                  </div>
                  <div className="skill-bar">
                    <div className="skill-bar-fill" style={{ width: `${Math.min(100, (count / (Object.values(langs)[0] || 1)) * 100)}%`, background: LANG_COLORS[lang] || "var(--accent)" }} />
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Stats */}
        <div className="card">
          <h3 className="mb-16">GitHub Stats</h3>
          <div className="card-grid grid-2" style={{ gap: 10 }}>
            {[
              { label: "Repositories", val: gh.public_repos || 0, color: "var(--accent)", icon: "📦" },
              { label: "Stars",        val: gh.total_stars || repos.reduce((a, r) => a + (r.stargazers_count || 0), 0), color: "var(--gold)",    icon: "⭐" },
              { label: "Followers",    val: gh.followers || 0,    color: "var(--accent2)", icon: "👥" },
              { label: "Following",    val: gh.following || 0,    color: "var(--muted)",   icon: "🔗" },
            ].map(s => (
              <div key={s.label} className="card card-sm" style={{ textAlign: "center", background: "var(--bg3)" }}>
                <div style={{ fontSize: 20, marginBottom: 4 }}>{s.icon}</div>
                <div style={{ fontSize: 22, fontWeight: 800, color: s.color, fontFamily: "var(--font-display)" }}>{s.val}</div>
                <div className="label mt-2" style={{ fontSize: 10 }}>{s.label}</div>
              </div>
            ))}
          </div>

          {gh.company && (
            <div className="flex items-center gap-8 mt-12" style={{ fontSize: 13 }}>
              <span>🏢</span> <span>{gh.company}</span>
            </div>
          )}
          {gh.blog && (
            <div className="flex items-center gap-8 mt-6" style={{ fontSize: 13 }}>
              <span>🌐</span>
              <a href={gh.blog} target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent)" }}>{gh.blog}</a>
            </div>
          )}
        </div>
      </div>

      {/* Top Repositories */}
      <div className="card">
        <h3 className="mb-16">Top Repositories</h3>
        {repos.length === 0 ? <Empty icon="📦" msg="No public repositories" /> : (
          <div className="card-grid grid-2">
            {repos.slice(0, 6).map((repo, i) => (
              <a key={i} href={repo.html_url} target="_blank" rel="noopener noreferrer"
                className="card card-sm" style={{ textDecoration: "none", color: "inherit", cursor: "pointer", display: "block" }}>
                <div className="flex items-center gap-8 mb-6">
                  <span style={{ fontSize: 14 }}>📦</span>
                  <span style={{ fontWeight: 700, fontSize: 13, color: "var(--accent)" }}>{repo.name}</span>
                  {repo.fork && <span className="muted" style={{ fontSize: 10 }}>(fork)</span>}
                </div>
                <div className="muted" style={{ fontSize: 12, marginBottom: 10, lineHeight: 1.5 }}>
                  {repo.description?.slice(0, 80) || "No description"}
                </div>
                <div className="flex gap-12" style={{ fontSize: 11, color: "var(--muted)" }}>
                  {repo.language && (
                    <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <span style={{ width: 8, height: 8, borderRadius: "50%", background: LANG_COLORS[repo.language] || "var(--accent)", display: "inline-block" }} />
                      {repo.language}
                    </span>
                  )}
                  <span>⭐ {repo.stargazers_count || 0}</span>
                  <span>🍴 {repo.forks_count || 0}</span>
                </div>
              </a>
            ))}
          </div>
        )}
      </div>

      {/* Reconnect option */}
      <div className="flex justify-end mt-16">
        <button className="btn btn-ghost btn-sm" onClick={() => setProfile(null)} style={{ color: "var(--muted)", fontSize: 12 }}>
          Change GitHub account
        </button>
      </div>
    </div>
  );
}

// ─── PUBLIC PORTFOLIO PAGE ────────────────────────────────────────────────────
function PublicPortfolio({ token, onToast }) {
  const [username, setUsername] = useState("");
  const [portfolio, setPortfolio] = useState(null);
  const [loading, setLoading]   = useState(false);
  const [myUsername, setMyUsername] = useState(null);

  useEffect(() => {
    api.get("/users/me/profile", token)
      .then(d => setMyUsername(d.username || d.display_name?.toLowerCase().replace(/\s+/g, "")))
      .catch(() => {});
  }, [token]);

  async function loadPortfolio(u) {
    const uname = u || username.trim();
    if (!uname) return;
    setLoading(true); setPortfolio(null);
    try {
      const d = await api.get(`/portfolio/${uname}`, token);
      setPortfolio(d);
    } catch(e) { onToast("Profile not found", "error"); }
    finally { setLoading(false); }
  }

  function copyLink() {
    const url = `${window.location.origin}/portfolio/${portfolio?.profile?.username || username}`;
    navigator.clipboard?.writeText(url).then(() => onToast("Portfolio link copied!", "success"));
  }

  const DIFF_COLOR = { easy: "var(--accent2)", medium: "var(--gold)", hard: "var(--accent3)" };

  return (
    <div className="content fade-in">
      <h2 className="mb-4">Developer Portfolio</h2>
      <div className="muted mb-20" style={{ fontSize: 13 }}>
        Every SkillOS user has a shareable public portfolio page. Share yours with recruiters, on LinkedIn, or in your resume.
      </div>

      {/* Your portfolio link */}
      {myUsername && (
        <div className="card mb-24" style={{ background: "linear-gradient(135deg, rgba(124,106,247,.08), rgba(6,214,160,.04))", borderColor: "rgba(124,106,247,.25)" }}>
          <div className="label mb-8" style={{ fontSize: 10 }}>YOUR PUBLIC PORTFOLIO</div>
          <div className="flex items-center gap-10" style={{ flexWrap: "wrap" }}>
            <code style={{ fontSize: 14, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--accent)", flex: "1 1 200px" }}>
              {window.location.origin}/portfolio/{myUsername}
            </code>
            <div className="flex gap-8">
              <button className="btn btn-primary btn-sm" onClick={() => loadPortfolio(myUsername)}>Preview</button>
              <button className="btn btn-secondary btn-sm" onClick={() => { navigator.clipboard?.writeText(`${window.location.origin}/portfolio/${myUsername}`); onToast("Link copied!", "success"); }}>📋 Copy</button>
            </div>
          </div>
        </div>
      )}

      {/* Search any portfolio */}
      <div className="flex gap-10 mb-20">
        <input className="input" style={{ maxWidth: 360 }}
          placeholder="Search any developer by username…" value={username}
          onChange={e => setUsername(e.target.value)}
          onKeyDown={e => e.key === "Enter" && loadPortfolio()} />
        <button className="btn btn-secondary" onClick={() => loadPortfolio()} disabled={loading || !username.trim()}>
          {loading ? "Loading…" : "View Portfolio →"}
        </button>
      </div>

      {/* Portfolio view */}
      {loading && <Spinner />}

      {portfolio && (
        <div className="fade-in">
          {/* Header */}
          <div className="card mb-20" style={{ background: "linear-gradient(135deg, rgba(124,106,247,.1), rgba(6,214,160,.05))", borderColor: "rgba(124,106,247,.3)" }}>
            <div className="flex items-center justify-between mb-16" style={{ flexWrap: "wrap", gap: 12 }}>
              <div className="flex items-center gap-16">
                {portfolio.profile?.avatar_url ? (
                  <img src={portfolio.profile.avatar_url} alt="" style={{ width: 72, height: 72, borderRadius: "50%", border: "3px solid var(--accent)" }} />
                ) : (
                  <div style={{ width: 72, height: 72, borderRadius: "50%", background: "linear-gradient(135deg, var(--accent), var(--accent2))", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 28, fontWeight: 800 }}>
                    {(portfolio.profile?.display_name || "?")[0]}
                  </div>
                )}
                <div>
                  <h2 style={{ marginBottom: 4 }}>{portfolio.profile?.display_name}</h2>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--accent)", marginBottom: 8 }}>
                    skillos.dev/{portfolio.profile?.username || username}
                  </div>
                  {portfolio.profile?.bio && <div className="muted" style={{ fontSize: 13 }}>{portfolio.profile.bio}</div>}
                  <div className="flex gap-12 mt-8" style={{ fontSize: 12, flexWrap: "wrap" }}>
                    {portfolio.profile?.location && <span className="muted">📍 {portfolio.profile.location}</span>}
                    {portfolio.profile?.college && <span className="muted">🎓 {portfolio.profile.college}</span>}
                  </div>
                </div>
              </div>
              <div className="flex gap-10" style={{ flexWrap: "wrap" }}>
                <button className="btn btn-sm btn-secondary" onClick={copyLink}>📋 Share</button>
                {portfolio.profile?.github_username && (
                  <a href={`https://github.com/${portfolio.profile.github_username}`} target="_blank" rel="noopener noreferrer" className="btn btn-sm btn-ghost">GitHub ↗</a>
                )}
              </div>
            </div>

            {/* Stats */}
            <div className="card-grid grid-4" style={{ gap: 10 }}>
              {[
                { label: "Reputation",   val: portfolio.profile?.reputation      || 0, color: "var(--gold)" },
                { label: "Solved",       val: portfolio.profile?.problems_solved  || 0, color: "var(--accent2)" },
                { label: "Streak",       val: `${portfolio.profile?.streak_current || 0}d`, color: "var(--orange)" },
                { label: "Skills",       val: (portfolio.profile?.skills || []).length, color: "var(--accent)" },
              ].map(s => (
                <div key={s.label} style={{ textAlign: "center", padding: "8px 0" }}>
                  <div style={{ fontSize: 24, fontWeight: 800, color: s.color, fontFamily: "var(--font-display)" }}>{s.val}</div>
                  <div className="label mt-2" style={{ fontSize: 10 }}>{s.label}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="card-grid grid-2 mb-20">
            {/* Recent solutions */}
            <div className="card">
              <h3 className="mb-16">Recent Solutions</h3>
              {(portfolio.recent_solutions || []).length === 0 ? <Empty icon="⌨️" msg="No public solutions yet" /> : (
                portfolio.recent_solutions.map((s, i) => (
                  <div key={i} className="flex items-center gap-10 mb-8 pb-8" style={{ borderBottom: "1px solid var(--border)" }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: DIFF_COLOR[s.difficulty] || "var(--muted)", minWidth: 48, textTransform: "capitalize" }}>
                      {s.difficulty}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>{s.title}</div>
                      {s.skill_name && <div className="muted" style={{ fontSize: 11 }}>{s.skill_name}</div>}
                    </div>
                    <div className="muted" style={{ fontSize: 10 }}>
                      {s.submitted_at ? new Date(s.submitted_at).toLocaleDateString() : ""}
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Certifications */}
            <div className="card">
              <h3 className="mb-16">Certifications</h3>
              {(portfolio.certifications || []).length === 0 ? <Empty icon="🎓" msg="No certifications yet" /> : (
                portfolio.certifications.map((c, i) => (
                  <div key={i} className="flex items-center gap-12 mb-10 pb-10" style={{ borderBottom: "1px solid var(--border)" }}>
                    <span style={{ fontSize: 24 }}>🎓</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 700, fontSize: 14 }}>{c.name}</div>
                      <div className="muted" style={{ fontSize: 11 }}>
                        Issued {c.issued_at ? new Date(c.issued_at).toLocaleDateString() : ""}
                      </div>
                    </div>
                    <span className="pill pill-green" style={{ fontSize: 10 }}>Verified</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* GitHub data if connected */}
          {portfolio.github && !portfolio.github.error && (
            <div className="card">
              <h3 className="mb-16">GitHub Activity</h3>
              <div className="flex items-center gap-16 mb-16">
                {portfolio.github.avatar_url && (
                  <img src={portfolio.github.avatar_url} alt="" style={{ width: 40, height: 40, borderRadius: "50%" }} />
                )}
                <div>
                  <div style={{ fontWeight: 600 }}>@{portfolio.github.login}</div>
                  <div className="muted" style={{ fontSize: 12 }}>{portfolio.github.public_repos || 0} public repos · {portfolio.github.followers || 0} followers</div>
                </div>
              </div>
              {(portfolio.github.top_repos || []).slice(0, 4).map((repo, i) => (
                <div key={i} className="flex items-center gap-10 mb-8" style={{ fontSize: 13 }}>
                  <span>📦</span>
                  <a href={repo.html_url} target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent)", flex: 1 }}>{repo.name}</a>
                  <span className="muted" style={{ fontSize: 11 }}>⭐ {repo.stargazers_count || 0}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Intro when nothing loaded */}
      {!portfolio && !loading && (
        <div className="card" style={{ textAlign: "center", padding: "48px 40px" }}>
          <div style={{ fontSize: 64, marginBottom: 16 }}>🌐</div>
          <h3 className="mb-8">Share Your Developer Identity</h3>
          <div className="muted" style={{ fontSize: 14, lineHeight: 1.7, maxWidth: 500, margin: "0 auto" }}>
            Every SkillOS user gets a public portfolio page showing their verified skills, solved problems, certifications, and GitHub contributions. It's better than a resume — it's proof.
          </div>
        </div>
      )}
    </div>
  );
}

// ─── MAIN APP ─────────────────────────────────────────────────────────────────
const NAV = [
  { id: "dashboard",  label: "Dashboard",      icon: "◈",  section: "platform" },
  { id: "problems",   label: "Problems",       icon: "⟨⟩", section: "platform" },
  { id: "paths",      label: "Learn",          icon: "◐",  section: "platform" },
  { id: "coaching",   label: "AI Coach",       icon: "✦",  section: "platform" },
  { id: "contests",   label: "Contests",       icon: "⚡",  section: "compete" },
  { id: "leaderboard",label: "Leaderboard",    icon: "⊞",  section: "compete" },
  { id: "community",  label: "Community",      icon: "◎",  section: "compete" },
  { id: "projects",   label: "Projects",       icon: "⌗",  section: "build" },
  { id: "recruiter",  label: "Recruiter",      icon: "⌖",  section: "build" },
  { id: "interview",  label: "Live Interview", icon: "⬡",  section: "build" },
  { id: "company",    label: "Company",        icon: "🏢",  section: "build" },
  { id: "analytics",  label: "Analytics",     icon: "📊",  section: "build" },
  { id: "profile",    label: "Profile",        icon: "◉",  section: "me" },
  { id: "security",    label: "Security",       icon: "🛡",  section: "me" },
  { id: "referrals",  label: "Referrals",      icon: "🔗",  section: "me" },
  { id: "certs",      label: "Certifications", icon: "🎓",  section: "me" },
  { id: "github",     label: "GitHub",         icon: "⚙",  section: "me" },
  { id: "portfolio",  label: "Portfolio",      icon: "🌐",  section: "me" },
  { id: "aireview",   label: "AI Review",      icon: "🤖",  section: "platform" },
];
const SECTIONS = { platform: "Platform", compete: "Compete", build: "Build", me: "Account" };

export default function App() {
  const [token, saveToken, clearToken] = useToken();
  const [user, setUser]   = useState(() => { try { return JSON.parse(localStorage.getItem("sk_user") || "null"); } catch { return null; } });
  const [page, setPage]   = useState("dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [toast, setToast] = useState(null);

  function onAuth(t, u) { saveToken(t); setUser(u); localStorage.setItem("sk_user", JSON.stringify(u)); }
  function onToast(msg, type = "success") { setToast({ msg, type }); }
  function logout() { clearToken(); setUser(null); localStorage.removeItem("sk_user"); }

  if (!token) return (
    <>
      <style>{css}</style>
      <AuthPage onAuth={onAuth} />
    </>
  );

  const sections = [...new Set(NAV.map(n => n.section))];

  return (
    <>
      <style>{css}</style>
      <div className="app">
        <div className="mobile-header">
          <button className="hamburger" onClick={() => setSidebarOpen(true)} style={{color:"#fff",fontSize:24,background:"none",border:"none",cursor:"pointer",padding:"4px 8px"}}>☰</button>
          <div className="mobile-logo">SKILL<span>OS</span></div>
          <div className="flex gap-8 items-center">
            <NotifBell token={token} />
            <div className="dot dot-green" />
          </div>
        </div>
        {sidebarOpen && <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />}
        <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
          <button className="sidebar-close" onClick={() => setSidebarOpen(false)}>✕</button>
          <div className="logo"><div className="logo-icon">S</div><div><div>SKILL<span>OS</span></div><small className="logo-sub">ELITE PLATFORM</small></div></div>
          <nav className="nav">
            {sections.map(sec => (
              <div key={sec}>
                <div className="nav-section">{SECTIONS[sec]}</div>
                {NAV.filter(n => n.section === sec).map(n => (
                  <div key={n.id} className={`nav-item ${page===n.id?"active":""}`} onClick={() => { setPage(n.id); setSidebarOpen(false); }}>
                    <span className="nav-icon">{n.icon}</span>
                    {n.label}
                  </div>
                ))}
              </div>
            ))}
          </nav>
          <div className="sidebar-user">
            <div className="avatar">{(user?.display_name || "D")[0]}</div>
            <div style={{ flex: 1, minWidth: 0, overflow: "hidden" }}>
              <div style={{ fontWeight: 600, fontSize: 13, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{user?.display_name || "Developer"}</div>
              <div style={{ fontSize: 11, opacity: 0.5, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{user?.email || ""}</div>
            </div>
            <button onClick={logout} title="Sign out" style={{ background: "none", border: "none", cursor: "pointer", color: "#f87171", fontSize: 16, padding: "4px 6px", borderRadius: 6, flexShrink: 0 }}>⏻</button>
          </div>
        </aside>

        <main className="main">
          <div className="topbar">
            <div className="page-title">{NAV.find(n => n.id===page)?.label || page}</div>
            <div className="flex gap-8 items-center">
              <NotifBell token={token} />
              <div className="dot dot-green" />
              <span className="muted" style={{ fontSize: 12 }}>Connected</span>
            </div>
          </div>

          {page === "dashboard"   && <Dashboard       token={token} user={user} />}
          {page === "problems"    && <Problems        token={token} onToast={onToast} />}
          {page === "paths"       && <LearningPaths   token={token} onToast={onToast} />}
          {page === "coaching"    && <Coaching        token={token} />}
          {page === "contests"    && <Contests        token={token} onToast={onToast} />}
          {page === "leaderboard" && <Leaderboard     token={token} />}
          {page === "community"   && <Community       token={token} onToast={onToast} />}
          {page === "projects"    && <Projects        token={token} onToast={onToast} />}
          {page === "recruiter"   && <Recruiter       token={token} onToast={onToast} />}
          {page === "interview"   && <LiveInterview   token={token} onToast={onToast} />}
          {page === "company"     && <CompanyDashboard token={token} onToast={onToast} />}
          {page === "analytics"   && <Analytics       token={token} />}
          {page === "profile"     && <Profile         token={token} onToast={onToast} />}
          {page === "security"    && <SecuritySettings token={token} onToast={onToast} />}
          {page === "referrals"   && <Referrals        token={token} onToast={onToast} />}
          {page === "certs"       && <Certifications   token={token} onToast={onToast} />}
          {page === "github"      && <GitHubProfile    token={token} onToast={onToast} />}
          {page === "portfolio"   && <PublicPortfolio  token={token} onToast={onToast} />}
          {page === "aireview"    && <AIReview         token={token} onToast={onToast} />}
        </main>
      </div>
      {toast && <Toast msg={toast.msg} type={toast.type} onClose={() => setToast(null)} />}
    </>
  );
}
