# encoding: utf-8
# @Time   : 2024/2/21
# @Author : Spike
# @Descr   :
import os
from typing import List
from langchain.document_loaders.unstructured import UnstructuredFileLoader
from crazy_functions.reader_fns.local_markdown import MdHandler
from common.path_handler import init_path


class ReaderMarkdownEve(UnstructuredFileLoader):

    def _get_elements(self) -> List:
        def md2md(file_path):
            save_path = os.path.dirname(file_path)
            return MdHandler(file_path, save_path).get_content().replace(init_path.base_path, './')

        markdown = md2md(file_path=self.file_path)
        from unstructured.partition.text import partition_text
        return partition_text(text=markdown, **self.unstructured_kwargs)