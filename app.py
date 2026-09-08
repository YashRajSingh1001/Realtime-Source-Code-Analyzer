from langchain.vectorstores import Chroma
from src.helper import load_embedding, repo_ingestion, clear_repo
from src.store_index import create_index, PERSIST_DIR
from dotenv import load_dotenv
import os
from flask import Flask, request, jsonify, render_template
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationSummaryMemory

app = Flask(__name__)

load_dotenv()

embeddings = load_embedding()

#The retriever and the conversation memory are rebuilt whenever a new repo
#is ingested. Holding them in a module-level dict keeps the swap in one place
#instead of scattering `global` statements through the routes.
state = {}


def build_qa_chain():
    """Construct a fresh chain bound to whatever is currently in the index.

    This has to run again after every ingestion. The retriever captures the
    collection it was created from, so a chain built at startup keeps
    answering from the old repo even after the index on disk is replaced.
    """
    vectordb = Chroma(persist_directory=PERSIST_DIR,
                      embedding_function=embeddings)
    llm = ChatOpenAI()
    #a new memory too, so questions about the previous repo do not leak
    #into the summary of the new conversation
    memory = ConversationSummaryMemory(llm=llm,
                                       memory_key="chat_history",
                                       return_messages=True)
    state["qa"] = ConversationalRetrievalChain.from_llm(
        llm,
        retriever=vectordb.as_retriever(search_type="mmr",
                                        search_kwargs={"k": 8}),
        memory=memory,
    )


build_qa_chain()


@app.route('/', methods=["GET", "POST"])
def index():
    return render_template('index.html')


@app.route('/chatbot', methods=["GET", "POST"])
def gitRepo():
    if request.method != 'POST':
        return jsonify({"response": "Send a repository URL with POST."})

    repo_url = request.form.get('question', '').strip()
    if not repo_url:
        return jsonify({"response": "Please provide a GitHub repository URL."})

    try:
        repo_ingestion(repo_url)
        create_index()
        #point the chain at the repo that was just indexed
        build_qa_chain()
    except Exception as exc:
        return jsonify({"response": f"Could not analyze that repository: {exc}"})

    return jsonify({"response": f"Indexed {repo_url}. Ask away."})


@app.route("/get", methods=["GET", "POST"])
def chat():
    msg = request.form["msg"]

    if msg.strip().lower() == "clear":
        clear_repo()
        return "Cleared the analyzed repository."

    try:
        result = state["qa"](msg)
    except Exception as exc:
        return f"Something went wrong answering that: {exc}"

    return str(result["answer"])


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    #debug must stay off by default. Werkzeug's debugger runs arbitrary
    #python through the browser, which is not something to expose on a
    #public URL - opt in locally with FLASK_DEBUG=1 instead.
    debug = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=port, debug=debug)
