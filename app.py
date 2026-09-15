import streamlit as st
from dotenv import load_dotenv

from chatbot import LangChainChatbot


load_dotenv()


# Page Configuration

st.set_page_config(
    page_title="LangChain Smart Chatbot",
    page_icon=None,
    layout="centered",
)


 
# Application Header
 
st.title("LangChain Smart Chatbot")
st.caption(
    "RunnableBranch + RunnableParallel + Pydantic Structured Output"
)


# Sidebar
 
with st.sidebar:
    st.header("Settings")

    provider = st.selectbox(
        "LLM Provider",
        ["groq", "openai", "gemini"],
        index=0,
    )

    st.info(
        "Set the corresponding API key in your .env file. "
        "See .env.example for the required variable names."
    )

    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()

    st.subheader("Pipeline")

    st.markdown(
        """
        **1. RunnableBranch**

        Routes the user question to one of three specialized
        pipelines: Programming, Mathematics, or General.

        **2. RunnableParallel**

        Generates multiple outputs from the routed response:
        Answer, Summary, Keywords, and Follow-up Question.

        **3. Pydantic Structured Output**

        Combines and validates the generated information using
        the `ChatResponse` Pydantic model.
        """
    )


 
# Session State
 

if "messages" not in st.session_state:
    st.session_state.messages = []


if (
    "chatbot" not in st.session_state
    or st.session_state.get("provider") != provider
):
    try:
        st.session_state.chatbot = LangChainChatbot(
            provider=provider
        )
        st.session_state.provider = provider

    except Exception as e:
        st.session_state.chatbot = None

        st.error(
            f"Could not initialize the {provider} LLM: {e}"
        )


 
# Display Chat History
 

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])

        if (
            message["role"] == "assistant"
            and "structured" in message
        ):
            with st.expander(
                "Structured Output (Pydantic ChatResponse)"
            ):
                st.json(message["structured"])


 
# Chat Input
 

user_input = st.chat_input(
    "Ask a programming, mathematics, or general question..."
)


if user_input:

    # Store user message
    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_input,
        }
    )

    with st.chat_message("user"):
        st.markdown(user_input)

    # Generate assistant response
    with st.chat_message("assistant"):

        if st.session_state.chatbot is None:

            st.error(
                "Chatbot is not initialized. "
                "Please check your API key and .env configuration."
            )

        else:

            with st.spinner("Processing your question..."):

                try:

                    result = st.session_state.chatbot.run(
                        user_input
                    )

                    structured = result["structured"]

                       
                    # Main Answer
                       

                    st.markdown(structured.answer)

                       
                    # Metadata
                       

                    col1, col2 = st.columns(2)

                    with col1:
                        st.metric(
                            "Category",
                            structured.category,
                        )

                    with col2:
                        st.metric(
                            "Confidence",
                            f"{structured.confidence:.2f}",
                        )

                       
                    # Summary
                       

                    st.markdown(
                        f"**Summary:** {structured.summary}"
                    )

                       
                    # Keywords
                       

                    if structured.keywords:

                        st.markdown(
                            "**Keywords:** "
                            + ", ".join(structured.keywords)
                        )

                       
                    # Follow-up Question
                       

                    if hasattr(
                        structured,
                        "follow_up_question",
                    ):
                        st.markdown(
                            "**Follow-up Question:** "
                            f"{structured.follow_up_question}"
                        )

                       
                    # Complete Pydantic Output
                       

                    with st.expander(
                        "Structured Output (Pydantic ChatResponse)"
                    ):
                        st.json(
                            structured.model_dump()
                        )

                    
                    # Store Assistant Message
                

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": structured.answer,
                            "structured": structured.model_dump(),
                        }
                    )

                except Exception as e:

                    st.error(
                        f"Something went wrong: {e}"
                    )
