# flake8: noqa --E501

from google.protobuf import json_format
from google.protobuf.struct_pb2 import Value
from model_mgmt import config, toolkit

from json_repair import repair_json
from vertexai.generative_models import Content, GenerationResponse, Part, ChatSession

import logging
from typing import Any
import json
# from IPython.display import Image, display


from langchain_core.runnables.graph import CurveStyle, MermaidDrawMethod, NodeStyles


import logging
from typing import Any
import json


project_id = config.project_id
location = config.location
project_number = config.project_number
model_to_call = config.generative_model


def get_chat_response(
        input: str,
        chat_session,
        function_response: bool = False,
) -> str:
    if type(input) == Content:
        contents = input
    else:
        contents = Content(role="user", parts=[
                           Part.from_text(input)])

    response = chat_session.send_message(contents, stream=False)
    return response


def parse_generate_sql_func(
    input_text,  # Original user input
    func_output,
    chat_session
):
    try:
       print(func_output)
       request = func_output["request"]
       print("Request:" + request)
       project_id = func_output["project_id"]
       print("Project:" + project_id)

    except (IndexError, json.JSONDecodeError):
        print("it's broke Jim")

    print("running_query_generation")
    query = toolkit.generate_sql(request=request, project_id=project_id)
    print(query)
    output = Part.from_function_response(
        name="generate_sql", response={"content": query})
    return output


def function_coordination(input: str, chat_session) -> str:
    model_instructions = " You must include the SQL text in the response if a function call is made."
    full_input = input.strip() + model_instructions
    input_part = Part.from_text(text=full_input)
    user_input_content = Content(
        role="user", parts=[input_part])
    output = get_chat_response(user_input_content, chat_session)
    if isinstance(output.candidates, list):
        output_candidate = output.candidates[0]
        if True in (output_candidate.function_calls is None, output_candidate.function_calls == []):
            text_response = output_candidate.text
        else:
            function_responses = []
            function_responses.append(input_part)
            for function_call in output_candidate.function_calls:
                if function_call.name == "generate_sql":
                    print("generate_sql function call found")
                    func_output = function_call.args
                    response = parse_generate_sql_func(
                        full_input, func_output, chat_session)
                    function_responses.append(response)
            # Create Content with function_responses
            if function_responses:
                # Send function responses in a single turn
                function_response_content = Content(parts=function_responses)
                response = get_chat_response(
                    function_response_content, chat_session=chat_session)
                text_response = response.candidates[0].text
            else:
                text_response = output_candidate.text
    else:
        text_response = output_candidate.text

    return text_response


# prompt_template = {
#     "user_input": lambda x: x["input"],
#     "agent_scratchpad": lambda x: format_to_tool_messages(x["intermediate_steps"]),
# } | ChatPromptTemplate.from_messages([
#     ("system", instructions.system_instructions),
#     ("placeholder", "{history}"),
#     ("user", "{user_input}"),
#     ("placeholder", "{agent_scratchpad}"),
# ])


# react_agent = reasoning_engines.LangchainAgent(
#     model=config.model_name,
#     prompt=prompt_template,
#     tools=toolkit.sql_tool_list,
# )
# img = react_agent.get_graph().draw_mermaid_png(
#     draw_method=MermaidDrawMethod.API,
# )
# with open("agent_graph.png", "wb") as f:
#     f.write(img)
