# Reflection on Multi-Agent Travel Planner Implementation

## What I Learned

Implementing this multi-agent workflow taught me that simplicity beats complexity in prompt engineering. I initially created 100+ line prompts with templates, examples, and checklists, assuming more guidance would yield better results. Instead, the model hallucinated (inserting random Korean characters) and refused to complete itineraries, asking for confirmation instead. When I simplified the FINAL REVISED ITINERARY section to just 2 critical rules, it worked perfectly. This revealed that LLMs, like humans, suffer from cognitive overload—concise, direct instructions outperform exhaustive documentation.

I also learned that constraint-based design shapes agent behavior. By withholding internet access from Marco (Planner) and giving it exclusively to Sophia (Reviewer), I created natural specialization. Marco became creative and storytelling-focused while Sophia became evidence-driven and skeptical. This architectural choice enforced role separation more effectively than any prompt instructions could.

## Challenges and Solutions

**Incomplete Outputs**: Sophia initially output only Day 1, then said "Day 2 will follow similarly." My elaborate prompts made her think this was a multi-turn conversation requiring confirmation. Solution: Reduced instructions from 50+ lines to "Provide the complete corrected itinerary with ALL days. Do not summarize any days."

**Formatting Issues**: The `~$` combination in `**Daily Budget**: ~$250` broke markdown rendering, causing asterisks to appear and "DailyBudget" to render in italics. Solution: Removed `~` symbols and added blank lines between fields for cleaner rendering. Also it helped to kill the streamlit and restart it to get better result.

## Creative Design Choices

**Agent Personas**: Marco as an enthusiastic 15-year experienced travel plnner and Sophia as a meticulous operations manager gave consistent voices that improved engagement.

**Creative Freedom Section**: Explicitly told Marco(Planner) that while format is structured, content choices are what make itineraries special—successfully balancing structure with creativity.

**Comprehensive Requirements**: Added city clustering, seasonal considerations, and accommodation tiers beyond the basic template, making outputs genuinely bookable.

## What Could Be Improved

**Reviewer Presentation**: Sophia(Reviewer) is currently functional but dry. She could maintain her evidence-based validation while presenting verified information more engagingly—like Marco's(Planner) storytelling style but grounded in facts. Instead of "✅ Louvre verified," she could say "Great news—verified the Louvre is open (Wednesdays 9 AM-6 PM). Recent reviews suggest arriving at 9 AM to avoid 2-hour lines. More details on why to visit, tips and suggestions for activites like the planner does. "

---

## External Tools Used

- **Claude Code**: Rapid iteration through 15+ prompt revisions, debugging issues, and implementing fixes
