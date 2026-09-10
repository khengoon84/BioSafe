# BioSafe WSL2 Development Environment v0.1

This is the recommended local development folder for BioSafe on Windows + WSL2 Ubuntu.

## Recommended architecture

- **Windows:** VS Code UI, browser, Ollama/Qwen
- **WSL2 Ubuntu:** BioSafe source, Python, Git, retrieval, benchmark runner
- **Project location:** `~/projects/biosafe` inside the Linux filesystem

Microsoft recommends keeping Linux-tool projects in the WSL filesystem rather than `/mnt/c/...` for better file-system performance.

## Folder structure

```text
biosafe/
├── .vscode/          VS Code WSL settings
├── benchmarks/       benchmark datasets
├── config/           local configuration examples
├── data/             frozen BioSafe KB / manifests / evaluator data
├── docs/             development notes
├── logs/             local logs (Git ignored)
├── models/           placeholder only; Ollama manages model storage
├── output/           benchmark JSONL outputs
├── prompts/          BioSafe system prompt / response schema
├── scripts/          WSL setup, preflight and benchmark commands
├── src/              frozen retrieval + integration source
├── .gitignore
├── requirements.txt
└── README.md
```

## First-time setup

From WSL2 Ubuntu:

```bash
mkdir -p ~/projects
cd ~/projects
```

Copy/extract this `biosafe` folder into `~/projects/biosafe`, then:

```bash
cd ~/projects/biosafe
chmod +x scripts/*.sh
./scripts/setup_wsl2.sh
```

Activate the environment:

```bash
source .venv/bin/activate
```

## VS Code

From the project directory:

```bash
code .
```

Make sure the VS Code window shows that it is connected to WSL/Ubuntu.

## Ollama

Keep Ollama on Windows initially.

On Windows PowerShell or Command Prompt:

```powershell
ollama pull qwen3:0.6b
ollama list
```

Back in WSL:

```bash
python3 scripts/detect_ollama.py
```

The detector tests localhost first, then the WSL default gateway.

## Five-case smoke test

```bash
source .venv/bin/activate
python scripts/run_wsl2_smoke.py --model qwen3:0.6b --limit 5
```

The JSONL result is written to `output/`.

Upload that file to ChatGPT for the first end-to-end BioSafe model evaluation.

## Important rules

- Keep the repository under `~/projects/biosafe`, not `/mnt/c/...`.
- Use Git from WSL for this repository.
- Do not commit `.venv`, model files, benchmark outputs, or logs.
- Keep CFG-02 + Router v0.2 + Scope Gate v0.2.1 frozen during initial LLM benchmarking.
- Fine-tuning remains out of scope until base-model + RAG benchmarking is complete.
