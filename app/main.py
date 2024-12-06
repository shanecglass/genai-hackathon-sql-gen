
from dataclasses import dataclass
import datetime
from langgraph.graph.message import add_messages

from model_calls import (
    function_coordination,
    # LangGraphApp,
    # react_agent
)

from model_mgmt import config
from operator import add
from typing import Annotated, Literal, TypedDict

from vertexai.generative_models import ChatSession, Content, Part
from model_mgmt import toolkit


import logging
import mesop as me
import os
from pathlib import Path
import time
import uuid


# flake8: noqa --E501


Role = Literal["user", "assistant"]
Selected_Model = config.Selected_Model
generative_model = config.generative_model
# endpoint_id = config.endpoint_id
# tool_node = toolkit.tool_node
session_id = str(uuid.uuid4())


@dataclass(kw_only=True)
class ChatMessage:
    """Chat message metadata."""

    role: Role = "user"
    content: str = ""
    edited: bool = False


@me.stateclass
class State:
    input: str
    output: list[ChatMessage]
    in_progress: bool
    message_count: int = 0
    reply_count: int = 0
    session_id: str = session_id
    is_loading: bool


class Chat_State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]
    user_email: str = ""
    user_id: int = ""


@me.page(
    security_policy=me.SecurityPolicy(
        dangerously_disable_trusted_types=True
    ),
    path="/",
    title="TravelChat",
    # on_load=on_load
)
def page():
    state = me.state(State)
    if state.is_loading:
        me.progress_spinner()
    global chat_session
    # Initialize chat session
    chat_session = generative_model.start_chat(response_validation=False)
    # react_agent.set_up()
    # Chat UI
    with me.box(style=_STYLE_APP_CONTAINER):
        me.text(_TITLE, type="headline-5", style=_STYLE_TITLE)
        with me.box(style=_STYLE_CHAT_BOX):
            for index, msg in enumerate(state.output):
                with me.box(
                    style=_make_style_chat_bubble_wrapper(msg.role),
                    key=f"msg-{index}",
                ):
                    if msg.role == _ROLE_ASSISTANT:
                        me.text(
                            _display_username(_BOT_USER_DEFAULT, msg.edited),
                            style=_STYLE_CHAT_BUBBLE_NAME,
                        )
                    with me.box(style=_make_chat_bubble_style(msg.role, msg.edited)):
                        if msg.role == _ROLE_USER:
                            me.text(msg.content,
                                    style=_STYLE_CHAT_BUBBLE_PLAINTEXT)
                        else:
                            me.markdown(msg.content)
                            with me.tooltip(message="Rewrite response"):
                                me.icon(icon="edit_note")

            if state.in_progress:
                with me.box(key="scroll-to", style=me.Style(height=250)):
                    pass
        with me.box(style=_STYLE_CHAT_INPUT_BOX):
            with me.box(style=me.Style(flex_grow=1)):
                me.input(
                    label=_LABEL_INPUT,
                    # Workaround: update key to clear input.
                    key=f"input-{len(state.output)}",
                    on_input=on_chat_input,
                    on_enter=on_click_submit_chat_msg,
                    style=_STYLE_CHAT_INPUT,
                )
            with me.content_button(
                color="primary",
                type="flat",
                disabled=state.in_progress,
                on_click=on_click_submit_chat_msg,
                style=_STYLE_CHAT_BUTTON,
            ):
                me.icon(
                    _LABEL_BUTTON_IN_PROGRESS if state.in_progress else _LABEL_BUTTON
                )
# Event Handlers


def on_chat_input(e: me.InputEvent):
    """Capture chat text input."""
    state = me.state(State)
    state.input = e.value


def on_click_submit_chat_msg(e: me.ClickEvent | me.InputEnterEvent):
    state = me.state(State)
    if state.in_progress or not state.input:
      return
    input = state.input
    state.input = ""

    yield

    submit_time = time.time()
    submit_time_bq_format = submit_time*pow(10, 6)
    submit_time_human = datetime.datetime.fromtimestamp(submit_time)
    logging.info(f"User message submitted as: {
                 input} at time: {submit_time_human}")
    state.message_count = state.message_count + 1

    output = state.output
    if output is None:
      output = []
    output.append(ChatMessage(role=_ROLE_USER, content=input))
    state.in_progress = True
    me.scroll_into_view(key="scroll-to")
    yield

    start_time = time.time()
    output_message = respond_to_chat(input, state.output)
    assistant_message = ChatMessage(role=_ROLE_ASSISTANT)
    output.append(assistant_message)
    state.output = output

    state.reply_count = state.reply_count + 1
    reply_time = time.time()
    response_time = reply_time - submit_time

    reply_time_human = datetime.datetime.fromtimestamp(reply_time)
    logging.info(f"Assistant message response sent as: {
                 output_message} at time: {reply_time_human}")
    logging.info(f"Response time in seconds: {response_time}")

    for content in output_message:
      assistant_message.content += content
      # TODO: 0.25 is an abitrary choice. In the future, consider making this adjustable.
      if (time.time() - start_time) >= 25:
        start_time = time.time()
    yield output_message
    state.in_progress = False
    yield

# Transform function for processing chat messages.


def respond_to_chat(input: str, history: list[ChatMessage]):
    state = me.state(State)
    chat_history = ""
    for h in history:
        chat_history += "<start_of_turn>{role}{content}<end_of_turn>".format(
            role=h.role, content=h.content)
    erd_json_file = Path(os.path.join(os.getcwd(), "app",
                         "model_mgmt", "erd_output.json"))
    with open(erd_json_file, "r") as f:
        erd_json = f.read()
        f.close()

    # message = {"messages": [("user", full_input)]}
    # result = react_agent.query(input=full_input)
    result = function_coordination(input, chat_session)

    return result

# Constants


_TITLE = "BQ SQL RAG"

_ROLE_USER = "user"
_ROLE_ASSISTANT = "assistant"
_ROLE_SYSTEM = "system"

_BOT_USER_DEFAULT = "bqsql-bot"

# Styles

_COLOR_BACKGROUND = "white"
_COLOR_CHAT_BUBBLE_YOU = "#F7F2FA"
_COLOR_CHAT_BUBBLE_BOT = "#E8DEF8"
_COLOR_CHAT_BUUBBLE_EDITED = "#FFD8E4"

_DEFAULT_PADDING = me.Padding.all(20)
_DEFAULT_BORDER_SIDE = me.BorderSide(
    width="1px", style="solid", color="#E8DEF8"
)

_LABEL_BUTTON = "send"
_LABEL_BUTTON_IN_PROGRESS = "pending"

_LABEL_INPUT = "Welcome to BigQuery SQL Bot!"

_STYLE_INPUT_WIDTH = me.Style(width="100%")

_STYLE_APP_CONTAINER = me.Style(
    background=_COLOR_BACKGROUND,
    display="flex",
    flex_direction="column",
    height="100%",
    margin=me.Margin.symmetric(vertical=0, horizontal="auto"),
    width="min(1024px, 100%)",
    box_shadow="0 3px 1px -2px #0003, 0 2px 2px #00000024, 0 1px 5px #0000001f",
    padding=me.Padding(top=20, left=20, right=20),
)
_STYLE_TITLE = me.Style(padding=me.Padding(left=10))
_STYLE_CHAT_BOX = me.Style(
    flex_grow=1,
    overflow_y="scroll",
    padding=_DEFAULT_PADDING,
    margin=me.Margin(bottom=20),
    border_radius="10px",
    border=me.Border(
        left=_DEFAULT_BORDER_SIDE,
        right=_DEFAULT_BORDER_SIDE,
        top=_DEFAULT_BORDER_SIDE,
        bottom=_DEFAULT_BORDER_SIDE,
    ),
)
_STYLE_CHAT_INPUT = me.Style(width="100%")
_STYLE_CHAT_INPUT_BOX = me.Style(
    padding=me.Padding(top=30), display="flex", flex_direction="row"
)
_STYLE_CHAT_BUTTON = me.Style(margin=me.Margin(top=8, left=8))
_STYLE_CHAT_BUBBLE_NAME = me.Style(
    font_weight="bold",
    font_size="12px",
    padding=me.Padding(left=15, right=15, bottom=5),
)
_STYLE_CHAT_BUBBLE_PLAINTEXT = me.Style(
    margin=me.Margin.symmetric(vertical=15))


def _make_style_chat_bubble_wrapper(role: Role) -> me.Style:
    """Generates styles for chat bubble position.

    Args:
        role: Chat bubble alignment depends on the role
    """
    align_items = "end" if role == _ROLE_USER else "start"
    return me.Style(
        display="flex",
        flex_direction="column",
        align_items=align_items,
    )


def _make_chat_bubble_style(role: Role, edited: bool) -> me.Style:
    """Generates styles for chat bubble.

    Args:
        role: Chat bubble background color depends on the role
        edited: Whether chat message was edited or not.
    """
    background = _COLOR_CHAT_BUBBLE_YOU
    if role == _ROLE_ASSISTANT:
        background = _COLOR_CHAT_BUBBLE_BOT
    if edited:
        background = _COLOR_CHAT_BUUBBLE_EDITED

    return me.Style(
        width="80%",
        font_size="13px",
        background=background,
        border_radius="15px",
        padding=me.Padding(right=15, left=15, bottom=3),
        margin=me.Margin(bottom=10),
        border=me.Border(
            left=_DEFAULT_BORDER_SIDE,
            right=_DEFAULT_BORDER_SIDE,
            top=_DEFAULT_BORDER_SIDE,
            bottom=_DEFAULT_BORDER_SIDE,
        ),
    )


def _display_username(username: str, edited: bool = False) -> str:
    """Displays the username

    Args:
        username: Name of the user
        edited: Whether the message has been edited.
    """
    edited_text = " (edited)" if edited else ""
    return username + edited_text
