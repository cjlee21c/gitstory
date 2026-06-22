import time

from app.llm.client import SEMANTIC_GATE_MODEL, client

GATE_PROMPT_TEMPLATE = (
    "Does this open-source discussion contain technical friction, architectural trade-offs, "
    "or design conflicts? Respond strictly with Yes or No.\n\n"
    "Context:\n{context}"
)


def pass_1_5_semantic_gate(qualified_candidates):
    print("\nInitiating Pass 1.5: Semantic Pre-Screening Gate...")
    start = time.time()
    elite_candidates = []

    for candidate in qualified_candidates:
        issue = candidate["issue"]
        comments_snippet = "\n".join(
            f"{c.get('user', {}).get('login', 'unknown')} ({c.get('author_association', 'NONE')}): {c.get('body', '')[:200]}"
            for c in candidate["comments"][:5]
        )
        compact_context = (
            f"Title: {issue['title']}\nBody: {str(issue.get('body', ''))[:400]}\nComments:\n{comments_snippet}"
        )
        prompt = GATE_PROMPT_TEMPLATE.format(context=compact_context)

        try:
            response = client.messages.create(
                model=SEMANTIC_GATE_MODEL,
                max_tokens=10,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            decision = response.content[0].text.strip()
            if "Yes" in decision:
                print(f"  [Elite] #{issue['number']}: {issue['title'][:50]}")
                elite_candidates.append(candidate)
            else:
                print(f"  [Skip] #{issue['number']} lacks technical drama")
        except Exception as e:
            print(f"  [API Error] #{issue['number']}: {e}")
        time.sleep(0.5)

    elapsed = round(time.time() - start, 1)
    print(f"\nPass 1.5 Complete. {len(elite_candidates)} elite candidates secured. ({elapsed}s)")
    return elite_candidates
