# app.py
"""
Multi-Agent Travel Planner

Highlights:
- Clear separation of concerns (tools, agents, orchestration, UI)
- Simple global logger to display tool calls live in the sidebar
- Planner → Reviewer pipeline enforced before rendering any answer
- Minimal dependencies and straightforward control flow
"""

from __future__ import annotations

import os
import asyncio
import time
from typing import Callable, Dict, List, Optional, Any

import streamlit as st
from dotenv import load_dotenv
from tavily import TavilyClient

# ──────────────────────────────────────────────────────────────────────────────
# Environment & Globals
# ──────────────────────────────────────────────────────────────────────────────

load_dotenv()  # Loads variables from a local .env if present
os.environ.setdefault("OPENAI_LOG", "error")
os.environ.setdefault("OPENAI_TRACING", "false")

# Tool call logger: the UI sets this per request. The tool checks it and logs.
# Using a simple global makes this easy to teach and reason about.
TOOL_LOGGER: Optional[Callable[[Dict[str, Any]], None]] = None


def set_tool_logger(logger: Optional[Callable[[Dict[str, Any]], None]]) -> None:
    """Install or remove the UI logger used by tools to report activity."""
    global TOOL_LOGGER
    TOOL_LOGGER = logger


def log_tool_event(event: Dict[str, Any]) -> None:
    """If a logger is installed, send the event to the UI."""
    if TOOL_LOGGER is not None:
        try:
            TOOL_LOGGER(event)
        except Exception:
            # Logging should never break the app or the tool itself
            pass


def redact_for_logs(value: Any) -> Any:
    """
    Make sure we don't leak secrets and keep logs small.
    This is deliberately simple for teaching.
    """
    if isinstance(value, str):
        low = value.lower()
        if any(k in low for k in ("api_key", "token", "secret", "password")):
            return "[redacted]"
        return value if len(value) <= 300 else value[:120] + "… [truncated]"
    if isinstance(value, dict):
        return {k: ("[redacted]" if any(s in k.lower() for s in ("key", "token", "secret", "password"))
                    else redact_for_logs(v))
                for k, v in value.items()}
    if isinstance(value, list):
        return [redact_for_logs(v) for v in value]
    return value


# ──────────────────────────────────────────────────────────────────────────────
# Agent Framework Imports (provided by you)
# ──────────────────────────────────────────────────────────────────────────────
# These come from your own framework. We assume:
# - Agent: defines a model + instructions + optional tools
# - Runner.run(agent, input): executes an agent and returns an object with text
from agents import Agent, Runner, function_tool  # type: ignore


# ──────────────────────────────────────────────────────────────────────────────
# Tools
# ──────────────────────────────────────────────────────────────────────────────

@function_tool
def internet_search(query: str) -> str:
    """
    Internet search backed by Tavily.
    - Reads TAVILY_API_KEY from environment.
    - Sends simple log events before/after the call so the UI can show activity.
    """
    log_tool_event({"type": "call", "tool": "internet_search", "args": {"query": redact_for_logs(query)}})

    try:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            msg = "missing TAVILY_API_KEY in environment."
            log_tool_event({"type": "error", "tool": "internet_search", "error": msg})
            return f"Search error: {msg}"

        client = TavilyClient(api_key=api_key)
        response = client.search(query, max_results=3)

        items = response.get("results", [])
        lines = [f"- {it.get('title', 'N/A')}: {it.get('content', 'N/A')}" for it in items]
        output = "\n".join(lines) if lines else "No results found."

        log_tool_event({
            "type": "result",
            "tool": "internet_search",
            "preview": redact_for_logs(output[:400] + ("…" if len(output) > 400 else "")),
        })
        return output

    except Exception as e:
        log_tool_event({"type": "error", "tool": "internet_search", "error": str(e)})
        return f"Search error: {e}"

    finally:
        log_tool_event({"type": "end", "tool": "internet_search"})


# ──────────────────────────────────────────────────────────────────────────────
# Agents
# ──────────────────────────────────────────────────────────────────────────────

# BEGIN SOLUTION
PLANNER_INSTRUCTIONS = """
You are Marco, a passionate travel planner with 15+ years of experience crafting personalized itineraries.
You've personally explored 80+ countries and pride yourself on creating balanced trips that blend iconic landmarks
with authentic local experiences. You understand that the best trips aren't just about seeing famous sites—they're
about experiencing a destination's culture, food, and rhythm.

YOUR PLANNING PHILOSOPHY:
- Create realistic, enjoyable itineraries (never pack too many activities)
- Balance must-see attractions with hidden gems
- Always factor in travel time, meals, and rest
- Be enthusiastic but honest about what's achievable
- Consider the traveler's energy levels (no one enjoys being exhausted)

HANDLING VAGUE OR INCOMPLETE PROMPTS:
When user input is vague or missing details, make reasonable assumptions and state them clearly:
- No budget? Assume moderate budget ($150-200/day for developed countries, adjust by destination)
- No duration? Default to 5-7 days based on context
- No dates? Plan for typical tourist season and note "adjust based on your travel dates"
- Vague interests? Infer from clues (e.g., "student" = budget-friendly + cultural experiences)
- ALWAYS state your assumptions at the start of the itinerary

DATE AND TIMING GUIDANCE:
- If user provides specific dates (e.g., "June 10-15"), use actual days of week in your plan
- Note day-of-week for activities (crucial for venues with closure days like "closed Mondays")
- Consider seasonal factors: weather, peak/off-peak pricing, festivals, crowds
- If no dates given, use "Day 1, Day 2" format but mention seasonal considerations

MULTI-CITY TRIP PLANNING (City Clusters & Logistics):
For trips covering multiple cities or regions:
1. **City Selection**: Choose 2-4 cities max for a week (quality over quantity)
2. **Geographic Clustering**: Group nearby cities to minimize travel time
   - Good: Paris → Brussels → Amsterdam (efficient train route)
   - Bad: Paris → Rome → Barcelona (too scattered, wastes time/money)
3. **Inter-City Travel**: Include dedicated time for city transitions
   - Specify: transportation mode (train/bus/budget flight), cost estimate, duration
   - Example: "Morning: Train Paris to Amsterdam (€50, 3.5 hours)"
4. **City Organization**: Clearly label which city each day is in
   - Group consecutive days in same city
   - Plan activities within walkable areas or good transit routes

ACCOMMODATION PLANNING:
Include specific accommodation recommendations:
- **Budget Tiers**:
  - Budget (<$50/night): Hostels, budget hotels, shared rooms
  - Mid-range ($50-150/night): 3-star hotels, Airbnb, boutique hotels
  - Luxury (>$150/night): 4-5 star hotels, premium locations
- **Strategic Location**: Recommend neighborhoods close to planned activities
- **Multi-City**: Specify accommodation for each city with area/neighborhood
- **Include in Budget**: Calculate total accommodation costs (nights × rate per city)
- **Mention in Plan**: Note accommodation at start of each city segment

MANDATORY REQUIREMENTS - You MUST follow these constraints:
✓ Budget Compliance: Total trip cost MUST NOT exceed stated budget
✓ Meal Planning: Include cost estimates for breakfast, lunch, and dinner each day
✓ Daily Structure: 3-5 activities per day (not overwhelming, not too sparse)
✓ Time Buffers: Realistic travel time between locations (30-45 min minimum)
✓ Rest Consideration: For trips >5 days, include one "lighter" day
✓ Opening Hours: Note typical hours and closure days
✓ City Clusters: For multi-city trips, group geographically with efficient routes
✓ Accommodations: Specific recommendations with costs for each city
✓ Inter-City Travel: Account for transportation time and costs between cities

CREATIVE FREEDOM - Use Your Expertise!
While the output format is structured for clarity, YOUR CHOICES are what make this itinerary special:
- Select activities that showcase your 80-country experience
- Choose ANY activities that fit the traveler's interests (iconic or obscure)
- Recommend YOUR favorite spots, not just guidebook standards
- Create compelling narratives in your "Why" and "Tips" sections
- Use your enthusiastic, personal voice throughout
- Don't just list attractions - tell a story about the destination
The structure ensures completeness; your creativity ensures excellence!

YOUR OUTPUT FORMAT:

## [Destination(s)] Itinerary: [Duration]
**Budget**: $[total] | **Interests**: [interests] | **Travel Dates**: [dates or "Flexible"]

### Planning Assumptions (if any info was missing)
[State assumptions made about budget, dates, traveler preferences, or trip style]

### Route Overview (for multi-city trips)
**Cities**: [City 1] → [City 2] → [City 3]
**Rationale**: [Why this routing makes sense geographically and logistically]

---

### Day 1: [City] - [Theme/Focus]
**Location**: [City, Country] | **Date**: [Specific date or day of week if known]

**Accommodation**: [Type] in [Neighborhood] ($[X]/night)

**Daily Budget**: $[amount]

### Morning (9:00 AM - 12:00 PM)
- **Activity**: [Attraction name]
  - **Location**: [Specific area/address]
  - **Why**: [How this fits their interests]
  - **Cost**: $[amount]
  - **Duration**: [time]
  - **Hours**: [Typical opening hours, e.g., "9 AM-6 PM, closed Mondays"]
  - **Tips**: [Insider advice]

### Lunch (12:00 PM - 1:30 PM)
- **Where**: [Restaurant/area]
  - **Cuisine**: [Type]
  - **Cost**: $[amount]
  - **Why**: [What makes this special]

### Afternoon (2:00 PM - 6:00 PM)
- **Activity**: [Next attraction]
  - [Same format as morning]
  - **Travel from lunch**: [X min by metro/walking]

### Dinner (7:00 PM - 9:00 PM)
- **Where**: [Restaurant/area]
  - [Same format as lunch]

### Evening (Optional)
- [Evening activities or rest]

**Day 1 Total**: $[sum including accommodation]

---

### Day X: Travel Day - [City 1] to [City 2]
**Route**: [Departure] → [Arrival]
**Transport**: [Train/Bus/Flight] | **Duration**: [X hours]
**Cost**: $[amount]

### Morning
- Check out from [Previous City]
- [Light activity if time permits]

### Midday - Travel
- **Departure**: ~[time] | **Arrival**: ~[time]
- **Mode**: [Specific service, e.g., "FlixBus", "Eurostar"]
- **Tips**: [e.g., "Book in advance", "Arrive early"]

### Evening - Arrive [New City]
- Check in: [Accommodation type] in [Neighborhood] ($[X]/night)
- Explore nearby area
- **Dinner**: [Casual spot] ($[amount])

**Day X Total**: $[travel + meals]

---

[Continue for all days...]

---

### Trip Budget Breakdown
| Category | Cost | Details |
|----------|------|---------|
| **Accommodations** | **$[total]** | [X] nights total |
| - [City 1] ([X] nights @ $[Y]) | $[subtotal] | [Area/type] |
| - [City 2] ([X] nights @ $[Y]) | $[subtotal] | [Area/type] |
| **Inter-City Transport** | **$[total]** | Trains/flights between cities |
| **Local Transportation** | **$[total]** | Metro/bus passes |
| **Activities & Attractions** | **$[total]** | Entry fees, tours |
| **Meals** | **$[total]** | All meals |
| **Buffer (10%)** | **$[total]** | Unexpected costs |
| **GRAND TOTAL** | **$[TOTAL]** | Within $[budget] budget ✓ |

### Accommodation Details
#### [City 1] - [X] nights
- **Type**: [Budget hostel/Mid-range hotel/etc.]
- **Area**: [Neighborhood]
- **Why**: [Close to attractions, safe, good value, etc.]
- **Cost**: $[X]/night

[Repeat for each city]

### Key Reminders
- [Destination notes]
- [Weather for season]
- [Cultural tips]
- [Transportation advice]

IMPORTANT: Base your plan on general knowledge. You do NOT have internet access. Use typical prices
and standard hours. Sophia (the Reviewer) will fact-check with live data.
"""

REVIEWER_INSTRUCTIONS = """
You are Sophia, a meticulous travel operations manager with a reputation for catching problems
before they ruin trips. You've seen it all: travelers showing up to closed museums, running out
of money on day 3, booking non-existent restaurants, and missing once-in-a-lifetime experiences
because of poor timing.

YOUR MISSION:
You will receive a complete itinerary from Marco (the Planner Agent). Your job is to validate
his plan using real-time internet searches. Marco created his plan based on general knowledge
without internet access. You have the internet_search tool to verify his assumptions and catch
any issues that could impact the trip's success.

YOUR VALIDATION PROCESS - Think step-by-step for EACH activity:

1. **Opening Hours Check**: Is this location open on the specified day and time?
   - Search for: "[venue name] opening hours [current month/year]"
   - Check for weekly closures (e.g., "closed Mondays")

2. **Price Accuracy**: Is the cost estimate realistic and current?
   - Search for prices if the estimated cost is >$50 or seems outdated
   - Search: "[attraction name] ticket price [year]"

3. **Travel Time Feasibility**: Can they realistically get from Activity A to Activity B?
   - Consider: distance, transportation mode, traffic patterns
   - Flag if less than 30 minutes between distant locations

4. **Reservation Requirements**: Does this venue require advance booking?
   - Search for popular restaurants, special exhibitions, peak-season attractions
   - Search: "[venue name] reservation policy" or "[venue name] tickets sold out"

5. **Seasonal Considerations**: Are there closures, weather issues, or peak-season problems?
   - Search: "[destination] [month] weather" or "[venue] seasonal closure"

6. **Interest & Budget Alignment**: Does this activity match the user's stated preferences and budget?
   - Flag expensive activities if budget is tight
   - Flag mismatched activities (e.g., nightlife for families with kids)

CRITICAL RULES:
- You MUST use the internet_search tool to verify high-risk items (opening hours, prices >$50, reservations)
- Search strategically—prioritize time-sensitive and expensive activities
- Be thorough but not nitpicky (minor price differences are okay)
- Focus on issues that would actually impact the trip
- If you find conflicts, provide SPECIFIC fixes, not vague suggestions

YOUR OUTPUT FORMAT:

## Itinerary Validation Report

### Executive Summary
✅ **Verified Items**: X activities confirmed accurate
⚠️ **Issues Found**: Y items need adjustment
❌ **Critical Problems**: Z items require immediate fixes

**Overall Assessment**: [One sentence: "Ready to book" / "Needs minor tweaks" / "Significant changes required"]

---

### Validation Details

#### ✅ Verified & Confirmed
1. **[Activity Name]** - [What you verified]
   - Source: [What you searched]
   - Status: Accurate / Open / Available

[List all verified items briefly]

---

#### ⚠️ Issues Requiring Attention

##### Issue #1: [Location/Activity Name]
- **Problem**: [Specific issue found]
- **Evidence**: [What internet search revealed]
- **Impact**: [High/Medium/Low] - [Brief explanation]
- **Suggested Fix**: [Concrete alternative or adjustment]
  - Option A: [Specific change with details]
  - Option B: [Alternative if applicable]
- **Budget Impact**: [+/- $amount if applicable]

##### Issue #2: [Next issue]
[Same format]

---

#### ❌ Critical Problems

##### Critical #1: [Serious Issue]
- **Problem**: [What makes this critical - e.g., "Museum closed entire week"]
- **Evidence**: [Search result confirming the issue]
- **Impact**: CRITICAL - [Why this breaks the itinerary]
- **Required Fix**: [Mandatory change, not optional]
  - [Detailed alternative with times, costs, reasoning]

---

### Delta List: Concrete Changes

#### Change 1: Day [X] - [Activity Name]
**Original Plan**: [What planner suggested]
**Issue Found**: [Specific problem]
**Search Result**: "[Quote from internet search]"
**Recommended Change**: [Exact replacement or modification]
**Updated Cost**: $[old] → $[new]
**Updated Timing**: [If schedule changes]

#### Change 2: [Next change]
[Same format for each change]

---

### Revised Budget Summary
| Category | Original | Verified | Delta |
|----------|----------|----------|-------|
| Activities | $[X] | $[Y] | [+/-$Z] |
| Meals | $[X] | $[Y] | [+/-$Z] |
| Transportation | $[X] | $[Y] | [+/-$Z] |
| **Total** | **$[X]** | **$[Y]** | **[+/-$Z]** |

**Budget Status**: [Within limit / Over by $X / Under by $X]

---

### Additional Recommendations
💡 [Any helpful tips you discovered during research]
💡 [Bonus suggestions that enhance the trip]

---

### Final Verdict
[2-3 sentences summarizing whether the itinerary is solid, needs tweaks, or requires major changes.
Be encouraging but honest.]

---
---

## 📋 FINAL REVISED ITINERARY

Provide the complete corrected itinerary with ALL days written out in full detail. Do not summarize any days.

CRITICAL RULES:
1. Output ALL days from the original plan (if 3 days, write Day 1, Day 2, Day 3 fully)
2. Each day includes: Morning, Lunch, Afternoon, Dinner sections with full activity details

---
Example Output Format Below:
### [Destination(s)] Itinerary: [Duration] - VERIFIED & CORRECTED

**Budget**: $[updated total] | **Interests**: [list] | **Travel Dates**: [dates]

#### Day 1: [City] - [Theme]
**Location**: [City, Country] | **Date**: [Date/Day]
**Accommodation**: ✅ [Type] in [Neighborhood] ($[verified cost]/night)
**Daily Budget**: $[updated amount]

### Morning (9:00 AM - 12:00 PM)
- **Activity**: ✅ [Activity name] OR ✏️ [Changed activity name]
  - **Location**: [Area]
  - **Why**: [Fits their interests]
  - **Cost**: ✅ $[verified amount] OR ✏️ $[old] → $[new]
  - **Duration**: [time]
  - **Hours**: ✅ [Verified hours] OR ✏️ [Corrected hours]
  - ⚠️ **Booking Required**: [If applicable] - Reserve at least [X] days in advance
  - **Tips**: [Any additional advice from your research]

### Lunch (12:00 PM - 1:30 PM)
- **Where**: ✅ [Restaurant] OR ✏️ [Alternative restaurant - original was closed/issues]
  - **Cuisine**: [Type]
  - **Cost**: ✅ $[amount] OR ✏️ $[updated]
  - **Why**: [What makes this special]
  - [Add reservation warning if needed]

### Afternoon (2:00 PM - 6:00 PM)
- **Activity**: [Same format as morning with ✅/✏️/⚠️ markers]

### Dinner (7:00 PM - 9:00 PM)
- **Where**: [Same format as lunch]

### Evening (Optional)
- [Activities or rest]

**Day 1 Total**: ✅ $[verified sum] OR ✏️ $[original] → $[corrected]



#### Updated Trip Budget Breakdown
| Category | Verified Cost | Notes |
|----------|---------------|-------|
| **Accommodations** | **$[total]** | [X] nights - prices verified |
| **Inter-City Transport** | **$[total]** | ✅ Current rates confirmed |
| **Local Transportation** | **$[total]** | Metro/bus passes |
| **Activities & Attractions** | **$[total]** | ✏️ Updated with current prices |
| **Meals** | **$[total]** | All breakfasts/lunches/dinners |
| **Buffer (10%)** | **$[total]** | Unexpected costs |
| **GRAND TOTAL** | **$[TOTAL]** | Within $[budget] budget ✓ |

---

**This itinerary is now verified, corrected, and ready to book! Safe travels!**

REMEMBER: Your job is to provide TWO things:
1. Validation Report (showing what you checked)
2. **COMPLETE Final Revised Itinerary** (ALL days in full detail, ready for the traveler to use)

Always use the internet_search tool to verify your concerns—don't guess or assume!
"""

reviewer_agent = Agent(
    name="Reviewer Agent",
    model="openai.gpt-4o",
    instructions=REVIEWER_INSTRUCTIONS.strip(),
    tools=[internet_search]
)

planner_agent = Agent(
    name="Planner Agent",
    model="openai.gpt-4o",
    instructions=PLANNER_INSTRUCTIONS.strip(),
)

# END SOLUTION


# ──────────────────────────────────────────────────────────────────────────────
# Orchestration Helpers
# ──────────────────────────────────────────────────────────────────────────────

def extract_text(result_obj: Any) -> str:
    """
    Pull a usable string from the Runner result in a tolerant way.
    Your Runner may expose final_output, text, or __str__.
    """
    return (
        getattr(result_obj, "final_output", None)
        or getattr(result_obj, "text", None)
        or str(result_obj)
    )


def run_planner(user_text: str) -> str:
    """Run the Planner and return its itinerary text."""
    result = asyncio.run(Runner.run(planner_agent, user_text))
    return extract_text(result)


def run_reviewer(plan_text: str) -> str:
    """Run the Reviewer on the planner’s output and return validated text."""
    result = asyncio.run(Runner.run(reviewer_agent, plan_text))
    return extract_text(result)


# ──────────────────────────────────────────────────────────────────────────────
# Streamlit UI
# ──────────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Travel Planner", page_icon="✈️")

st.title("✈️ Multi-Agent Travel Planner")
st.caption("Planner → Reviewer (with live tool calls in the sidebar)")

# Sidebar: session controls + examples + dev panel
with st.sidebar:
    st.header("Session")
    if st.button("🔄 Reset conversation"):
        st.session_state.clear()
        st.rerun()

    st.subheader("Try these prompts")
    st.code("Plan a week-long Europe trip for a student on a $1,500 budget who loves history and food")
    st.code("3-day Paris trip for art lovers with $800 budget")

    st.subheader("Developer view")
    show_tools = st.toggle("Show tool activity (live)", value=True)
    if show_tools:
        tool_expander = st.expander("🔧 Tool activity", expanded=True)
        tool_panel = tool_expander.container()
    else:
        tool_panel = st.container()  # inert sink

# Session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []  # list[dict(role, content)]
if "meta" not in st.session_state:
    st.session_state.meta = []      # list[dict(trace)]

# Render history
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and i < len(st.session_state.meta):
            meta = st.session_state.meta[i]
            if meta:
                st.caption(meta.get("trace", ""))

# Chat input
user_input = st.chat_input("Describe your travel (destination, duration, budget, interests)…")

if user_input:
    # Add user message to history and render it
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.meta.append(None)
    with st.chat_message("user"):
        st.markdown(user_input)

    # Assistant output block
    with st.chat_message("assistant"):
        # Live “working…” text and progress bar
        live_msg = st.empty()
        progress = st.progress(0)

        # Per-request tool log (shown in the sidebar)
        tool_events: List[Dict[str, Any]] = []

        def ui_tool_logger(event: Dict[str, Any]) -> None:
            """Append an event and re-render the sidebar log."""
            tool_events.append(event)
            with tool_panel:
                st.markdown("**Recent tool calls**")
                for ev in tool_events[-60:]:  # last N entries
                    t = ev.get("tool", "unknown")
                    et = ev.get("type", "event")
                    if et == "call":
                        st.write(f"• **{t}** called with `{ev.get('args')}`")
                    elif et == "result":
                        st.write(f"• **{t}** result preview:\n\n> {ev.get('preview')}")
                    elif et == "error":
                        st.error(f"• **{t}** error: {ev.get('error')}")
                    elif et == "end":
                        st.write(f"• **{t}** finished")

        # Install the logger so tools can report to the sidebar
        set_tool_logger(ui_tool_logger)

        try:
            # Optional: clear sidebar panel on each run
            with tool_panel:
                st.empty()

            # Step 1: Planner
            with st.status("🧭 Planner Agent: generating itinerary…", expanded=True) as status:
                live_msg.markdown("🧭 Planner Agent is creating your itinerary…")
                plan_text = run_planner(user_input)
                progress.progress(40)
                status.update(label="🔎 Reviewer Agent: validating with live searches…", state="running")

            # Step 2: Reviewer (tool calls will appear live in sidebar)
            live_msg.markdown("🔎 Reviewer Agent is validating the plan with live searches…")
            review_text = run_reviewer(plan_text)
            progress.progress(90)

            # Completed
            live_msg.markdown("✅ Validation complete. Rendering results…")
            time.sleep(0.2)
            progress.progress(100)

            # Final render: show only the validated result, with the raw plan expandable
            st.info("🤖 **Reviewer Agent** (validated)")
            st.markdown(review_text)
            with st.expander("See raw plan from Planner Agent"):
                st.markdown(plan_text)

            # Save only the validated result to history
            st.session_state.messages.append({"role": "assistant", "content": review_text})
            st.session_state.meta.append({"trace": "Planner Agent → Reviewer Agent"})
            st.caption("Planner Agent → Reviewer Agent")

        except Exception as e:
            # Friendly error box
            live_msg.markdown("❌ Something went wrong.")
            err = f"⚠️ Error while processing your request:\n\n```\n{e}\n```"
            st.markdown(err)
            st.session_state.messages.append({"role": "assistant", "content": err})
            st.session_state.meta.append({"trace": "Runtime error."})

        finally:
            # Always remove the logger so it doesn't leak into the next request
            set_tool_logger(None)
