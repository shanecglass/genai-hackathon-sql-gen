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


# from json_repair import repair_json
# from model_mgmt.src import prompts, instructions
# from model_mgmt.src.sql import erd, schema
from pathlib import Path


local_dir = os.path.join(os.getcwd(), "app", "model_mgmt")
schema_dir = Path(os.path.join(local_dir, "schemas"))

print(dataset_list)
