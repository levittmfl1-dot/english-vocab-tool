import streamlit as st
import sqlite3
import pandas as pd
from openai import OpenAI
import json
import random

# ==========================================
# 1. 基础配置与 CSS 样式 (3D 翻转卡片)
# ==========================================
st.set_page_config(page_title="AI Vocab Master", layout="wide")

# CSS for Flashcard Flip Animation
st.markdown("""
<style>
.flip-card {
  background-color: transparent;
  width: 100%;
  height: 300px;
  perspective: 1000px;
  margin-bottom: 20px;
}

.flip-card-inner {
  position: relative;
  width: 100%;
  height: 100%;
  text-align: center;
  transition: transform 0.6s;
  transform-style: preserve-3d;
  box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
  border-radius: 15px;
}

.flip-card-front, .flip-card-back {
  position: absolute;
  width: 100%;
  height: 100%;
  -webkit-backface-visibility: hidden;
  backface-visibility: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 15px;
  padding: 20px;
}

.flip-card-front {
  background-color: #f1f1f1;
  color: black;
  border: 2px solid #ddd;
}

.flip-card-back {
  background-color: #e3f2fd;
  color: black;
  transform: rotateY(180deg);
  border: 2px solid #90caf9;
  overflow-y: auto;
}

.flipped {
  transform: rotateY(180deg);
}

.word-text { font-size: 32px; font-weight: bold; color: #333; }
.def-text { font-size: 18px; margin-top: 10px; }
.cn-text { font-size: 20px; color: #555; font-weight: bold; margin-top: 5px;}
.context-text { font-size: 14px; color: #d81b60; font-style: italic; margin-top: 15px; border-top: 1px dashed #ccc; padding-top: 5px;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 数据库管理
# ==========================================
def init_db():
    # 加上 check_same_thread=False 防止多线程报错
    conn = sqlite3.connect('vocab.db', check_same_thread=False)
    c = conn.cursor()
    # 单词表
    c.execute('''CREATE TABLE IF NOT EXISTS words
                 (id INTEGER PRIMARY KEY, word TEXT UNIQUE, 
                  def_en TEXT, def_cn TEXT, ipa TEXT, 
                  sample_sentence TEXT, source_context TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # 历史记录表
    c.execute('''CREATE TABLE IF NOT EXISTS history
                 (id INTEGER PRIMARY KEY, target_word TEXT, 
                  user_sentence TEXT, correction TEXT, feedback TEXT, status TEXT, 
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def get_db_connection():
    return sqlite3.connect('vocab.db', check_same_thread=False)

# 初始化数据库
init_db()

# ==========================================
# 3. AI 逻辑
# ==========================================
# 获取 API Key
api_key = st.secrets.get("OPENAI_API_KEY")
if not api_key:
    api_key = st.sidebar.text_input("OpenAI API Key", type="password")

client = None
if api_key:
    client = OpenAI(api_key=api_key)

def generate_word_info(word):
    if not client: return None
    prompt = f"""
    Analyze the English word: "{word}".
    1. Provide a concise English definition (Cambridge/Oxford style).
    2. Provide a Chinese definition.
    3. Provide IPA pronunciation.
    4. Provide a standard sample sentence.
    5. CRITICAL: If this word has a specific slang, internet, or social media usage (e.g., "Cap", "Salty", "Ghost"), explain it in 'source_context'. If not, leave it empty.
    
    Output JSON format:
    {{
        "def_en": "...",
        "def_cn": "...",
        "ipa": "...",
        "sample": "...",
        "context": "..."
    }}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        st.error(f"AI Error: {e}")
        return None

def check_sentence(word, sentence, context_info):
    if not client: return None
    prompt = f"""
    Word: "{word}"
    Definition: {context_info}
    User Sentence: "{sentence}"
    
    Task:
    1. Check if the user used the word correctly in context.
    2. Fix grammar errors.
    3. Suggest a more native/natural version.
    
    Output JSON:
    {{
        "status": "Perfect" or "Good" or "Incorrect",
        "corrected": "...",
        "feedback": "Explain grammar or usage logic briefly.",
        "native_suggestion": "..."
    }}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are a strict English teacher."},
                      {"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        st.error(f"AI Error: {e}")
        return None

# ==========================================
# 4. 界面逻辑
# ==========================================

# 侧边栏导航
menu = st.sidebar.radio("Menu", ["📖 Add Word", "🗂 Flashcards", "✍️ Practice", "⚙️ Manage List"])

# --- 页面 1: 添加单词 ---
if menu == "📖 Add Word":
    st.header("Add New Word")
    new_word = st.text_input("Enter English Word").strip()
    
    if st.button("✨ Auto-Generate & Save"):
        if not new_word:
            st.warning("Please enter a word.")
        elif not client:
            st.error("Please provide OpenAI API Key in Sidebar.")
        else:
            with st.spinner(f"Searching Cambridge/Oxford & Internet context for '{new_word}'..."):
                data = generate_word_info(new_word)
                if data:
                    conn = get_db_connection()
                    try:
                        conn.execute("INSERT INTO words (word, def_en, def_cn, ipa, sample_sentence, source_context) VALUES (?, ?, ?, ?, ?, ?)",
                                     (new_word, data['def_en'], data['def_cn'], data['ipa'], data['sample'], data['context']))
                        conn.commit()
                        st.success(f"Added: **{new_word}**")
                        st.json(data)
                    except sqlite3.IntegrityError:
                        st.warning("Word already exists in database!")
                    finally:
                        conn.close()

# --- 页面 2: 闪卡复习 (3D 动画版) ---
elif menu == "🗂 Flashcards":
    st.header("Flashcards Review")
    
    mode = st.radio("Select Mode", ["Mode A: Recall (See Word -> Defs)", "Mode B: Challenge (See En Def -> Word)"], horizontal=True)
    
    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM words", conn)
    conn.close()
    
    if df.empty:
        st.info("No words yet. Go add some!")
    else:
        # Session state to track current card index and flip state
        if 'card_idx' not in st.session_state:
            st.session_state.card_idx = random.randint(0, len(df)-1)
        if 'is_flipped' not in st.session_state:
            st.session_state.is_flipped = False

        # Get current word data
        row = df.iloc[st.session_state.card_idx]
        
        # Determine Front/Back content based on Mode
        if "Mode A" in mode:
            front_main = row['word']
            front_sub = row['ipa']
            back_main = row['def_cn']
            back_sub = f"🇬🇧 {row['def_en']}"
            context = row['source_context']
        else:
            front_main = row['def_en']
            front_sub = "Guess the word?"
            back_main = row['word']
            back_sub = row['def_cn']
            context = row['source_context']

        # CSS Class for flip
        flip_class = "flipped" if st.session_state.is_flipped else ""

        # HTML Structure for the Card
        card_html = f"""
        <div class="flip-card">
          <div class="flip-card-inner {flip_class}">
            <div class="flip-card-front">
              <div class="word-text">{front_main}</div>
              <div class="def-text">{front_sub}</div>
            </div>
            <div class="flip-card-back">
              <div class="word-text">{back_main}</div>
              <div class="def-text">{back_sub}</div>
              {f'<div class="context-text">💡 {context}</div>' if context else ''}
            </div>
          </div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

        # Control Buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Flip Card", use_container_width=True):
                st.session_state.is_flipped = not st.session_state.is_flipped
                st.rerun()
        with col2:
            if st.button("➡️ Next Random", use_container_width=True):
                st.session_state.card_idx = random.randint(0, len(df)-1)
                st.session_state.is_flipped = False
                st.rerun()

# --- 页面 3: 造句练习 (直接输入) ---
elif menu == "✍️ Practice":
    st.header("Sentence Practice")
    
    col_input, col_sent = st.columns([1, 2])
    
    with col_input:
        target_word = st.text_input("Target Word (Type directly)").strip()
    
    with col_sent:
        user_sent = st.text_input("Make a sentence with it")

    if st.button("Check My Sentence"):
        if not target_word or not user_sent:
            st.warning("Please fill in both fields.")
        elif not client:
            st.error("No API Key found.")
        else:
            conn = get_db_connection()
            # 修复：防止代码太长被截断，拆开写
            query_sql = "SELECT * FROM words WHERE word = ?"
            row = pd.read_sql(query_sql, conn, params=(target_word,))
            conn.close()
            
            word_context = "General English Word"
            if not row.empty:
                word_context = f"{row.iloc[0]['def_en']} ({row.iloc[0]['def_cn']})"
            
            with st.spinner("AI Teacher is correcting..."):
                res = check_sentence(target_word, user_sent, word_context)
                if res:
                    st.divider()
                    if res['status'] == "Perfect":
                        st.success(f"🎉 {res['status']}!")
                    else:
                        st.info(f"📊 Status: {res['status']}")
                    
                    st.write(f"**Your Sentence:** {user_sent}")
                    st.write(f"**Corrected:** {res['corrected']}")
                    st.write(f"**Native Way:** {res['native_suggestion']}")
                    st.caption(f"💡 Feedback: {res['feedback']}")
                    
                    # Save to history
                    conn = get_db_connection()
                    conn.execute("INSERT INTO history (target_word, user_sentence, correction, feedback, status) VALUES (?, ?, ?, ?, ?)",
                                 (target_word, user_sent, res['corrected'], res['feedback'], res['status']))
                    conn.commit()
                    conn.close()

# --- 页面 4: 管理列表 (删除功能) ---
elif menu == "⚙️ Manage List":
    st.header("Manage Vocabulary")
    
    conn = get_db_connection()
    df = pd.read_sql("SELECT id, word, def_cn, created_at FROM words ORDER BY created_at DESC", conn)
    conn.close()
    
    if not df.empty:
        for index, row in df.iterrows():
            col1, col2, col3, col4 = st.columns([2, 3, 2, 1])
            with col1:
                st.write(f"**{row['word']}**")
            with col2:
                st.write(row['def_cn'])
            with col3:
                st.caption(row['created_at'])
            with col4:
                if st.button("🗑️", key=f"del_{row['id']}"):
                    conn = get_db_connection()
                    conn.execute("DELETE FROM words WHERE id = ?", (row['id'],))
                    conn.commit()
                    conn.close()
                    st.rerun()
    else:
        st.write("No words found.")
