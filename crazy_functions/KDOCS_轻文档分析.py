#! .\venv\
# encoding: utf-8
# @Time   : 2023/6/15
# @Author : Spike
# @Descr   :
import func_box
from crazy_functions import crazy_box
from toolbox import update_ui, trimmed_format_exc
from toolbox import CatchException, report_execption, write_results_to_file, zip_folder


@CatchException
def Kdocs_轻文档批量操作(link, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, web_port):
    link = str(link).split()
    links = []
    for i in link:
        if i.startswith('http'):
            links.append(i)
    if not links:
        chatbot.append((None, f'输入框空空如也？{link}\n\n'
                              '请在输入框中输入需要解析的轻文档链接，点击插件按钮，链接需要是可访问的，如以下格式，如果有多个文档则用换行或空格隔开'
                             f'\n\n【金山文档】 xxxx https://kdocs.cn/l/xxxxxxxxxx'
                             f'\n\n https://kdocs.cn/l/xxxxxxxxxx'))
        yield from update_ui(chatbot, history)
    docs_file_content = []
    temp_num = 0
    for url in links:
        try:
            temp_num += 1
            chatbot.append([f'爬虫开始工作了！ {url}', None])
            content = crazy_box.get_docs_content(url)
            title = content.split()[0]+f'_{temp_num}'
            docs_file_content.append({title: content})
            yield from update_ui(chatbot, history)
        except:
            chatbot.append([f'啊哦，爬虫歇菜了！ {url}', f'{func_box.html_a_blank(url)} 请检查一下哦，这个链接我们访问不了，是否开启分享？是否设置密码？'])
            yield from update_ui(chatbot, history)
    yield from Kdocs轻文档转Markdown(docs_file_content, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, web_port)


def Kdocs轻文档转Markdown(file_limit, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, web_port):
    import time, os, re
    from crazy_functions import crazy_utils
    from request_llm import bridge_all
    model = llm_kwargs['llm_model']
    max_length = llm_kwargs['max_length']/2  # 考虑到对话+回答会超过tokens,所以/2
    max_length = 500
    get_token_num = bridge_all.model_info[model]['token_cnt']
    temp_dict_limit = {}
    temp_chat_context = ''
    # 分批次+分词
    for job_dict in file_limit:
        for k, v in job_dict.items():
            temp_chat_context += f'{func_box.html_tag_color(k)} 开始分词,分好词才能避免对话超出tokens错误...'
            chatbot[-1] = [chatbot[-1][0], temp_chat_context]
            yield from update_ui(chatbot, history)
            if get_token_num(v) > max_length:
                segments = crazy_utils.breakdown_txt_to_satisfy_token_limit(v, get_token_num, max_length)
                for i in range(len(segments)):
                    temp_dict_limit[k+f'_{i}'] = segments[i]
            else:
                temp_dict_limit[k] = v

    yield from update_ui(chatbot, history)



