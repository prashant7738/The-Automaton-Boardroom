"""Quick smoke-test: run tester_node against a minimal React (Vite) project."""
from dotenv import load_dotenv
load_dotenv()

from agency.nodes import tester_node

MINIMAL_REACT = {
    "package.json": """{
  "name": "test-app",
  "version": "0.0.1",
  "private": true,
  "scripts": {
    "build": "vite build"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "@vitejs/plugin-react": "^4.0.0"
  }
}
""",
    "vite.config.js": """import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({ plugins: [react()] });
""",
    "index.html": """<!DOCTYPE html>
<html lang="en">
  <head><meta charset="UTF-8" /><title>Test App</title></head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
""",
    "src/main.jsx": """import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
ReactDOM.createRoot(document.getElementById('root')).render(<App />);
""",
    "src/App.jsx": """import React from 'react';
export default function App() {
  return <h1>Hello from tester!</h1>;
}
""",
}

state = {
    "app_idea": "simple react app",
    "specification": "",
    "source_code": MINIMAL_REACT,
    "test_logs": "",
    "iterations": 1,
    "approved_by_human": False,
    "human_feedback": "",
    "required_inputs": [],
    "user_inputs": {},
}

print("Running tester_node...")
result = tester_node(state)
print("=== test_logs ===")
print(result["test_logs"])
