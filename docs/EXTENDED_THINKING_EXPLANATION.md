# Extended Thinking System - Technical Explanation

## Overview

The Extended Thinking System transforms AI from an instant-response tool into a deliberative reasoner that explores problems over minutes or hours, explicitly tracking uncertainty and building understanding incrementally.

## Core Concept

**Traditional AI**: Question → Immediate Answer
**Extended Thinking**: Question → Hours of Exploration → Evolved Understanding

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     USER SUBMITS QUESTION                    │
│            "What is the relationship between                 │
│             consciousness and intelligence?"                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              SESSION MANAGER (session_manager.py)            │
│  • Creates ThinkingSession in database                       │
│  • Spawns background asyncio task                            │
│  • Returns session_id to user immediately                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│            THINKING ENGINE LOOP (thinking_engine.py)         │
│                                                              │
│  ┌──────────────── MAIN LOOP ─────────────────┐            │
│  │                                              │            │
│  │  1. FOCUS SELECTION                         │            │
│  │     ├─ Unexplored questions exist?          │            │
│  │     │  └─ Pick highest priority question    │            │
│  │     └─ No questions?                        │            │
│  │        └─ Return to original question       │            │
│  │                                              │            │
│  │  2. THOUGHT GENERATION (via Ollama)         │            │
│  │     ├─ Send prompt with current focus       │            │
│  │     ├─ AI generates 3-5 thoughts            │            │
│  │     ├─ Parse: thought_text, type, confidence│            │
│  │     └─ Store as Thought records in DB       │            │
│  │                                              │            │
│  │  3. QUESTION GENERATION (every 5 thoughts)  │            │
│  │     ├─ QuestionGenerator analyzes thoughts  │            │
│  │     ├─ AI generates follow-up questions     │            │
│  │     ├─ Assigns priority (1-10)              │            │
│  │     └─ Store as SubQuestion records         │            │
│  │                                              │            │
│  │  4. SYNTHESIS (every 5 minutes)             │            │
│  │     ├─ Summarize current understanding      │            │
│  │     ├─ Extract key insights                 │            │
│  │     ├─ Calculate confidence level           │            │
│  │     ├─ List remaining questions             │            │
│  │     └─ Store as ThinkingSynthesis record    │            │
│  │                                              │            │
│  │  5. CHECK TIME BUDGET                       │            │
│  │     ├─ Time remaining?                      │            │
│  │     │  └─ Loop to step 1                    │            │
│  │     └─ Time expired?                        │            │
│  │        └─ Proceed to final synthesis        │            │
│  │                                              │            │
│  └──────────────────────────────────────────────┘            │
│                                                              │
│  6. FINAL SYNTHESIS                                         │
│     ├─ Review all thoughts, questions, syntheses            │
│     ├─ Generate comprehensive answer                        │
│     ├─ Calculate final confidence                           │
│     └─ Mark session as "completed"                          │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Thought Generation

**Prompt sent to Ollama**:
```
Question: What is consciousness?
Current Focus: Exploring the relationship between awareness and self-reflection

Generate 3-5 distinct thoughts about this focus.

Format:
THOUGHT: [your thought]
TYPE: [exploration/critique/connection/insight]
CONFIDENCE: [0.0-1.0]
---
```

**AI Response**:
```
THOUGHT: Consciousness might be best understood as layered awareness
TYPE: exploration
CONFIDENCE: 0.6
---
THOUGHT: Self-reflection requires metacognitive awareness
TYPE: connection
CONFIDENCE: 0.75
---
THOUGHT: But this circular definition doesn't explain origins
TYPE: critique
CONFIDENCE: 0.8
```

**Parsed and Stored**:
```python
Thought(
    session_id="abc-123",
    sequence_number=0,
    thought_text="Consciousness might be best understood as layered awareness",
    thought_type="exploration",
    confidence=0.6,
    time_offset_seconds=15
)
# ... stored in database
```

### 2. Question Generation

After accumulating thoughts, the QuestionGenerator:

**Prompt**:
```
Original Question: What is consciousness?

Recent thoughts:
- [exploration] Consciousness might be layered awareness
- [connection] Self-reflection requires metacognitive awareness
- [critique] Circular definition doesn't explain origins

What new questions arise that would help answer the original question?

Format:
QUESTION: [question text]
PRIORITY: [1-10]
WHY: [explanation]
---
```

**AI Response**:
```
QUESTION: How do different layers of awareness interact?
PRIORITY: 8
WHY: Understanding interaction could explain emergence
---
QUESTION: Can consciousness exist without self-reflection?
PRIORITY: 9
WHY: Tests whether self-reflection is necessary or optional
```

**Stored**:
```python
SubQuestion(
    session_id="abc-123",
    question_text="Can consciousness exist without self-reflection?",
    priority=9,
    explored=False
)
```

### 3. Synthesis Generation

Every 5 minutes, the engine synthesizes:

**Prompt**:
```
Original Question: What is consciousness?

Thoughts so far (last 20):
[... list of thoughts ...]

Sub-questions explored:
[... list with insights ...]

Synthesize your current understanding:

SYNTHESIS: [summary of understanding]
INSIGHTS:
- [key insight 1]
- [key insight 2]
CONFIDENCE: [0.0-1.0]
REMAINING:
- [unanswered question 1]
- [unanswered question 2]
```

**Stored**:
```python
ThinkingSynthesis(
    session_id="abc-123",
    sequence_number=2,
    synthesis_text="Current understanding: Consciousness appears to be...",
    key_insights=["Layered structure", "Requires feedback loops"],
    confidence_level=0.65,
    remaining_questions=["Origins still unclear", "Hard problem unresolved"],
    time_offset_seconds=600  # 10 minutes in
)
```

## Key Technical Components

### 1. ThinkingEngine (`thinking_engine.py`)

The core orchestrator running the thinking loop.

**Key Methods**:

```python
async def think(session, db_session, synthesis_interval):
    """Main thinking loop"""
    while not time_budget_exhausted:
        # 1. Decide focus
        focus = await self._decide_next_focus(session, db_session)

        # 2. Generate thoughts
        thoughts = await self._generate_thoughts(session, focus, db_session)

        # 3. Generate questions (every 5 thoughts)
        if should_generate_questions:
            questions = await self._generate_questions(session, db_session)

        # 4. Synthesize (every synthesis_interval)
        if should_synthesize:
            synthesis = await self._synthesize_understanding(session, db_session)

        # 5. Check time
        if time_expired:
            break

    # Final synthesis
    final = await self._final_synthesis(session, db_session)
```

### 2. QuestionGenerator (`question_generator.py`)

Generates and prioritizes follow-up questions.

**Key Methods**:

```python
async def generate_questions(session, recent_thoughts, max_questions=3):
    """Generate new questions from recent thoughts"""
    # Build prompt with thought context
    prompt = build_question_prompt(session, recent_thoughts)

    # Get AI response
    response = await ollama.generate_response(prompt)

    # Parse questions and priorities
    questions = self._parse_questions(response)

    return questions  # [(question_text, priority), ...]

async def prioritize_questions(session, questions, db_session):
    """Re-prioritize existing questions based on current understanding"""
    # AI re-ranks questions given current context
    # Updates priority scores
    return sorted_questions
```

### 3. SessionManager (`session_manager.py`)

Manages session lifecycle and background tasks.

**Key Methods**:

```python
async def start_session(question, duration_minutes, model_id):
    """Start a new thinking session"""
    # 1. Create database record
    session = ThinkingSession(
        original_question=question,
        thinking_duration_minutes=duration_minutes,
        model_id=model_id,
        status="created"
    )
    db.add(session)

    # 2. Spawn background task
    task = asyncio.create_task(
        self._run_thinking_session(session.id, synthesis_interval)
    )
    self.active_tasks[session.id] = task

    return session

async def pause_session(session_id):
    """Pause a running session"""
    # Cancel background task
    task = self.active_tasks.get(session_id)
    task.cancel()

    # Update database
    session.status = "paused"
    session.paused_at = now()

async def resume_session(session_id):
    """Resume a paused session"""
    # Adjust time budget to account for pause
    # Restart background task
```

## Parsing Logic

The system uses regex patterns to parse AI responses:

```python
def _parse_thoughts(response_text):
    """Extract thoughts from AI response"""
    blocks = response_text.split("---")

    for block in blocks:
        # Extract thought text
        thought_match = re.search(
            r"THOUGHT:\s*(.+?)(?=TYPE:|$)",
            block,
            re.DOTALL
        )

        # Extract type
        type_match = re.search(r"TYPE:\s*(\w+)", block)

        # Extract confidence
        confidence_match = re.search(r"CONFIDENCE:\s*([\d.]+)", block)

        if thought_match:
            thoughts.append((
                thought_match.group(1).strip(),
                type_match.group(1) if type_match else "exploration",
                float(confidence_match.group(1)) if confidence_match else 0.5
            ))

    return thoughts
```

**Fallback handling**: If parsing fails, uses sensible defaults rather than crashing.

## State Management

### Session States

```python
class ThinkingStatus(str, Enum):
    CREATED = "created"      # Session created, not started
    THINKING = "thinking"    # Active thinking in progress
    PAUSED = "paused"       # Temporarily paused
    COMPLETED = "completed" # Finished successfully
    FAILED = "failed"       # Encountered error
```

### State Transitions

```
created → thinking → completed
         ↓         ↗
      paused ----→

         ↓
       failed
```

## Confidence Evolution

The system tracks how confidence changes over time:

```python
# Stored in ThinkingSession.confidence_evolution as JSON array
[
    0.4,   # After first synthesis (low confidence)
    0.55,  # After second synthesis (growing)
    0.65,  # After third synthesis (moderate)
    0.75   # Final synthesis (higher confidence)
]
```

This reveals:
- **Increasing confidence**: Understanding is converging
- **Decreasing confidence**: Discovering more complexity
- **Stable confidence**: Reached understanding plateau

## Concurrency Model

```python
# FastAPI runs on async event loop
app = FastAPI()

# Each thinking session runs as background task
@router.post("/start")
async def start_thinking(request):
    # Returns immediately
    session = await session_manager.start_session(...)
    return {"session_id": session.id}

# Background:
async def _run_thinking_session(session_id):
    # Runs independently
    await thinking_engine.think(session, db, interval)
```

Users can start multiple thinking sessions, each running concurrently as separate async tasks.

## Database Schema

```
thinking_sessions (1) ─┬─→ (N) thoughts
                       ├─→ (N) sub_questions
                       └─→ (N) thinking_syntheses

thoughts (N) ─→ (1) sub_questions [optional relationship]
```

**Foreign Keys**:
- All child tables reference `thinking_sessions.id` with `CASCADE DELETE`
- `thoughts.related_to_question_id` → `sub_questions.id` (nullable)

## Performance Considerations

### Time Budget Management

```python
def get_elapsed_seconds(self):
    """Calculate time spent thinking"""
    if not self.started_at:
        return 0

    elapsed = (datetime.utcnow() - self.started_at).total_seconds()

    # Subtract paused time
    if self.paused_at and self.resumed_at:
        pause_duration = (self.resumed_at - self.paused_at).total_seconds()
        elapsed -= pause_duration

    return elapsed

def get_progress_percentage(self):
    """Calculate % of time budget used"""
    elapsed = self.get_elapsed_seconds()
    total_seconds = self.thinking_duration_minutes * 60
    return (elapsed / total_seconds) * 100
```

### Ollama API Calls

Each thinking cycle makes 3-4 Ollama API calls:
1. Thought generation (~5-10 seconds)
2. Question generation (every 5 thoughts, ~3-5 seconds)
3. Synthesis (every 5 minutes, ~10-15 seconds)
4. Final synthesis (at end, ~15-20 seconds)

**For a 30-minute session**:
- ~360 thought generations (30 min / 5 sec each)
- ~72 question generations (360 thoughts / 5)
- ~6 syntheses (30 min / 5 min)
- 1 final synthesis

**Total API calls**: ~440

## Example Session Timeline

```
00:00 - Session created
        Status: "created"

00:01 - Background task starts
        Status: "thinking"
        Focus: "What is consciousness?"

00:05 - Generated 3 thoughts (exploration type)
        Confidence: 0.5, 0.6, 0.55

00:10 - Generated 3 more thoughts (connection type)
        Created 2 sub-questions
        Confidence: 0.65, 0.7, 0.68

05:00 - First synthesis
        Key insights: 2
        Remaining questions: 4
        Confidence: 0.65

05:01 - Focus shifts to highest-priority question:
        "Can consciousness exist without self-reflection?"

10:00 - Second synthesis
        Key insights: 4
        Remaining questions: 3
        Confidence: 0.72

30:00 - Time budget exhausted
        Final synthesis begins

30:15 - Final synthesis complete
        Status: "completed"
        Final confidence: 0.78
        Total thoughts: 180
        Total questions: 36
        Total syntheses: 7
```

## API Integration

All operations are accessible via REST API:

```python
# Start session
POST /api/thinking/start
→ Returns session_id immediately
→ Thinking begins in background

# Monitor progress
GET /api/thinking/{session_id}
→ Returns current status, progress %, thought counts

# View thinking stream
GET /api/thinking/{session_id}/stream
→ Returns all thoughts in order

# Pause if needed
POST /api/thinking/{session_id}/pause
→ Suspends thinking, can resume later
```

## Why This Architecture?

### 1. **Explicit Uncertainty Tracking**
Rather than hiding uncertainty, the system makes it visible through:
- Confidence scores on each thought
- Sub-questions that represent unknowns
- Remaining questions in syntheses

### 2. **Incremental Understanding**
Knowledge builds over time through:
- Sequential thoughts that build on each other
- Questions that emerge from exploration
- Syntheses that consolidate progress

### 3. **Transparent Reasoning**
Users can inspect:
- Exact sequence of thoughts (stream of consciousness)
- What questions were asked and why
- How understanding evolved (via syntheses)
- Confidence trajectory over time

### 4. **Flexible Time Investment**
User controls thinking duration:
- Quick exploration: 5 minutes
- Moderate depth: 30 minutes
- Deep analysis: 2+ hours

### 5. **Pausable and Resumable**
Long sessions can be:
- Paused when insights are sufficient
- Resumed if more depth needed
- Exported for analysis

## Limitations and Trade-offs

### Relies on Format Compliance
- AI must follow THOUGHT:/TYPE:/CONFIDENCE: format
- Parsing failures fall back to defaults
- Quality depends on model instruction-following

### Sequential Processing
- One focus at a time (not parallel exploration)
- Design choice for coherent narrative
- Could parallelize in future version

### Fixed Synthesis Intervals
- Currently time-based (every N minutes)
- Could be event-based (after N insights)
- Trade-off: predictability vs. adaptiveness

### No Cross-Session Learning
- Each session is independent
- Could benefit from previous session insights
- Future: session memory/context

## Comparison to Other Approaches

### vs. Chain-of-Thought (CoT)
- **CoT**: Single-pass reasoning with explicit steps
- **Extended Thinking**: Multi-pass with explicit uncertainty and question generation

### vs. Tree-of-Thoughts (ToT)
- **ToT**: Explores multiple reasoning paths, prunes branches
- **Extended Thinking**: Linear exploration with course correction via questions

### vs. Reflexion
- **Reflexion**: Generates, evaluates, refines
- **Extended Thinking**: Continuous exploration with periodic consolidation

### Unique Aspects
- **Time-based**: Allocates thinking time budget
- **Question-driven**: Autonomously discovers unknowns
- **Confidence-tracked**: Quantifies certainty evolution
- **Stream-of-consciousness**: Full thought history accessible

## Summary

The Extended Thinking System provides **deliberative AI reasoning** through:

1. **Autonomous exploration** over extended time periods
2. **Explicit uncertainty** via sub-questions and confidence scores
3. **Incremental understanding** through periodic syntheses
4. **Transparent reasoning** via full thought stream access
5. **Flexible control** with pause/resume capability

The architecture separates concerns cleanly (engine, generator, manager), uses async for concurrency, persists all data for analysis, and provides a comprehensive REST API for integration.

This enables AI to **think deeply** rather than just **respond quickly**.
