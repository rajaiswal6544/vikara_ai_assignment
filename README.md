# CloudDash Multi-Agent Customer Support System

This is a prototype multi-agent AI support system I built for **CloudDash**, a fictional cloud infrastructure monitoring SaaS. The goal was to go beyond a simple chatbot and build something closer to how a real support team actually works — specialized agents that hand off to each other, a shared knowledge base they all draw from, and guardrails to keep responses safe and grounded.

---

## What does it actually do?

When a customer sends a message, it doesn't just go to one generic AI. There's a small team of specialized agents behind the scenes:

- **Triage Agent** reads the message first, figures out what the customer actually needs (billing issue? technical problem? account question?), and routes them to the right specialist.
- **Technical Agent** handles things like broken alerts, dashboard issues, API problems, AWS credential misconfigurations, and SSO failures.
- **Billing Agent** handles invoices, refunds, plan upgrades, payment failures, and double-charge complaints.
- **Escalation Agent** kicks in when a human needs to step in — it packages the full conversation context, generates a ticket ID, and hands everything off cleanly.

Every agent's response is grounded in a knowledge base of 22 articles. They don't just make things up — they retrieve relevant KB sections first and cite their sources.

---

## How to get it running

### What you need

- Python 3.10 or newer
- An OpenAI API key (the system uses GPT-4o for agents and `text-embedding-3-small` for the knowledge base)

### Step 1 — Install dependencies

```bash
cd Vikaraai_assign
pip install -r requirements.txt
```

### Step 2 — Set your API key

```bash
copy .env.example .env
```

Open `.env` and replace the placeholder with your real key:

```
OPENAI_API_KEY=sk-proj-your-key-here
DISABLE_RERANKER=1
```

> `DISABLE_RERANKER=1` skips downloading a 100MB cross-encoder model on first startup. Good for quick testing. Remove it later if you want the best retrieval quality.

### Step 3 — Start the server

**Windows CMD:**
```cmd
set OPENAI_API_KEY=sk-proj-your-key-here
set DISABLE_RERANKER=1
uvicorn app.main:app --reload --port 8000
```

**Linux / Mac:**
```bash
export OPENAI_API_KEY=sk-proj-your-key-here
export DISABLE_RERANKER=1
uvicorn app.main:app --reload --port 8000
```

### Step 4 — Open the chat UI

Go to `http://localhost:8000` in your browser. You'll see a clean chat interface where you can talk to the support system directly — no curl commands needed.

The API documentation is also available at `http://localhost:8000/docs` if you want to explore the raw endpoints.

---

## Testing the 4 assignment scenarios

These are the exact scenarios from the assignment spec, with the curl commands if you prefer to test from the terminal.

### Scenario 1 — Technical issue (AWS alerts not firing)

```cmd
curl -s -X POST http://localhost:8000/conversations -H "Content-Type: application/json" -d "{\"customer_id\":\"cust_001\",\"initial_message\":\"My alerts stopped firing after I updated my AWS credentials. I am on Pro plan.\"}"
```

Triage routes this to the Technical Agent, which retrieves the relevant KB article and walks through the fix step by step with source citations.

---

### Scenario 2 — Cross-agent handover (SSO → plan upgrade)

```cmd
curl -s -X POST http://localhost:8000/conversations -H "Content-Type: application/json" -d "{}"
```

Copy the `conversation_id` from the response, then:

```cmd
curl -s -X POST http://localhost:8000/conversations/YOUR_ID/messages -H "Content-Type: application/json" -d "{\"message\":\"My Okta SSO login is broken, users cannot sign in.\"}"
```

```cmd
curl -s -X POST http://localhost:8000/conversations/YOUR_ID/messages -H "Content-Type: application/json" -d "{\"message\":\"Also I want to upgrade from Pro to Enterprise.\"}"
```

```cmd
curl -s http://localhost:8000/conversations/YOUR_ID/handovers
```

Technical Agent handles the SSO issue, then detects the billing intent in the follow-up and hands the conversation over to Billing Agent. The handover log shows the full transfer with a context snapshot so Billing doesn't start from scratch.

---

### Scenario 3 — Escalation (double charge + refund + manager request)

```cmd
curl -s -X POST http://localhost:8000/conversations -H "Content-Type: application/json" -d "{\"customer_id\":\"cust_002\",\"initial_message\":\"I was charged twice for April. I need an immediate refund and want to speak to a manager.\"}"
```

The orchestrator detects the escalation intent immediately (phrases like "speak to a manager" or "charged twice" trigger it), routes straight to the Escalation Agent, and returns `escalated: true` with a ticket ID like `CLD-XXXXXX`.

---

### Scenario 4 — KB miss handled gracefully (Datadog integration)

```cmd
curl -s -X POST http://localhost:8000/conversations -H "Content-Type: application/json" -d "{\"initial_message\":\"Does CloudDash support integration with Datadog for cross-platform alerting?\"}"
```

The agent finds KB-006 which honestly documents that there's no native Datadog integration. Rather than hallucinating an answer, it acknowledges the limitation and offers alternatives or escalation.

---

## Running the test suite

```bash
pytest tests/ -v
```

All 32 tests pass. The tests cover orchestrator routing, handover logic, input/output guardrails, RAG chunking and retrieval, and agent response formatting.

---

## Architecture and design decisions

I want to be transparent about every significant design choice I made and why.

### A hand-rolled orchestrator instead of LangGraph or CrewAI

I considered using a graph-based framework like LangGraph but decided against it for this prototype. The control flow here is genuinely simple — four agents with well-defined transitions between them. A hand-rolled state machine in `orchestrator.py` makes that flow explicit and readable. You can read the `_dispatch` method and understand exactly what happens at every step without learning a framework's abstractions. If this were scaling to 20+ agents with complex parallel flows, LangGraph would make more sense.

### OpenAI for everything — one API key, consistent behavior

The original design brief didn't mandate a specific LLM provider. I chose OpenAI because it lets the evaluator run the whole system with a single API key. I use `gpt-4o` for the four customer-facing agents (where reasoning quality matters most) and `gpt-4o-mini` for fast utility tasks like query rewriting and generating context snapshots during handovers (where speed and cost matter more than depth).

### Hybrid retrieval — dense + sparse, fused and re-ranked

Each agent doesn't just do a vector similarity search. The RAG pipeline runs two retrieval strategies in parallel:

1. **Dense retrieval** via ChromaDB with `text-embedding-3-small` embeddings — good at semantic similarity, finding conceptually related content even when the exact keywords don't match.
2. **Sparse retrieval** via BM25 — good at exact keyword matching, especially useful for product names, error codes, and technical terms.

The results are fused using **Reciprocal Rank Fusion (RRF)**, which combines rankings without needing any training data. A cross-encoder re-ranker then does a final quality pass to push the most genuinely relevant chunks to the top. This three-stage pipeline is meaningfully better than any single retrieval strategy alone.

### ChromaDB over Pinecone or Qdrant

ChromaDB runs entirely in-process — no external service to set up, no API key, no Docker container. For a prototype where the evaluator needs to get it running in minutes, zero infrastructure is the right call. The retrieval quality is the same.

### Query rewriting before retrieval

Before hitting the knowledge base, each agent rewrites the customer's message into a cleaner search query using `gpt-4o-mini`. This matters because customers write things like "it's still not working after I did what you said" — a direct embedding of that sentence retrieves nothing useful. The rewriter expands it with context from the conversation history into something like "CloudDash alert not firing after AWS credential rotation Pro plan" which retrieves exactly the right KB article.

### YAML-driven agent configuration

All agent definitions live in `config/agents.yaml`. Adding a new agent type doesn't require touching the orchestrator or any existing code — you add a YAML entry and create a Python file inheriting `BaseAgent`. The orchestrator resolves agent classes dynamically using `importlib`. This is the kind of extensibility that matters in a production system where new agent types get added regularly.

### Guardrails on both input and output

**Input guardrails** check every customer message before it reaches any agent:
- Prompt injection detection (regex patterns catching things like "ignore all previous instructions")
- Off-topic filter (blocks questions completely unrelated to CloudDash)

**Output guardrails** check every agent response before it goes back to the customer:
- PII redaction (strips email addresses, phone numbers, credit card patterns)
- Hallucination check (flags responses that claim certainty about things not in the retrieved sources)

### Structured logging with trace IDs

Every request gets a `trace_id` that follows it through every component — triage, RAG retrieval, handover, guardrails. The logs are structured JSON via `structlog`, which means in a real deployment you could pipe them directly into Datadog or CloudWatch and search/filter by trace ID. This is the logging pattern I'd want in any production system.

---

## Known limitations (being honest)

1. **No persistence** — conversation state lives in memory and is lost when the server restarts. A production version would need a database.
2. **No authentication** — all endpoints are open. In production, you'd add API key validation or JWT auth.
3. **Mock account data** — the Billing Agent works from fixture data, not a real CRM or billing system.
4. **Single-node only** — the in-memory state can't be shared across multiple server instances. Real deployment would need Redis or a database-backed state store.
5. **No rate limiting** — nothing stops a client from hammering the API. A production version needs a token bucket or request rate limiter.

---

## Project structure

```
Vikaraai_assign/
├── app/
│   ├── main.py              # FastAPI app, endpoints, and UI serving
│   ├── orchestrator.py      # Central routing state machine
│   ├── models.py            # All Pydantic data models
│   ├── handover.py          # Handover protocol and context snapshots
│   ├── logger.py            # Structured JSON logging with trace IDs
│   ├── static/
│   │   └── index.html       # Chat UI (served at http://localhost:8000)
│   ├── agents/
│   │   ├── base.py          # BaseAgent abstract class
│   │   ├── triage.py        # Intent classification and routing
│   │   ├── technical.py     # Technical support specialist
│   │   ├── billing.py       # Billing support specialist
│   │   └── escalation.py    # Human escalation handler
│   ├── rag/
│   │   ├── loader.py        # Knowledge base ingestion and chunking
│   │   ├── embedder.py      # ChromaDB vector store
│   │   ├── retriever.py     # Hybrid retrieval (dense + BM25 + re-ranking)
│   │   └── rewriter.py      # Query rewriting with gpt-4o-mini
│   └── guardrails/
│       ├── input_guard.py   # Injection detection and off-topic filter
│       └── output_guard.py  # PII redaction and hallucination check
├── config/
│   └── agents.yaml          # Agent definitions — extend without touching code
├── knowledge_base/          # 22 KB articles across 5 categories
├── prompts/                 # System prompts for each agent
├── tests/                   # 32 pytest tests
├── prd.md                   # Product Requirements Document
├── architecture.md          # System architecture document
├── design.md                # Design decisions document
├── requirements.txt
└── .env.example
```

---

## API endpoints

| Method | Endpoint | What it does |
|--------|----------|--------------|
| GET | `/` | Opens the chat UI |
| GET | `/health` | Server liveness check |
| POST | `/conversations` | Start a new conversation (optionally with a first message) |
| POST | `/conversations/{id}/messages` | Send a follow-up message |
| GET | `/conversations/{id}` | Full conversation history |
| GET | `/conversations/{id}/handovers` | Handover audit log |
| GET | `/docs` | Interactive API documentation |
