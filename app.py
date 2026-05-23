import streamlit as st
import json
import random
from pathlib import Path
from datetime import datetime

VOCAB_FILE = "vocab_vi.json"
PROGRESS_FILE = "progress.json"

st.set_page_config(
    page_title="TOEIC Vocab Trainer",
    page_icon="📘",
    layout="centered"
)

def load_vocab():
    with open(VOCAB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def load_progress():
    if Path(PROGRESS_FILE).exists():
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_progress(progress):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)

def update_progress(word, correct):
    progress = load_progress()

    if word not in progress:
        progress[word] = {
            "correct": 0,
            "wrong": 0,
            "last_review": ""
        }

    if correct:
        progress[word]["correct"] += 1
    else:
        progress[word]["wrong"] += 1

    progress[word]["last_review"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_progress(progress)

def get_new_index(vocab):
    old_index = st.session_state.get("index", None)

    if len(vocab) <= 1:
        return 0

    new_index = random.randint(0, len(vocab) - 1)

    while new_index == old_index:
        new_index = random.randint(0, len(vocab) - 1)

    return new_index

def next_card():
    st.session_state["index"] = get_new_index(vocab)
    st.session_state["show_answer"] = False
    st.session_state["checked"] = False

    if "choices" in st.session_state:
        del st.session_state["choices"]

    if "result" in st.session_state:
        del st.session_state["result"]

def init_state():
    if "index" not in st.session_state:
        st.session_state["index"] = random.randint(0, len(vocab) - 1)

    if "show_answer" not in st.session_state:
        st.session_state["show_answer"] = False

    if "checked" not in st.session_state:
        st.session_state["checked"] = False

if not Path(VOCAB_FILE).exists():
    st.error("Không tìm thấy file vocab_vi.json.")
    st.stop()

vocab = load_vocab()
progress = load_progress()
init_state()

st.title("📘 TOEIC Vocab Trainer")
st.write("Học từ vựng TOEIC bằng tiếng Việt.")

st.sidebar.title("Menu")
mode = st.sidebar.radio(
    "Chọn chế độ",
    ["Flashcard", "Trắc nghiệm", "Tìm kiếm từ", "Thống kê"]
)

st.sidebar.write("---")
st.sidebar.write(f"Tổng số từ: **{len(vocab)}**")
st.sidebar.write(f"Đã học: **{len(progress)}**")

if mode == "Flashcard":
    st.header("🃏 Flashcard")

    item = vocab[st.session_state["index"]]

    st.subheader(item["word"])
    st.caption(f"Nguồn: {item.get('source', '')} - trang {item.get('page', '')}")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("👀 Hiện nghĩa", key="show_flashcard"):
            st.session_state["show_answer"] = True

    with col2:
        if st.button("➡️ Câu tiếp theo", key="next_flashcard"):
            next_card()
            st.rerun()

    if st.session_state["show_answer"]:
        st.success(f"Nghĩa tiếng Việt: {item['meaning_vi']}")

        col3, col4 = st.columns(2)

        with col3:
            if st.button("✅ Tôi nhớ đúng", key="right_flashcard"):
                update_progress(item["word"], True)
                next_card()
                st.rerun()

        with col4:
            if st.button("❌ Tôi chưa nhớ", key="wrong_flashcard"):
                update_progress(item["word"], False)
                next_card()
                st.rerun()

elif mode == "Trắc nghiệm":
    st.header("📝 Trắc nghiệm 4 đáp án")

    item = vocab[st.session_state["index"]]

    st.subheader(item["word"])

    if "choices" not in st.session_state:
        correct = item["meaning_vi"]
        choices = [correct]

        while len(choices) < 4:
            random_meaning = random.choice(vocab)["meaning_vi"]
            if random_meaning not in choices:
                choices.append(random_meaning)

        random.shuffle(choices)
        st.session_state["choices"] = choices

    choice = st.radio("Chọn nghĩa đúng:", st.session_state["choices"], key="quiz_choice")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Kiểm tra", key="check_quiz"):
            if choice == item["meaning_vi"]:
                st.session_state["result"] = "correct"
                update_progress(item["word"], True)
            else:
                st.session_state["result"] = "wrong"
                update_progress(item["word"], False)

    with col2:
        if st.button("➡️ Câu tiếp theo", key="next_quiz"):
            next_card()
            st.rerun()

    if st.session_state.get("result") == "correct":
        st.success("Đúng rồi!")

    if st.session_state.get("result") == "wrong":
        st.error("Sai rồi.")
        st.info(f"Đáp án đúng: {item['meaning_vi']}")

elif mode == "Tìm kiếm từ":
    st.header("🔎 Tìm kiếm từ")

    keyword = st.text_input("Nhập từ cần tìm")

    if keyword:
        results = [
            item for item in vocab
            if keyword.lower() in item["word"].lower()
        ]

        st.write(f"Tìm thấy **{len(results)}** kết quả.")

        for item in results[:50]:
            with st.expander(item["word"]):
                st.write(f"**Nghĩa:** {item['meaning_vi']}")
                st.write(f"**Nguồn:** {item.get('source', '')} - trang {item.get('page', '')}")

elif mode == "Thống kê":
    st.header("📊 Thống kê")

    progress = load_progress()

    total_correct = sum(p["correct"] for p in progress.values())
    total_wrong = sum(p["wrong"] for p in progress.values())
    total = total_correct + total_wrong

    col1, col2, col3 = st.columns(3)

    col1.metric("Từ đã học", len(progress))
    col2.metric("Đúng", total_correct)
    col3.metric("Sai", total_wrong)

    if total > 0:
        st.metric("Tỷ lệ đúng", f"{total_correct / total * 100:.2f}%")

    st.subheader("10 từ nên ôn lại nhiều nhất")

    weak_words = sorted(
        progress.items(),
        key=lambda x: x[1]["wrong"] - x[1]["correct"],
        reverse=True
    )[:10]

    if not weak_words:
        st.info("Chưa có dữ liệu.")
    else:
        for word, data in weak_words:
            st.write(f"- **{word}**: đúng {data['correct']}, sai {data['wrong']}")