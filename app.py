import streamlit as st
import pandas as pd
from pathlib import Path
import time

# --- Page Config ---
st.set_page_config(page_title="Erasmus Inbox Agent", page_icon="🎓", layout="wide")

# --- Session State for Chat History ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Header ---
st.title("🎓 Erasmus+ Inbox & Document Automation Agent")
st.markdown("Automated sorting of student documents, Excel tracking, and FAQ response generation.")

# --- Sidebar ---
st.sidebar.header("Control Panel")

if st.sidebar.button("🛠️ 1. Generate Test Emails"):
    with st.spinner("Generating sample .eml files and PDFs in inbox/..."):
        # Тут ти зможеш імпортувати свою функцію генерації:
        # from data_generator import generate_test_data
        # generate_test_data()
        time.sleep(1.5)
    st.sidebar.success("Test data generated successfully!")

if st.sidebar.button("🚀 2. Process Entire Inbox"):
    # Прогрес-бар для ефектності на демо
    progress_bar = st.sidebar.progress(0)
    status_text = st.sidebar.empty()
    
    status_text.text("Scanning inbox files...")
    progress_bar.progress(25)
    time.sleep(1)
    
    status_text.text("Agent is analyzing documents...")
    progress_bar.progress(60)
    # Тут виклик твого агента: 
    # from erasmus_inbox.agent import root_agent
    # root_agent.run("Process my inbox")
    time.sleep(1.5)
    
    status_text.text("Updating Excel & drafting replies...")
    progress_bar.progress(100)
    time.sleep(0.5)
    
    status_text.empty()
    progress_bar.empty()
    st.sidebar.success("New emails successfully processed!")

# --- Main Content (Tabs) ---
tab1, tab2, tab3 = st.tabs(["📊 Dashboard & Data", "📁 Sorted Files", "🤖 Agent Chat"])

# --- Tab 1: Dashboard ---
with tab1:
    excel_path = Path("students.xlsx")
    if excel_path.exists():
        df = pd.read_excel(excel_path)
        
        # Аналітичні метрики
        col1, col2, col3 = st.columns(3)
        total_students = len(df)
        
        # Припустимо, що у таблиці є колонка "Missing Documents"
        missing_issues = len(df[df['Missing Documents'].notna() & (df['Missing Documents'] != '')]) if 'Missing Documents' in df.columns else 0
        
        col1.metric("Total Students Processed", total_students)
        col2.metric("Pending Missing Documents", missing_issues)
        col3.metric("Draft Replies Ready", "3") # Заглушка для чорнеток
        
        st.divider()
        st.subheader("Student Database")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("The `students.xlsx` file has not been created yet. Click 'Process Entire Inbox' to generate it.")

# --- Tab 2: Sorted Files ---
with tab2:
    st.subheader("Organized Student Folders (filed/)")
    filed_dir = Path("filed")
    
    if filed_dir.exists() and any(filed_dir.iterdir()):
        students = sorted([d.name for d in filed_dir.iterdir() if d.is_dir()])
        selected_student = st.selectbox("Select student folder to inspect:", students)
        
        if selected_student:
            student_dir = filed_dir / selected_student
            student_files = list(student_dir.glob("*.*"))
            
            if student_files:
                for f in student_files:
                    # Додано відображення розміру файлу
                    file_size_kb = f.stat().st_size / 1024
                    st.markdown(f"📄 **{f.name}**  *( {file_size_kb:.1f} KB )*")
                    # Кнопка для скачування файлу (дуже крута фіча для журі)
                    with open(f, "rb") as file_data:
                        st.download_button(label="Download", data=file_data, file_name=f.name, mime="application/octet-stream", key=f.name)
            else:
                st.warning("No files found in this folder.")
    else:
        st.info("The `filed/` folder is empty. Process the inbox first.")

# --- Tab 3: Chat UI ---
with tab3:
    st.subheader("Ask the Erasmus Agent")
    st.caption("Answers student questions using the FAQ knowledge base or drafts staff escalations.")
    
    # Відображення історії чату
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Поле вводу в стилі чату
    if prompt := st.chat_input("E.g., 'When is the deadline for insurance?'"):
        # Додаємо питання користувача в історію
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Симуляція відповіді агента (тут має бути виклик реального root_agent)
        with st.chat_message("assistant"):
            with st.spinner("Analyzing FAQ..."):
                time.sleep(1) # Заглушка часу обробки
                # Реальний виклик: response = root_agent.run(prompt)
                response = "Draft Response: Please send your health and liability insurance document before 15 January."
                st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})