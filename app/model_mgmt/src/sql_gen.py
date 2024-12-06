# flake8: noqa --E501


from pathlib import Path
from vertexai.generative_models import (
    GenerativeModel
)
import json
import magika
import os
import app.model_mgmt.src.prompts as prompts
import vertexai


m = magika.Magika()

schema_dir = "./schemas"

project_id = "scg-l200-genai2"
location = "us-west1"

vertexai.init(project=project_id, location=location)

MODEL_ID = "gemini-1.5-pro-002"

model = GenerativeModel(
    MODEL_ID,
    system_instruction=[
        "You are a SQL expert.",
        "You are tasked with generating SQL that uses valid BigQuery syntax.",
    ],
)


def call_gemini(prompt_text):
    contents = [prompt_text]
    output = model.generate_content(contents)
    return output.text


def extract_sql(schema_dir):
    """Create an index, extract content of code/text files."""
    code_index = []
    bq_schema = {}
    for root, datasets, tables in os.walk(schema_dir):
        dataset_list = datasets
        for dataset in datasets:
            bq_schema[dataset] = {}
        for table in tables:
            table_name = table.split(".")[0]
            file_path = os.path.join(root, table)
            folder_path = os.path.dirname(file_path)
            dataset = os.path.basename(folder_path)
            file_type = m.identify_path(Path(file_path))
            if file_type.output.group in ("json", "code"):
                try:
                    with open(file_path) as f:
                        schema = json.load(f)
                        bq_schema[dataset][table_name] = schema
                except Exception:
                    pass
    return bq_schema, dataset_list


bq_schema, dataset_list = extract_sql(
    schema_dir)

with open("./erd_output.json", "r") as erd:
    erd_json = erd.read()

generated_query = call_gemini(
    prompts.query_generation(bq_schema, erd_json))

print(generated_query)

checked_query = call_gemini(
    prompts.query_check(generated_query, bq_schema, project_id, dataset_list))

print(checked_query)
