# [PRD/Specification] GitStories: Software Engineering Learning Platform

## 1. Executive Summary & Core Paradigm Shift

### 1.1 Product Vision
**GitStories** is an interactive software engineering learning platform and academic research evaluation tool. Instead of feeding students dry textbooks or isolated code snippets, GitStories mines real-world Open Source Software (OSS) history to teach the messy, complex reality of software evolution and maintenance.

### 1.2 The Paradigm Shift: From "Code Diffs" to "Engineering Drama"
This project rejects superficial code-level tutoring in favor of deep architectural reverse-engineering.

* **The Old Approach (Code-Centric):** Focused heavily on micro-level syntax errors, line-by-line file diffs (Red/Green lines), and tedious Python-based code slicing to isolate 40 lines of source code.
* **The New Approach (Drama-Centric):** Shifts the entire pedagogical focus to the **human and technical friction** inside GitHub issues and Pull Requests. It treats the heated arguments, architectural debates, maintainer pushbacks, and ultimate design compromises as the primary educational material.
* **The LLM as an Architect Analyst:** The LLM ceases to be a simple formatting engine. Instead, it acts as an advanced analyst capable of decoding complex developer timelines to understand *why* an initial solution failed, *how* system scalability or security concerns were raised, and *what* architectural tradeoffs were settled upon.

---

## 2. System Architecture & Dual-Track Pipeline

The platform uses a decoupled stack featuring a **React frontend** and a **FastAPI REST API backend**, running a highly optimized multi-pass curation pipeline.

```
[Student Input: Interest] ➔ [Repo Discovery & Summary] ➔ [Student Selects Repo]
│
┌─────────────────────────────────────────────────────────────────┘
▼
[Pass 1: Mechanical Screening] ➔ [Pass 1.5: Semantic Gate (Haiku)] ➔ [Pass 2: Deep Enrichment]
```

### 2.1 The Data Extraction & Refinement Engine
To build high-value "Story Bundles" without bloated low-level source code scraping, the pipeline operates in three distinct, cost-effective stages:

#### Pass 1: Mechanical Screening (Heuristic Filtering)
The system hits the GitHub API to gather closed issues sorted by high engagement, applying strict mechanical constraints to isolate prime educational contexts:
* **High Engagement:** The issue must contain **at least 8 comments**.
* **Proven Resolution:** The issue must be linked to a **successfully merged Pull Request**.
* **Scope Constraint:** The PR must contain **5 or fewer changed files**, preventing massive, unreadable refactors and keeping the context focused.
* **Diverse Perspectives:** The discussion must feature **at least 3 unique active authors** to ensure a genuine technical debate occurred.

#### Pass 1.5: Semantic Pre-Screening Gate
To avoid wasting API costs on generic troubleshooting or setup noise, a lightweight, ultra-fast LLM (claude model) performs a binary triage on a compact context snippet (Issue title, body snippet, and early comment snippets).
* **Prompt Criteria:** *"Does this open-source discussion contain technical friction, architectural trade-offs, or design conflicts? Respond strictly with Yes or No."*
* Only candidates receiving a definitive **"Yes"** advance to final enrichment.

#### Pass 2: Deep Data Enrichment
Surviving elite candidates are compiled into a comprehensive, code-free `raw_story_bundles.json`. This bundle contains:
* **Discussion Timeline:** Complete chronological text logs mapping author usernames, their repository roles (e.g., Member, Contributor), and raw comment contents.
* **Commit History Metadata:** Sequential commit hashes and messages providing a roadmap of how the implementation evolved across developer iterations.
* **Metadata Integration:** Target courses, repository labels, and pull request review histories.

---

## 3. Product Walkthrough & User Experience Flow

```
+--------------------------------------+
| 1. Select Domain (e.g., Game Dev)    |
+--------------------------------------+
│
▼
+--------------------------------------+
| 2. Browse Suggested Verified Repos   |
+--------------------------------------+
│
▼
+--------------------------------------+
| 3. Deep-Dive: ~4 Extracted Stories   |
+--------------------------------------+
│
▼
+--------------------------------------+
| 4. Interactive Drama & Quiz Workspace|
+--------------------------------------+
```

### 3.1 Step 1: Personalized Onboarding
Upon entering the application, students explicitly state their current engineering focus or industry interests (e.g., *Game Development*, *E-Commerce backends in Java*, *AI Agent Frameworks*).

### 3.2 Step 2: Repository Discovery
Based on the student's inputs, the tool dynamically surfaces a tailored selection of high-star, highly reputable, and active GitHub repositories. Each repository option is presented alongside an LLM-generated high-level summary outlining its architectural significance.

### 3.3 Step 3: Story Catalog Generation
Once the student selects a specific repository to explore, the backend extracts a curated set of prominent engineering narratives (targeted cap: **4 core stories** per repository execution) using the enriched pipeline data.

### 3.4 Step 4: The Interactive Workspace (Under Active Research)
Students progress through the extracted stories sequentially. The workspace presents the "Engineering Drama" chronologically.
* **Context Delivery:** The application reveals the evolving technical dilemma, the differing viewpoints of the developers, and the stakes involved.
* **Evaluation Mode:** Students engage with interactive quizzes or analytical checkpoints embedded directly within the timeline of the debate before discovering the team's final decision.
* **Progression:** Completing a story logs metrics to the backend and unlocks the next narrative in the repository sequence.

---

## 4. Current Research Core Objective

The primary metric of success for GitStories is not standard feature deployment, but academic validation. The absolute priority of the current experimental phase is to evaluate:

> **General Comprehension Capacity:** Can an LLM, given *only* our mechanically and semantically refined issue-comment text bundles, accurately reverse-engineer and comprehend the high-level architectural disputes and ultimate design decisions of human software engineers?

By treating the version control history as a living narrative, GitStories aims to bridge the gap between classroom theory and production-level system design engineering.