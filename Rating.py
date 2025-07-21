import streamlit as st
import pandas as pd
import io
from datetime import datetime

filename = f"Рейтинг_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.xlsx"

st.set_page_config(page_title="Рейтинг вступників", layout="wide")

# --- ВКЛАДКИ ---
tab1, tab2 = st.tabs(["📋 Рейтинг", "⚙️ Параметри"])

# --- ПАРАМЕТРИ ---
with tab2:
    st.header("⚙️ Налаштування кількості місць за спеціальностями")
    max_places = {}
    max_places['Безпека інфокомунікаційних систем та мереж'] = st.number_input(
        "Безпека інфокомунікаційних систем та мереж:", min_value=0, max_value=100, value=20, step=1)
    max_places['Комп’ютерні системи та мережі'] = st.number_input(
        "Комп’ютерні системи та мережі:", min_value=0, max_value=100, value=23, step=1)
    max_places['Програмне забезпечення інфокомунікаційних систем'] = st.number_input(
        "Програмне забезпечення інфокомунікаційних систем:", min_value=0, max_value=100, value=20, step=1)
    max_places['Інфокомунікаційні системи та мережі'] = st.number_input(
        "Інфокомунікаційні системи та мережі:", min_value=0, max_value=100, value=20, step=1)
    max_places["Системи та мережі мобільного зв'язку"] = st.number_input(
        "Системи та мережі мобільного зв'язку:", min_value=0, max_value=100, value=20, step=1)
    max_places['Поштово-логістичні системи'] = st.number_input(
        "Поштово-логістичні системи:", min_value=0, max_value=100, value=20, step=1)

# --- ОСНОВНА ВКЛАДКА ---
with tab1:
    st.title("🎓 Рейтинг абітурієнтів")

    uploaded_file = st.file_uploader("📂 Завантажте Excel-файл", type=["xlsx"])
    split_fio = st.checkbox("🔀 Розділити ПІБ на окремі колонки", value=True)

    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        df = df.rename(columns=lambda x: str(x).strip())

        # Розділення ПІБ
        if split_fio and 'ПІБ' in df.columns:
            df[['Прізвище', "Ім'я", 'По батькові']] = df['ПІБ'].str.split(' ', n=2, expand=True)

        # Стандартизація назв колонок
        if 'ID' not in df.columns:
            df.insert(0, 'ID', range(1, len(df) + 1))
        if 'Прізвище' not in df.columns:
            df.rename(columns={df.columns[1]: 'Прізвище'}, inplace=True)
        if "ім’я" in df.columns:
            df.rename(columns={"ім’я": "Ім'я"}, inplace=True)
        if 'по-батькові' in df.columns:
            df.rename(columns={'по-батькові': 'По батькові'}, inplace=True)
        if 'Оцінка' not in df.columns and 'общий бал' in df.columns:
            df.rename(columns={'общий бал': 'Оцінка'}, inplace=True)

        # Стандартизовані колонки спеціальностей (максимум 5)
        for i in range(1, 6):
            if str(i) not in df.columns:
                df[str(i)] = None

        # Обробка оцінок
        def parse_score(x):
            try:
                score = float(x)
                return score if score >= 120 else None
            except:
                return 'п' if str(x).lower() == 'п' else None

        df['Оцінка'] = df['Оцінка'].apply(parse_score)
        df = df[df['Оцінка'].notnull()].copy()

        # Сортування: пільги = найвище
        df['tmp_score'] = df['Оцінка'].apply(lambda x: float('inf') if x == 'п' else float(x))
        df = df.sort_values(by='tmp_score', ascending=False).reset_index(drop=True)

        # Призначення спеціальності
        specialties = {k: [] for k in max_places}

        def assign(row):
            for i in ['1', '2', '3', '4', '5']:
                spec = row[i]
                if spec in specialties and len(specialties[spec]) < max_places[spec]:
                    specialties[spec].append(row['ID'])
                    return spec
            return 'Рекомендовано на контракт'

        df['Спеціальність'] = df.apply(assign, axis=1)
        df.drop(columns=['tmp_score'], inplace=True)

        # Форматування оцінок
        df['Оцінка'] = df['Оцінка'].apply(lambda x: 'п' if x == 'п' else round(float(x), 1))

        # Сортування: пільговики зверху, потім за оцінкою
        df['sort_score'] = df['Оцінка'].apply(lambda x: -1 if x == 'п' else -float(x))
        df = df.sort_values(by=['Спеціальність', 'sort_score'], ascending=[True, True])
        df.drop(columns=['sort_score'], inplace=True)

        # Контракт — внизу
        contract_data = df[df['Спеціальність'] == 'Рекомендовано на контракт']
        passed_data = df[df['Спеціальність'] != 'Рекомендовано на контракт']
        df = pd.concat([passed_data, contract_data], ignore_index=True)

        # --- Фільтри ---
        col1, col2, col3 = st.columns(3)
        with col1:
            f1 = st.text_input("Фільтр: Прізвище")
        with col2:
            f2 = st.text_input("Фільтр: Ім'я")
        with col3:
            f3 = st.selectbox("Фільтр: Спеціальність", ['Усі'] + list(df['Спеціальність'].unique()))

        filtered = df.copy()
        if f1:
            filtered = filtered[filtered['Прізвище'].str.contains(f1, case=False, na=False)]
        if f2:
            filtered = filtered[filtered["Ім'я"].str.contains(f2, case=False, na=False)]
        if f3 != 'Усі':
            filtered = filtered[filtered['Спеціальність'] == f3]

        final = filtered[['Оцінка', 'Спеціальність', 'Прізвище', "Ім'я", 'По батькові']]
        spec_counts = df['Спеціальність'].value_counts().reset_index()
        spec_counts.columns = ['Спеціальність', 'Кількість']

        # --- Дві колонки: Рейтинг та Підрахунок ---
        left_col, right_col = st.columns([3, 1])
        with left_col:
            st.markdown("### 🧾 Таблиця рейтингу")
            st.dataframe(final, use_container_width=True)

        with right_col:
            st.markdown("### 📊 Кількість вступників за спеціальностями")
            st.table(spec_counts)

        # Завантаження Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            final.to_excel(writer, index=False, sheet_name='Результат')
            spec_counts.to_excel(writer, index=False, sheet_name='Підрахунок')
        output.seek(0)

        st.download_button("⬇️ Завантажити результат у Excel", data=output.getvalue(),
                           file_name=filename,
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

