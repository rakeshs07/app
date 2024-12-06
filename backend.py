import os
import ast
import sqlite3
import pdfplumber
import pandas as pd
from PIL import Image
import streamlit as st
from typing import Literal
from dotenv import load_dotenv
import google.generativeai as genai
# from pinecone import Pinecone, ServerlessSpec
# from sentence_transformers import SentenceTransformer



load_dotenv()
genai.configure(api_key='AIzaSyC9ygffGdw5GRHa9X4wpVRuhYxTVVrNvoU')
# hf_key = os.getenv("HUGGINGFACE_TOKEN")


def extract_text_from_pdf(pdf_path):
    text_data = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text_data += page.extract_text()
    return text_data


def prompt_design_pdf(text_data):
    prompt = """
            You are an expert data engineer/analyst. I will mention below non-table content and table content. 
            I want you to return only the table content along with a generated table name. 
            Please return this in a dictionary format, 
            where the key is the table name, and the value is a list of tuples containing the table name and its content.
            Do not include any formatting characters like ``` in your output.
            I want you to handle all the tables present,Ensure that all tables in the input are extracted and included in the output.

            Here are some examples for reference:
        
        Example 0:
        Extracted Text:Employee
        Customer ID Name Address Phone Email
        CUST001 Customer 1 Address 1 123-456-7891 customer1@example.com

        output:
        {
        'employee':[
        ('Customer ID', 'Name', 'Address, 'Phone', 'Email'),
        ('CUST001', 'Customer 1', 'Address 1', '1234567891','customer1@example.com')]
        }


        Example 1:
        Extracted Text: Employee Records
        Employee ID Name Age Department Salary
        E001 John Doe 30 Marketing 60000
        E002 Jane Smith 28 Sales 55000
        E003 Mike Johnson 35 IT 70000

        Output:
        {
            "Employee Records": [
                ("Employee ID", "Name", "Age", "Department", "Salary"),
                ("E001", "John Doe", 30, "Marketing", 60000),
                ("E002", "Jane Smith", 28, "Sales", 55000),
                ("E003", "Mike Johnson", 35, "IT", 70000)
            ]
        }

        Example 2:
        Extracted Text: Inventory List
        Item ID Item Name Quantity Price
        I001 Laptop 50 1200.00
        I002 Mouse 150 25.00
        I003 Keyboard 100 45.00

        Extracted Text: Employee Records
        Employee ID Name Age Department Salary
        E001 John Doe 30 Marketing 60000
        E002 Jane Smith 28 Sales 55000
        E003 Mike Johnson 35 IT 70000

        Output:
        {
            "Inventory List": [
                ("Item ID", "Item Name", "Quantity", "Price"),
                ("I001", "Laptop", 50, 1200.00),
                ("I002", "Mouse", 150, 25.00),
                ("I003", "Keyboard", 100, 45.00)
            ],
            "Employee Records":[
                ("Employee ID", "Name", "Age", "Department", "Salary"),
                ("E001", "John Doe", 30, "Marketing", 60000),
                ("E002", "Jane Smith", 28, "Sales", 55000),
                ("E003", "Mike Johnson", 35, "IT", 70000)
            ]
        }
        
        Extracted Text: BTO
        Zero Days Zero Days Zero Days Zero Days Zero Days Zero Days
        MU
        (Jan) (Feb) (Mar) (Apr) (May) (June)
        NA CPRS 3171 2792 2734 1668 1607 1484
        NA MALS 3148 2817 2789 1818 1629 1530
        NA TMT 1495 1266 1141 780 759 724
        Others 893 782 721 491 409 397
        NA EUC 627 596 560 379 349 318
        NA CANADA 196 157 189 107 104 98
        Grand Total 9530 8410 8134 5243 4857 4551
        Zero Days Zero Days Zero Days Zero Days Zero Days Zero Days
        Practice
        (Jan) (Feb) ( Mar) (Apr) (May) (Jun)
        Testing 1915 1594 1420 856 818 723
        Central 213 169 126 102 88 87
        Sector 14 7 5 3 4 2
        Grand Total 2142 1770 1551 961 910 812
        output:{
            
        "MU":[
            ("MU",Zero Days\n(Jan), Zero Days\n(Feb), Zero Days\n(Mar), Zero Days\n(Apr), Zero Days\n(May),  Zero Days\n(June)),
            ("NA CPRS" 3171, 2792, 2734, 1668, 1607, 1484),
        ("NA MALS", 3148, 2817, 2789, 1818, 1629, 1530),
        ("NA TMT", 1495, 1266, 1141, 780, 759, 724),
        ("Others", 893, 782, 721, 491, 409, 397),
        ("NA EUC", 627, 596, 560, 379, 349, 318),
        ("NA CANADA", 196, 157, 189, 107, 104, 98),
        ("Grand Total", 9530, 8410, 8134, 5243, 4857, 4551)
        ],
        "Practice":[
        ("Practice", Zero Days\n(Jan), Zero Days\n(Feb), Zero Days\n( Mar), Zero Days\n(Apr), Zero Days\n(May), Zero Days\n(Jun))
        (Testing 1915 ,1594 ,1420 ,856 ,818 ,723),
        (Central 213 ,169 ,126 ,102 ,88 ,87),
        (Sector 14 ,7 ,5 ,3 ,4 ,2),
        (Grand Total ,2142 ,1770 ,1551 ,961 ,910, 812)
        ]
        }

        Now, based on the extracted text below, please provide the output:

    """
    prompt += text_data
    return prompt


def table_output_preprocess(table_content: str):
    try:
        table_content = table_content.split("=", 1)[1].strip()
    except IndexError:
        table_content = table_content.strip()

    table_content = table_content.replace("(", "[").replace(")", "]")
    table_content = ast.literal_eval(table_content)
    return table_content


def data_ingest(table_name, data: pd.DataFrame):
    # embedding(table_name,data)
    with sqlite3.connect("mydatabase.db") as conn:
        data.to_sql(table_name, conn, if_exists="replace", index=False)


def pdf_to_dict(a: dict):
    for table_name, rows in a.items():
        columns = rows[0]
        for i in range(len(columns)):
            columns[i] = columns[i].replace("-", "_").replace(" ", "")
        print(columns)
        data_rows = rows[1:]
        df = pd.DataFrame(data_rows, columns=columns)
        table_name = table_name.replace("-", "_").replace(" ", "").replace('[','').replace(']','').replace('<','').replace('>','')
        st.session_state.tables[table_name] = columns
        data_ingest(table_name, df)


def flatten_json(df):
    for column in df.columns:
        if isinstance(df[column].iloc[0], dict):
            nested_df = pd.json_normalize(df[column])
            df = df.drop(columns=[column]).join(nested_df)
    return df

def data_ingestion(dataset, table_name, type: Literal["c", "j"] = "c"):
    if type == "c":
        data = pd.read_csv(dataset)
    elif type == "j":
        data = pd.read_json(dataset)
        data = flatten_json(data)
    fields = data.columns.to_list()
    data.ffill(inplace=True)
    data_ingest(table_name=table_name, data=data)
    return fields


def get_gemini_response(question, prompt):
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content([prompt, question])
    return response.text

def get_gemini_response1(input,image):
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content([input,image])
    return response.text


def read_sql_query(sql, db):
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        column_names = [description[0] for description in cur.description]
    return column_names, rows


def prompt_Design(table_name, fields):
    prompt = [
        f"""
    you are an expert in converting english question to SQL query!
    the SQL has a database and in that the table name is:{table_name} 
    and has the following columns : {fields} \n\n
    for example,\nexample 1: How many entries of records are present?,
    the sql command will be something like this SELECT COUNT(*) FROM {table_name};
    example 2: Tell me avg of some column?,
    the sql command will be something like this SELECT AVG(some column) FROM {table_name};
    the sql query should be generate from {table_name} table completely without any assumptions 
    also the sql code should not have ```in the beginning or end and sql word is output"""
    ]
    return prompt


def prompttttt(a: dict):
    """
    Generates a prompt for converting English questions to SQL queries based on provided table and column names.
    """
    b = [
        f"""
    You are an expert in converting English questions to SQL queries!
    Your tables are mentioned below along with column names.

    Example 1: "How many entries of records are present?"
    The SQL command will be: SELECT COUNT(*) FROM table_name;

    Example 2: "Tell me the average of some column?"
    The SQL command will be: SELECT AVG(column_name) FROM table_name;

    The SQL query should be generated from the provided table and column names with no assumptions.
    When performing JOIN operations or subqueries, do NOT return duplicate columns.
    Always qualify column names with their table names when necessary (e.g., `table_name.column_name`) to avoid ambiguity.

    The SQL query should NOT include any SQL code fencing or extra words like `sql`.
    """
    ]
    for i, j in a.items():
        b[0] += f"table {i} has fields {j}\n"
    st.session_state.prompt = b


def pre__(file_type, table_name, uploaded_file):
    """
    Ingests data from a file into a specified table and updates the session state.
    """
    try:
        st.session_state.fields = data_ingestion(uploaded_file, table_name, file_type)
        st.success(
            f"Data ingested successfully into the '{
                st.session_state.table_name}' table."
        )
        st.session_state.tables[st.session_state.table_name] = st.session_state.fields
    except Exception as e:
        st.error(f"An error occurred: {e}")


def remove_duplicate_columns(columns, data):
    """
    Takes in columns and data, merges duplicate columns if their data is identical,
    and returns a DataFrame with duplicates removed.
    """
    df = pd.DataFrame(data, columns=columns)
    column_groups = {}
    for col in df.columns:
        if col not in column_groups:
            column_groups[col] = [df[col]]
        else:
            column_groups[col].append(df[col])

    for col, group in column_groups.items():
        if len(group) > 1:
            if all(group[0].equals(g) for g in group[1:]):
                df[col] = group[0]  # Keep the first occurrence
                for dup_col in group[1:]:
                    df = df.drop(dup_col.name, axis=1)  # Drop duplicates

    # df_transposed = df.T
    # df_transposed = df_transposed.drop_duplicates(keep='first')
    # return df_transposed.T
    return df

