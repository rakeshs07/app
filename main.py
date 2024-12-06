from backend import *


st.set_page_config(page_title="Structured Data & Q&A App", layout="centered", page_icon="📈")
st.title("Structured Data Analysis")

# Initialize session state variables if they are not present
if "table_name" not in st.session_state:
    st.session_state.table_name = {}
if "tables" not in st.session_state:
    st.session_state.tables = {}
if "prompt" not in st.session_state:
    st.session_state.prompt = []
if "fields" not in st.session_state:
    st.session_state.fields = []
if "question" not in st.session_state:
    st.session_state.question = []
if "data_ingested" not in st.session_state:
    st.session_state.data_ingested = False
if "selected_section" not in st.session_state:
    st.session_state.selected_section = "none"

# Sidebar options for different functionalities
st.sidebar.header("Choose an Option")

# Button to select structured data analysis section
if st.sidebar.button("Structured Data Analysis"):
    st.session_state.selected_section = "data_analysis"

# Button to select image-based Q&A section
if st.sidebar.button("Image-Based Q&A"):
    st.session_state.selected_section = "image_qna"

# Section for Structured Data Analysis (CSV, JSON, PDF)
if st.session_state.selected_section == "data_analysis":
    st.header("Structured Data")

    # File uploader for data files
    uploaded_files = st.file_uploader("Choose files", type=["csv", "json", "pdf"], accept_multiple_files=True)
    if uploaded_files and st.button("Ingest Data"):
        for uploaded_file in uploaded_files:
            if uploaded_file.name.endswith(".csv"):
                file_type = "c"
                st.session_state.table_name = (
                    os.path.splitext(uploaded_file.name)[0]
                    .replace("-", "_")
                    .replace(" ", "")
                )
                pre__(file_type, st.session_state.table_name, uploaded_file)
            elif uploaded_file.name.endswith(".json"):
                file_type = "j"
                st.session_state.table_name = (
                    os.path.splitext(uploaded_file.name)[0]
                    .replace("-", "_")
                    .replace(" ", "")
                )
                pre__(file_type, st.session_state.table_name, uploaded_file)
            elif uploaded_file.name.endswith(".pdf"):
                textdata = extract_text_from_pdf(uploaded_file)
                model = genai.GenerativeModel("gemini-pro")
                response = model.generate_content(prompt_design_pdf(textdata))
                a = response.text.replace("```", "")
                pdf_to_dict(table_output_preprocess(a))
            else:
                st.error(f"Unsupported file type: {uploaded_file.name}. Please upload a CSV, JSON, or PDF file.")
            st.session_state.data_ingested = True

    # Process prompts for SQL generation if data has been ingested
    prompttttt(st.session_state.tables)
    if st.session_state.data_ingested:
        
        question = st.text_input("Enter your query")
        st.session_state.question = question
        if st.button("Get Data"):
            # query(question)

            response = (
                get_gemini_response(
                    question=st.session_state.question, prompt=st.session_state.prompt[0]
                )
                .replace("```", "")
                .replace("sql", "")
                .strip()
            )
            st.subheader("Generated SQL Query:")
            st.write(response)
            column, response = read_sql_query(response, "mydatabase.db")

            st.subheader("Query Result:")
            if response:
                if "final_df" not in st.session_state:
                    st.session_state.final_df = None
                try:
                    st.session_state.final_df = pd.DataFrame(columns=column, data=response)
                    st.dataframe(st.session_state.final_df)
                except:
                    st.session_state.final_df = remove_duplicate_columns(columns=column, data=response)
                    st.dataframe(st.session_state.final_df)

# Section for Image-Based Q&A
elif st.session_state.selected_section == "image_qna":
    st.header("Gemini LLM Q&A with Image Support")

    # Image file uploader
    uploaded_image = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])
    
    # Display the uploaded image and text input for question
    if uploaded_image:
        image = Image.open(uploaded_image)
        st.image(image, caption="Uploaded Image", use_column_width=True)
        st.session_state.image = image

    # Input text for the question
    input_text = st.text_input("Input your question:", key="input_text")
    submit_button = st.button("Ask the Question")

    # Generate a response if an image and question have been provided
    if submit_button and uploaded_image:
        response = get_gemini_response1(input_text, st.session_state.image)
        st.subheader("Response:")
        st.write(response)
