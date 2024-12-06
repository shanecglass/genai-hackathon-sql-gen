# flake8: noqa --E501

import bigframes as bf
import bigframes.pandas as bpd
import json
import os
import pickle
import app.model_mgmt.src.prompts as prompts
import vertexai

from datetime import datetime, timezone
from google.cloud import bigquery
from json_repair import repair_json
from pathlib import Path
from src import erd, schema
from vertexai.generative_models import (
    GenerativeModel,
)

project_id = "scg-l200-genai2"
location = "us-west1"

vertexai.init(project=project_id, location=location)

MODEL_ID = "gemini-1.5-pro-002"

model = GenerativeModel(
    MODEL_ID,
    system_instruction=[
        "You are a coding expert.",
        "Your mission is to answer all code related questions with given context and instructions.",

    ],
    generation_config={"response_mime_type": "application/json"},
)

local_dir = os.getcwd()
schema_folder = Path(os.path.join(local_dir, "schemas"))
if schema_folder.exists():
    print(f"{schema_folder} already exists")
else:
    schema_folder.mkdir(parents=True, exist_ok=True)
    print(f"{schema_folder} created")


def bf_call(query, project_id=project_id, location=location):
    # Create BigFrames session and set location
    bpd.options.bigquery.project = project_id
    bpd.options.bigquery.location = location

    query_response_json = bpd.read_gbq(
        query).to_dict(orient="records")

    # Close BigFrames session so location can be changed if needed
    bpd.close_session()
    return query_response_json


def erd_request(purpose: str):
    project_queries = bf_call(erd.query_text)[0]
    prompt = prompts.template(project_queries, purpose)
    contents = [prompt]
    output = model.generate_content(contents)
    cwd = os.getcwd()
    if purpose == "json":
        output_path = Path(os.path.join(cwd, "erd_output.json"))
        response = repair_json(output.text)
    if purpose == "summary":
        output_path = Path(os.path.join(cwd, "erd_summary.md"))
        response = output.text
    with open(output_path, "w") as file:
        file.write(response)


def get_table_schemas(schema_folder=schema_folder, project_id=project_id):
    client = bigquery.Client()
    datasets = list(client.list_datasets())  # Make an API request.
    if datasets:
        for dataset in datasets:
            dataset = client.get_dataset(f"{project_id}.{dataset.dataset_id}")
            dataset_id = dataset.dataset_id
            folder_path = Path(os.path.join(schema_folder, dataset_id))
            if folder_path.exists():
                print(f"{folder_path} already exists")
            else:
                folder_path.mkdir(parents=True, exist_ok=True)
                print(f"{folder_path} created")
            dataset_location = dataset.location
            table_list = client.list_tables(f"{project_id}.{dataset_id}")
            if table_list:
                for table in table_list:
                    table = client.get_table(
                        f"{project_id}.{dataset_id}.{table.table_id}")
                    table_id = table.table_id
                    table_last_modified = table.modified
                    table_schema_file = Path(os.path.join(
                        folder_path, f"{table_id}.json"))
                    last_updated_file = Path(os.path.join(
                        folder_path, f"last_updated.pickle"))
                    if last_updated_file.exists():
                        with open(last_updated_file, 'rb') as f:
                            last_local_update = pickle.load(f)
                    else:
                        last_local_update = datetime.now(tz=timezone.utc)
                    if table_last_modified < last_local_update and table_schema_file.exists():
                        print(
                            f"{table_id} not changed since last local schema refresh")
                        continue
                    else:
                        table_schema_query = schema.query_text(
                            project_id, dataset_id, table_id)
                        table_schema = bf_call(
                            table_schema_query, project_id, location=dataset_location)
                        with open(table_schema_file, "w") as file:
                            file.write(json.dumps(table_schema, indent=4))
                            print(f"{table_id} schema written to {
                                table_schema_file}")
                        last_updated_file = Path(os.path.join(
                            folder_path, f"last_updated.pickle"))
                        with open(last_updated_file, 'wb') as f:
                            last_updated_time = datetime.now(tz=timezone.utc)
                            pickle.dump(last_updated_time, f)
            else:
                print(
                    f"Dataset {dataset.dataset_id} does not contain any tables.")
    else:
        print(f"Project {project_id} does not contain any datasets.")


purposes = ["json", "summary"]

for purpose in purposes:
    erd_request(purpose)
    print(f"ERD {purpose} file written")

get_table_schemas()
print("Schema files updated")
