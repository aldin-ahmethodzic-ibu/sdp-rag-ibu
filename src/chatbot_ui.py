import os
import streamlit as st
import random
import time
import hmac
from dotenv import load_dotenv
from src.chatbot import Chatbot
import string

load_dotenv()

STREAMLIT_PASSWORD = os.getenv("STREAMLIT_PASSWORD")


def generate_random_string(length=8):
    """Generate a random string of letters and digits."""
    characters = string.ascii_letters + string.digits
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string


def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], STREAMLIT_PASSWORD):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    # Return True if the password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show input for password.
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False


if not check_password():
    st.stop()  # Do not continue if check_password is not True.


# Streamed response emulator
def response_generator(prompt):

    answer = st.session_state.chatbot.get_answer(prompt, st.session_state.session_id)
    store_to_txt()

    for word in answer.split():
        yield word + " "
        time.sleep(0.05)


def store_to_txt():
    history = st.session_state.chatbot.sessions[st.session_state.session_id].conversation_history()

    # Merge the conversation history into a single string
    conversation_history_text = '\n\n'.join([
        f'{message["role"]}: {message["content"]}' for message in history
    ])

    with open(st.session_state.session_id + '.txt', 'w') as file:
        file.write(conversation_history_text)


st.title("IBU AI Assistant")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.chatbot = Chatbot()
    st.session_state.session_id = generate_random_string()

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("Type your query here..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        response = st.write_stream(response_generator(prompt))
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})