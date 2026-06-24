import streamlit as st
from langchain_community.document_loaders import WebBaseLoader
from datetime import datetime
import time
import re
import requests
from urllib.parse import urlparse

from chains import Chain
from portfolio import Portfolio
from utils import clean_text


def highlight_and_underline_skills(text: str, skills) -> str:
    """Wrap occurrences of skills with bold+underline HTML (no color).
    Uses case-insensitive matching and prioritizes longer phrases first.
    Converts any existing <mark> tags to <strong> for consistency.
    """
    if not text or not skills:
        return text
    # Normalize skills list
    if not isinstance(skills, list):
        skills = [str(skills)] if skills else []
    skills_sorted = sorted([str(s).strip() for s in skills if str(s).strip()], key=len, reverse=True)
    # Convert any color-highlight tags to bold
    out = re.sub(r"(?is)<u>\s*<mark>(.*?)</mark>\s*</u>", r"<u><strong>\1</strong></u>", text)
    out = re.sub(r"(?is)<mark>(.*?)</mark>", r"<strong>\1</strong>", out)
    # Shield existing bold/underline to avoid double-wrapping
    placeholders = []
    def _shield(m):
        placeholders.append(m.group(0))
        return f"__HL_PLACE_{len(placeholders)-1}__"
    out = re.sub(r"(?is)<u>\s*<strong>.*?</strong>\s*</u>", _shield, out)
    out = re.sub(r"(?is)<strong>.*?</strong>", _shield, out)
    for skill in skills_sorted:
        escaped = re.escape(skill)
        # Avoid matching inside larger alphanumeric tokens
        pattern = re.compile(rf"(?i)(?<![A-Za-z0-9])({escaped})(?![A-Za-z0-9])")
        out = pattern.sub(r"<u><strong>\1</strong></u>", out)
    # Restore original highlight tags
    for i, val in enumerate(placeholders):
        out = out.replace(f"__HL_PLACE_{i}__", val)
    return out


def make_links_clickable(text: str) -> str:
    """Convert bare URLs to clickable anchor tags."""
    if not text:
        return text
    # Avoid converting URLs already inside anchor tags
    url_pattern = re.compile(r"(?<!href=\")((?:https?://)[^\s)]+)")
    return url_pattern.sub(r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>', text)


def insert_shiv_portfolio_link(text: str, shiv_url: str = "https://github.com/shiv-portfolio.") -> str:
    """Append a plain clickable portfolio URL (auto-linked) for Shiv.
    Inserts before the signature if present; otherwise appends at end.
    """
    if not text:
        return text
    # If the Shiv URL already exists, skip
    if re.search(r"https?://github\.com/shiv-portfolio", text, flags=re.IGNORECASE):
        return text
    url_text = shiv_url
    # Insert before signature if present
    signature_pattern = re.compile(r"(?i)(\n\s*Best regards,\s*\n)\s*Shiv\s*&\s*Sakshi")
    if signature_pattern.search(text):
        return signature_pattern.sub(f"\nAdditional portfolio: {url_text}\n\\1Shiv & Sakshi", text)
    # Otherwise, append at end
    return text + f"\n\nAdditional portfolio: {url_text}"


def read_job_link(url: str) -> str:
    """Fetch page content from a job link.
    Tries WebBaseLoader first; falls back to requests with a desktop UA.
    Returns raw HTML/text; may be empty if the site blocks scraping.
    """
    try:
        loader = WebBaseLoader([url])
        docs = loader.load()
        if docs:
            return docs[0].page_content or ""
    except Exception:
        pass
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/118.0 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=12)
        resp.raise_for_status()
        return resp.text
    except Exception:
        return ""


def detect_platform(url: str) -> str:
    """Infer platform from URL domain for tailored email style."""
    try:
        domain = urlparse(url).netloc.lower()
    except Exception:
        domain = ""
    if "linkedin" in domain:
        return "linkedin"
    freelancing_domains = [
        "upwork", "fiverr", "freelancer", "guru", "peopleperhour", "toptal", "truelancer",
    ]
    if any(d in domain for d in freelancing_domains):
        return "freelancing"
    return "generic"

def create_streamlit_app(llm, portfolio, clean_text):
    st.set_page_config(layout="wide", page_title="AI Email Forge", page_icon="🤖")
    
    # Enhanced CSS with animations
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        
        @keyframes glow {
            0% { text-shadow: 0 0 5px rgba(0,255,136,0.5); }
            50% { text-shadow: 0 0 20px rgba(0,255,136,0.8); }
            100% { text-shadow: 0 0 5px rgba(0,255,136,0.5); }
        }
        
        @keyframes borderGlow {
            0% { border-color: #00ff88; }
            50% { border-color: #00ccff; }
            100% { border-color: #00ff88; }
        }
        
        .main {background: linear-gradient(135deg, #1a1a1a, #2d2d2d); color: #fff; padding: 2rem;}
        .stTitle {font-family: 'Roboto Mono', monospace; color: #00ff88; text-align: center; animation: glow 2s infinite;}
        .tech-card {
            background: rgba(30,30,30,0.9);
            border: 2px solid #00ff88;
            border-radius: 15px;
            padding: 20px;
            margin: 10px 0;
            transition: all 0.3s;
            animation: borderGlow 3s infinite;
        }
        .tech-card:hover { transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,255,136,0.3); }
        .stButton>button {
            width: 100%;
            background: linear-gradient(45deg, #00ff88, #00ccff);
            color: #000;
            font-family: 'Roboto Mono';
            font-weight: bold;
            border: none;
            transition: all 0.3s;
            animation: pulse 2s infinite;
        }
        .stButton>button:hover { transform: scale(1.1); box-shadow: 0 5px 15px rgba(0,255,136,0.6); }
        .stTextInput>div>div>input {
            background: rgba(30,30,30,0.9);
            color: #00ff88;
            border: 2px solid #00ff88;
            border-radius: 10px;
            transition: all 0.3s;
        }
        .stTextInput>div>div>input:focus { border-color: #00ccff; box-shadow: 0 0 15px rgba(0,204,255,0.5); }
        .output-container {
            background: rgba(30,30,30,0.9);
            border: 2px solid #00ff88;
            padding: 20px;
            border-radius: 15px;
            color: #fff;
            transition: all 0.3s;
        }
        .output-container:hover { transform: scale(1.02); }
        .status-text { font-family: 'Roboto Mono'; color: #00ccff; }
        .terminal-text { font-family: 'Roboto Mono'; color: #00ff88; }
        
        .typing-effect { overflow: hidden; white-space: nowrap; margin: 0 auto; letter-spacing: .15em; }
        </style>
    """, unsafe_allow_html=True)

    # Animated header with static text (JavaScript doesn't work in Streamlit)
    st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <h1 class='stTitle' style='font-size: 3em;'>🤖 AI Email Forge v3.0</h1>
            <div class='terminal-text typing-effect' style='font-size: 1.2em;'>
                > System initialized... Ready for quantum operations...
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Interactive system status
    col1, col2, col3 = st.columns(3)
    with col1:
        status_card = st.empty()
        status_card.markdown(f"""<div class='tech-card' onclick='this.style.transform="scale(1.1)"'>
            <p class='terminal-text'>🔋 System Status: <span style='color:#00ccff'>ONLINE</span></p>
        </div>""", unsafe_allow_html=True)
    with col2:
        time_card = st.empty()
    with col3:
        core_card = st.empty()

    # Display static time and core status instead of using threading
    time_card.markdown(f"""<div class='tech-card'>
        <p class='terminal-text'>⏰ System Time: {datetime.now().strftime('%H:%M:%S')}</p>
    </div>""", unsafe_allow_html=True)
    
    core_card.markdown("""<div class='tech-card'>
        <p class='terminal-text'>📡 Quantum Core: <span style='color:#00ccff'>ACTIVE</span></p>
    </div>""", unsafe_allow_html=True)

    # Enhanced input section
    st.markdown("<div class='tech-card' style='transform-style: preserve-3d;'>", unsafe_allow_html=True)
    url_input = st.text_input(
        "🎯 Target Job URL",
        value="https://www.linkedin.com/jobs/view/4221227654",
        help="Enter the URL of your target position",
        key="url_input"
    )

    # Variants controls
    variants_n = st.slider(
        "🔢 Number of emails to generate",
        min_value=1,
        max_value=100,
        value=10,
        help="Generate up to 100 distinct variants per job"
    )
    high_diversity = st.checkbox("🎨 High diversity (strongly vary style and structure)", value=True)
    tones_selected = st.multiselect(
        "🎭 Tones",
        options=["friendly", "technical", "formal", "confident", "persuasive", "concise", "empathetic", "results-driven"],
        default=["friendly", "technical", "formal", "confident"],
        help="Select one or more tones; variants will be split across tones"
    )

    # Auto-trigger generation when tone selection changes
    tones_changed = False
    if "tones_last" in st.session_state:
        try:
            tones_changed = list(st.session_state["tones_last"]) != list(tones_selected)
        except Exception:
            tones_changed = st.session_state.get("tones_last") != tones_selected
    st.session_state["tones_last"] = list(tones_selected)

    # Animated submit button
    col1, col2, col3 = st.columns([2,1,2])
    with col2:
        submit_button = st.button("🚀 INITIATE FORGE")

    st.markdown("</div>", unsafe_allow_html=True)

    if submit_button or tones_changed:
        try:
            progress = st.progress(0)
            status_container = st.empty()

            # Animated processing steps
            for i in range(5):
                status_container.markdown(f"""<div class='tech-card' style='animation: pulse 1s infinite'>
                    <p class='status-text'>⚡ Initializing quantum systems... {'.'*(i+1)}</p>
                </div>""", unsafe_allow_html=True)
                time.sleep(0.2)

            # Enhanced job analysis
            status_container.markdown("""<div class='tech-card'>
                <p class='status-text'>🔍 Executing deep neural scan...</p>
            </div>""", unsafe_allow_html=True)
            status_container.markdown("""<div class='tech-card'>
                <p class='status-text'>🌐 Reading job link...</p>
            </div>""", unsafe_allow_html=True)
            raw_page = read_job_link(url_input)
            if not raw_page:
                st.error("🚨 Unable to read the job link. The site may block scraping or require login.")
                return
            data = clean_text(raw_page)
            progress.progress(25)

            # Portfolio integration with animation
            status_container.markdown("""<div class='tech-card'>
                <p class='status-text'>🧬 Synthesizing quantum portfolio matrix...</p>
            </div>""", unsafe_allow_html=True)
            portfolio.load_portfolio()
            progress.progress(50)

            # AI processing with effects
            status_container.markdown("""<div class='tech-card'>
                <p class='status-text'>🤖 Activating neural pathways...</p>
            </div>""", unsafe_allow_html=True)
            jobs = llm.extract_jobs(data)
            progress.progress(75)

            if not jobs:
                st.error("🚨 Quantum analysis failed to detect job parameters.")
                return

            # Enhanced email generation (variants)
            for job in jobs:
                skills = job.get('skills', [])
                if not skills:
                    st.warning("⚠️ Skill matrix compilation incomplete.")
                    continue

                platform_detected = detect_platform(url_input)
                status_container.markdown(f"""<div class='tech-card'>
                    <p class='status-text'>⚡ Platform detected: <span style='color:#00ccff'>{platform_detected}</span>. Generating {variants_n} diversified emails across tones: {', '.join(tones_selected or ['friendly'])}...</p>
                </div>""", unsafe_allow_html=True)
                links = portfolio.query_links(skills)
                # Distribute variants across selected tones
                tone_list = tones_selected or ["friendly"]
                total = variants_n
                per = max(1, total // len(tone_list))
                remainder = total - per * len(tone_list)
                variants = []
                for idx_t, tone in enumerate(tone_list):
                    count = per + (1 if idx_t < remainder else 0)
                    if count <= 0:
                        continue
                    chunk = llm.write_mail_variants(
                        job,
                        links,
                        num_variants=count,
                        tone=tone,
                        max_batch=10,
                        platform=platform_detected,
                        link_content=data[:1200],
                        diversity="high" if high_diversity or variants_n > 10 else "standard",
                    )
                    # Annotate each variant with its tone for display
                    for item in chunk:
                        item["tone"] = tone
                    variants.extend(chunk)
                progress.progress(100)

                # Animated results display
                st.markdown("""<div class='output-container' style='animation: borderGlow 3s infinite'>""", unsafe_allow_html=True)
                st.markdown("### 📧 Quantum-Forged Communication — Variants")
                # Render each variant with subject header and processed body (skills highlighted & links clickable)
                all_md = []
                for idx, item in enumerate(variants, start=1):
                    tone = item.get("tone", "mixed")
                    subject = item.get("subject", f"Variant {idx}")
                    body = item.get("body", "")
                    body_processed = make_links_clickable(highlight_and_underline_skills(body, skills))
                    body_processed = insert_shiv_portfolio_link(body_processed)
                    with st.expander(f"{idx:02d}. [{tone}] {subject}"):
                        st.markdown(body_processed, unsafe_allow_html=True)
                    all_md.append(f"## [{tone}] {subject}\n\n{body_processed}\n\n---\n")
                combined_md = "".join(all_md)
                st.markdown("</div>", unsafe_allow_html=True)

                # Interactive success message
                st.success("🎉 Quantum forge sequence complete!")

                # Enhanced action buttons
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        "💾 Save All Variants",
                        combined_md,
                        "email_variants.md",
                        "text/markdown",
                        help="Download all generated emails in one Markdown file"
                    )
                with col2:
                    st.download_button(
                        "💾 Save First Variant",
                        combined_md.split("---\n")[0] if combined_md else "",
                        "email_variant_01.md",
                        "text/markdown",
                    )

        except FileNotFoundError as e:
            st.error(f"🚨 Quantum matrix not found: {str(e)}")
        except Exception as e:
            st.error(f"⚠️ Quantum core malfunction: {str(e)}")
        finally:
            if 'progress' in locals(): progress.empty()
            if 'status_container' in locals(): status_container.empty()

if __name__ == "__main__":
    try:
        chain = Chain()
        portfolio = Portfolio()
        create_streamlit_app(chain, portfolio, clean_text)
    except Exception as e:
        st.error(f"🚨 Quantum core initialization failure: {str(e)}")

