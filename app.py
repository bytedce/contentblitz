# app.py
import os
import time
import threading
import queue

import streamlit as st

from agents import ContentOrchestrator, LinkedInPostAgent, LinkedInPostSubmitAgent
from storage import load_history, add_to_history
from config import APP_NAME

os.environ["TOKENIZERS_PARALLELISM"] = "false"
# --------------------------------------------------
# Page config
# --------------------------------------------------
st.set_page_config(page_title=APP_NAME, layout="wide")

# --------------------------------------------------
# Session state initialization
# --------------------------------------------------
if "history" not in st.session_state:
    st.session_state.history = load_history()

if "logs" not in st.session_state:
    st.session_state.logs = []

if "result" not in st.session_state:
    st.session_state.result = None

if "progress" not in st.session_state:
    st.session_state.progress = 0

if "is_running" not in st.session_state:
    st.session_state.is_running = False

if "event_queue" not in st.session_state:
    st.session_state.event_queue = queue.Queue()

if "topic" not in st.session_state:
    st.session_state.topic = ""

# --------------------------------------------------
# Log colors
# --------------------------------------------------
LOG_COLORS = {
    "SYSTEM": "#6c757d",
    "RESEARCH": "#0d6efd",
    "BLOG": "#198754",
    "IMAGE": "#fd7e14",
    "LINKEDIN": "#6f42c1",
    "INFO": "#495057",
    "ERROR": "#dc3545",
}

# --------------------------------------------------
# Background pipeline (NO Streamlit calls)
# --------------------------------------------------
def run_pipeline(topic: str, event_q: queue.Queue):
    def emit_event(stage: str, message: str):
        event_q.put(("log", stage, message))

    try:
        emit_event("SYSTEM", "Starting content generation")
        event_q.put(("progress", 10))

        orchestrator = ContentOrchestrator()
        result = orchestrator.run(topic, emit_event)

        event_q.put(("result", result))
        event_q.put(("progress", 100))
        emit_event("SYSTEM", "All agents completed")

    except Exception as e:
        emit_event("ERROR", str(e))
        event_q.put(("progress", 0))

# --------------------------------------------------
# Process background events (MAIN THREAD ONLY)
# --------------------------------------------------
while not st.session_state.event_queue.empty():
    event = st.session_state.event_queue.get()

    if event[0] == "log":
        _, stage, msg = event
        st.session_state.logs.append((stage, msg))

    elif event[0] == "progress":
        st.session_state.progress = event[1]

    elif event[0] == "result":
        st.session_state.result = event[1]
        st.session_state.history = add_to_history(
            st.session_state.history,
            event[1],
        )
        st.session_state.is_running = False

# --------------------------------------------------
# Title
# --------------------------------------------------
st.title(APP_NAME)

# --------------------------------------------------
# Layout
# --------------------------------------------------
col1, col2, col3 = st.columns([1, 2, 3], gap="large")

# --------------------------------------------------
# COLUMN 1 — HISTORY
# --------------------------------------------------
with col1:
    st.subheader("🕘 History")

    if st.session_state.history:
        for item in reversed(st.session_state.history):
            if st.button(item["topic"], key=f"hist_{item['topic']}"):
                st.session_state.result = item
                st.session_state.logs = [("INFO", "Loaded from history")]
                st.session_state.progress = 100
                st.session_state.is_running = False
    else:
        st.info("No history yet.")

# --------------------------------------------------
# COLUMN 2 — INPUT + LOGS
# --------------------------------------------------
with col2:
    st.subheader("🔍 Blog Topic")

    st.text_input(
        "Enter topic",
        placeholder="e.g. Top 10 perfumes under 1000",
        key="topic",
    )

    generate_clicked = st.button(
        "Generate Content",
        disabled=st.session_state.is_running,
    )

    reset_clicked = st.button(
        "Reset / New Search",
        disabled=st.session_state.is_running,
    )

    # ---------- Reset ----------
    if reset_clicked:
        st.session_state.logs.clear()
        st.session_state.result = None
        st.session_state.progress = 0
        st.session_state.event_queue = queue.Queue()
        st.session_state.is_running = False
        st.session_state.topic = ""
        st.success("Ready for a new search.")

    st.progress(st.session_state.progress)

    st.markdown("---")
    st.subheader("⚙️ Agent Logs")

    log_container = st.container(height=320)
    with log_container:
        for stage, msg in st.session_state.logs:
            color = LOG_COLORS.get(stage, "#000000")
            st.markdown(
                f"""
                <div style="
                    padding:4px 6px;
                    margin-bottom:4px;
                    border-radius:4px;
                    background-color:#f8f9fa;
                    color:{color};
                    font-size:0.9em;">
                    [{stage}] {msg}
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Auto-scroll
        st.markdown("<div id='log-end'></div>", unsafe_allow_html=True)
        st.markdown(
            """
            <script>
                document.getElementById("log-end")
                    ?.scrollIntoView({behavior: "smooth"});
            </script>
            """,
            unsafe_allow_html=True,
        )

    # ---------- Start pipeline ----------
    if generate_clicked and not st.session_state.is_running:
        if not st.session_state.topic.strip():
            st.warning("Please enter a valid topic.")
        else:
            st.session_state.logs.clear()
            st.session_state.result = None
            st.session_state.progress = 0
            st.session_state.is_running = True
            st.session_state.event_queue = queue.Queue()

            threading.Thread(
                target=run_pipeline,
                args=(st.session_state.topic, st.session_state.event_queue),
                daemon=True,
            ).start()

# --------------------------------------------------
# COLUMN 3 — BLOG + IMAGE + LINKEDIN
# --------------------------------------------------
with col3:
    st.subheader("📝 Blog Output")

    if st.session_state.result:
        images = st.session_state.result.get("images")

        # ---- Blog container (image + blog together) ----
        with st.container(border=True):

            # Image appears as blog header media
            if images and isinstance(images, dict):
                image_path = images.get("image_path")
                caption = images.get("caption", "Generated marketing image")

                if image_path and os.path.exists(image_path):
                    st.image(
                        image_path,
                        caption=caption,
                        width=380,   # blog-header sized
                    )

            # Blog content immediately follows image
            st.text_area(
                "Marketing Blog",
                st.session_state.result["blog"],
                height=420,
                label_visibility="visible",
            )

        st.markdown("---")

        # ---- LinkedIn section (separate) ----
        st.subheader("💼 LinkedIn Post")

        st.text_area(
            "LinkedIn Content",
            st.session_state.result["linkedin"],
            height=220,
        )

        approved = st.checkbox("I approve this LinkedIn post")

        already_posted = st.session_state.result.get("linkedin_posted", False)

        if approved and not already_posted:
            if st.button("🚀 Post on LinkedIn"):
                try:
                    emit_event = lambda s, m: st.session_state.event_queue.put(
                        ("log", s, m)
                    )

                    agent = LinkedInPostSubmitAgent()
                    agent.post(
                        st.session_state.result["linkedin"],
                        emit_event,
                    )

                    st.session_state.result["linkedin_posted"] = True
                    st.success("Successfully posted on LinkedIn!")

                except Exception as e:
                    st.error(str(e))

        elif already_posted:
            st.success("This LinkedIn post has already been published.")

    else:
        st.info("No content generated yet.")
# --------------------------------------------------
# Poll rerun AFTER render
# --------------------------------------------------
if st.session_state.is_running:
    time.sleep(0.3)
    st.rerun()
