import streamlit as st
import json
import random
from pathlib import Path
from datetime import datetime
from supabase import create_client

VOCAB_FILE = "vocab_vi.json"

st.set_page_config(
    page_title="TOEIC Vocab Trainer",
    page_icon="📘",
    layout="centered"
)

# =========================
# KẾT NỐI SUPABASE
# =========================

@st.cache_resource
def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = get_supabase()

# =========================
# ĐỌC TỪ VỰNG
# =========================

@st.cache_data
def load_vocab():
    if not Path(VOCAB_FILE).exists():
        return []

    with open(VOCAB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

vocab = load_vocab()

if not vocab:
    st.error("Không tìm thấy file vocab_vi.json.")
    st.stop()

# =========================
# HÀM XỬ LÝ TIẾN ĐỘ
# =========================

def load_progress(user_id):
    """
    Đọc tiến độ của riêng user_id từ Supabase.
    Trả về dạng:
    {
        "word": {"correct": 1, "wrong": 2, "last_review": "..."}
    }
    """
    try:
        response = (
            supabase
            .table("progress")
            .select("word, correct, wrong, last_review")
            .eq("user_id", user_id)
            .execute()
        )

        progress = {}

        for row in response.data:
            progress[row["word"]] = {
                "correct": row.get("correct", 0),
                "wrong": row.get("wrong", 0),
                "last_review": row.get("last_review", "")
            }

        return progress

    except Exception as e:
        st.error(f"Lỗi đọc tiến độ từ Supabase: {e}")
        return {}


def update_progress(user_id, word, correct_answer):
    """
    Cập nhật tiến độ của 1 từ.
    Nếu chưa có thì insert.
    Nếu có rồi thì update.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # Tìm dòng hiện tại
        response = (
            supabase
            .table("progress")
            .select("correct, wrong")
            .eq("user_id", user_id)
            .eq("word", word)
            .execute()
        )

        if response.data:
            current = response.data[0]
            new_correct = current.get("correct", 0)
            new_wrong = current.get("wrong", 0)

            if correct_answer:
                new_correct += 1
            else:
                new_wrong += 1

            (
                supabase
                .table("progress")
                .update({
                    "correct": new_correct,
                    "wrong": new_wrong,
                    "last_review": now
                })
                .eq("user_id", user_id)
                .eq("word", word)
                .execute()
            )

        else:
            (
                supabase
                .table("progress")
                .insert({
                    "user_id": user_id,
                    "word": word,
                    "correct": 1 if correct_answer else 0,
                    "wrong": 0 if correct_answer else 1,
                    "last_review": now
                })
                .execute()
            )

    except Exception as e:
        st.error(f"Lỗi lưu tiến độ vào Supabase: {e}")


def get_new_index():
    old_index = st.session_state.get("index", None)

    if len(vocab) <= 1:
        return 0

    new_index = random.randint(0, len(vocab) - 1)

    while new_index == old_index:
        new_index = random.randint(0, len(vocab) - 1)

    return new_index


def next_card():
    st.session_state["index"] = get_new_index()
    st.session_state["show_answer"] = False

    if "choices" in st.session_state:
        del st.session_state["choices"]

    if "result" in st.session_state:
        del st.session_state["result"]


def init_state():
    if "index" not in st.session_state:
        st.session_state["index"] = random.randint(0, len(vocab) - 1)

    if "show_answer" not in st.session_state:
        st.session_state["show_answer"] = False


# =========================
# ĐĂNG NHẬP ĐƠN GIẢN
# =========================

st.title("📘 TOEIC Vocab Trainer")
st.write("Học từ vựng TOEIC bằng tiếng Việt.")

st.sidebar.title("Người học")

user_id = st.sidebar.text_input(
    "Nhập tên hoặc mã học viên",
    placeholder="Ví dụ: thanh, phuong, an01"
)

if not user_id:
    st.info("Hãy nhập tên hoặc mã học viên ở thanh bên trái để bắt đầu học.")
    st.stop()

user_id = user_id.strip().lower()

if len(user_id) < 2:
    st.warning("Tên/mã học viên nên có ít nhất 2 ký tự.")
    st.stop()

progress = load_progress(user_id)
init_state()

st.sidebar.success(f"Đang học với mã: {user_id}")

# =========================
# MENU
# =========================

st.sidebar.title("Menu")
mode = st.sidebar.radio(
    "Chọn chế độ",
    ["Flashcard", "Trắc nghiệm", "Tìm kiếm từ", "Thống kê"]
)

st.sidebar.write("---")
st.sidebar.write(f"Tổng số từ: **{len(vocab)}**")
st.sidebar.write(f"Đã học: **{len(progress)}**")

# =========================
# FLASHCARD
# =========================

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
                update_progress(user_id, item["word"], True)
                next_card()
                st.rerun()

        with col4:
            if st.button("❌ Tôi chưa nhớ", key="wrong_flashcard"):
                update_progress(user_id, item["word"], False)
                next_card()
                st.rerun()

# =========================
# TRẮC NGHIỆM
# =========================

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
                update_progress(user_id, item["word"], True)
            else:
                st.session_state["result"] = "wrong"
                update_progress(user_id, item["word"], False)

    with col2:
        if st.button("➡️ Câu tiếp theo", key="next_quiz"):
            next_card()
            st.rerun()

    if st.session_state.get("result") == "correct":
        st.success("Đúng rồi!")

    if st.session_state.get("result") == "wrong":
        st.error("Sai rồi.")
        st.info(f"Đáp án đúng: {item['meaning_vi']}")

# =========================
# TÌM KIẾM
# =========================

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

# =========================
# THỐNG KÊ
# =========================

elif mode == "Thống kê":
    st.header("📊 Thống kê")

    progress = load_progress(user_id)

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
