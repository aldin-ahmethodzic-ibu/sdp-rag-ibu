from datetime import datetime


class ConversationSession:

    def __init__(self, session_id: str):
        self.messages = []
        self.session_id = session_id
        self.updated_at = datetime.now()

    def update_session(self, answer: str):
        """
        Update the session with the chatbot's response. Also updates the timestamp of the session.

        :param answer: The answer given by the chatbot.
        """

        self.messages.extend([
            {"role": "assistant", "content": answer}
        ])
        self.updated_at = datetime.now()

    def conversation_history(self):
        """
        Get the conversation history for the user.

        :return: The conversation history for the user.
        """
        return self.messages