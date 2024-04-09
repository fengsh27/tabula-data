from typing import Optional
import streamlit as st
from datetime import datetime
import logging
from nanoid import generate
from streamlit_modal import Modal

from extractor.stampers import Stamper
from extractor.article_retriever import ExtendArticleRetriever, ArticleRetriever
from extractor.request_openai import request_to_chatgpt
from extractor.utils import (
    convert_csv_table_to_dataframe,
    convert_html_to_text,
    escape_markdown,
    is_valid_csv_table,
    remove_references,
)
from extractor.html_table_extractor import HtmlTableExtractor
from extractor.prompts_utils import (
    generate_paper_text_prompts,
    generate_tables_prompts,
    generate_question,
    TableExtractionPromptsGenerator,
)
from extractor.request_geminiai import request_to_gemini

logger = logging.getLogger(__name__)

stamper = None
ss = st.session_state

def clear_results(clear_retrieved_table=False):
    ss.main_info = ""
    if clear_retrieved_table:
        ss.main_retrieved_tables=[]
    ss.main_extracted_result = None
    ss.main_token_usage = None

def on_input_change(pmid: Optional[str]=None):
    if pmid is None:
        pmid = ss.get("w-pmid-input")
    pmid = pmid.strip()
    stamper.pmid = pmid
    # initialize
    clear_results(True)
    ss.main_extracted_btn_disabled = True

    # retrieve article
    retriever = ArticleRetriever() # ExtendArticleRetriever() #
    res, html_content, code = retriever.request_article(pmid)
    if not res:
        error_msg = f"Failed to retrieve article. \n {html_content}"
        st.error(error_msg)
        ss.main_retrieved_tables = []
        return
    stamper.output_html(html_content)

    # extract text and tables
    paper_text = convert_html_to_text(html_content)
    paper_text = remove_references(paper_text)
    ss.main_article_text = paper_text
    extractor = HtmlTableExtractor()
    retrieved_tables = extractor.extract_tables(html_content)
    ss.main_retrieved_tables = retrieved_tables
    ss.main_extracted_btn_disabled = False
    tmp_info = (
        'no table found' 
        if len(retrieved_tables) == 0 
        else f'{len(retrieved_tables)} tables found'
    )
    ss.main_info = f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S')} Retrieving completed, {tmp_info}"

def on_extract(pmid: str):
    # initialize
    pmid = pmid.strip()
    stamper.pmid = pmid
    clear_results()

    # prepare prompts including article prmpots and table prompts
    prmpt_generator = TableExtractionPromptsGenerator()
    first_prompots = prmpt_generator.generate_system_prompts()

    include_tables = []
    for ix in range(len(ss.main_retrieved_tables)):
        include_tbl = ss.get(f"w-pmid-tbl-check-{ix}")
        if include_tbl:
            include_tables.append(ss.main_retrieved_tables[ix])
    prompts_list = [{"role": "user", "content": first_prompots}]
    if len(include_tables) > 0:
        prompts_list.append({
            "role": "user",
            "content": generate_tables_prompts(include_tables)
        })
        
    source = ""
    if len(include_tables) > 0:
        source = "tables"
    else:
        st.error("Please select at least one table")
        return
    assert len(prompts_list) > 0
    
    # chat with LLM
    try:
        stamper.output_prompts(prompts_list)
        res, content, usage = request_to_gemini( # request_to_gemini(
            prompts_list,
            generate_question(source),
        )
        stamper.output_result(f"{content}\n\nUsage: {str(usage) if usage is not None else ''}")
        ss.main_extracted_result = content
        ss.main_token_usage = usage
        
        ss.main_info = f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S')} Extracting completed"
    except Exception as e:
        logger.error(e)
        st.error(e)
        return

def on_extract_from_html_table(html_table: str):
    html_table = html_table.strip()
    if len(html_table) == 0:
        return
    clear_results(True)
    stamper.pmid = generate(size=10)
    table_extractor = HtmlTableExtractor()
    tables = table_extractor.extract_tables(html_table)
    if len(tables) == 0:
        tables = [{"caption": "", "footnote": "", "table": html_table, "raw_tag": html_table}]
    prmpt_generator = TableExtractionPromptsGenerator()
    first_prompts = prmpt_generator.generate_system_prompts()
    prompts_list = [{"role": "user", "content": first_prompts}]
    prompts_list.append({
        "role": "user",
        "content": generate_tables_prompts(tables)
    })
    try:
        stamper.output_prompts(prompts_list)
        res, content, usage = request_to_gemini(
            prompts_list,
            generate_question("table")
        )
        stamper.output_result(f"{content}\n\nUsage: {str(usage) if usage is not None else ''}")
        ss.main_extracted_result = content
        ss.main_token_usage = usage
        ss.main_info = f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S')} Extracting completed"
    except Exception as e:
        logger.error(e)
        st.error(e)
        return


def main_tab(stmpr: Stamper):
    ss.setdefault("main_info", "")
    ss.setdefault("main_article_text", "")
    ss.setdefault("main_extracted_result", None)
    ss.setdefault("main_token_usage", None)
    ss.setdefault("main_retrieved_tables", None)
    ss.setdefault("main_extracted_btn_disabled", True)

    modal = Modal(
        "Prompts",
        key="prompts-modal",
        padding=10,
        max_width=1200,
    )
    global stamper
    stamper = stmpr
    st.title("Extract Tabula Data")
    extracted_panel, prompts_panel = st.columns([5, 1])
    with extracted_panel:
        with st.expander("Input PMID/PMCID"):
            the_pmid = st.text_input(
            # the_pmid = st.text_input(
                label="PMID/PMCID",
                placeholder="Enter PMID or PMCID",
                key="w-pmid-input",            
            )
            pmid_retrieve_btn = st.button(
            # retrieve_btn = st.button(
                'Retrieve Article ...',
                key='w-pmid-retrieve',
            )
            pmid_extract_btn = st.button(
                'Extract Data...',
                key='w-pmid-extract',
            )
                
            if the_pmid and pmid_retrieve_btn:
                with st.spinner("Obtaining article ..."):
                    on_input_change(the_pmid)
            if the_pmid and pmid_extract_btn:
                with st.spinner("Extracting data ..."):
                    on_extract(the_pmid)
        with st.expander("Input Html table"):
            html_table_input = st.text_area(
                label="html table",
                height=400
            )
            html_table_extract_btn = st.button(
                "Extract Data ...",
                key="w-html-table-extract",
            )
            if html_table_input and html_table_extract_btn:
                with st.spinner("Extract data ..."):
                    on_extract_from_html_table(html_table_input)              

        open_modal = st.button("View Prompts ...")
            
        if ss.main_info and len(ss.main_info) > 0:
            st.write(ss.main_info)
        if ss.main_extracted_result is not None:
            usage = ss.main_token_usage
            st.header(f"Extracted Result {'' if usage is None else '(token: '+str(usage)+')'}", divider="blue")
            if is_valid_csv_table(ss.main_extracted_result):
                df = convert_csv_table_to_dataframe(ss.main_extracted_result)
                if df is not None:
                    st.dataframe(df)
                else:
                    st.markdown(ss.main_extracted_result)
            else:
                st.markdown(ss.main_extracted_result)
            # st.markdown(ss.main_extracted_result)
            st.divider()
        if (
            ss.main_retrieved_tables is not None and 
            len(ss.main_retrieved_tables) > 0
        ):
            st.subheader("Tables in Article:")
            for ix in range(len(ss.main_retrieved_tables)):
                tbl = ss.main_retrieved_tables[ix]
                st.subheader(f"Table {ix+1}")
                if "caption" in tbl:
                    st.markdown(escape_markdown(tbl["caption"]))
                if "table" in tbl:
                    st.dataframe(tbl["table"])
                if "footnote" in tbl:
                    st.markdown(escape_markdown(tbl["footnote"]))
                if "raw_tag" in tbl:
                    with st.expander("Html Table"):
                        st.write(tbl["raw_tag"])
                st.divider()
    with prompts_panel:
        if not ss.main_extracted_btn_disabled:
            tables = (
                ss.main_retrieved_tables if ss.main_retrieved_tables is not None else []
            )
            for ix in range(len(tables)):
                st.checkbox(
                    f"table {ix+1}",
                    key=f"w-pmid-tbl-check-{ix}"
                )
    
    if open_modal:
        modal.open()
    if modal.is_open():
        generator = TableExtractionPromptsGenerator()
        prmpts = generator.get_prompts_file_content()
        prmpts += "\n\n\n"
        with modal.container():
            st.text(prmpts)
