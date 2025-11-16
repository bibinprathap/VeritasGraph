import gradio as gr
import os
import asyncio
import pandas as pd
import tiktoken
from dotenv import load_dotenv

from graphrag.query.indexer_adapters import read_indexer_entities, read_indexer_reports
from graphrag.query.structured_search.global_search.community_context import GlobalCommunityContext
from graphrag.query.structured_search.global_search.search import GlobalSearch
from graphrag.query.llm.oai.chat_openai import ChatOpenAI
from graphrag.query.llm.oai.typing import OpenaiApiType
from graphrag.query.question_gen.local_gen import LocalQuestionGen
from graphrag.query.context_builder.entity_extraction import EntityVectorStoreKey
from graphrag.query.indexer_adapters import (
    read_indexer_covariates,
    read_indexer_entities,
    read_indexer_relationships,
    read_indexer_reports,
    read_indexer_text_units,
)
from graphrag.query.input.loaders.dfs import (
    store_entity_semantic_embeddings,
)
from graphrag.query.llm.oai.embedding import OpenAIEmbedding
from graphrag.query.question_gen.local_gen import LocalQuestionGen
from graphrag.query.structured_search.local_search.mixed_context import (
    LocalSearchMixedContext,
)
from graphrag.query.structured_search.local_search.search import LocalSearch
from graphrag.vector_stores.lancedb import LanceDBVectorStore

load_dotenv('.env')
join = os.path.join

PRESET_MAPPING = {
    "Default": {
        "community_level": 2,
        "response_type": "Multiple Paragraphs"
    },
    "Detailed": {
        "community_level": 4,
        "response_type": "Multi-Page Report"
    },
    "Quick": {
        "community_level": 1,
        "response_type": "Single Paragraph"
    },
    "Bullet": {
        "community_level": 2,
        "response_type": "List of 3-7 Points"
    },
    "Comprehensive": {
        "community_level": 5,
        "response_type": "Multi-Page Report"
    },
    "High-Level": {
        "community_level": 1,
        "response_type": "Single Page"
    },
    "Focused": {
        "community_level": 3,
        "response_type": "Multiple Paragraphs"
    }
}

async def global_search(query, input_dir, community_level=2, temperature=0.5, response_type="Multiple Paragraphs"):
        api_key = os.environ["GRAPHRAG_API_KEY"]
        llm_model = os.environ["GRAPHRAG_LLM_MODEL"]
        api_base = os.environ["GRAPHRAG_LLM_API_BASE"]

        llm = ChatOpenAI(
            api_key=api_key,
            api_base=api_base,
            model=llm_model,
            api_type=OpenaiApiType.OpenAI,  
            max_retries=10,
        )

        token_encoder = tiktoken.get_encoding("cl100k_base")

        COMMUNITY_REPORT_TABLE = "create_final_community_reports"
        ENTITY_TABLE = "create_final_nodes"
        ENTITY_EMBEDDING_TABLE = "create_final_entities"
        
        entity_df = pd.read_parquet(join(input_dir, f"{ENTITY_TABLE}.parquet"))
        report_df = pd.read_parquet(join(input_dir, f"{COMMUNITY_REPORT_TABLE}.parquet"))
        entity_embedding_df = pd.read_parquet(join(input_dir, f"{ENTITY_EMBEDDING_TABLE}.parquet"))

        reports = read_indexer_reports(report_df, entity_df, community_level)
        entities = read_indexer_entities(entity_df, entity_embedding_df, community_level)

        context_builder = GlobalCommunityContext(
            community_reports=reports,
            entities=entities,
            token_encoder=token_encoder,
        )

        context_builder_params = {
            "use_community_summary": False,  # False means using full community reports. True means using community short summaries.
            "shuffle_data": True,
            "include_community_rank": True,
            "min_community_rank": 0,
            "community_rank_name": "rank",
            "include_community_weight": True,
            "community_weight_name": "occurrence weight",
            "normalize_community_weight": True,
            "max_tokens": 4000,  # change this based on the token limit you have on your model (if you are using a model with 8k limit, a good setting could be 5000)
            "context_name": "Reports",
        }

        map_llm_params = {
            "max_tokens": 1000,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

        reduce_llm_params = {
            "max_tokens": 2000,  # change this based on the token limit you have on your model (if you are using a model with 8k limit, a good setting could be 1000-1500)
            "temperature": temperature,
        }

        search_engine = GlobalSearch(
            llm=llm,
            context_builder=context_builder,
            token_encoder=token_encoder,
            max_data_tokens=5000,  # change this based on the token limit you have on your model (if you are using a model with 8k limit, a good setting could be 5000)
            map_llm_params=map_llm_params,
            reduce_llm_params=reduce_llm_params,
            allow_general_knowledge=False,  # set this to True will add instruction to encourage the LLM to incorporate general knowledge in the response, which may increase hallucinations, but could be useful in some use cases.
            json_mode=True,  # set this to False if your LLM model does not support JSON mode.
            context_builder_params=context_builder_params,
            concurrent_coroutines=1,
            response_type=response_type,  # free form text describing the response type and format, can be anything, e.g. prioritized list, single paragraph, multiple paragraphs, multiple-page report
        )

        result = await search_engine.asearch(query)
        return result.response

def prepare_local_search(input_dir, community_level=2, temperature=0.5):
    LANCEDB_URI = f"{input_dir}/lancedb"

    COMMUNITY_REPORT_TABLE = "create_final_community_reports"
    ENTITY_TABLE = "create_final_nodes"
    ENTITY_EMBEDDING_TABLE = "create_final_entities"
    RELATIONSHIP_TABLE = "create_final_relationships"
    COVARIATE_TABLE = "create_final_covariates"
    TEXT_UNIT_TABLE = "create_final_text_units"

    entity_df = pd.read_parquet(join(input_dir, f"{ENTITY_TABLE}.parquet"))
    entity_embedding_df = pd.read_parquet(join(input_dir, f"{ENTITY_EMBEDDING_TABLE}.parquet"))

    entities = read_indexer_entities(entity_df, entity_embedding_df, community_level)

    # load description embeddings to an in-memory lancedb vectorstore
    # to connect to a remote db, specify url and port values.
    description_embedding_store = LanceDBVectorStore(
        collection_name="entity_description_embeddings",
    )
    description_embedding_store.connect(db_uri=LANCEDB_URI)
    entity_description_embeddings = store_entity_semantic_embeddings(
        entities=entities, vectorstore=description_embedding_store
    )

    relationship_df = pd.read_parquet(join(input_dir, f"{RELATIONSHIP_TABLE}.parquet"))
    relationships = read_indexer_relationships(relationship_df)

    # covariate_df = pd.read_parquet(join(input_dir, f"{COVARIATE_TABLE}.parquet"))
    # claims = read_indexer_covariates(covariate_df)
    # covariates = {"claims": claims}

    report_df = pd.read_parquet(join(input_dir, f"{COMMUNITY_REPORT_TABLE}.parquet"))
    reports = read_indexer_reports(report_df, entity_df, community_level)

    text_unit_df = pd.read_parquet(join(input_dir, f"{TEXT_UNIT_TABLE}.parquet"))
    text_units = read_indexer_text_units(text_unit_df)

    api_key = os.environ["GRAPHRAG_API_KEY"]
    llm_model = os.environ["GRAPHRAG_LLM_MODEL"]
    embedding_model = os.environ["GRAPHRAG_EMBEDDING_MODEL"]
    api_llm_base = os.environ["GRAPHRAG_LLM_API_BASE"]
    api_embedding_base = os.environ["GRAPHRAG_EMBEDDING_API_BASE"]

    llm = ChatOpenAI(
        api_key=api_key,
        api_base=api_llm_base,
        model=llm_model,
        api_type=OpenaiApiType.OpenAI,  
        max_retries=10,
    )

    token_encoder = tiktoken.get_encoding("cl100k_base")

    text_embedder = OpenAIEmbedding(
        api_key=api_key,
        api_base=api_embedding_base,
        api_type=OpenaiApiType.OpenAI,
        model=embedding_model,
        deployment_name=embedding_model,
        max_retries=10,
    )

    context_builder = LocalSearchMixedContext(
        community_reports=reports,
        text_units=text_units,
        entities=entities,
        relationships=relationships,
        entity_text_embeddings=description_embedding_store,
        embedding_vectorstore_key=EntityVectorStoreKey.ID,  # if the vectorstore uses entity title as ids, set this to EntityVectorStoreKey.TITLE
        text_embedder=text_embedder,
        token_encoder=token_encoder,
    )

    local_context_params = {
        "text_unit_prop": 0.5,
        "community_prop": 0.1,
        "conversation_history_max_turns": 5,
        "conversation_history_user_turns_only": True,
        "top_k_mapped_entities": 10,
        "top_k_relationships": 10,
        "include_entity_rank": True,
        "include_relationship_weight": True,
        "include_community_rank": False,
        "return_candidate_context": False,
        "embedding_vectorstore_key": EntityVectorStoreKey.ID,  # set this to EntityVectorStoreKey.TITLE if the vectorstore uses entity title as ids
        "max_tokens": 5000,  # change this based on the token limit you have on your model (if you are using a model with 8k limit, a good setting could be 5000)
    }

    llm_params = {
        "max_tokens": 1500,  # change this based on the token limit you have on your model (if you are using a model with 8k limit, a good setting could be 1000=1500)
        "temperature": temperature,
    }

    return llm, context_builder, token_encoder, llm_params, local_context_params

async def local_search(query, input_dir, community_level=2, temperature=0.5, response_type="Multiple Paragraphs"):
    (
        llm, 
        context_builder, 
        token_encoder, 
        llm_params, 
        local_context_params
    ) = prepare_local_search(input_dir, community_level, temperature)

    search_engine = LocalSearch(
        llm=llm,
        context_builder=context_builder,
        token_encoder=token_encoder,
        llm_params=llm_params,
        context_builder_params=local_context_params,
        response_type=response_type,  # free form text describing the response type and format, can be anything, e.g. prioritized list, single paragraph, multiple paragraphs, multiple-page report
    )

    result = await search_engine.asearch(query)
    return result.response

async def local_question_generate(question_history, input_dir, community_level=2, temperature=0.5):
    (
        llm, 
        context_builder, 
        token_encoder, 
        llm_params, 
        local_context_params
    ) = prepare_local_search(input_dir, community_level, temperature)

    question_generator = LocalQuestionGen(
        llm=llm,
        context_builder=context_builder,
        token_encoder=token_encoder,
        llm_params=llm_params,
        context_builder_params=local_context_params,
    )

    result = await question_generator.agenerate(
        question_history=question_history, context_data=None, question_count=5
    )
    return result.response


async def chat_graphrag(
        query, 
        history,
        selected_folder,
        query_type,
        temperature,
        preset
    ):
    output_dir = join("output", selected_folder)
    input_dir = join(output_dir, "artifacts")

    community_level = PRESET_MAPPING[preset]["community_level"]
    response_type = PRESET_MAPPING[preset]["response_type"]

    response = None
    if query == "/generate":
        question_history = list(map(lambda x: x[0], history))
        # the first question is None
        if question_history and len(question_history) <= 1:
            question_history = []
        else: 
            question_history = question_history[1:]
        response = await local_question_generate(
            question_history, input_dir, community_level, temperature
        )
    elif query_type == "global":
        response = await global_search(
            query, input_dir, community_level, temperature, response_type
        )
    elif query_type == "local":
        response = await local_search(
            query, input_dir, community_level, temperature, response_type
        )
    else:
        response = "Sorry, I can't do a search for you right now"

    print(response)
    history.append((query, response))
    return "", history

def list_output_folders(root_dir):
    output_dir = join(root_dir, "output")
    folders = [f for f in os.listdir(output_dir) if os.path.isdir(join(output_dir, f)) and f[0].isdigit()]
    return sorted(folders, reverse=True)

def create_gradio_interface():
    custom_css = """
    .contain { display: flex; flex-direction: column; }

    #component-0 { height: 100%; }

    #main-container { display: flex; height: 100%; }

    #right-column { height: calc(100vh - 100px); }

    #chatbot { flex-grow: 1; overflow: auto; }

    """
    with gr.Blocks(css=custom_css, theme=gr.themes.Base()) as demo:
        with gr.Row(elem_id="main-container"):
            with gr.Column(scale=1, elem_id="left-column"):
                output_folders = list_output_folders(".")
                output_folder = output_folders[0] if output_folders else ""
                selected_folder = gr.Dropdown(
                    label="Select Output Folder",
                    choices=output_folders,
                    value=output_folder,
                    interactive=True
                )

                query_type = gr.Radio(
                    ["global", "local"],
                    label="Query Type",
                    value="global",
                    info="Global: community-based search, Local: entity-based search"
                )

                temperature = gr.Slider(
                    label="Temperature",
                    minimum=0.0,
                    maximum=2.0,
                    step=0.1,
                    value=float(0.5)
                )

                preset = gr.Radio(
                    ["Default", "Detailed", "Quick", "Bullet", "Comprehensive", "High-Level", "Focused"],
                    label="Preset",
                    value="Default",
                    info="How specified is the query result"
                )

            with gr.Column(scale=2, elem_id="right-column"):
                chatbot = gr.Chatbot(
                    label="Chat History", 
                    elem_id="chatbot",
                    value=[(None,"Feel free to ask me anything about the book, or use \"/generate\" to generate questions")]
                )
                with gr.Row():
                    query = gr.Textbox(
                        label="Input",
                        placeholder="Enter your query here...",
                        elem_id="query-input",
                        scale=3
                    )
                    query_btn = gr.Button("Send Query", variant="primary")

        query.submit(
            fn=chat_graphrag, 
            inputs=[
                query, 
                chatbot,
                selected_folder,
                query_type,
                temperature,
                preset
            ], 
            outputs=[query, chatbot]
        )
        query_btn.click(
            fn=chat_graphrag, 
            inputs=[
                query, 
                chatbot,
                selected_folder,
                query_type,
                temperature,
                preset
            ], 
            outputs=[query, chatbot]
        )

    return demo.queue()


demo = create_gradio_interface()
app = demo.app

if __name__ == "__main__":
    demo.launch(server_port=7860, share=True)