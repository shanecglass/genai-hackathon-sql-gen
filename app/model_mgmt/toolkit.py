# flake8: noqa --E501


import bigframes

import bigframes.pandas as bpd
import json
import magika
import os
import pandas as pd
import pickle
import vertexai
# from langchain_core.tools import tool


from datetime import datetime, timezone
from google.cloud import bigquery
from json_repair import repair_json
from model_mgmt.src import prompts, instructions
from model_mgmt.src.sql import erd, schema
from pathlib import Path
from vertexai.generative_models import (
    FunctionDeclaration,
    GenerationConfig,
    GenerativeModel,
    Tool
)


# import testing as testing
# project_id = testing.project_id
# location = testing.location


# project_id = os.environ.get("PROJECT_ID")
# location = os.environ.get("LOCATION")
project_id = "scg-l200-genai2"
location = "us-west1"

# vertexai.init(project=project_id, location=location)
PRO_MODEL_ID = "gemini-1.5-pro-002"
FLASH_MODEL_ID = "gemini-1.5-flash-002"
system_instructions = instructions.system_instructions


local_dir = os.path.join(os.getcwd(), "app", "model_mgmt")
schema_dir = Path(os.path.join(local_dir, "schemas"))
if schema_dir.exists():
    print(f"{schema_dir} already exists")
else:
    schema_dir.mkdir(parents=True, exist_ok=True)
    print(f"{schema_dir} created")


def bf_call(query, project_id=project_id, location=location):
    # Create BigFrames session and set location
    bpd.options.bigquery.project = project_id
    bpd.options.bigquery.location = location

    query_response_json = bpd.read_gbq(
        query).to_dict(orient="records")

    # Close BigFrames session so location can be changed if needed
    bpd.close_session()
    return query_response_json


def gemini_call(model_id, prompt_text, system_instructions=system_instructions):
    model = GenerativeModel(
        model_id,
        system_instruction=system_instructions,
    )
    contents = [prompt_text]
    output = model.generate_content(contents)
    return output.text


def erd_request(purpose: str, system_instructions: list = system_instructions):
    system_instructions = system_instructions[0]
    system_instructions += "Your mission is to identify and describe relationships between tables and datasets in BigQuery using the given context and instructions."
    model = GenerativeModel(
        PRO_MODEL_ID,
        system_instruction=system_instructions
    )
    print(os.getcwd())
    project_queries = bf_call(erd.query_text)[0]
    prompt = prompts.erd_template(project_queries, purpose)
    contents = [prompt]
    output = model.generate_content(contents)
    if purpose == "json":
        output_path = Path(os.path.join(local_dir, "src", "erd_output.json"))
        response = repair_json(output.text)
    if purpose == "summary":
        output_path = Path(os.path.join(local_dir, "src", "erd_summary.md"))
        response = output.text
    with open(output_path, "w") as f:
        f.write(response)
        f.close()
    return response


def generate_erd():
    """
    Generate an entity relationship diagram (ERD) using the query history in a given project.
    Used to improve the quality of sql generation across the project.

    Args:

    Returns:
       erd_dict (dict): A dictionary with the ERD in both JSON and Markdown (summary) format
    """
    erd_dict = {}
    purposes = ["json", "summary"]

    for purpose in purposes:
        response = erd_request(purpose)
        print(f"ERD {purpose} file written")
        erd_dict[purpose] = response

    return erd_dict["json"]


def get_table_schemas(schema_folder=schema_dir,
                      project_id=project_id):
    """
    Generate schema files for all tables in BigQuery datasets within the given project
    Used to improve the quality of sql generation across the project.


    Args:
        schema_folder (str): The directory with a folder for each BigQuery dataset that contain schema files for each table
        project_id (str): A string the project ID for the relevant project

    Returns:
       None
    """
    client = bigquery.Client()
    datasets = list(client.list_datasets())  # Make an API request.
    datasets_dict = {}
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
                    table_dict = {}
                    table = client.get_table(
                        f"{project_id}.{dataset_id}.{table.table_id}")
                    table_id = table.table_id
                    table_last_modified = table.modified
                    table_schema_file = Path(os.path.join(
                        folder_path, f"{table_id}.json"))
                    table_dict[table_id] = str(table_schema_file)
                    last_updated_file = Path(os.path.join(
                        folder_path, f"last_updated.pkl"))
                    if last_updated_file.exists():
                        with open(last_updated_file, 'rb') as f:
                            last_local_update = pickle.load(f)
                            f.close()
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
                        with open(table_schema_file, "w") as f:
                            f.write(json.dumps(table_schema, indent=4))
                            print(f"{table_id} schema written to {
                                table_schema_file}")
                            f.close()
                        with open(last_updated_file, 'wb') as f:
                            last_updated_time = datetime.now(tz=timezone.utc)
                            pickle.dump(last_updated_time, f)
                            f.close()
            else:
                print(
                    f"Dataset {dataset.dataset_id} does not contain any tables.")
    else:
        print(f"Project {project_id} does not contain any datasets.")


def extract_sql(schema_dir):
    """
    Load BigQuery table schemas into a nested dictionary to make it available for models to analyze

    Args:
        schema_dir (str): The root directory where table schemas are stored

    Returns:
       bq_schema (dict): A nested dictionary containing the table schema for each table in each dataset within a given project
    """
    m = magika.Magika()

    bq_schema = {}
    for root, datasets, tables in os.walk(schema_dir):
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
                        f.close()
                except Exception:
                    pass
    output_file = Path(os.path.join(schema_dir, "bq_schema_project.pkl"))
    with open(output_file, "wb") as f:
        pickle.dump(bq_schema, f)
        f.close()
    return bq_schema


def rag_to_run():
    generate_erd()
    get_table_schemas()
    extract_sql(schema_dir)


def generate_sql(request: str, project_id: str = project_id) -> str:
    """
    Generate a valid BigQuery SQL query that fulfills the user request

    Args:
        request (str): The task that defines the query output
        project_id (str): A string the project ID for the relevant project

    Returns:
       json: A JSON object containing a BigQuery SQL query that fulfills the user request and an explanation of why this query was generated
    """
    dataset_list = []
    for x, datasets, y in os.walk(schema_dir):
        for dataset in datasets:
            dataset_list.append(dataset)
    print(dataset_list)
    bq_schema = extract_sql(schema_dir)
    erd_json_path = Path(os.path.join(local_dir, "src", "erd_output.json"))
    with open(erd_json_path, "r") as f:
        erd_json = json.load(f)
    generated_query = gemini_call(FLASH_MODEL_ID,
                                  prompts.query_generation(request, bq_schema, erd_json))
    print("First query: " + generated_query)
    output = {}
    output['query_and_explain'] = generated_query
    confirmed_query = gemini_call(FLASH_MODEL_ID,
                                  prompts.query_check(generated_query, bq_schema, erd_json, project_id, dataset_list))
    print("Second query: " + confirmed_query)
    output['query'] = confirmed_query
    return output


generate_sql_func = FunctionDeclaration(
    name="generate_sql",
    description="""
    Generate a valid BigQuery SQL query that fulfills the user request

    Args:
        request (str): The task that defines the query output
        project_id (str): The project ID for the relevant Google Cloud project

    Returns:
       checked_query (str): A BigQuery SQL query that fulfills the user request
    """,
    parameters={
        "type": "object",
        "properties": {
            "request": {"type": "string", "description": "The task that defines the query output"},
            "project_id": {"type": "string", "description": "The project ID for the relevant Google Cloud project"},
        },
        "required": ["request", "project_id"],
    },
)

sql_tool_list = [
    generate_sql,
]

sql_gemini_tool_list = [
    generate_sql_func,
]

sql_gemini_tools = Tool(
    function_declarations=sql_gemini_tool_list
)


all_tools = []
for tool in sql_tool_list:
    all_tools.append(tool)
# for tool in weather_tool_list:
#     all_tools.append(tool)


# florence_tool_node = ToolNode(florence_tool_list)
# weather_tool_node = ToolNode(weather_tool_list)
