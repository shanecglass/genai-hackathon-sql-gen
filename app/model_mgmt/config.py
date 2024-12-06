from google.cloud import aiplatform
from vertexai.generative_models import (
    GenerationConfig,
    GenerativeModel,
    HarmCategory,
    HarmBlockThreshold,
    ToolConfig
)

import logging
import model_mgmt.src.instructions as instructions
import model_mgmt.primary as primary
import model_mgmt.testing as testing
import model_mgmt.toolkit as toolkit
import os
import vertexai

# flake8: noqa --E501

# project_number = os.environ.get("PROJECT_NUMBER")
# gemma_endpoint_id = os.environ.get("GEMMA_ENDPOINT_ID")
# gemini_tuned_endpoint_id = os.environ.get("GEMINI_TUNED_ENDPOINT_ID")
# project_id = os.environ.get("PROJECT_ID")
# location = os.environ.get("LOCATION")

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


project_number = testing.project_number
project_id = testing.project_id
location = testing.location

configured_model = primary.configured_model
vertexai.init(project=project_id, location=location)

Valid_Models = {
    # Define the list of valid models.
    # This is used to check if the selected model defined above is valid
    # Only change this if you have added support for a new model
    "GEMINI_FLASH": "gemini-1.5-flash-002",
    "GEMMA": "gemma2-9b-it",
    "GEMINI_PRO_TUNED": "gemini-1.0-pro-002_tuned",
}

# Sets a default value for the chat to use in case an invalid select is made
default_model = Valid_Models["GEMINI_FLASH"]


def model_check(
        ##
        # Check to see if the selected_model is a valid option.
        # If it is, the chat will use selected_model
        # If not, the chat will use default_model and log an error
        ##
    Valid_Models: dict = Valid_Models,
    configured_model: str = configured_model,
    default_model: str = default_model
) -> str:
    try:
        configured_model in Valid_Models.keys()
        Model = Valid_Models[configured_model]
        logging.info(f'Selected model for this chat is {Model}')
        print(f'Selected model for this chat is {Model}')
    except ValueError:
        logging.info(ValueError)
        Model = default_model
        logging.info(f'''
                     Invalid model selection in `primary.py` file.
                     Defaulting to {Model}
                    ''')
    return (Model)


Selected_Model = model_check()


gen_config = {
    "temperature": 0.2,
    "top_p": .1,
    "top_k": 1,
    "candidate_count": 1,
    "max_output_tokens": 1048,
}


generation_config = GenerationConfig(
    temperature=gen_config['temperature'],
    # top_p=gen_config['top_p'],
    # top_k=gen_config['top_k'],
    # candidate_count=gen_config['candidate_count'],
    # max_output_tokens=gen_config['max_output_tokens'],
)


safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
}


def model_to_call(Selected_Model=Selected_Model):
    model_id = Selected_Model
    model_to_call = GenerativeModel(
        model_name=model_id,
        generation_config=generation_config,
        # safety_settings=safety_settings,
        system_instruction=instructions.system_instructions,
        tools=[toolkit.sql_gemini_tools],
        tool_config=ToolConfig(
            function_calling_config=ToolConfig.FunctionCallingConfig(
                # ANY mode forces the model to predict only function calls
                mode=ToolConfig.FunctionCallingConfig.Mode.AUTO,
                # Allowed function calls to predict when the mode is ANY. If empty, any  of
                # the provided function calls will be predicted.
            )
        ))
    return model_to_call, model_id


generative_model, model_name = model_to_call(Selected_Model)


# def agent_model_to_call(project_id: str = project_id, location: str = location, model_name: str = model_name):
#     model = ChatVertexAI(
#         model=model_name,
#         temperature=gen_config["temperature"],
#         safety_settings=safety_settings,
#         max_output_tokens=gen_config["max_output_tokens"],
#         project=project_id,
#         location=location,
#     )
#     return model


# agent_chat_session = agent_model_to_call()
