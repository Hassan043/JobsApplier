# Free local AI with Ollama

JobsApplier includes an Ollama adapter without an SDK dependency or API key. The runtime and model are separate prerequisites; adding this adapter does not install them.

## Windows setup

1. Install [Ollama for Windows](https://ollama.com/download/windows) from its official source.
2. Open a **new terminal**, then run `ollama --version`. If PowerShell says the term is not recognized, it cannot find the executable. Check the installation and reopen the terminal after installation; do not keep rerunning a missing command.
3. Choose a model appropriate for available RAM/VRAM. `qwen3:4b` is a small starting candidate, not a measured quality recommendation; its Ollama catalog download is about 2.5 GB, and running it needs additional memory for weights/context. The 8B variant is larger. CPU inference may exceed the app's timeout.
4. Download only when you are ready for that storage/network use:

```powershell
ollama pull qwen3:4b
ollama list
```

5. Use **local models**, and disable cloud features in the Ollama runtime. Ollama documents `OLLAMA_NO_CLOUD=1` or `disable_ollama_cloud` in its server configuration; restart the runtime after changing it. A variable set only for JobsApplier does not reconfigure an already running Ollama process.
6. Start JobsApplier, open **Sources & AI**, choose **Ollama**, enter the exact installed model name, set one AI call initially, enable AI, and choose **Reassess saved jobs** using synthetic data.

CLI equivalent:

```powershell
python main.py run --profile examples/demo_profile.json --input examples/jobs.json --ai --provider ollama --model qwen3:4b --max-jobs 2 --max-ai-calls 1
```

There is no provider API fee for local inference, but downloads, electricity, memory, and runtime are still required. The app sends requests only to `http://127.0.0.1:11434/api/chat`, refuses redirects/proxies, rejects cloud-named models, and does not automatically pull a model. A trusted local runtime can still be configured in ways the client cannot fully inspect; disable cloud explicitly rather than assuming localhost guarantees offline computation.

## Validation and failure behavior

Local requests enforce a JSON schema, disable thinking output, use temperature zero, and undergo the same exact-quotation validation as hosted AI. This checks provenance, not semantic correctness or calibration. A failure remains an unavailable AI score with the local baseline retained; it is not treated as a successful AI result. A slow CPU/model can time out at 60 seconds. An input above the conservative 12,000-character prompt bound is rejected without sending it. No retries, silent truncation, or model downloads occur.

The Ollama transport is fixture-tested, including grounded results, fabrication, incomplete output, call caps, input bounds, and cache separation from hosted providers. **No actual local model evaluation was performed for this release because the runtime was not installed.** Do not claim Qwen or another local model improves the existing benchmark until measured.

Hosted alternatives such as Groq and Gemini have free tiers subject to their model/account limits; they are research alternatives and are **not integrated providers in this release**. Use synthetic CVs when exploring a hosted service's terms.

References: [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs), [chat API](https://docs.ollama.com/api/chat), [local/cloud configuration](https://docs.ollama.com/faq), [Qwen3 catalog](https://ollama.com/library/qwen3), [Groq free-tier limits](https://console.groq.com/docs/rate-limits), [Gemini pricing and data-use differences](https://ai.google.dev/gemini-api/docs/pricing).
