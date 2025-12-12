import streamlit as st
import requests
import pandas as pd
import numpy as np
import datetime
import re
import html

st.set_page_config(
    page_title="PsiSearch Pro",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Source Sans Pro', sans-serif;
        background-color: #f8f9fa;
        color: #212529;
    }

    /* CARD STRUCTURE */
    .result-card {
        background-color: #ffffff;
        padding: 24px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.04);
        margin-bottom: 24px;
        border: 1px solid #e9ecef;
    }

    /* TYPOGRAPHY */
    .card-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #1a202c;
        text-decoration: none;
        display: block;
        margin-bottom: 8px;
        line-height: 1.4;
    }
    .card-title:hover { color: #3182ce; }

    .card-meta {
        font-size: 0.85rem;
        color: #718096;
        margin-bottom: 16px;
        font-weight: 400;
        border-bottom: 1px solid #edf2f7;
        padding-bottom: 12px;
    }

    /* BADGES & TOOLTIPS MAGIC */
    .badge-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 12px;
    }
    
    /* Base Badge Style */
    .badge {
        position: relative;
        display: inline-flex;
        align-items: center;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        cursor: help; /* Cursor vira ? */
        border: 1px solid transparent;
    }

    /* Tooltip Box Style */
    .badge .tooltip-text {
        visibility: hidden;
        width: 180px;
        background-color: #2d3748;
        color: #fff;
        text-align: center;
        border-radius: 6px;
        padding: 8px;
        position: absolute;
        z-index: 10;
        bottom: 125%; /* Aparece em cima */
        left: 50%;
        margin-left: -90px;
        opacity: 0;
        transition: opacity 0.3s;
        font-size: 0.65rem;
        font-weight: 400;
        text-transform: none;
        line-height: 1.3;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    
    /* Seta do Tooltip */
    .badge .tooltip-text::after {
        content: "";
        position: absolute;
        top: 100%;
        left: 50%;
        margin-left: -5px;
        border-width: 5px;
        border-style: solid;
        border-color: #2d3748 transparent transparent transparent;
    }

    /* Show on Hover */
    .badge:hover .tooltip-text {
        visibility: visible;
        opacity: 1;
    }

    /* COLORS */
    .b-book { background: #fffaf0; color: #c05621; border-color: #feebc8; }
    .b-art  { background: #ebf8ff; color: #2b6cb0; border-color: #bee3f8; }
    .b-lang { background: #f7fafc; color: #4a5568; border-color: #e2e8f0; }
    .b-trend { background: #e6fffa; color: #047481; border-color: #b2f5ea; }
    .b-gem   { background: #faf5ff; color: #805ad5; border-color: #e9d8fd; }
    .b-auth  { background: #f0fff4; color: #276749; border-color: #9ae6b4; }

    /* METRIC BOX WITH TOOLTIP */
    .metric-box {
        background: #f8fafc;
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 16px;
        border: 1px solid #edf2f7;
        position: relative;
    }
    .metric-head {
        display: flex; justify-content: space-between; 
        font-size: 0.7rem; font-weight: 700; color: #a0aec0; text-transform: uppercase;
        margin-bottom: 6px;
        cursor: help;
    }
    /* Reusing tooltip logic for metric header */
    .metric-head .tooltip-text {
        visibility: hidden;
        width: 200px;
        background-color: #2d3748;
        color: #fff;
        text-align: center;
        border-radius: 6px;
        padding: 8px;
        position: absolute;
        z-index: 10;
        bottom: 100%;
        left: 0;
        opacity: 0;
        transition: opacity 0.3s;
        font-size: 0.65rem;
        font-weight: 400;
        text-transform: none;
    }
    .metric-head:hover .tooltip-text { visibility: visible; opacity: 1; }

    /* TOPICS */
    .topic-tag {
        display: inline-block;
        font-size: 0.75rem;
        color: #4a5568;
        background: #edf2f7;
        padding: 2px 8px;
        border-radius: 4px;
        margin-right: 6px; margin-bottom: 6px;
        border: 1px solid #e2e8f0;
    }
    
    .footer { text-align: center; margin-top: 50px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #cbd5e0; font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)

def clean_text(text):
    if not text: return "No synopsis available."
    clean = re.sub(r'<[^>]+>', '', str(text))
    return html.escape(clean)

def format_language(lang_code):
    if not lang_code: return "INTL"
    return str(lang_code).upper()[:2]

def reconstruct_abstract(inverted_index):
    if not inverted_index: return None
    try:
        word_index = []
        for word, positions in inverted_index.items():
            for pos in positions:
                word_index.append((pos, word))
        return " ".join([w[1] for w in sorted(word_index, key=lambda x: x[0])])
    except: return None

def search_openalex(query, limit=20):
    url = f"https://api.openalex.org/works?filter=concepts.id:C15744967,default.search:{query}&per-page={limit}&sort=relevance_score:desc"
    try:
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            data = r.json().get('results', [])
            normalized = []
            for item in data:
                authors = ", ".join([a['author']['display_name'] for a in item.get('authorships', [])[:2]]) or "Unknown"
                abstract = reconstruct_abstract(item.get('abstract_inverted_index'))
                concepts = [c['display_name'] for c in item.get('concepts', [])[:3]]
                normalized.append({
                    'title': item.get('title'), 'year': item.get('publication_year'),
                    'authors': authors, 'impact': item.get('cited_by_count', 0),
                    'url': item.get('doi') or item.get('id'), 'abstract': abstract,
                    'type': 'Article', 'language': item.get('language', 'en'), 'topics': concepts
                })
            return normalized
    except: pass 
    return []

def search_google_books(query, limit=20):
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {"q": f"{query}+subject:psychology", "maxResults": limit, "printType": "books"}
    try:
        r = requests.get(url, params=params, timeout=5)
        if r.status_code == 200:
            items = r.json().get('items', [])
            normalized = []
            for item in items:
                info = item.get('volumeInfo', {})
                pub_date = info.get('publishedDate', '0000')[:4]
                year = int(pub_date) if pub_date.isdigit() else 0
                page_count = info.get('pageCount', 0)
                impact = info.get('ratingsCount', 0) * 10
                if impact == 0 and page_count > 0: impact = page_count / 40
                normalized.append({
                    'title': info.get('title'), 'year': year,
                    'authors': ", ".join(info.get('authors', ['N/A'])[:2]),
                    'impact': impact, 'url': info.get('infoLink'),
                    'abstract': info.get('description'), 'type': 'Book',
                    'language': info.get('language', 'en'), 'topics': info.get('categories', ['Psychology'])
                })
            return normalized
    except: pass
    return []

def calculate_score(df, slider_weight):
    if df.empty: return df
    current_year = datetime.datetime.now().year
    df['year'] = df['year'].fillna(current_year).astype(int)
    df['impact'] = df['impact'].fillna(0).astype(float)
    df = df[df['year'] > 1900]

    min_year, max_year = df['year'].min(), df['year'].max()
    if max_year == min_year: df['n_age'] = 1.0
    else: df['n_age'] = (df['year'] - min_year) / (max_year - min_year)

    df['log_impact'] = np.log1p(df['impact'])
    min_log, max_log = df['log_impact'].min(), df['log_impact'].max()
    if max_log == min_log: df['n_impact'] = 0.0
    else: df['n_impact'] = (df['log_impact'] - min_log) / (max_log - min_log)

    df['score'] = (df['n_impact'] * slider_weight) + (df['n_age'] * (1 - slider_weight))
    df['trust_ui'] = ((df['n_impact'] * 0.7) + (df['n_age'] * 0.3)) * 100
    return df.sort_values(by='score', ascending=False)

def render_card(row):
    safe_title = clean_text(row['title'])
    safe_abstract = clean_text(row['abstract'])
    
    badges_html = '<div class="badge-container">'

    if row['type'] == 'Book': 
        badges_html += '<span class="badge b-book">📖 Book<span class="tooltip-text">Published Book or Chapter</span></span>'
    else: 
        badges_html += '<span class="badge b-art">📄 Article<span class="tooltip-text">Peer-reviewed Journal Article</span></span>'
        
    badges_html += f'<span class="badge b-lang">{format_language(row.get("language"))}</span>'
    
    current_year = datetime.datetime.now().year
    age = current_year - row['year']
    score = row['trust_ui']
    impact = row['impact']

    txt_trend = "Published in the last 3 years. Current & fresh data."
    txt_auth  = "High citation count + Impact. A verified classic."
    txt_gem   = "Moderate impact + Recent. A potential hidden treasure."
    
    if age <= 3: 
        badges_html += f'<span class="badge b-trend">🔥 Trending<span class="tooltip-text">{txt_trend}</span></span>'
    
    if score > 75: 
        badges_html += f'<span class="badge b-auth">🏆 Authority<span class="tooltip-text">{txt_auth}</span></span>'
    elif age < 10 and impact > 5 and score < 75: 
        badges_html += f'<span class="badge b-gem">💎 Gem<span class="tooltip-text">{txt_gem}</span></span>'

    badges_html += '</div>'


    topics_html = ""
    if row['topics']:
        topics_html = '<div style="margin-bottom:10px;">'
        clean_topics = [clean_text(t) for t in row['topics'] if len(t) < 25][:4]
        for t in clean_topics: topics_html += f'<span class="topic-tag">#{t}</span>'
        topics_html += '</div>'

    if score > 75: bar_color = "#48BB78"
    elif score > 40: bar_color = "#ECC94B"
    else: bar_color = "#CBD5E0"

    txt_metric = "Algorithm combining citation count (Impact) and publication date (Recency)."

    return f"""
<div class="result-card">
{badges_html}
<a href="{row['url']}" target="_blank" class="card-title">{safe_title}</a>
<div class="card-meta">{row['year']} • {row['authors']}</div>
<div class="metric-box">
<div class="metric-head">
<span>Academic Reliability <span style="font-size:0.8em">ⓘ</span></span>
<span class="tooltip-text">{txt_metric}</span>
<span>{int(score)}%</span>
</div>
<div style="background:#e2e8f0; border-radius:3px; height:6px; width:100%;">
<div style="width:{score}%; background-color:{bar_color}; height:100%; border-radius:3px;"></div>
</div>
</div>
{topics_html}
<div style="font-size: 0.95rem; color: #4A5568; line-height: 1.5;">{safe_abstract[:300]}...</div>
</div>
"""

st.title("PsiSearch")
st.caption("Psychology & Neuroscience Research Aggregator")
query = st.text_input("", placeholder="Search (e.g., Autistic Burnout, CBT Evidence)")

st.write("")
c1, c2, c3 = st.columns([1.5, 1.5, 2])
with c1: f_type = st.multiselect("Source", ["Book", "Article"], default=["Book", "Article"])
with c2: f_lang = st.multiselect("Language", ["English", "Portuguese", "Spanish"])
with c3:
    st.write("Sorting")
    p = st.slider("sort_slider", 0.0, 1.0, 0.5, label_visibility="collapsed")
    if p < 0.4: st.caption("Show Newest")
    elif p > 0.6: st.caption("Show Most Cited")
    else: st.caption("Balanced Mix")

st.markdown("---")

if query:
    with st.spinner("Analyzing databases..."):
        arts = search_openalex(query)
        books = search_google_books(query)
        full_data = arts + books
        
        if not full_data: st.info("No results found.")
        else:
            df = pd.DataFrame(full_data)
            if f_type: df = df[df['type'].isin(f_type)]
            if f_lang:
                codes = []
                if "English" in f_lang: codes.append('en')
                if "Portuguese" in f_lang: codes.append('pt')
                if "Spanish" in f_lang: codes.append('es')
                if codes: df = df[df['language'].apply(lambda x: any(c in str(x).lower() for c in codes))]

            if df.empty: st.warning("Filters too strict.")
            else:
                df_scored = calculate_score(df, p)
                st.markdown(f"**{len(df_scored)} Results**")
                for _, row in df_scored.iterrows():
                    st.markdown(render_card(row), unsafe_allow_html=True)


st.markdown('<div class="footer">PsiSearch Pro v1.0', unsafe_allow_html=True)

st.sidebar.markdown("---") 

st.sidebar.markdown(
    """
    <div style='text-align: center;'>
        <p style='font-style: italic; font-weight: bold;'>
            I exist, therefore I code. 🍊
        </p>
        <p>
            This tool is free and open-source. If it helped your research or saved you time:
        </p>
    </div>
    <a href="YOUR_KOFI_LINK" target="_blank" style="
        display: block;
        padding: 10px;
        margin: 10px 0;
        text-align: center;
        background-color: #ff5e5b; /* Cor Ko-fi/Laranja */
        color: white;
        text-decoration: none;
        border-radius: 5px;
        font-weight: bold;
    ">
        ☕ Buy Orange_dp a Coffee
    </a>
    """,
    unsafe_allow_html=True
)
