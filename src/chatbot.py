from src.context_retrieval import ContextRetrieval
from src.conversation_session import ConversationSession
from core.config import GPT_MODEL, NUM_OF_CONTEXT_CHUNKS
from openai import OpenAI
from typing import List, Dict
from core.logger import get_logger

logger = get_logger(__name__, log_file="chatbot.log")

class Chatbot:
    def __init__(self):
        """
        Initialize the chatbot with context retrieval, OpenAI client, and sessions.
        """
        try:
            logger.info("Initializing Chatbot...")
            self.context_retrieval = ContextRetrieval()
            self.openai_client = OpenAI()
            self.sessions = {}
            logger.info("Chatbot initialized successfully.")
        except Exception as e:
            logger.exception("Failed to initialize Chatbot.")
            raise e

    @staticmethod
    def create_prompt(question: str, context: List[Dict], conversation_history: List[dict]) -> List[Dict]:
        """
        Create a prompt for the chatbot to answer a question.

        :param question: The question to be answered.
        :param context:
            The context to be used for the question. This is a list of retrieved chunks from the Vespa AI.
        :param conversation_history:
            The conversation history of the user for the session. This is a list of dictionaries with the keys 'role'
            and 'content', as per OpenAI's required format.
        :return: The prompt for the chatbot to answer the question, in the same format as conversation_history.
        """
        try:
            logger.info("Creating prompt for the chatbot.")
            logger.debug(f"Question: {question}")
            logger.debug(f"Retrieved context chunks: {len(context)}")
            logger.debug(f"Conversation history: {len(conversation_history)} messages")

            # Merge the context chunks into a single string separated by newlines
            context_chunks = [chunk["fields"]["chunk_text"] for chunk in context]
            merged_context_chunks = '\n\n'.join(context_chunks)
            logger.debug(f"Merged context chunks: {merged_context_chunks}")

            # Add the last question to conversation history
            conversation_history.append({"role": "user", "content": question})
            logger.debug(f"Updated conversation history: {conversation_history}")

            # Merge the conversation history into a single string
            conversation_history_text = '\n'.join([
                f'{message["role"]}: {message["content"]}' for message in conversation_history
            ])
            logger.debug(f"Merged conversation history: {conversation_history_text}")

            messages = [
                {
                    "role": "system",
                    "content":
                        "You are an AI Assistant for International Burch University (IBU). Your role is to provide accurate and precise answers "
                        "based on the provided context chunks if possible. You are only allowed to discuss topics related to International Burch University, "
                        "such as its academic programs, faculties, events, application procedures, and other university-related questions. "
                        "If the requested information is not in the provided context, respond with 'I'm sorry, but I cannot answer that based on the given information.' "
                        "You must not make up answers. Here is the context and conversation history:"
                },
                {
                    "role": "system",
                    "content": f"Context chunks:\n\n{merged_context_chunks}"
                },
                {
                    "role": "system",
                    "content": f"Conversation history:\n\n{conversation_history_text}"
                }
            ]

            logger.info("Prompt created successfully.")
            return messages
        except Exception as e:
            logger.exception("Error creating prompt for the chatbot.")
            raise e

    def get_answer(self, question: str, session_id: str) -> str:
        """
        Get the answer to a question, using the context retrieval system.

        :param question: The question to be answered.
        :param session_id: The session ID of the user to retrieve the chat history.

        :return: The answer to the question.
        """
        try:
            logger.info(f"Received question: '{question}' for session_id: {session_id}")

            # Check if session exists, and create if not
            if session_id not in self.sessions:
                logger.info(f"Creating new session for session_id: {session_id}")
                self.sessions[session_id] = ConversationSession(session_id)

            # Rephrase the question
            rephrased_question = self.rephrase_question(question, session_id)
            logger.debug(f"Rephrased question: '{rephrased_question}'")

            # Retrieve context chunks
            logger.info(f"Retrieving context for rephrased question: '{rephrased_question}'")
            context = ContextRetrieval().semantic_search(
                collection_name='chunks', query=rephrased_question, hits=NUM_OF_CONTEXT_CHUNKS
            )
            logger.debug(f"Retrieved {len(context)} context chunks.")

            # Construct a prompt with conversation history and context
            prompt = self.create_prompt(question, context, self.sessions[session_id].conversation_history())
            logger.info("Prompt created successfully.")

            # Get the answer from the ChatGPT API
            logger.info("Sending prompt to ChatGPT API.")
            response = self.openai_client.chat.completions.create(model=GPT_MODEL, messages=prompt)
            answer = response.choices[0].message.content
            logger.info("Received response from ChatGPT API.")

            # Update the session with the new answer
            self.sessions[session_id].update_session(answer)
            logger.info(f"Updated session history for session_id: {session_id}")

            return answer
        except Exception as e:
            logger.exception(f"Error in get_answer for session_id: {session_id}: {str(e)}")
            raise e

    def rephrase_question(self, question: str, session_id: str) -> str:
        """
        Rephrase the question to improve context retrieval by making it more explicit. For instance, replacing pronouns
        with their respective technical terms or clarifying implicit references using the conversation history.

        :param question: The original question to be rephrased.
        :param session_id: The session ID of the user to retrieve the chat history.

        :return: Rephrased question.
        """
        try:
            logger.info(f"Rephrasing question for session_id: {session_id}")
            logger.debug(f"Original question: '{question}'")

            # Retrieve the conversation history for the session
            conversation_history = self.sessions[session_id].conversation_history()
            logger.debug(f"Conversation history for session_id {session_id}: {conversation_history}")

            # Merge the conversation history into a single string
            conversation_history_text = '\n'.join([
                f'{message["role"]}: {message["content"]}' for message in conversation_history
            ])
            logger.debug(f"Merged conversation history: {conversation_history_text}")

            # Prepare the prompt for the OpenAI API
            prompt = [
                {
                    "role": "system",
                    "content":
                        "You are an AI Assistant for International Burch University (IBU). Your task is to rephrase user queries to make them "
                        "more explicit and clear, focusing only on university-related information. Use the provided conversation history "
                        "to replace pronouns, vague terms, or implicit references with specific terms related to IBU—such as academic programs, faculties, departments, events, or procedures. "
                        "Do not add unrelated or fabricated information. If clarification is not possible, return the query unchanged.\n\n"

                        "Here is an example:\n\n"

                        "Conversation history:\n"
                        "user: How do I apply?\n"
                        "assistant: You can apply through the university's online application portal.\n\n"
                        "user: What documents do I need?\n"
                        "Query to be rephrased: What documents do I need for the online application to International Burch University?\n\n"

                        "Now, use the conversation history and the provided query to rephrase the following question explicitly."
                },
                {
                    "role": "user",
                    "content": f"Conversation history:\n{conversation_history_text}\n\n"
                               f"Query to be rephrased: {question}\n"
                }
            ]
            logger.info("Prepared prompt for OpenAI API.")

            # Call the OpenAI API to get the rephrased question
            logger.info("Sending prompt to OpenAI API for rephrasing.")
            response = self.openai_client.chat.completions.create(model=GPT_MODEL, messages=prompt)
            rephrased_question = response.choices[0].message.content.strip()
            logger.info(f"Rephrased question received: '{rephrased_question}'")

            return rephrased_question
        except Exception as e:
            logger.exception(f"Error in rephrasing question for session_id {session_id}: {str(e)}")
            raise e

    def remove_session(self, session_id: str):
        """
        Remove a session from the chatbot.

        :param session_id: The session ID to be removed.
        """
        try:
            logger.info(f"Attempting to remove session with ID: {session_id}")

            if session_id in self.sessions:
                del self.sessions[session_id]
                logger.info(f"Session with ID {session_id} successfully removed.")
            else:
                logger.error(f"Session with ID {session_id} does not exist.")
                raise Exception(f"Session with ID {session_id} does not exist.")
        except Exception as e:
            logger.exception(f"Error removing session with ID {session_id}: {str(e)}")
            raise e